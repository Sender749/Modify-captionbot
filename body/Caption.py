import asyncio
import re
import os
import sys
import traceback
from typing import Tuple, List, Dict, Optional
from pyrogram import Client, filters, errors, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ChatMemberUpdated
from pyrogram.errors import ChatAdminRequired, RPCError
from pyrogram import enums
from info import *
from Script import script
from body.database import *  

bot_data = {
    "caption_set": {},
    "block_words_set": {},
    "suffix_set": {},
    "prefix_set": {},
    "replace_words_set": {}
}

@Client.on_chat_member_updated()
async def when_added_as_admin(client, chat_member_update):
    try:
        new = chat_member_update.new_chat_member
        chat = chat_member_update.chat
        if not new or not getattr(new, "user", None) or not new.user.is_self:
            return
        owner = getattr(chat_member_update, "from_user", None)
        if not owner:
            print(f"[INFO] Bot added manually to: {chat.title}")
            return
        owner_id = owner.id
        owner_name = owner.first_name
        await add_user_channel(owner_id, chat.id, chat.title or "Unnamed Channel")
        existing = await get_channel_caption(chat.id)
        if not existing:
            await addCap(chat.id, DEF_CAP)
            await set_block_words(chat.id, [])
            await set_prefix(chat.id, "")
            await set_suffix(chat.id, "")
            await set_replace_words(chat.id, "")
            await set_link_remover_status(chat.id, False)

        try:
            await client.send_message(
                owner_id,
                f"✅ Bot added to <b>{chat.title}</b>.\nYou can manage it anytime using /settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Open Settings", callback_data="settings")]
                ])
            )
            print(f"[NEW] Added to {chat.title} by {owner_name} ({owner_id})")
        except Exception as e:
            print(f"[WARN] Could not notify user: {e}")

    except Exception as e:
        print(f"[ERROR] when_added_as_admin: {e}")


# ---------------- Commands ----------------
@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    user_id = int(message.from_user.id)
    await insert_user(user_id)

    bot_me = await client.get_me()
    bot_username = bot_me.username or (BOT_USERNAME if "BOT_USERNAME" in globals() else bot_me.username or "Bot")

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕️ Add me to your channel ➕️", url=f"https://t.me/{bot_username}?startchannel=true")],
            [InlineKeyboardButton("Hᴇʟᴘ", callback_data="help"), InlineKeyboardButton("⚙ Settings", callback_data="settings_cb")],
            [InlineKeyboardButton("🌐 Update", url="https://t.me/Silicon_Bot_Update"),
             InlineKeyboardButton("📜 Support", url="https://t.me/Silicon_Botz")],
        ]
    )

    await message.reply_photo(
        photo=SILICON_PIC,
        caption=f"<b>Hᴇʟʟᴏ {message.from_user.mention}\n\nI am auto caption bot with custom caption.</b>",
        reply_markup=keyboard,
    )

@Client.on_message(filters.private & filters.user(ADMIN) & filters.command(["total_users"]))
async def all_db_users_here(client, message):
    silicon = await message.reply_text("Please Wait....")
    silicon_botz = await total_user()
    await silicon.edit(f"Tᴏᴛᴀʟ Usᴇʀ :- `{silicon_botz}`")


@Client.on_message(filters.private & filters.user(ADMIN) & filters.command(["broadcast"]))
async def broadcast(client, message):
    if (message.reply_to_message):
        silicon = await message.reply_text("Getting all ids from database.. Please wait")
        all_users = await getid()
        tot = await total_user()
        success = failed = deactivated = blocked = 0
        await silicon.edit("ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ...")
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
                pass
            try:
                await silicon.edit(
                    f"<u>ʙʀᴏᴀᴅᴄᴀsᴛ ᴘʀᴏᴄᴇssɪɴɢ</u>\n\n"
                    f"• ᴛᴏᴛᴀʟ ᴜsᴇʀs: {tot}\n• sᴜᴄᴄᴇssғᴜʟ: {success}\n• ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs: {blocked}\n• ᴅᴇʟᴇᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛs: {deactivated}\n• ᴜɴsᴜᴄᴄᴇssғᴜʟ: {failed}"
                )
            except errors.FloodWait as e:
                await asyncio.sleep(e.value)
        await silicon.edit(
            f"<u>ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</u>\n\n"
            f"• ᴛᴏᴛᴀʟ ᴜsᴇʀs: {tot}\n• sᴜᴄᴄᴇssғᴜʟ: {success}\n• ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs: {blocked}\n• ᴅᴇʟᴇᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛs: {deactivated}\n• ᴜɴsᴜᴄᴄᴇssғᴜʟ: {failed}"
        )


@Client.on_message(filters.private & filters.user(ADMIN) & filters.command("restart"))
async def restart_bot(client, message):
    silicon = await client.send_message(
        chat_id=message.chat.id,
        text="**🔄 𝙿𝚁𝙾𝙲𝙴𝚂𝚂𝙴𝚂 𝚂𝚃𝙾𝙿𝙿ᴇᴅ. 𝙱𝙾𝚃 𝙸𝚂 𝚁𝙴𝚂𝚃𝙰𝚁𝚃𝙸𝙽𝙶...**",
    )
    await asyncio.sleep(3)
    await silicon.edit("**✅️ 𝙱𝙾𝚃 𝙸𝚂 𝚁𝙴𝚂𝚃𝙰𝚁𝚃𝙴𝙳. 𝙽𝙾𝚆 𝚈𝙾𝚄 𝙲𝙰𝙽 𝚄𝚂𝙴 𝙼𝙴**")
    os.execl(sys.executable, sys.executable, *sys.argv)


@Client.on_message(filters.command("settings") & filters.private)
async def user_settings(client, message):
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
                try:
                    chat = await client.get_chat(ch_id)
                    ch_title = getattr(chat, "title", ch_title)
                except Exception:
                    pass
                valid_channels.append({"channel_id": ch_id, "channel_title": ch_title})
            else:
                await users.update_one({"_id": user_id}, {"$pull": {"channels": {"channel_id": ch_id}}})
                removed_titles.append(ch_title)

        except (ChatAdminRequired, errors.RPCError) as e:
            print(f"[INFO] Removing inaccessible channel {ch_id}: {e}")
            await users.update_one({"_id": user_id}, {"$pull": {"channels": {"channel_id": ch_id}}})
            removed_titles.append(ch_title)

        except Exception as ex:
            print(f"[WARN] Unexpected error checking channel {ch_id}: {ex}")
            valid_channels.append({"channel_id": ch_id, "channel_title": ch_title})

    if removed_titles:
        removed_text = "• " + "\n• ".join(removed_titles)
        await message.reply_text(f"⚠️ Removed (no admin/access):\n{removed_text}")

    if not valid_channels:
        return await message.reply_text("No active channels where I am admin.")

    buttons = [[InlineKeyboardButton(ch["channel_title"], callback_data=f"chinfo_{ch['channel_id']}")] for ch in valid_channels]
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_msg")])
    await message.reply_text("📋 Your added channels:", reply_markup=InlineKeyboardMarkup(buttons))
    
@Client.on_message(filters.command("reset") & filters.user(ADMIN))
async def reset_db(client, message):
    await message.reply_text("⚠️ This will delete all users, channels, captions, and settings from the database.\nProcessing...")

    await users.delete_many({})
    await chnl_ids.delete_many({})
    await user_channels.delete_many({})

    await message.reply_text("✅ All database records have been deleted successfully!")


# ---------------- Auto Caption core ----------------
@Client.on_message(filters.channel)
async def reCap(client, message):
    chnl_id = message.chat.id
    default_caption = message.caption or ""

    if not message.media:
        return

    file_name = None
    file_size = None
    for file_type in ("video", "audio", "document", "voice"):
        obj = getattr(message, file_type, None)
        if obj:
            file_name = getattr(obj, "file_name", None)
            if not file_name and file_type == "voice":
                file_name = "Voice Message"
            elif not file_name:
                file_name = "File"
            file_name = file_name.replace("_", " ").replace(".", " ")
            file_size = get_size(getattr(obj, "file_size", 0))
            break

    if not file_name:
        return

    cap_doc = await chnl_ids.find_one({"chnl_id": chnl_id}) or {}
    cap_template = cap_doc.get("caption") or DEF_CAP
    link_remover_on = bool(cap_doc.get("link_remover", False))
    blocked_words = cap_doc.get("block_words", []) or []
    suffix = cap_doc.get("suffix", "") or ""
    prefix = cap_doc.get("prefix", "") or ""
    replace_raw = cap_doc.get("replace_words", None)

    language = extract_language(default_caption)
    year = extract_year(default_caption)
    try:
        new_caption = cap_template.format(
            file_name=file_name,
            file_size=file_size,
            default_caption=default_caption,
            language=language,
            year=year
        )
    except Exception as e:
        print("Caption template format error:", e)
        new_caption = (cap_doc.get("caption") or DEF_CAP)

    if replace_raw:
        replace_pairs = parse_replace_pairs(replace_raw)
        if replace_pairs:
            new_caption = apply_replacements(new_caption, replace_pairs)

    if blocked_words:
        new_caption = apply_block_words(new_caption, blocked_words)

    if link_remover_on:
        new_caption = strip_links_and_mentions_keep_text(new_caption)

    if prefix:
        new_caption = f"{prefix}\n\n{new_caption}".strip()
    if suffix:
        new_caption = f"{new_caption}\n\n{suffix}".strip()

    new_caption = re.sub(r'\s+\n', '\n', new_caption).strip()

    try:
        await message.edit_caption(new_caption)
    except errors.FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        print("Caption edit failed:", e)

# ---------------- Helper functions ----------------

def _status_name(member_obj):
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
    if not member_obj:
        return False
    status = getattr(member_obj, "status", "")
    try:
        if hasattr(status, "value"):
            status = str(status.value)
    except Exception:
        status = str(status)
    return str(status).lower() in ("administrator", "creator", "owner")

def get_size(size: int) -> str:
    units = ["Bytes", "KB", "MB", "GB", "TB"]
    i = 0
    while size >= 1024.0 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return "%.2f %s" % (size, units[i])


def extract_language(default_caption: str) -> str:
    pattern = r'\b(Hindi|English|Tamil|Telugu|Malayalam|Kannada|Hin)\b'
    langs = set(re.findall(pattern, default_caption or "", re.IGNORECASE))
    return ", ".join(sorted(langs, key=str.lower)) if langs else "Hindi-English"


def extract_year(default_caption: str) -> Optional[str]:
    match = re.search(r'\b(19\d{2}|20\d{2})\b', default_caption or "")
    return match.group(1) if match else None


URL_RE = re.compile(
    r"(https?://[^\s]+|www\.[^\s]+|t\.me/[^\s/]+(?:/[^\s]+)?)",
    flags=re.IGNORECASE
)

MENTION_RE = re.compile(r'@\w+', flags=re.IGNORECASE)
MD_LINK_RE = re.compile(r'\[([^\]]+)\]\((?:https?:\/\/[^\)]+|tg:\/\/[^\)]+)\)', flags=re.IGNORECASE)
HTML_A_RE = re.compile(r'<a\s+[^>]*href=["\'](?:https?:\/\/|tg:\/)[^"\']+["\'][^>]*>(.*?)</a>', flags=re.IGNORECASE)
TG_USER_LINK_RE = re.compile(r'\[([^\]]+)\]\(tg:\/\/user\?id=\d+\)', flags=re.IGNORECASE)

def strip_links_and_mentions_keep_text(text: str) -> str:
    if not text:
        return text

    text = MD_LINK_RE.sub(r'\1', text)
    text = TG_USER_LINK_RE.sub(r'\1', text)
    text = HTML_A_RE.sub(r'\1', text)
    text = URL_RE.sub("", text)
    text = MENTION_RE.sub("", text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def remove_mentions_only(text: str) -> str:
    if not text:
        return text
    text = MENTION_RE.sub("", text)
    text = TG_USER_LINK_RE.sub("", text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_replace_pairs(replace_raw: str) -> list[tuple[str, str]]:
    pairs = []
    for item in replace_raw.split(","):
        if ":" in item:
            old, new = item.split(":", 1)
            pairs.append((old.strip(), new.strip()))
    return pairs

def apply_replacements(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = re.sub(re.escape(old), new, text, flags=re.IGNORECASE)
    return text

def apply_block_words(text: str, blocked: List[str]) -> str:
    if not blocked or not text:
        return text
    safe_text = text
    for w in blocked:
        if not w:
            continue
        pattern = r'\b' + re.escape(w) + r'\b'
        safe_text = re.sub(pattern, '', safe_text, flags=re.IGNORECASE)
    safe_text = re.sub(r'\s+', ' ', safe_text).strip()
    return safe_text


def parse_replace_pairs(raw):
    if not raw:
        return []
    # Convert list -> string (joined by commas)
    if isinstance(raw, list):
        raw = ','.join(map(str, raw))
    elif not isinstance(raw, str):
        raw = str(raw)
    raw = raw.replace('\n', ',')
    items = [p.strip() for p in raw.split(',') if p.strip()]
    pairs = []
    for item in items:
        parts = item.split(None, 1)
        if len(parts) == 2:
            pairs.append((parts[0], parts[1]))
    return pairs

def parse_replace_words(text: str) -> dict:
    replace_dict = {}
    if not text:
        return replace_dict
    lines = text.strip().split("\n")
    for line in lines:
        if ":" in line:
            old, new = line.split(":", 1)
            replace_dict[old.strip()] = new.strip()
    return replace_dict

def apply_replace_words(text: str, replace_raw: str) -> str:
    """
    Apply replace words to a caption.
    replace_raw format: "old1:new1,old2:new2"
    """
    if not replace_raw:
        return text

    try:
        pairs = [pair.split(":", 1) for pair in replace_raw.split(",") if ":" in pair]
        for old, new in pairs:
            text = text.replace(old, new)
    except Exception:
        pass

    return text


def apply_replacements(text: str, pairs: List[Tuple[str, str]]) -> str:
    if not pairs or not text:
        return text
    new_text = text
    for old, new in pairs:
        if not old:
            continue
        try:
            pattern = re.compile(r'\b' + re.escape(old) + r'\b', flags=re.IGNORECASE)
            new_text = pattern.sub(new, new_text)
            if re.search(re.escape(old), new_text, flags=re.IGNORECASE):
                new_text = re.sub(re.escape(old), new, new_text, flags=re.IGNORECASE)
        except re.error:
            new_text = new_text.replace(old, new)
    new_text = re.sub(r'\s+', ' ', new_text).strip()
    return new_text

# ---------------- Function Handler ----------------
@Client.on_message(filters.private)
async def capture_user_input(client, message):
    user_id = message.from_user.id
    text = (message.text or message.caption or "").strip()
    if not text:
        return

     # --- Caption ---
    if user_id in bot_data.get("caption_set", {}):
        session = bot_data["caption_set"][user_id]
        channel_id = session["channel_id"]
        instr_msg_id = session.get("instr_msg_id")
        await updateCap(channel_id, text)
        bot_data["caption_set"].pop(user_id, None)
        try:
            await client.delete_messages(user_id, [message.id, instr_msg_id])
        except Exception:
            pass
        buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"back_to_captionmenu_{channel_id}")]]
        await client.send_message(user_id,"✅ Caption updated!",reply_markup=InlineKeyboardMarkup(buttons))
        return

    # --- Block words ---
    if user_id in bot_data.get("block_words_set", {}):
        session = bot_data["block_words_set"][user_id]
        channel_id = session["channel_id"]
        instr_msg_id = session.get("instr_msg_id")
        words = [w.strip() for w in re.split(r'[,\n]+', text) if w.strip()]
        if words:
            await set_block_words(channel_id, words)
            buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"back_to_blockwords_{channel_id}")]]
            await client.send_message(user_id,f"✅ Blocked words updated!\n🚫 {', '.join(words)}",reply_markup=InlineKeyboardMarkup(buttons))
        bot_data["block_words_set"].pop(user_id, None)
        try:
            await client.delete_messages(user_id, [message.id, instr_msg_id])
        except Exception:
            pass
        return

    # --- Replace words ---
    if user_id in bot_data.get("replace_words_set", {}):
        session = bot_data["replace_words_set"][user_id]
        channel_id = session["channel_id"]
        instr_msg_id = session.get("instr_msg_id")
        pairs = parse_replace_pairs(text)
        if pairs:
            await set_replace_words(channel_id, pairs)
            formatted_pairs = [f"{old} → {new}" for old, new in pairs]
            buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"back_to_replace_{channel_id}")]]
            await client.send_message(user_id,f"✅ Replace words updated!\n🚫 {', '.join(formatted_pairs)}",reply_markup=InlineKeyboardMarkup(buttons))
        bot_data["replace_words_set"].pop(user_id, None)
        try:
            await client.delete_messages(user_id, [message.id, instr_msg_id])
        except Exception:
            pass
        return

    # --- Prefix / Suffix ---
    if user_id in bot_data.get("prefix_set", {}):
        session = bot_data["prefix_set"][user_id]
        channel_id = session["channel_id"]
        instr_msg_id = session.get("instr_msg_id")
        await set_prefix(channel_id, text)
        bot_data["prefix_set"].pop(user_id, None)
        try:
            await client.delete_messages(user_id, [message.id, instr_msg_id])
        except Exception:
            pass
        buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"back_to_suffixprefix_{channel_id}")]]
        await client.send_message(user_id,"✅ Caption updated!",reply_markup=InlineKeyboardMarkup(buttons))
        return

    if user_id in bot_data.get("suffix_set", {}):
        session = bot_data["suffix_set"][user_id]
        channel_id = session["channel_id"]
        instr_msg_id = session.get("instr_msg_id")
        await set_suffix(channel_id, text)
        bot_data["suffix_set"].pop(user_id, None)
        try:
            await client.delete_messages(user_id, [message.id, instr_msg_id])
        except Exception:
            pass
        buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"back_to_suffixprefix_{channel_id}")]]
        await client.send_message(user_id,"✅ Caption updated!",reply_markup=InlineKeyboardMarkup(buttons))
        return

# ---------------- Back Button Handler ----------------
@Client.on_callback_query(filters.regex(r"^back_to_captionmenu_(-?\d+)$"))
async def back_to_caption_menu(client, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id

    # Clean user caption set state if exists
    if "caption_set" in bot_data and user_id in bot_data["caption_set"]:
        bot_data["caption_set"].pop(user_id, None)

    # Load channel details
    chat = await client.get_chat(channel_id)
    chat_title = getattr(chat, "title", str(channel_id))

    caption_data = await get_channel_caption(channel_id)
    current_caption = caption_data["caption"] if caption_data else None
    caption_display = f"📝 **Current Caption:**\n{current_caption}" if current_caption else "📝 **Current Caption:** None set yet."

    # Buttons same as your menu
    buttons = [
        [InlineKeyboardButton("🆕 Set Caption", callback_data=f"setcapmsg_{channel_id}"),
         InlineKeyboardButton("❌ Delete Caption", callback_data=f"delcap_{channel_id}")],
        [InlineKeyboardButton("🔤 Caption Font", callback_data=f"capfont_{channel_id}")],
        [InlineKeyboardButton("↩ Back", callback_data=f"chinfo_{channel_id}")]
    ]

    await query.message.edit_text(
        f"⚙️ **Channel:** {chat_title}\n{caption_display}\n\nChoose what you want to do 👇",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex(r"^back_to_blockwords_(-?\d+)$"))
async def back_to_blockwords_menu(client, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id

    if "block_words_set" in bot_data and user_id in bot_data["block_words_set"]:
        bot_data["block_words_set"].pop(user_id, None)

    chat = await client.get_chat(channel_id)
    chat_title = getattr(chat, "title", str(channel_id))

    blocked_words = await get_block_words(channel_id)
    words_text = ", ".join(blocked_words) if blocked_words else "None set yet."

    text = (
        f"📛 **Channel:** {chat_title}\n\n"
        f"🚫 **Blocked Words:**\n{words_text}\n\n"
        f"Choose what you want to do 👇"
    )

    buttons = [
        [InlineKeyboardButton("📝 Set Block Words", callback_data=f"addwords_{channel_id}"),
         InlineKeyboardButton("🗑️ Delete Block Words", callback_data=f"delwords_{channel_id}")],
        [InlineKeyboardButton("↩ Back", callback_data=f"chinfo_{channel_id}")]
    ]

    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r"^back_to_replace_(-?\d+)$"))
async def back_to_replace_menu(client, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id

    if "replace_words_set" in bot_data and user_id in bot_data["replace_words_set"]:
        bot_data["replace_words_set"].pop(user_id, None)

    chat = await client.get_chat(channel_id)
    chat_title = getattr(chat, "title", str(channel_id))

    replace_dict = await get_replace_words(channel_id)
    if replace_dict:
        replace_text = "\n".join(f"{old} → {new}" for old, new in replace_dict.items())
    else:
        replace_text = "None set yet."

    text = (
        f"📛 **Channel:** {chat_title}\n\n"
        f"🔤 **Replace Words:**\n{replace_text}\n\n"
        f"Choose what you want to do 👇"
    )

    buttons = [
        [InlineKeyboardButton("📝 Set Replace Words", callback_data=f"addreplace_{channel_id}"),
         InlineKeyboardButton("🗑️ Delete Replace Words", callback_data=f"delreplace_{channel_id}")],
        [InlineKeyboardButton("↩ Back", callback_data=f"chinfo_{channel_id}")]
    ]

    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r"^back_to_suffixprefix_(-?\d+)$"))
async def back_to_suffixprefix_menu(client, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id

    if "suffix_set" in bot_data and user_id in bot_data["suffix_set"]:
        bot_data["suffix_set"].pop(user_id, None)
    if "prefix_set" in bot_data and user_id in bot_data["prefix_set"]:
        bot_data["prefix_set"].pop(user_id, None)

    suffix, prefix = await get_suffix_prefix(channel_id)
    chat = await client.get_chat(channel_id)
    chat_title = getattr(chat, "title", str(channel_id))

    buttons = [
        [InlineKeyboardButton("Set Suffix", callback_data=f"set_suf_{channel_id}"),
         InlineKeyboardButton("Del Suffix", callback_data=f"del_suf_{channel_id}")],
        [InlineKeyboardButton("Set Prefix", callback_data=f"set_pre_{channel_id}"),
         InlineKeyboardButton("Del Prefix", callback_data=f"del_pre_{channel_id}")],
        [InlineKeyboardButton("↩ Back", callback_data=f"chinfo_{channel_id}")]
    ]

    text = (
        f"📌 Channel: {chat_title}\n\n"
        f"Current Suffix: {suffix or 'None'}\n"
        f"Current Prefix: {prefix or 'None'}"
    )

    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
