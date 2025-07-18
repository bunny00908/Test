import re
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode, ChatMemberStatus

# =========== CONFIGURATION ===========
API_ID = 28232616
API_HASH = "82e6373f14a917289086553eefc64afe"
BOT_TOKEN = "7673804034:AAFU7Wh8ejap55mwTiqV-2OwFLldRJ_xp8o"

SOURCE_GROUPS = [-1002854404728]  # Default source group
TARGET_CHANNELS = []  # Default target channels

ADMIN_ID = 5387926427  # Your Telegram user ID
WELCOME_IMAGE = "https://cdn.nekos.life/neko/neko370.jpeg"
# =====================================

logging.basicConfig(level=logging.INFO)
app = Client("cc_scraper_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ========== Helper Functions ==========
def extract_credit_cards(text):
    pattern = r'(\d{13,19})\|(\d{1,2})\|(\d{2,4})\|(\d{3,4})'
    return re.findall(pattern, text or "")

def format_card_message(cc):
    card_number, month, year, cvv = cc
    return f"Card: <code>{card_number}|{month}|{year}|{cvv}</code>\n"

async def delete_after_delay(message, delay=120):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Error deleting message: {e}")

async def is_bot_admin(chat_id):
    try:
        member = await app.get_chat_member(chat_id, "me")
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

async def is_user_admin(chat_id, user_id):
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

# ========== Command Handlers ==========
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{app.me.username}?startgroup=true")],
        [InlineKeyboardButton("🆔 Get Group ID", callback_data="get_group_id")]
    ])
    
    await message.reply_photo(
        photo=WELCOME_IMAGE,
        caption="✅ Welcome to @Test_090bot!\n\nAdd me to your group as an admin to start.\n\nFor any issues, contact: @approvedccm_bot",
        reply_markup=keyboard
    )

@app.on_message(filters.command("id"))
async def get_id_command(client, message: Message):
    if message.chat.type != "private" and not await is_user_admin(message.chat.id, message.from_user.id):
        await message.reply("❌ You need to be admin to use this command!")
        return
    
    chat_id = message.chat.id
    await message.reply(f"👥 Chat ID: <code>{chat_id}</code>", parse_mode=ParseMode.HTML)

@app.on_callback_query(filters.regex("^get_group_id$"))
async def get_group_id_callback(client, callback_query):
    await callback_query.answer()
    await callback_query.message.reply(
        "👥 Please follow these steps:\n"
        "1. Add me to your group\n"
        "2. Make me admin\n"
        "3. Send me the Group ID here\n\n"
        "Use /id in your group to get its ID"
    )

# ========== Admin Commands ==========
@app.on_message(filters.command("addgroup") & filters.user(ADMIN_ID))
async def add_source_group(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /addgroup <group_id>")
        return
    
    try:
        group_id = int(message.command[1])
        if group_id not in SOURCE_GROUPS:
            SOURCE_GROUPS.append(group_id)
            await message.reply(f"✅ Added group: {group_id}")
            
            if not await is_bot_admin(group_id):
                await message.reply(f"⚠️ Warning: I'm not admin in {group_id}")
        else:
            await message.reply(f"ℹ️ Group already exists")
    except ValueError:
        await message.reply("❌ Invalid group ID")

@app.on_message(filters.command("addtarget") & filters.user(ADMIN_ID))
async def add_target_channel(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /addtarget <channel_id>")
        return
    
    try:
        channel_id = int(message.command[1])
        if channel_id not in TARGET_CHANNELS:
            TARGET_CHANNELS.append(channel_id)
            await message.reply(f"✅ Added target channel: {channel_id}")
        else:
            await message.reply(f"ℹ️ Channel already exists")
    except ValueError:
        await message.reply("❌ Invalid channel ID")

# ========== Run the Bot ==========
print("✅ Bot is running. Press Ctrl+C to stop")
app.run()
