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
TARGET_GROUPS = []  # Default target groups (must be groups, not channels)

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

async def is_group(chat_id):
    try:
        chat = await app.get_chat(chat_id)
        return chat.type in ["group", "supergroup"]
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
    # Only respond to commands from admins or private chats
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
        "3. Send me the Group ID here (just paste it in this chat).\n"
        "4. (Optional) Provide the group link for verification.\n\n"
        "To get your Group ID, go to your group and send the /id command, then copy the ID and send it here.\n\n"
        "For any issues, contact: @approvedccm_bot"
    )

# Handle when users send their group ID
@app.on_message(filters.regex(r'^-?\d+$') & filters.private & ~filters.command(["start", "id", "addgroup", "addtarget"]))
async def handle_group_id_submission(client, message: Message):
    group_id = int(message.text)
    
    # Check if this is actually a group
    if not await is_group(group_id):
        await message.reply("❌ The ID you provided is not a valid group. Please provide a group ID.")
        return
    
    # Notify user
    await message.reply("✅ Your group ID has been sent to the admin. Please wait for manual approval.")
    
    # Notify admin
    await app.send_message(
        ADMIN_ID,
        f"📨 New group ID submission:\n\n"
        f"Group ID: <code>{group_id}</code>\n"
        f"Submitted by: {message.from_user.mention}\n"
        f"User ID: <code>{message.from_user.id}</code>\n\n"
        f"To add this as source group, use:\n<code>/addgroup {group_id}</code>\n"
        f"To add as target group, use:\n<code>/addtarget {group_id}</code>",
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
        if not await is_group(group_id):
            await message.reply("❌ This ID is not a valid group. Please provide a group ID.")
            return
            
        if group_id not in SOURCE_GROUPS:
            SOURCE_GROUPS.append(group_id)
            await message.reply(f"✅ Added source group: {group_id}")
            
            # Check if bot is admin in the new group
            if not await is_bot_admin(group_id):
                await message.reply(f"⚠️ Warning: I'm not admin in group {group_id}. I won't be able to process messages.")
            
            # Notify the group
            try:
                await app.send_message(
                    group_id,
                    "👋 This group has been approved as a source group!\n\n"
                    "The bot will now monitor this group for credit cards.\n"
                    "Only group admins can post CCs that will be forwarded."
                )
            except Exception as e:
                logging.error(f"Could not send message to group {group_id}: {e}")
        else:
            await message.reply(f"ℹ️ Group {group_id} is already in the source list.")
    except ValueError:
        await message.reply("❌ Invalid group ID. Please provide a numeric ID.")

@app.on_message(filters.command("addtarget") & filters.user(ADMIN_ID))
async def add_target_group(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /addtarget <group_id>")
        return
    
    try:
        group_id = int(message.command[1])
        if not await is_group(group_id):
            await message.reply("❌ This ID is not a valid group. Please provide a group ID.")
            return
            
        if group_id not in TARGET_GROUPS:
            TARGET_GROUPS.append(group_id)
            await message.reply(f"✅ Added target group: {group_id}")
            
            # Check if bot is admin in the new group
            if not await is_bot_admin(group_id):
                await message.reply(f"⚠️ Warning: I'm not admin in group {group_id}. I won't be able to post messages.")
        else:
            await message.reply(f"ℹ️ Group {group_id} is already in the target list.")
    except ValueError:
        await message.reply("❌ Invalid group ID. Please provide a numeric ID.")

@app.on_message(filters.command("listsources") & filters.user(ADMIN_ID))
async def list_source_groups(client, message: Message):
    groups_info = []
    for group_id in SOURCE_GROUPS:
        try:
            chat = await app.get_chat(group_id)
            groups_info.append(f"{chat.title} (<code>{group_id}</code>)")
        except Exception:
            groups_info.append(f"Unknown Group (<code>{group_id}</code>)")
    
    await message.reply(
        "📋 Source Groups:\n\n" + "\n".join(groups_info),
        parse_mode=ParseMode.HTML
    )

@app.on_message(filters.command("listtargets") & filters.user(ADMIN_ID))
async def list_target_groups(client, message: Message):
    groups_info = []
    for group_id in TARGET_GROUPS:
        try:
            chat = await app.get_chat(group_id)
            groups_info.append(f"{chat.title} (<code>{group_id}</code>)")
        except Exception:
            groups_info.append(f"Unknown Group (<code>{group_id}</code>)")
    
    await message.reply(
        "📋 Target Groups:\n\n" + "\n".join(groups_info),
        parse_mode=ParseMode.HTML
    )

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
            await message.reply(f"ℹ️ Group {group_id} is not in the source list.")
    except ValueError:
        await message.reply("❌ Invalid group ID. Please provide a numeric ID.")

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
            await message.reply(f"ℹ️ Group {group_id} is not in the target list.")
    except ValueError:
        await message.reply("❌ Invalid group ID. Please provide a numeric ID.")

# New admin commands to reply to users by ID
@app.on_message(filters.command("reply") & filters.user(ADMIN_ID))
async def reply_to_user(client, message: Message):
    if len(message.command) < 3:
        await message.reply("Usage: /reply <user_id> <message>")
        return
    
    try:
        user_id = int(message.command[1])
        reply_text = " ".join(message.command[2:])
        
        try:
            await app.send_message(user_id, f"📨 Admin Reply:\n\n{reply_text}")
            await message.reply(f"✅ Message sent to user {user_id}")
        except Exception as e:
            await message.reply(f"❌ Failed to send message to user {user_id}: {str(e)}")
    except ValueError:
        await message.reply("❌ Invalid user ID. Please provide a numeric ID.")

@app.on_message(filters.command("broadcast") & filters.user(ADMIN_ID))
async def broadcast_message(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /broadcast <message>")
        return
    
    broadcast_text = " ".join(message.command[1:])
    total_users = len(SOURCE_GROUPS) + len(TARGET_GROUPS)
    sent_count = 0
    
    processing_msg = await message.reply(f"📢 Broadcasting to {total_users} groups...")
    
    # Send to source groups
    for group_id in SOURCE_GROUPS:
        try:
            await app.send_message(group_id, f"📢 Admin Broadcast:\n\n{broadcast_text}")
            sent_count += 1
        except Exception as e:
            logging.error(f"Error broadcasting to source group {group_id}: {e}")
    
    # Send to target groups
    for group_id in TARGET_GROUPS:
        try:
            await app.send_message(group_id, f"📢 Admin Broadcast:\n\n{broadcast_text}")
            sent_count += 1
        except Exception as e:
            logging.error(f"Error broadcasting to target group {group_id}: {e}")
    
    await processing_msg.edit_text(f"✅ Broadcast completed!\n\nSuccessfully sent to {sent_count}/{total_users} groups.")

# ========== Main CC Scraper ==========
@app.on_message(filters.chat(SOURCE_GROUPS))
async def cc_scraper(client, message: Message):
    # Strict admin check - only process if bot is admin
    if not await is_bot_admin(message.chat.id):
        return  # Silently ignore if not admin
    
    # Also ignore messages from non-admins
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return
    
    # Ignore messages from other bots
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
                sent = await app.send_message(
                    group_id,
                    msg_text,
                    parse_mode=ParseMode.HTML
                )
                asyncio.create_task(delete_after_delay(sent))
            except Exception as e:
                logging.warning(f"Error sending/deleting message in {group_id}: {e}")

# Notify when added to a group
@app.on_message(filters.new_chat_members)
async def new_chat_members(client, message: Message):
    if app.me.id in [user.id for user in message.new_chat_members]:
        # Send welcome message to the group
        await message.reply(
            "👋 Thanks for adding me to this group!\n\n"
            "To start using this bot:\n"
            "1. Make me admin\n"
            "2. Send the group ID to @approvedccm_bot\n"
            "3. Only admins can post CCs that will be forwarded\n\n"
            "Use /id to get this group's ID"
        )
        
        # Notify admin
        await app.send_message(
            ADMIN_ID,
            f"📨 Bot was added to new group:\n\n"
            f"Group ID: <code>{message.chat.id}</code>\n"
            f"Group Title: {message.chat.title}\n\n"
            f"To approve as source group, use: /addgroup {message.chat.id}\n"
            f"To approve as target group, use: /addtarget {message.chat.id}"
        )

# ========== Run the Bot ==========
print("✅ Bot is running. Press Ctrl+C to stop.")
app.run()
