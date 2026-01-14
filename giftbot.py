import os
import requests
import re
import asyncio
from collections import deque
from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel

# ================= GAME BLOCK =================
GAMES = [
    {"number": 1, "name": "91club", "SERVER_URL": "https://hary.click/kelvin/91club/gift.php", "TELEGRAM_CHANNEL": "@sanzi91clubvip"},
    {"number": 2, "name": "okwin", "SERVER_URL": "https://hary.click/game/okwin/gift.php", "TELEGRAM_CHANNEL": "@OKWINUpdates"},
    {"number": 3, "name": "jalwa", "SERVER_URL": "https://hary.click/game/jalwa/gift.php", "TELEGRAM_CHANNEL": "@JalwaGameOfficialUpdates"},
    {"number": 4, "name": "55club", "SERVER_URL": "https://hary.click/kelvin/55club/gift.php", "TELEGRAM_CHANNEL": "https://t.me/moneytrickss55"},
    {"number": 5, "name": "in999", "SERVER_URL": "https://hary.click/kelvin/in999/gift.php", "TELEGRAM_CHANNEL": "https://t.me/SIGMAGIFTCODES"}
]

# ================= ENV CONFIG =================
GAME_NUMBER = int(os.environ.get("GAME_NUMBER", 1))  # default 1
CFG = GAMES[GAME_NUMBER - 1]

TELEGRAM_CHANNEL = os.environ.get("TELEGRAM_CHANNEL", CFG["TELEGRAM_CHANNEL"])
TELEGRAM_API_ID   = int(os.environ.get("TELEGRAM_API_ID", 38774511))
TELEGRAM_API_HASH = os.environ.get("TELEGRAM_API_HASH", "f331bddaf4bb7d47a081df59a8269cd3")
TELEGRAM_PHONE    = os.environ.get("TELEGRAM_PHONE", "+917407705409")
SESSION_NAME      = f"giftblast_{CFG['name']}"

# ============= COLORS =============
PINK  = "\u001B[95m"
RED   = "\u001B[91m"
GREEN = "\u001B[92m"
RESET = "\u001B[0m"

# ===== GLOBALS =====
gift_queue = deque()
processing = False
last_gift_code = None
TARGET_CHANNEL_ID = None
last_message_id   = 0

# ===== TELEGRAM CLIENT =====
client = TelegramClient(SESSION_NAME, TELEGRAM_API_ID, TELEGRAM_API_HASH)

def extract_text_from_msg(msg):
    return (getattr(msg, "message", None) or getattr(msg, "raw_text", None) or "").strip()

def print_server_response(resp_text):
    """Print all server text, but color only Success/Failure words"""
    for line in resp_text.splitlines():
        colored_line = line
        colored_line = re.sub(r"\bSuccess\b", f"{GREEN}Success{RESET}", colored_line)
        colored_line = re.sub(r"\bFailure\b", f"{RED}Failure{RESET}", colored_line)
        print(colored_line)

# ===== WORKER =====
async def worker_process():
    global processing
    if processing:
        return
    processing = True

    while gift_queue:
        code = gift_queue.popleft()
        print(f"{GREEN}Processing queued code: {code}{RESET}")

        try:
            resp = requests.get(CFG["SERVER_URL"], params={"gift": code}, timeout=15)
            server_output = resp.text
        except Exception as e:
            server_output = f"Failure: Error sending code: {e}"

        print_server_response(server_output)

        if gift_queue:
            await asyncio.sleep(2.5)  # gap between codes

    processing = False

# ===== TELEGRAM HANDLER =====
async def process_message(msg):
    global last_gift_code, gift_queue
    text = extract_text_from_msg(msg)
    if not text:
        return

    codes = re.findall(r"\b[A-Z0-9]{32}\b", text)
    if not codes:
        return

    for code in codes:
        if code == last_gift_code:
            continue
        last_gift_code = code
        gift_queue.append(code)

    asyncio.create_task(worker_process())

@client.on(events.NewMessage)
async def handler(event):
    global TARGET_CHANNEL_ID, last_message_id
    msg = event.message
    peer = msg.peer_id

    if not isinstance(peer, PeerChannel):
        return
    if TARGET_CHANNEL_ID and peer.channel_id != TARGET_CHANNEL_ID:
        return
    if msg.id <= last_message_id:
        return

    last_message_id = msg.id
    await process_message(msg)

async def history_poller():
    global last_message_id
    await asyncio.sleep(3)
    while True:
        try:
            msgs = await client.get_messages(TELEGRAM_CHANNEL, limit=5)
            for m in reversed(msgs):
                if isinstance(m.peer_id, PeerChannel) and m.id > last_message_id:
                    last_message_id = m.id
                    await process_message(m)
        except Exception as e:
            print(f"{RED}History poll error: {e}{RESET}")
        await asyncio.sleep(0.7)

async def keep_alive():
    while True:
        try:
            await client.get_me()
        except:
            pass
        await asyncio.sleep(0.10)

# ===== MAIN =====
async def main():
    global TARGET_CHANNEL_ID, last_message_id

    print(f"{PINK}Starting Telegram login...{RESET}")
    await client.start(phone=TELEGRAM_PHONE)
    user = await client.get_me()
    print(f"{GREEN}Logged in as: {user.first_name} ({user.phone}){RESET}")

    chan = await client.get_entity(TELEGRAM_CHANNEL)
    TARGET_CHANNEL_ID = chan.id
    print(f"{GREEN}Connected to channel {TELEGRAM_CHANNEL} (ID={TARGET_CHANNEL_ID}){RESET}")

    msgs = await client.get_messages(TELEGRAM_CHANNEL, limit=1)
    last_message_id = msgs[0].id if msgs else 0

    is_private = TELEGRAM_CHANNEL.startswith("https://t.me/+") or TELEGRAM_CHANNEL.startswith("t.me/+")
    asyncio.create_task(keep_alive())

    if not is_private:
        asyncio.create_task(history_poller())
        print(f"{PINK}Hybrid mode: push + history poll enabled{RESET}")
    else:
        print(f"{PINK}Private channel detected → history poll disabled{RESET}")

    print(f"{GREEN}Session OK ✓{RESET}")
    print(f"{PINK}Listening for new codes in hybrid mode (fast + safe){RESET}")
    print(f"{PINK}Waiting for messages...{RESET}")

    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(main())