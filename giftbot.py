import os
import re
import asyncio
import requests
from collections import deque
from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel

# ================= TELEGRAM CONFIG =================
TELEGRAM_API_ID   = int(os.environ.get("TELEGRAM_API_ID", 38774511))
TELEGRAM_API_HASH = os.environ.get("TELEGRAM_API_HASH", "f331bddaf4bb7d47a081df59a8269cd3")
TELEGRAM_PHONE    = os.environ.get("TELEGRAM_PHONE", "+917407705409")

SESSION_NAME = "giftblast"   # ONE SESSION FOR ALL GAMES

# ================= CHANNEL → SERVER MAP =================
CHANNEL_ROUTER = {
    "sanzi91clubvip": "https://hary.click/kelvin/91club/gift.php",
    "OKWINUpdates": "https://hary.click/game/okwin/gift.php",
    "JalwaGameOfficialUpdates": "https://hary.click/game/jalwa/gift.php",
    "moneytrickss55": "https://hary.click/kelvin/55club/gift.php",
    "SIGMAGIFTCODES": "https://hary.click/kelvin/in999/gift.php",
}

# ================= COLORS =================
GREEN = "\u001B[92m"
RED   = "\u001B[91m"
PINK  = "\u001B[95m"
RESET = "\u001B[0m"

# ================= GLOBALS =================
gift_queue = deque()
processing = False
last_seen = set()

# ================= CLIENT =================
client = TelegramClient(SESSION_NAME, TELEGRAM_API_ID, TELEGRAM_API_HASH)

# ================= HELPERS =================
def extract_codes(text):
    return re.findall(r"\b[A-Z0-9]{32}\b", text or "")

def print_server_response(resp_text):
    for line in resp_text.splitlines():
        line = re.sub(r"\bSuccess\b", f"{GREEN}Success{RESET}", line)
        line = re.sub(r"\bFailure\b", f"{RED}Failure{RESET}", line)
        print(line)

# ================= WORKER =================
async def worker():
    global processing
    if processing:
        return

    processing = True
    while gift_queue:
        code, url = gift_queue.popleft()
        print(f"{GREEN}Sending {code} → {url}{RESET}")
        try:
            r = requests.get(url, params={"gift": code}, timeout=15)
            print_server_response(r.text)
        except Exception as e:
            print(f"{RED}Failure: {e}{RESET}")

        if gift_queue:
            await asyncio.sleep(2.5)

    processing = False

# ================= TELEGRAM HANDLER =================
@client.on(events.NewMessage)
async def handler(event):
    msg = event.message
    peer = msg.peer_id

    if not isinstance(peer, PeerChannel):
        return

    username = event.chat.username
    if not username:
        return

    server_url = CHANNEL_ROUTER.get(username)
    if not server_url:
        return  # channel not mapped

    codes = extract_codes(msg.message)
    if not codes:
        return

    for code in codes:
        key = f"{username}:{code}"
        if key in last_seen:
            continue
        last_seen.add(key)
        gift_queue.append((code, server_url))
        print(f"{PINK}Queued {code} from @{username}{RESET}")

    asyncio.create_task(worker())

# ================= MAIN =================
async def main():
    print(f"{PINK}Starting Telegram client...{RESET}")
    await client.start(phone=TELEGRAM_PHONE)
    me = await client.get_me()
    print(f"{GREEN}Logged in as {me.first_name}{RESET}")
    print(f"{PINK}Listening to channels...{RESET}")
    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(main())