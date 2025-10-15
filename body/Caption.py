import asyncio
import re
import os
import sys
from typing import Tuple, List, Optional
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from info import *
from Script import script
from body.database import *

# Runtime session cache for user input
user_sessions = {}


# ---------------------- ON ADMIN ADDED ----------------------
@Client.on_chat_member_updated()
async def when_added_as_admin(client, update):
    """Handles when the bot is added or promoted as admin in a channel."""
    try:
        new = update.new_chat_member
        if not new.user or not new.user.is_self:
            return

        chat = update.chat
        owner = getattr(update, "from_user", None)
        owner_id = owner.id if owner else None
        owner_name = owner.first_name if owner else "Unknown"

        await add_user_channel(owner_id, chat.id, chat.title or "Unnamed Channel")

        # Initialize default settings if not exist
        existing = await get_channel_caption(chat.id)
        if not existing:
            await addCap(chat.id, DEF_CAP)
            await set_block_words(chat.id, [])
            await set_prefix(chat.id, "")
            await set_suffix(chat.id, "")
            await set_replace_words(chat.id, "")
            await set_link_remover_status(chat.id, False)

        # Notify user
        try:
            await client.send_message(
                owner_id,
                f"✅ Added to <b>{chat.title}</b>.\nManage it anytime from /settings.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Open Settings", callback_data="settings")]])
            )
        except Exception:
            pass

        print(f"[+] Added to {chat.title} by {owner_name} ({owner_id})")

    except Exception as e:
        print(f"[ERROR] when_added_as_admin: {e}")


# ---------------------- START COMMAND ----------------------
@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    user_id = message.from_user.id
    await insert_user(user_id)

    me = await client.get_me()
    bot_username = me.username or BOT_USERNAME

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕️ Add me to your channel ➕️", url=f"https://t.me/{bot_username}?startchannel=true")],
        [InlineKeyboardButton("Hᴇʟᴘ", callback_data="help"),
         InlineKeyboardButton("⚙ Settings", callback_data="settings_cb")],
        [InlineKeyboardButton("🌐 Update", url="https://t.me/Silicon_Bot_Update"),
         InlineKeyboardButton("📜 Support", url="https://t.me/Silicon_Botz")]
    ])

    await message.reply_photo(
        photo=SILICON_PIC,
        caption=f"<b>Hᴇʟʟᴏ {message.from_user.mention}\n\nI’m an auto-caption bot with custom formatting features.</b>",
        reply_markup=keyboard
    )


# ---------------------- CAPTION HANDLER ----------------------
@Client.on_message(filters.channel)
async def recaption_media(client, message):
    """Auto-edits media captions according to user settings."""
    if not message.media:
        return

    ch_id = message.chat.id
    caption = message.caption or ""
    cap_doc = await chnl_ids.find_one({"chnl_id": ch_id}) or {}

    cap_template = cap_doc.get("caption") or DEF_CAP
    prefix = cap_doc.get("prefix") or ""
    suffix = cap_doc.get("suffix") or ""
    blocked = cap_doc.get("block_words", []) or []
    replace_raw = cap_doc.get("replace_words", "")
    link_remover = bool(cap_doc.get("link_remover", False))

    # Extract media name and size
    file_name, file_size = extract_file_data(message)
    language = extract_language(caption)
    year = extract_year(caption)

    try:
        new_cap = cap_template.format(
            file_name=file_name,
            file_size=file_size,
            default_caption=caption,
            language=language,
            year=year
        )
    except Exception as e:
        print("Template format error:", e)
        new_cap = DEF_CAP

    # Apply replacements
    replace_pairs = parse_replace_pairs(replace_raw)
    if replace_pairs:
        new_cap = apply_replacements(new_cap, replace_pairs)

    # Blocked words
    if blocked:
        new_cap = apply_block_words(new_cap, blocked)

    # Remove links & mentions if enabled
    if link_remover:
        new_cap = strip_links_and_mentions_keep_text(new_cap)

    # Add prefix/suffix
    if prefix:
        new_cap = f"{prefix}\n\n{new_cap}"
    if suffix:
        new_cap = f"{new_cap}\n\n{suffix}"

    # Clean spaces
    new_cap = re.sub(r'\s+\n', '\n', new_cap).strip()

    try:
        await message.edit_caption(new_cap)
    except errors.FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        print("Caption edit failed:", e)


# ---------------------- FILE & TEXT HELPERS ----------------------
def extract_file_data(msg):
    for t in ("video", "audio", "document", "voice"):
        obj = getattr(msg, t, None)
        if obj:
            name = getattr(obj, "file_name", None) or ("Voice Message" if t == "voice" else "File")
            size = get_size(getattr(obj, "file_size", 0))
            return name.replace("_", " ").replace(".", " "), size
    return None, None


def get_size(size: int) -> str:
    units = ["Bytes", "KB", "MB", "GB"]
    for u in units:
        if size < 1024.0:
            return f"{size:.2f} {u}"
        size /= 1024.0
    return f"{size:.2f} TB"


def extract_language(caption: str):
    langs = re.findall(r'\b(Hindi|English|Tamil|Telugu|Malayalam|Kannada|Hin)\b', caption, re.I)
    return ", ".join(sorted(set(langs), key=str.lower)) or "Hindi-English"


def extract_year(caption: str):
    m = re.search(r'\b(19\d{2}|20\d{2})\b', caption)
    return m.group(1) if m else None


# ---------------------- TEXT CLEANUP ----------------------
URL_RE = re.compile(r"(https?://\S+|www\.\S+|t\.me/\S+)", re.I)
MENTION_RE = re.compile(r'@\w+', re.I)
MD_LINK = re.compile(r'\[([^\]]+)\]\([^\)]+\)')
HTML_LINK = re.compile(r'<a[^>]+>(.*?)</a>', re.I)


def strip_links_and_mentions_keep_text(text):
    text = MD_LINK.sub(r'\1', text)
    text = HTML_LINK.sub(r'\1', text)
    text = URL_RE.sub("", text)
    text = MENTION_RE.sub("", text)
    return re.sub(r'\s+', ' ', text).strip()


def apply_block_words(text, words):
    for w in words:
        text = re.sub(r'\b' + re.escape(w) + r'\b', '', text, flags=re.I)
    return re.sub(r'\s+', ' ', text).strip()


def parse_replace_pairs(raw):
    if not raw:
        return []
    raw = raw.replace('\n', ',')
    pairs = []
    for item in [i.strip() for i in raw.split(',') if i.strip()]:
        p = item.split(None, 1)
        if len(p) == 2:
            pairs.append((p[0], p[1]))
    return pairs


def apply_replacements(text, pairs):
    for old, new in pairs:
        text = re.sub(re.escape(old), new, text, flags=re.I)
    return text.strip()
