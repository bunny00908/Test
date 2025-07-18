import re
import asyncio
import logging
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

# =========== CONFIGURATION ===========
API_ID = 28232616
API_HASH = "82e6373f14a917289086553eefc64afe"
BOT_TOKEN = "7673804034:AAFU7Wh8ejap55mwTiqV-2OwFLldRJ_xp8o"

SOURCE_GROUPS = [-1002854404728]
TARGET_CHANNELS = []  # Dynamically add via /add_target

ADMIN_ID = 5387926427  # Your Telegram numeric user ID
# =====================================

logging.basicConfig(level=logging.INFO)
app = Client("cc_scraper_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ========== Extract CCs ==========
def extract_credit_cards(text):
    pattern = r'(\d{13,19})\|(\d{1,2})\|(\d{2,4})\|(\d{3,4})'
    return re.findall(pattern, text or "")

def format_card_message(cc):
    card_number, month, year, cvv = cc
    return f"Card: <code>{card_number}|{month}|{year}|{cvv}</code>\n"

# ========== Delete after delay ==========
async def delete_after_delay(message):
    await asyncio.sleep(120)
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Error deleting message: {e}")

# ========== Listen to Source Group ==========
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
                sent = await app.send_message(
                    channel,
                    msg_text,
                    parse_mode=ParseMode.HTML
                )
                asyncio.create_task(delete_after_delay(sent))
            except Exception as e:
                logging.warning(f"Error sending/deleting message in {channel}: {e}")

# ========== /start Command (Private Only) ==========
@app.on_message(filters.private & filters.command("start"))
async def start_command(client, message: Message):
    welcome_text = (
        "✅ Welcome to @Test_090bot!\n"
        "Add me to your group as an admin to start.\n\n"
        "For any issues, contact: @approvedccm_bot"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Group", url="https://t.me/Test_090bot?startgroup=true")],
        [InlineKeyboardButton("📥 Get Group ID", callback_data="get_group_id")]
    ])
    await message.reply_photo(
        photo="https://cdn.nekos.life/neko/neko370.jpeg",
        caption=welcome_text,
        reply_markup=keyboard
    )

# ========== Button Callback ==========
@app.on_callback_query(filters.regex("get_group_id"))
async def get_group_id_cb(client, callback_query):
    await callback_query.message.reply(
        "👥 Please follow these steps:\n"
        "1. Add me to your group.\n"
        "2. Make me an admin.\n"
        "3. Send me the Group ID here (just paste it in this chat).\n"
        "4. (Optional) Provide the channel link for verification.\n\n"
        "To get your Group ID, go to your group and send the /id command, then copy the ID and send it here.\n\n"
        "For any issues, contact: @approvedccm_bot"
    )

# ========== Receive Group ID (Only Plain IDs) ==========
@app.on_message(filters.private)
async def receive_group_id(client, message: Message):
    text = message.text.strip()

    if text.startswith("/") or len(text.split()) > 3:
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

# ========== Admin Commands ==========
@app.on_message(filters.private & filters.command("add_target"))
async def add_target_command(client, message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.reply("❌ Unauthorized")

    args = message.text.split()
    if len(args) != 2:
        return await message.reply("Usage: /add_target <chat_id>")

    try:
        chat_id = int(args[1])
        if chat_id not in TARGET_CHANNELS:
            TARGET_CHANNELS.append(chat_id)
            await message.reply(f"✅ Added <code>{chat_id}</code> to target channels.", parse_mode=ParseMode.HTML)
            await client.send_message(chat_id, "🛡️ This channel has been added to receive CC data.")
        else:
            await message.reply("⚠️ Already in target channels.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@app.on_message(filters.private & filters.command("remove_target"))
async def remove_target_command(client, message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.reply("❌ Unauthorized")

    args = message.text.split()
    if len(args) != 2:
        return await message.reply("Usage: /remove_target <chat_id>")

    try:
        chat_id = int(args[1])
        if chat_id in TARGET_CHANNELS:
            TARGET_CHANNELS.remove(chat_id)
            await message.reply(f"✅ Removed <code>{chat_id}</code> from target channels.", parse_mode=ParseMode.HTML)
        else:
            await message.reply("⚠️ Chat ID not found in target channels.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@app.on_message(filters.private & filters.command("list_chats"))
async def list_chats_command(client, message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.reply("❌ Unauthorized")

    if not TARGET_CHANNELS:
        return await message.reply("📭 No target channels configured.")

    await message.reply("📋 Target Channels:\n" + "\n".join([f"- <code>{cid}</code>" for cid in TARGET_CHANNELS]), parse_mode=ParseMode.HTML)

@app.on_message(filters.private & filters.command("contact"))
async def contact_user(client, message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.reply("❌ Unauthorized")

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.reply("Usage: /contact <user_id> <message>")

    try:
        user_id = int(args[1])
        msg = args[2]
        await client.send_message(user_id, f"📩 Message from Admin:\n{msg}")
        await message.reply("✅ Sent.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

# ========== Run the Bot ==========
print("✅ Bot is running. Press Ctrl+C to stop.")
app.run()
