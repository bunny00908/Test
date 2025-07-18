import re
import asyncio
import logging
import json
import os
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait

# =========== CONFIGURATION ===========
API_ID = 28232616
API_HASH = "82e6373f14a917289086553eefc64afe"
BOT_TOKEN = "7673804034:AAFU7Wh8ejap55mwTiqV-2OwFLldRJ_xp8o"

SOURCE_GROUPS = [-1002854404728]
TARGET_CHANNELS_FILE = "target_channels.json"
TARGET_CHANNELS = []  # Loaded from file
ADMIN_ID = 5387926427  # Your Telegram user ID

# =========== Clean Logging Setup ===========
class SensitiveDataFilter(logging.Filter):
    def filter(self, record):
        # Filter out sensitive data and protocol messages
        msg = record.getMessage()
        if any(x in msg for x in ['types.User', 'access_hash', '".":', 'Message{']):
            return False
        return True

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_clean.log'),
        logging.StreamHandler()
    ]
)

# Apply filters and reduce verbosity
logger = logging.getLogger()
logger.addFilter(SensitiveDataFilter())
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pyrogram.session.session").setLevel(logging.ERROR)
logging.getLogger("pyrogram.connection.connection").setLevel(logging.ERROR)

# =========== Load/Save Target Channels ===========
def load_target_channels():
    global TARGET_CHANNELS
    if os.path.exists(TARGET_CHANNELS_FILE):
        with open(TARGET_CHANNELS_FILE, "r") as f:
            TARGET_CHANNELS = json.load(f)
    else:
        TARGET_CHANNELS = []

def save_target_channels():
    with open(TARGET_CHANNELS_FILE, "w") as f:
        json.dump(TARGET_CHANNELS, f)

load_target_channels()

# =========== Bot Client ===========
app = Client(
    "cc_scraper_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True  # Reduces some internal logging
)

# =========== Helpers ===========
def extract_credit_cards(text):
    pattern = r'(\d{13,19})\|(\d{1,2})\|(\d{2,4})\|(\d{3,4})'
    return re.findall(pattern, text or "")

def format_card_message(cc):
    card_number, month, year, cvv = cc
    return f"Card: <code>{card_number}|{month}|{year}|{cvv}</code>\n"

async def delete_after_delay(message):
    await asyncio.sleep(120)
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Message delete error: {str(e)[:50]}")  # Truncated error

# =========== Message Handlers ===========
@app.on_message(filters.chat(SOURCE_GROUPS))
async def cc_scraper(client, message: Message):
    text = message.text or message.caption
    if not (cards := extract_credit_cards(text)):
        return

    for cc in cards:
        msg_text = format_card_message(cc)
        for channel in TARGET_CHANNELS:
            try:
                sent = await app.send_message(channel, msg_text, parse_mode=ParseMode.HTML)
                asyncio.create_task(delete_after_delay(sent))
            except FloodWait as e:
                await asyncio.sleep(e.value)
                continue
            except Exception as e:
                logging.warning(f"Channel {channel} error: {str(e)[:50]}")

# [Rest of your handlers (start, admin commands etc.) remain the same...]
# =========== Start Bot ===========
async def main():
    await app.start()
    logging.info("Bot started cleanly")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped")
    except Exception as e:
        logging.error(f"Fatal error: {str(e)[:100]}")
    finally:
        asyncio.run(app.stop())
