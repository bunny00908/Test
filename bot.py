import re
import asyncio
import logging
import json
import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode, ChatType
from pyrogram.errors import PeerIdInvalid, ChatAdminRequired

# Configuration
API_ID = 28232616
API_HASH = "82e6373f14a917289086553eefc64afe"
BOT_TOKEN = "7673804034:AAFU7Wh8ejap55mwTiqV-2OwFLldRJ_xp8o"
ADMIN_ID = 5387926427  # Only this user can use admin commands

# Data storage
SOURCE_CHATS = []  # Channels only
TARGET_CHATS = []  # Groups only
SOURCE_CHATS_FILE = "source_chats.json"
TARGET_CHATS_FILE = "target_chats.json"

if os.path.exists(SOURCE_CHATS_FILE):
    with open(SOURCE_CHATS_FILE, "r") as f:
        SOURCE_CHATS = json.load(f)

if os.path.exists(TARGET_CHATS_FILE):
    with open(TARGET_CHATS_FILE, "r") as f:
        TARGET_CHATS = json.load(f)

SUPPORT_USERNAME = "@approvedccm_bot"
WELCOME_IMAGE_URL = "https://cdn.nekos.life/neko/neko370.jpeg"

logging.basicConfig(level=logging.INFO, filename="bot.log", filemode="a")

app = Client("cc_scraper_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def save_source_chats():
    with open(SOURCE_CHATS_FILE, "w") as f:
        json.dump(SOURCE_CHATS, f)

def save_target_chats():
    with open(TARGET_CHATS_FILE, "w") as f:
        json.dump(TARGET_CHATS, f)

def extract_credit_cards(text):
    pattern = r'(\d{13,19})\|(\d{1,2})\|(\d{2,4})\|(\d{3,4})'
    return re.findall(pattern, text or "")

def format_card_message(cc):
    return f"Card: <code>{cc[0]}|{cc[1]}|{cc[2]}|{cc[3]}</code>"

async def delete_after_delay(message):
    await asyncio.sleep(120)
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Error deleting message: {e}")

@app.on_message(filters.command("start") & filters.private)
async def start(client, message: Message):
    user = message.from_user
    instructions = f"""✅ Welcome to @{(await client.get_me()).username}!
Add me to your group as an admin to start.

For any issues, contact: {SUPPORT_USERNAME}"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{(await client.get_me()).username}?startgroup=true")]
    ])

    try:
        await message.reply_photo(
            photo=WELCOME_IMAGE_URL,
            caption=instructions,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    except Exception:
        await message.reply(instructions, reply_markup=keyboard, parse_mode=ParseMode.HTML)

@app.on_message(filters.command("id") & (filters.group | filters.channel))
async def get_id(client, message: Message):
    await message.reply(
        f"🆔 <b>Chat ID:</b> <code>{message.chat.id}</code>",
        parse_mode=ParseMode.HTML
    )

@app.on_message(filters.private & ~filters.user(ADMIN_ID) & ~filters.command())
async def handle_chat_id_submission(client, message: Message):
    if message.forward_from_chat:
        chat = message.forward_from_chat
        if chat.type != ChatType.CHANNEL:
            await message.reply("⚠️ Please forward a message from a channel only.")
            return

        await client.send_message(
            ADMIN_ID,
            f"📩 New Channel Submission:\n👤 From: @{message.from_user.username or message.from_user.id}\n🆔 ID: <code>{chat.id}</code>\n📛 Name: {chat.title}\n\n📊 Source Groups: {SOURCE_CHATS}\n📊 Target Groups: {TARGET_CHATS}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Approve", callback_data=f"approve_{chat.id}"),
                    InlineKeyboardButton("Reject", callback_data=f"reject_{chat.id}")
                ]
            ])
        )
        await message.reply("✅ Submission sent for admin approval. Please wait.")
        return

    try:
        chat_id = int(message.text.strip())
        chat = await client.get_chat(chat_id)

        await client.send_message(
            ADMIN_ID,
            f"📩 New Group Submission:\n👤 From: @{message.from_user.username or message.from_user.id}\n🆔 ID: <code>{chat.id}</code>\n📛 Name: {chat.title}\n\n📊 Source Groups: {SOURCE_CHATS}\n📊 Target Groups: {TARGET_CHATS}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Approve", callback_data=f"approve_{chat.id}"),
                    InlineKeyboardButton("Reject", callback_data=f"reject_{chat.id}")
                ]
            ])
        )
        await message.reply("✅ Group submitted for admin approval. Please wait.")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

@app.on_callback_query(filters.regex(r"^(approve|reject)_(\-?\d+)$"))
async def handle_approval(client, callback_query):
    action, chat_id = callback_query.data.split("_")
    chat_id = int(chat_id)

    if action == "approve":
        if chat_id not in SOURCE_CHATS:
            SOURCE_CHATS.append(chat_id)
            save_source_chats()
        if chat_id not in TARGET_CHATS:
            TARGET_CHATS.append(chat_id)
            save_target_chats()
        await callback_query.answer("✅ Approved.")
        try:
            await client.send_message(chat_id, "✅ Your chat has been approved and added.")
        except: pass
    else:
        await callback_query.answer("❌ Rejected.")
        try:
            await client.send_message(chat_id, f"❌ Your chat was rejected. Contact {SUPPORT_USERNAME} for help.")
        except: pass

@app.on_message(filters.chat(SOURCE_CHATS))
async def scrape_credit_cards(client, message: Message):
    text = message.text or message.caption
    if not text:
        return

    cards = extract_credit_cards(text)
    if not cards:
        return

    for cc in cards:
        msg = format_card_message(cc)
        for target in TARGET_CHATS:
            try:
                chat = await client.get_chat(target)
                if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
                    continue
                sent = await client.send_message(target, msg, parse_mode=ParseMode.HTML)
                asyncio.create_task(delete_after_delay(sent))
            except Exception as e:
                logging.error(f"Error sending to {target}: {e}")

@app.on_message(filters.command("contact") & filters.user(ADMIN_ID))
async def contact_user(client, message: Message):
    if len(message.command) < 3:
        await message.reply("❌ Usage: /contact <user_id> <message>")
        return

    try:
        user_id = int(message.command[1])
        msg_text = " ".join(message.command[2:])
        await client.send_message(user_id, f"📢 Admin Message:\n{msg_text}\n\nFor any issues, contact: {SUPPORT_USERNAME}")
        await message.reply("✅ Message sent!")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

@app.on_message(filters.command("add_source") & filters.user(ADMIN_ID))
async def add_source_chat(client, message: Message):
    try:
        chat_id = int(message.command[1])
        if chat_id not in SOURCE_CHATS:
            SOURCE_CHATS.append(chat_id)
            save_source_chats()
            await message.reply(f"✅ Added {chat_id} to source chats.")
        else:
            await message.reply(f"ℹ️ {chat_id} is already in source chats.")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

@app.on_message(filters.command("add_target") & filters.user(ADMIN_ID))
async def add_target_chat(client, message: Message):
    try:
        chat_id = int(message.command[1])
        if chat_id not in TARGET_CHATS:
            TARGET_CHATS.append(chat_id)
            save_target_chats()
            await message.reply(f"✅ Added {chat_id} to target chats.")
        else:
            await message.reply(f"ℹ️ {chat_id} is already in target chats.")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

@app.on_message(filters.command("list_chats") & filters.user(ADMIN_ID))
async def list_chats(client, message: Message):
    source_list = "\n".join(str(c) for c in SOURCE_CHATS)
    target_list = "\n".join(str(c) for c in TARGET_CHATS)
    await message.reply(f"📋 <b>Sources</b>:\n{source_list or 'None'}\n\n🎯 <b>Targets</b>:\n{target_list or 'None'}", parse_mode=ParseMode.HTML)

@app.on_message(filters.command("remove_source") & filters.user(ADMIN_ID))
async def remove_source_chat(client, message: Message):
    try:
        chat_id = int(message.command[1])
        if chat_id in SOURCE_CHATS:
            SOURCE_CHATS.remove(chat_id)
            save_source_chats()
            await message.reply(f"✅ Removed {chat_id} from sources.")
        else:
            await message.reply(f"ℹ️ Not in source chats.")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

@app.on_message(filters.command("remove_target") & filters.user(ADMIN_ID))
async def remove_target_chat(client, message: Message):
    try:
        chat_id = int(message.command[1])
        if chat_id in TARGET_CHATS:
            TARGET_CHATS.remove(chat_id)
            save_target_chats()
            await message.reply(f"✅ Removed {chat_id} from targets.")
        else:
            await message.reply(f"ℹ️ Not in target chats.")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

print("✅ Bot is running...")
app.run()
