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
ADMIN_ID = 5387926427  # Replace with your actual Telegram user ID

# =========== Logging Setup ===========
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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
app = Client("cc_scraper_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

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
        logging.warning(f"Error deleting message: {e}")

# =========== Listen to Source Group ===========
@app.on_message(filters.chat(SOURCE_GROUPS))
async def cc_scraper(client, message: Message):
    text = message.text or message.caption
    cards = extract_credit_cards(text)
    if not cards:
        return

    for cc in cards:
        msg_text = format_card_message(cc)
        for channel in TARGET_CHANNELS:
            try:
                sent = await app.send_message(channel, msg_text, parse_mode=ParseMode.HTML)
                asyncio.create_task(delete_after_delay(sent))
            except FloodWait as e:
                logging.warning(f"Flood wait for {e.value} seconds in channel {channel}")
                await asyncio.sleep(e.value)
                sent = await app.send_message(channel, msg_text, parse_mode=ParseMode.HTML)
                asyncio.create_task(delete_after_delay(sent))
            except Exception as e:
                logging.warning(f"Error sending/deleting message in {channel}: {e}")

# =========== /start ===========
@app.on_message(filters.private & filters.command("start"))
async def start_command(client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Group", url="https://t.me/Test_090bot?startgroup=true")],
        [InlineKeyboardButton("📥 Get Group ID", callback_data="get_group_id")]
    ])
    try:
        await message.reply_photo(
            photo="https://cdn.nekos.life/neko/neko370.jpeg",
            caption=(
                "✅ Welcome to @Test_090bot!\n"
                "Add me to your group as an admin to start.\n\n"
                "For any issues, contact: @approvedccm_bot"
            ),
            reply_markup=keyboard
        )
    except Exception as e:
        logging.error(f"Error sending /start response: {e}")
        await message.reply("❌ Error displaying start message. Please try again.")

# =========== Get Group ID Button ===========
@app.on_callback_query(filters.regex("get_group_id"))
async def get_group_id_cb(client, callback_query):
    await callback_query.message.reply(
        "👥 Please follow these steps:\n"
        "1. Add me to your group.\n"
        "2. Make me an admin.\n"
        "3. Send me the Group ID here (e.g. -1001234567890)."
    )

# =========== Receive Group ID ===========
@app.on_message(filters.private & ~filters.command(["start", "add_target", "remove_target", "list_chats", "contact"]))
async def receive_group_id(client, message: Message):
    text = message.text.strip()
    if len(text.split()) > 3:
        return

    match = re.fullmatch(r"-100\d{10,}", text)
    if not match:
        return

    group_id = match.group()
    user = message.from_user
    name = user.first_name
    username = f"@{user.username}" if user.username else "No username"
    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    await message.reply(
        f"📩 <b>Chat Submission Received</b>\n\n"
        f"🆔 ID: <code>{group_id}</code>\n"
        f"📛 Name: {name}\n"
        f"🔹 Type: Group\n\n"
        f"⏳ Please wait while we verify your submission...",
        parse_mode=ParseMode.HTML
    )

    await client.send_message(
        ADMIN_ID,
        f"📩 <b>New Group Submission</b>\n"
        f"👤 From: {username}\n"
        f"🕒 Time: {current_time}\n"
        f"🆔 ID: <code>{group_id}</code>\n"
        f"📊 Total Target Channels: {len(TARGET_CHANNELS)}",
        parse_mode=ParseMode.HTML
    )

# =========== Admin Commands ===========
@app.on_message(filters.private & filters.command("add_target"))
async def add_target_command(client, message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.reply("❌ Unauthorized")

    args = message.text.split()
    if len(args) != 2:
        return await message.reply("❗ Usage: /add_target <chat_id>")

    try:
        chat_id = int(args[1])
        if chat_id > 0 and not str(chat_id).startswith("-100"):
            return await message.reply("❌ Use a negative chat ID (e.g., -100...).")
        if chat_id not in TARGET_CHANNELS:
            TARGET_CHANNELS.append(chat_id)
            save_target_channels()
            await message.reply(f"✅ Added <code>{chat_id}</code> to target channels.", parse_mode=ParseMode.HTML)
            try:
                await client.send_message(chat_id, "🛡️ This channel has been added to receive CC data.")
            except Exception as e:
                logging.warning(f"Could not notify {chat_id}: {e}")
        else:
            await message.reply("⚠️ Already in target channels.")
    except ValueError:
        await message.reply("❗ Invalid chat ID. Please provide a numeric value.")
    except Exception as e:
        logging.error(f"Error in /add_target: {e}")
        await message.reply(f"❌ Error: {e}")

@app.on_message(filters.private & filters.command("remove_target"))
async def remove_target_command(client, message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.reply("❌ Unauthorized")
    
    args = message.text.split()
    if len(args) != 2:
        return await message.reply("❗ Usage: /remove_target <chat_id>")

    try:
        chat_id = int(args[1])
        if chat_id in TARGET_CHANNELS:
            TARGET_CHANNELS.remove(chat_id)
            save_target_channels()
            await message.reply(f"✅ Removed <code>{chat_id}</code>.", parse_mode=ParseMode.HTML)
        else:
            await message.reply("⚠️ Chat not found in target channels.")
    except ValueError:
        await message.reply("❗ Invalid chat ID. Please provide a numeric value.")
    except Exception as e:
        logging.error(f"Error in /remove_target: {e}")
        await message.reply(f"❌ Error: {e}")

@app.on_message(filters.private & filters.command("list_chats"))
async def list_chats_command(client, message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.reply("❌ Unauthorized")
    
    if not TARGET_CHANNELS:
        return await message.reply("📭 No target channels.")
    
    await message.reply(
        "📋 Target Channels:\n" + "\n".join([f"<code>{cid}</code>" for cid in TARGET_CHANNELS]),
        parse_mode=ParseMode.HTML
    )

@app.on_message(filters.private & filters.command("contact"))
async def contact_user(client, message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.reply("❌ Unauthorized")
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.reply("❗ Usage: /contact <user_id> <message>")

    try:
        user_id = int(args[1])
        msg = args[2]
        await client.send_message(user_id, f"📩 Message from Admin:\n{msg}")
        await message.reply("✅ Message sent.")
    except ValueError:
        await message.reply("❗ Invalid user ID. Please provide a numeric value.")
    except Exception as e:
        logging.error(f"Error in contact: {e}")
        await message.reply(f"❌ Error: {e}")

# =========== Run Bot ===========
async def main():
    try:
        await app.start()
        print("✅ Bot is running. Press Ctrl+C to stop.")
        await asyncio.Event().wait()
    except Exception as e:
        logging.error(f"Bot failed: {e}")
    finally:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
