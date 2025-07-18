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
TARGET_CHANNELS = {}  # Using set for easier management
ADMIN_ID = 5387926427  # Your Telegram numeric user ID
# =====================================

logging.basicConfig(level=logging.INFO)
app = Client("cc_scraper_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ========== CC Extractor ==========
def extract_credit_cards(text):
    pattern = r'(\d{13,19})\|(\d{1,2})\|(\d{2,4})\|(\d{3,4})'
    return re.findall(pattern, text or "")

def format_card_message(cc):
    card_number, month, year, cvv = cc
    return f"Card: <code>{card_number}|{month}|{year}|{cvv}</code>"

# ========== Delete After Delay ==========
async def delete_after_delay(message):
    await asyncio.sleep(120)
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Error deleting message: {e}")

# ========== /start Command ==========
@app.on_message(filters.private & filters.command("start"))
async def start_handler(client, message: Message):
    welcome_text = (
        "✅ <b>Welcome to @Test_090bot!</b>\n"
        "Add me to your group as an <b>admin</b> to start.\n\n"
        "For any issues, contact: @approvedccm_bot"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Group", url="https://t.me/Test_090bot?startgroup=true")],
        [InlineKeyboardButton("📥 Get Group ID", callback_data="get_group_id")]
    ])
    await message.reply_photo(
        "https://cdn.nekos.life/neko/neko370.jpeg",
        caption=welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=buttons
    )

# ========== "Get Group ID" Button ==========
@app.on_callback_query(filters.regex("get_group_id"))
async def handle_get_group_id(client, callback_query):
    await callback_query.message.reply(
        "👥 <b>Please follow these steps:</b>\n"
        "1. Add me to your group.\n"
        "2. Make me an admin.\n"
        "3. Send me the Group ID here (just paste it in this chat).\n"
        "4. (Optional) Provide the channel link for verification.\n\n"
        "<b>To get your Group ID</b>, go to your group and send the <code>/id</code> command, "
        "then copy the ID and send it here.\n\n"
        "For any issues, contact: @approvedccm_bot",
        parse_mode=ParseMode.HTML
    )

# ========== Group ID Submission ==========
@app.on_message(filters.private & filters.regex(r"-100\d{10,}"))
async def receive_group_id(client, message: Message):
    group_id = message.text.strip()
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

# ========== CC Scraper ==========
@app.on_message(filters.chat(SOURCE_GROUPS))
async def cc_scraper(client, message: Message):
    text = message.text or message.caption
    cards = extract_credit_cards(text)
    if not cards:
        return

    msg_text = "\n".join([format_card_message(cc) for cc in cards])

    for channel in TARGET_CHANNELS:
        try:
            if message.photo:
                sent = await app.send_photo(
                    channel,
                    photo=message.photo.file_id,
                    caption=msg_text,
                    parse_mode=ParseMode.HTML
                )
            elif message.document:
                sent = await app.send_document(
                    channel,
                    document=message.document.file_id,
                    caption=msg_text,
                    parse_mode=ParseMode.HTML
                )
            elif message.video:
                sent = await app.send_video(
                    channel,
                    video=message.video.file_id,
                    caption=msg_text,
                    parse_mode=ParseMode.HTML
                )
            else:
                sent = await app.send_message(
                    channel,
                    msg_text,
                    parse_mode=ParseMode.HTML
                )
            asyncio.create_task(delete_after_delay(sent))
        except Exception as e:
            logging.warning(f"Error sending message to {channel}: {e}")

# ========== Admin Commands ==========
@app.on_message(filters.command(["add_target", "remove_target", "list_chats", "contact", "admin"]) & filters.user(ADMIN_ID))
async def admin_commands(client, message: Message):
    cmd = message.command
    if cmd[0] == "add_target" and len(cmd) > 1:
        try:
            chat_id = int(cmd[1])
            if chat_id not in TARGET_CHANNELS:
                TARGET_CHANNELS.add(chat_id)
                await message.reply(f"✅ Added <code>{chat_id}</code> to target channels.", parse_mode=ParseMode.HTML)

                # Notify the new target channel
                try:
                    await client.send_message(
                        chat_id,
                        "🛡️ This channel has been added to receive CC data."
                    )
                except Exception as notify_err:
                    await message.reply(f"⚠️ Added but could not notify target: {notify_err}")
            else:
                await message.reply("ℹ️ This chat is already in the target list.")
        except Exception as e:
            await message.reply(f"❌ Invalid Chat ID.\nError: {e}")

    elif cmd[0] == "remove_target" and len(cmd) > 1:
        try:
            chat_id = int(cmd[1])
            TARGET_CHANNELS.discard(chat_id)
            await message.reply(f"🗑 Removed <code>{chat_id}</code> from target channels.", parse_mode=ParseMode.HTML)
        except:
            await message.reply("❌ Invalid Chat ID.")

    elif cmd[0] == "list_chats":
        if TARGET_CHANNELS:
            chats = "\n".join([f"- <code>{chat}</code>" for chat in TARGET_CHANNELS])
            await message.reply(f"📋 Target Channels:\n{chats}", parse_mode=ParseMode.HTML)
        else:
            await message.reply("⚠️ No target channels.")

    elif cmd[0] == "contact" and len(cmd) > 2:
        user_id = int(cmd[1])
        text = " ".join(cmd[2:])
        try:
            await client.send_message(user_id, f"📬 Message from Admin:\n\n{text}")
            await message.reply("✅ Message sent to user.")
        except Exception as e:
            await message.reply(f"❌ Failed to send message: {e}")

    elif cmd[0] == "admin":
        await message.reply(
            "🛠 <b>Admin Commands:</b>\n\n"
            "/add_target [chat_id] - Add target chat\n"
            "/remove_target [chat_id] - Remove target chat\n"
            "/list_chats - List all monitored chats\n"
            "/contact [user_id] [message] - Contact user",
            parse_mode=ParseMode.HTML
        )

# ========== Start Bot ==========
print("✅ Bot is running. Press Ctrl+C to stop.")
app.run()
