import re
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

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

# Store pending group additions (group_id: user_id)
pending_groups = {}

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
    pending_groups[group_id] = message.from_user.id
    
    # Notify user
    await message.reply("✅ Your group ID has been sent to the admin. Please wait for verification.")
    
    # Notify admin
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{group_id}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"reject_{group_id}")]
    ])
    
    await app.send_message(
        ADMIN_ID,
        f"📨 New group ID submission:\n\n"
        f"Group ID: <code>{group_id}</code>\n"
        f"Submitted by: {message.from_user.mention}\n"
        f"User ID: <code>{message.from_user.id}</code>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

# Admin approval callback
@app.on_callback_query(filters.regex(r'^(approve|reject)_(-?\d+)$'))
async def handle_admin_approval(client, callback_query):
    action, group_id = callback_query.data.split('_')
    group_id = int(group_id)
    
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("❌ You're not authorized!", show_alert=True)
        return
    
    if group_id not in pending_groups:
        await callback_query.answer("❌ This group ID is no longer pending.", show_alert=True)
        return
    
    user_id = pending_groups[group_id]
    
    if action == "approve":
        if group_id not in SOURCE_GROUPS:
            SOURCE_GROUPS.append(group_id)
        await callback_query.answer("✅ Group approved!")
        await callback_query.message.edit_text(f"✅ Approved group ID: {group_id}")
        
        # Notify user
        try:
            await app.send_message(
                user_id,
                f"🎉 Your group (<code>{group_id}</code>) has been approved by admin!\n\n"
                "The bot will now monitor this group for credit cards.",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logging.error(f"Error notifying user: {e}")
    else:
        await callback_query.answer("❌ Group rejected!")
        await callback_query.message.edit_text(f"❌ Rejected group ID: {group_id}")
        
        # Notify user
        try:
            await app.send_message(
                user_id,
                f"❌ Your group (<code>{group_id}</code>) has been rejected by admin.\n\n"
                "Please contact @approvedccm_bot for more information.",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logging.error(f"Error notifying user: {e}")
    
    del pending_groups[group_id]

# Admin commands
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

# ========== Main CC Scraper ==========
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

# ========== Run the Bot ==========
print("✅ Bot is running. Press Ctrl+C to stop.")
app.run()
