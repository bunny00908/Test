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
async def is_bot_admin(chat_id):
    try:
        member = await app.get_chat_member(chat_id, "me")
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

async def notify_non_admin_group(chat_id):
    try:
        await app.send_message(
            chat_id,
            "⚠️ *Admin Required*\n\n"
            "I need to be made admin with:\n"
            "- Post Messages\n- Delete Messages\n\n"
            "Until then, I won't process any cards.",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logging.error(f"Couldn't send admin warning to {chat_id}: {e}")

# ========== New Chat Handler ==========
@app.on_message(filters.new_chat_members)
async def handle_new_chat(client, message: Message):
    if app.me.id in [user.id for user in message.new_chat_members]:
        if not await is_bot_admin(message.chat.id):
            await notify_non_admin_group(message.chat.id)

# ========== Target Channel Commands ==========
@app.on_message(filters.command("addtarget") & filters.user(ADMIN_ID))
async def add_target(client, message: Message):
    try:
        target_id = int(message.command[1])
        if target_id not in TARGET_CHANNELS:
            TARGET_CHANNELS.append(target_id)
            await message.reply(f"✅ Added target: {target_id}")
        else:
            await message.reply(f"⚠️ {target_id} is already a target")
    except (IndexError, ValueError):
        await message.reply("Usage: /addtarget -10012345678")

@app.on_message(filters.command("deltarget") & filters.user(ADMIN_ID))
async def del_target(client, message: Message):
    try:
        target_id = int(message.command[1])
        if target_id in TARGET_CHANNELS:
            TARGET_CHANNELS.remove(target_id)
            await message.reply(f"✅ Removed target: {target_id}")
        else:
            await message.reply(f"⚠️ {target_id} not in targets")
    except (IndexError, ValueError):
        await message.reply("Usage: /deltarget -10012345678")

@app.on_message(filters.command("listtargets") & filters.user(ADMIN_ID))
async def list_targets(client, message: Message):
    await message.reply(
        "📋 Current Targets:\n" + 
        "\n".join(f"• <code>{tid}</code>" for tid in TARGET_CHANNELS),
        parse_mode=ParseMode.HTML
    )

# ========== CC Processing ==========
@app.on_message(filters.chat(SOURCE_GROUPS))
async def process_cc(client, message: Message):
    if not await is_bot_admin(message.chat.id):
        return  # Silent exit if not admin

    # ... (rest of your CC processing logic)

# ========== Run Bot ==========
app.run()
