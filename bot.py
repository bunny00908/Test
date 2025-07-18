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
    chat_id = message.chat.id
    await message.reply(f"👥 Group ID: <code>{chat_id}</code>", parse_mode=ParseMode.HTML)

@app.on_callback_query(filters.regex("^get_group_id$"))
async def get_group_id_callback(client, callback_query):
    await callback_query.answer()
    await callback_query.message.reply(
        "👥 Please follow these steps:\n"
        "1. Add me to your group.\n"
        "2. Make me an admin.\n"
        "3. Send me the Group ID here (just paste it in this chat).\n"
        "4. (Optional) Provide the channel link for verification.\n\n"
        "To get your Group ID, go to your group and send the /id command, then copy the ID and send it here.\n\n"
        "For any issues, contact: @approvedccm_bot"
    )

# Handle when users send their group ID
@app.on_message(filters.regex(r'^-?\d+$') & filters.private & ~filters.command(["start", "id"]))
async def handle_group_id_submission(client, message: Message):
    group_id = int(message.text)
    
    # Notify user
    await message.reply("✅ Your group ID has been sent to the admin. Please wait for manual approval.")
    
    # Notify admin
    await app.send_message(
        ADMIN_ID,
        f"📨 New group ID submission:\n\n"
        f"Group ID: <code>{group_id}</code>\n"
        f"Submitted by: {message.from_user.mention}\n"
        f"User ID: <code>{message.from_user.id}</code>\n\n"
        f"To add this group, use:\n<code>/addgroup {group_id}</code>",
        parse_mode=ParseMode.HTML
    )

# Admin commands
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
            
            # Notify the group
            try:
                await app.send_message(
                    group_id,
                    "👋 This group has been approved by admin!\n\n"
                    "The bot will now monitor this group for credit cards."
                )
            except Exception as e:
                logging.error(f"Could not send message to group {group_id}: {e}")
        else:
            await message.reply(f"ℹ️ Group {group_id} is already in the source list.")
    except ValueError:
        await message.reply("❌ Invalid group ID. Please provide a numeric ID.")

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

@app.on_message(filters.command("listgroups") & filters.user(ADMIN_ID))
async def list_source_groups(client, message: Message):
    if not SOURCE_GROUPS:
        await message.reply("❌ No source groups configured.")
        return
    
    groups_list = "\n".join([f"• <code>{group_id}</code>" for group_id in SOURCE_GROUPS])
    await message.reply(
        f"📋 Source Groups ({len(SOURCE_GROUPS)}):\n\n{groups_list}",
        parse_mode=ParseMode.HTML
    )

@app.on_message(filters.command("addchannel") & filters.user(ADMIN_ID))
async def add_target_channel(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /addchannel <channel_id>")
        return
    
    try:
        channel_id = int(message.command[1])
        if channel_id not in TARGET_CHANNELS:
            TARGET_CHANNELS.append(channel_id)
            await message.reply(f"✅ Added target channel: {channel_id}")
        else:
            await message.reply(f"ℹ️ Channel {channel_id} is already in the target list.")
    except ValueError:
        await message.reply("❌ Invalid channel ID. Please provide a numeric ID.")

@app.on_message(filters.command("removechannel") & filters.user(ADMIN_ID))
async def remove_target_channel(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /removechannel <channel_id>")
        return
    
    try:
        channel_id = int(message.command[1])
        if channel_id in TARGET_CHANNELS:
            TARGET_CHANNELS.remove(channel_id)
            await message.reply(f"✅ Removed target channel: {channel_id}")
        else:
            await message.reply(f"ℹ️ Channel {channel_id} is not in the target list.")
    except ValueError:
        await message.reply("❌ Invalid channel ID. Please provide a numeric ID.")

@app.on_message(filters.command("listchannels") & filters.user(ADMIN_ID))
async def list_target_channels(client, message: Message):
    if not TARGET_CHANNELS:
        await message.reply("❌ No target channels configured.")
        return
    
    channels_list = "\n".join([f"• <code>{channel_id}</code>" for channel_id in TARGET_CHANNELS])
    await message.reply(
        f"📋 Target Channels ({len(TARGET_CHANNELS)}):\n\n{channels_list}",
        parse_mode=ParseMode.HTML
    )

# Admin reply to user by ID
@app.on_message(filters.command("reply") & filters.user(ADMIN_ID))
async def admin_reply(client, message: Message):
    if len(message.command) < 3:
        await message.reply("Usage: /reply <user_id> <message>")
        return
    
    try:
        user_id = int(message.command[1])
        reply_text = " ".join(message.command[2:])
        
        try:
            await app.send_message(user_id, reply_text)
            await message.reply(f"✅ Message sent to user {user_id}")
        except Exception as e:
            await message.reply(f"❌ Failed to send message to user {user_id}: {e}")
    except ValueError:
        await message.reply("❌ Invalid user ID. Please provide a numeric ID.")

# Admin announcement to all groups
@app.on_message(filters.command("announce") & filters.user(ADMIN_ID))
async def admin_announcement(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /announce <message>")
        return
    
    announcement = " ".join(message.command[1:])
    success = 0
    failed = 0
    
    for group_id in SOURCE_GROUPS:
        try:
            await app.send_message(group_id, f"📢 Admin Announcement:\n\n{announcement}")
            success += 1
        except Exception as e:
            logging.error(f"Failed to send announcement to group {group_id}: {e}")
            failed += 1
    
    await message.reply(
        f"📢 Announcement Results:\n\n"
        f"✅ Success: {success} groups\n"
        f"❌ Failed: {failed} groups"
    )

# ========== Main CC Scraper ==========
@app.on_message(filters.chat(SOURCE_GROUPS))
async def cc_scraper(client, message: Message):
    # Check if bot is admin in the group
    if not await is_bot_admin(message.chat.id):
        return  # Silently ignore if not admin
    
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

# ========== Run the Bot ==========
print("✅ Bot is running. Press Ctrl+C to stop.")
app.run()
