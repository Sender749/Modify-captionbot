import asyncio
import re
import os
import sys
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import enums

from info import *
from Script import script
from body.database import *

bot_data = {}  # Stores temporary user sessions like caption_set, block_words_set, etc.

# ================= Helper functions =================
def _status_name(member_obj):
    """Return string representation of chat member status."""
    status = getattr(member_obj, "status", "")
    try:
        if hasattr(status, "value"):
            return str(status.value).lower()
    except Exception:
        pass
    try:
        return str(status).lower()
    except Exception:
        return ""

def _is_admin_member(member_obj) -> bool:
    """Check if member is admin/creator/owner."""
    name = _status_name(member_obj)
    return any(x in name for x in ["administrator", "creator", "owner"])

def get_size(size: int) -> str:
    """Convert file size to human-readable format."""
    units = ["Bytes", "KB", "MB", "GB", "TB"]
    i = 0
    while size >= 1024.0 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return "%.2f %s" % (size, units[i])

def extract_language(default_caption: str) -> str:
    """Extract language from caption."""
    pattern = r'\b(Hindi|English|Tamil|Telugu|Malayalam|Kannada|Hin)\b'
    langs = set(re.findall(pattern, default_caption or "", re.IGNORECASE))
    return ", ".join(sorted(langs, key=str.lower)) if langs else "Hindi-English"

def extract_year(default_caption: str) -> str:
    """Extract year from caption if present."""
    match = re.search(r'\b(19\d{2}|20\d{2})\b', default_caption or "")
    return match.group(1) if match else None

def remove_links_and_mentions(text: str, remove_on: bool = False) -> str:
    """Remove Telegram links and mentions from text if remove_on is True."""
    if not remove_on:
        return text
    text = re.sub(r'https?://t\.me/\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'\[([^\]]+)\]\((?:https?:\/\/[^\)]+)\)', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ================= Commands =================
@Client.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    """Start command handler."""
    user_id = message.from_user.id
    await insert_user(user_id)

    bot_me = await client.get_me()
    bot_username = bot_me.username or BOT_USERNAME if "BOT_USERNAME" in globals() else (bot_me.username or "Bot")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕️ Add me to your channel ➕️", url=f"https://t.me/{bot_username}?startchannel=true")],
        [InlineKeyboardButton("Hᴇʟᴘ", callback_data="help"),
         InlineKeyboardButton("⚙ Settings", callback_data="settings_cb")],
        [InlineKeyboardButton("🌐 Update", url="https://t.me/Silicon_Bot_Update"),
         InlineKeyboardButton("📜 Support", url="https://t.me/Silicon_Botz")]
    ])

    await message.reply_photo(
        photo=SILICON_PIC,
        caption=f"<b>Hello {message.from_user.mention}\n\nI am an auto caption bot with custom caption features.</b>",
        reply_markup=keyboard
    )

@Client.on_message(filters.private & filters.user(ADMIN) & filters.command("total_users"))
async def total_users_cmd(client, message):
    """Admin command to get total users."""
    msg = await message.reply_text("Please wait...")
    total = await total_user()
    await msg.edit(f"Total Users: `{total}`")

@Client.on_message(filters.private & filters.user(ADMIN) & filters.command("broadcast"))
async def broadcast_cmd(client, message):
    """Admin broadcast command."""
    if not message.reply_to_message:
        return await message.reply_text("Reply to a message to broadcast.")

    msg = await message.reply_text("Getting all user IDs...")
    all_users = await getid()
    tot = await total_user()
    success = failed = deactivated = blocked = 0

    await msg.edit("Broadcasting...")

    for user in all_users:
        try:
            await asyncio.sleep(1)
            await message.reply_to_message.copy(user["_id"])
            success += 1
        except errors.InputUserDeactivated:
            deactivated += 1
            await delete_user(user["_id"])
        except errors.UserIsBlocked:
            blocked += 1
            await delete_user(user["_id"])
        except Exception:
            failed += 1
            await delete_user(user["_id"])
        try:
            await msg.edit(
                f"<u>Broadcasting in progress</u>\n\n"
                f"• Total Users: {tot}\n"
                f"• Success: {success}\n"
                f"• Blocked: {blocked}\n"
                f"• Deactivated: {deactivated}\n"
                f"• Failed: {failed}"
            )
        except errors.FloodWait as e:
            await asyncio.sleep(e.value)

    await msg.edit(
        f"<u>Broadcast completed</u>\n\n"
        f"• Total Users: {tot}\n"
        f"• Success: {success}\n"
        f"• Blocked: {blocked}\n"
        f"• Deactivated: {deactivated}\n"
        f"• Failed: {failed}"
    )

@Client.on_message(filters.private & filters.user(ADMIN) & filters.command("restart"))
async def restart_bot_cmd(client, message):
    """Restart bot command."""
    msg = await client.send_message(message.chat.id, "**Restarting bot...**")
    await asyncio.sleep(2)
    os.execl(sys.executable, sys.executable, *sys.argv)

@Client.on_message(filters.command("settings") & filters.private)
async def user_settings_cmd(client, message):
    """Display user channels and settings."""
    user_id = message.from_user.id
    channels = await get_user_channels(user_id)

    if not channels:
        return await message.reply_text("You haven’t added me to any channels yet!")

    valid_channels = []
    removed_titles = []

    for ch in channels:
        ch_id = ch.get("channel_id")
        ch_title = ch.get("channel_title", str(ch_id))
        try:
            member = await client.get_chat_member(ch_id, "me")
            if _is_admin_member(member):
                valid_channels.append({"channel_id": ch_id, "channel_title": ch_title})
            else:
                await users.update_one({"_id": user_id}, {"$pull": {"channels": {"channel_id": ch_id}}})
                removed_titles.append(ch_title)
        except Exception:
            await users.update_one({"_id": user_id}, {"$pull": {"channels": {"channel_id": ch_id}}})
            removed_titles.append(ch_title)

    if removed_titles:
        removed_text = "• " + "\n• ".join(removed_titles)
        await message.reply_text(f"⚠️ Some channels removed due to lost admin access:\n\n{removed_text}")

    if not valid_channels:
        return await message.reply_text("No active channels found where I am admin.")

    buttons = [[InlineKeyboardButton(ch["channel_title"], callback_data=f"chinfo_{ch['channel_id']}")] for ch in valid_channels]
    await message.reply_text("📋 Your added channels:", reply_markup=InlineKeyboardMarkup(buttons))

# ================= Auto Caption =================
@Client.on_message(filters.channel)
async def auto_caption(client, message):
    """Automatically edit caption for channel messages."""
    chnl_id = message.chat.id
    default_caption = message.caption or ""

    if not message.media:
        return

    for file_type in ("video", "audio", "document", "voice"):
        obj = getattr(message, file_type, None)
        if obj and hasattr(obj, "file_name"):
            file_name = obj.file_name.replace("_", " ").replace(".", " ")
            file_size = get_size(obj.file_size)
            language = extract_language(default_caption)
            year = extract_year(default_caption)

            cap_dets = await get_channel_caption(chnl_id)
            cap = cap_dets["caption"] if cap_dets else DEF_CAP
            link_remover_on = await get_link_remover_status(chnl_id)

            try:
                new_caption = cap.format(
                    file_name=file_name, file_size=file_size,
                    default_caption=default_caption, language=language, year=year
                )
                new_caption = remove_links_and_mentions(new_caption, link_remover_on)
                await message.edit_caption(new_caption)
            except errors.FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception as e:
                print(f"Caption edit failed: {e}")

# ================= Callbacks =================
# start, help, settings_cb, etc callbacks will be added in CallbackQuery.py
# Only channel/channel-admin related functions are kept here for performance
