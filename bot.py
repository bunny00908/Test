import re
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode, ChatMemberStatus

# =========== CONFIGURATION ===========
API_ID = 28232616
API_HASH = "82e6373f14a917289086553eefc64afe"
BOT_TOKEN = "8039426526:AAFSqWU-fRl_gwTPqYLK8yxuS0N9at1hC4s"

SOURCE_GROUPS = [-1002854404728]  # Default source group
TARGET_GROUPS = []  # Default target groups

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
        return
    
    chat_id = message.chat.id
    await message.reply(f"👥 Chat ID: <code>{chat_id}</code>", parse_mode=ParseMode.HTML)

@app.on_callback_query(filters.regex("^get_group_id$"))
async def get_group_id_callback(client, callback_query):
    await callback_query.answer()
    await callback_query.message.reply(
        "👥 Please follow these steps:\n"
        "1. Add me to your group.\n"
        "2. Make me an admin.\n"
        "3. Send me the Group ID here.\n\n"
        "Use /id in your group to get its ID."
    )

# Handle group ID submissions
@app.on_message(filters.regex(r'^-?\d+$') & filters.private & ~filters.command(["start", "id"]))
async def handle_group_id_submission(client, message: Message):
    group_id = int(message.text)
    await message.reply("✅ Your group ID has been sent to the admin for approval.")
    
    await app.send_message(
        ADMIN_ID,
        f"📨 New group ID submission:\n\n"
        f"Group ID: <code>{group_id}</code>\n"
        f"User: {message.from_user.mention}\n"
        f"User ID: <code>{message.from_user.id}</code>\n\n"
        f"To add as source: /addgroup {group_id}\n"
        f"To add as target: /addtarget {group_id}",
        parse_mode=ParseMode.HTML
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
            await message.reply(f"✅ Added source group: {group_id}")
            
            if not await is_bot_admin(group_id):
                await message.reply(f"⚠️ Note: I'm not admin in {group_id}")
        else:
            await message.reply(f"ℹ️ Already in source list: {group_id}")
    except ValueError:
        await message.reply("❌ Invalid ID format.")

@app.on_message(filters.command("addtarget") & filters.user(ADMIN_ID))
async def add_target_group(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /addtarget <group_id>")
        return
    
    try:
        group_id = int(message.command[1])
        if group_id not in TARGET_GROUPS:
            TARGET_GROUPS.append(group_id)
            await message.reply(f"✅ Added target group: {group_id}")
            
            if not await is_bot_admin(group_id):
                await message.reply(f"⚠️ Note: I'm not admin in {group_id}")
        else:
            await message.reply(f"ℹ️ Already in target list: {group_id}")
    except ValueError:
        await message.reply("❌ Invalid ID format.")

@app.on_message(filters.command("listsources") & filters.user(ADMIN_ID))
async def list_source_groups(client, message: Message):
    if not SOURCE_GROUPS:
        await message.reply("No source groups added.")
        return
    
    groups_info = []
    for group_id in SOURCE_GROUPS:
        try:
            chat = await app.get_chat(group_id)
            groups_info.append(f"{chat.title} (<code>{group_id}</code>)")
        except Exception:
            groups_info.append(f"Unknown Group (<code>{group_id}</code>)")
    
    await message.reply("📋 Source Groups:\n\n" + "\n".join(groups_info), parse_mode=ParseMode.HTML)

@app.on_message(filters.command("listtargets") & filters.user(ADMIN_ID))
async def list_target_groups(client, message: Message):
    if not TARGET_GROUPS:
        await message.reply("No target groups added.")
        return
    
    groups_info = []
    for group_id in TARGET_GROUPS:
        try:
            chat = await app.get_chat(group_id)
            groups_info.append(f"{chat.title} (<code>{group_id}</code>)")
        except Exception:
            groups_info.append(f"Unknown Group (<code>{group_id}</code>)")
    
    await message.reply("📋 Target Groups:\n\n" + "\n".join(groups_info), parse_mode=ParseMode.HTML)

@app.on_message(filters.command("removegroup") & filters.user(ADMIN_ID))
async def remove_source_group(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /removegroup <group_id>")
        return
    
    try:
        group_id = int(message.command[1])
        if group_id in SOURCE_GROUPS:
            SOURCE_GROUPS.remove(group_id)
            await message.reply(f"✅ Removed source group: {group_id}")
        else:
            await message.reply(f"ℹ️ Not in source list: {group_id}")
    except ValueError:
        await message.reply("❌ Invalid ID format.")

@app.on_message(filters.command("removetarget") & filters.user(ADMIN_ID))
async def remove_target_group(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /removetarget <group_id>")
        return
    
    try:
        group_id = int(message.command[1])
        if group_id in TARGET_GROUPS:
            TARGET_GROUPS.remove(group_id)
            await message.reply(f"✅ Removed target group: {group_id}")
        else:
            await message.reply(f"ℹ️ Not in target list: {group_id}")
    except ValueError:
        await message.reply("❌ Invalid ID format.")

# ========== Main CC Scraper ==========
@app.on_message(filters.chat(SOURCE_GROUPS))
async def cc_scraper(client, message: Message):
    if not await is_bot_admin(message.chat.id) or not await is_user_admin(message.chat.id, message.from_user.id):
        return
    
    if message.from_user and message.from_user.is_bot:
        return
    
    text = message.text or message.caption
    if not text:
        return
        
    cards = extract_credit_cards(text)
    if not cards:
        return

    for cc in cards:
        msg_text = format_card_message(cc)
        for group_id in TARGET_GROUPS:
            try:
                sent = await app.send_message(group_id, msg_text, parse_mode=ParseMode.HTML)
                asyncio.create_task(delete_after_delay(sent))
            except Exception as e:
                logging.warning(f"Error in {group_id}: {e}")

# ========== New Member Handler ==========
@app.on_message(filters.new_chat_members)
async def new_chat_members(client, message: Message):
    if app.me.id in [user.id for user in message.new_chat_members]:
        await message.reply(
            "👋 Thanks for adding me!\n\n"
            "1. Make me admin\n"
            "2. Send group ID to @approvedccm_bot\n"
            "Use /id to get group ID"
        )
        
        await app.send_message(
            ADMIN_ID,
            f"📨 New group:\n"
            f"ID: <code>{message.chat.id}</code>\n"
            f"Title: {message.chat.title}\n\n"
            f"Add commands:\n"
            f"/addgroup {message.chat.id}\n"
            f"/addtarget {message.chat.id}",
            parse_mode=ParseMode.HTML
        )

# ========== Run the Bot ==========
print("✅ Bot is running...")
app.run()
