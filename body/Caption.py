import sys, time, os, re, asyncio
from typing import Tuple, List, Optional
from pyrogram import Client, filters, errors, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ChatMemberUpdated, CallbackQuery
from pyrogram.errors import ChatAdminRequired, RPCError, FloodWait
from pyrogram.enums import ParseMode
from info import *
from Script import script
from body.database import *  
from body.file_forward import FF_SESSIONS, enqueue_forward_jobs
from collections import deque, defaultdict
MESSAGE_LINK_RE = re.compile(r"(?:https?://)?t\.me/(?:c/\d+|[A-Za-z0-9_]+)/(\d+)")
EDIT_DELAY = 2.0  # seconds (not exceed 1.5)
WORKERS = 3       # make 2 if crash and edit delay 2.2
CHANNEL_CACHE = {}
bot_data = {
    "caption_set": {},
    "block_words_set": {},
    "suffix_set": {},
    "prefix_set": {},
    "replace_words_set": {}
}

def extract_msg_id_from_text(text: str) -> int | None:
    if not text:
        return None
    m = MESSAGE_LINK_RE.search(text)
    if m:
        return int(m.group(1))
    if text.isdigit():
        return int(text)
    return None

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
        owner_name = owner.first_name or "Unknown User"
        await add_user_channel(owner_id, chat.id, chat.title or "Unnamed Channel")
        existing = await get_channel_caption(chat.id)
        if not existing:
            await addCap(chat.id, DEF_CAP)
            await set_block_words(chat.id, "")
            await set_prefix(chat.id, "")
            await set_suffix(chat.id, "")
            await set_replace_words(chat.id, "")
            await set_link_remover_status(chat.id, False)
        try:
            msg = await client.send_message(
                owner_id,
                f"✅ Bot added to <b>{chat.title}</b>.\nYou can manage it anytime using /settings.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Open Settings", callback_data="settings_cb")]
                ])
            )
            print(f"[NEW] Added to {chat.title} by {owner_name} ({owner_id})")
            try:
                if chat.username:
                    channel_link = f"https://t.me/{chat.username}"
                    channel_name_clickable = f"<a href='{channel_link}'>{chat.title}</a>"
                else:
                    channel_name_clickable = f"{chat.title} (Private Channel)"
                log_text = script.NEW_CHANNEL_TXT.format(
                    owner_name=owner_name,
                    owner_id=owner_id,
                    channel_name=channel_name_clickable,
                    channel_id=chat.id
                )
                await client.send_message(LOG_CH, log_text, disable_web_page_preview=True)
            except Exception as e:
                print(f"[WARN] Failed to send log message: {e}")
            asyncio.create_task(auto_delete_message(msg, 60))
        except Exception as e:
            print(f"[WARN] Could not notify user: {e}")
    except Exception as e:
        print(f"[ERROR] when_added_as_admin: {e}")

async def auto_delete_message(msg, delay: int):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except:
        pass

@Client.on_callback_query(filters.regex(r"^settings_cb$"))
async def settings_button_handler(client: Client, query: CallbackQuery):
    await query.answer()

    async def edit_sender(text, **kwargs):
        await query.message.edit_text(text, **kwargs)

    await user_settings(
        client,
        user=query.from_user,
        send_func=edit_sender
    )

@Client.on_callback_query(filters.regex("^help$"))
async def help_callback(client, query: CallbackQuery):
    await query.answer()
    bot_me = await client.get_me()
    bot_username = bot_me.username
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕️ Add me to your channel ➕️", url=f"https://t.me/{bot_username}?startchannel=true")],
        [InlineKeyboardButton("⬅️ Back", callback_data="start")]
    ])
    await query.message.edit_text(
        text=script.HELP_TEXT,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

@Client.on_callback_query(filters.regex("^start$"))
async def back_to_start(client: Client, query: CallbackQuery):
    await query.answer()
    await show_start_ui(
        client,
        chat_id=query.message.chat.id,
        mention=query.from_user.mention,
        edit_message=query.message
    )

async def show_start_ui(
    client: Client,
    *,
    chat_id: int,
    mention: str,
    edit_message=None
):
    bot_me = await client.get_me()
    bot_username = bot_me.username or BOT_USERNAME
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕️ Add me to your channel ➕️", url=f"https://t.me/{bot_username}?startchannel=true")],
            [InlineKeyboardButton("📂Help", callback_data="help"), InlineKeyboardButton("⚙ Settings", callback_data="settings_cb")],
            [InlineKeyboardButton("ℹ️ About", callback_data="about_cb")],
        ]
    )
    text = script.START_TXT.format(mention=mention)
    if edit_message:
        await edit_message.edit_text(
            text=text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    else:
        await client.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

@Client.on_callback_query(filters.regex("^about_cb$"))
async def about_callback(client: Client, query: CallbackQuery):
    await query.answer()
    bot = await client.get_me()
    text = script.ABOUT_TXT.format(
        bot_name=bot.first_name,
        bot_username=bot.username
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Owner", url="https://t.me/Navex_69"),InlineKeyboardButton("⬅️ Back", callback_data="start")]
    ])
    await query.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

# ---------------- Commands ----------------
@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    try:
        user = message.from_user
        user_id = int(user.id)
        user_name = user.first_name or "Unknown User"
        username = user.username
        is_new_user = await insert_user_check_new(user_id)
        await show_start_ui(
            client,
            chat_id=message.chat.id,
            mention=user.mention
        )
        if is_new_user:
            try:
                if username:
                    user_clickable = f"<a href='https://t.me/{username}'>{user_name}</a>"
                else:
                    user_clickable = f"{user_name}"
                log_text = script.NEW_USER_TXT.format(user=user_clickable, user_id=user_id)
                await client.send_message(LOG_CH, log_text, disable_web_page_preview=True)
            except Exception as e:
                print(f"[WARN] Failed to send log message for new user: {e}")
    except Exception as e:
        print(f"[ERROR] in start_cmd: {e}")

@Client.on_message(filters.private & filters.command("file_forward"))
async def ff_start(client, message):
    uid = message.from_user.id
    channels = await get_user_channels(uid)
    if not channels:
        return await message.reply_text("❌ No admin channels found.")
    FF_SESSIONS[uid] = {
        "step": "src",
        "channels": channels,
        "expires": None  
    }
    kb = [[InlineKeyboardButton(ch["channel_title"], callback_data=f"ff_src_{ch['channel_id']}")] for ch in channels]
    kb.append([InlineKeyboardButton("❌ Cancel", callback_data="ff_cancel")])
    await message.reply_text("📤 **Select SOURCE channel**", reply_markup=InlineKeyboardMarkup(kb))
        
@Client.on_message(filters.private & filters.user(ADMIN) & filters.command("admin"))
async def admin_help(client, message):
    text = script.ADMIN_HELP_TEXT.format(
        workers=WORKERS,
        delay=EDIT_DELAY
    )
    await message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

@Client.on_message(filters.private & filters.user(ADMIN) & filters.command("stats"))
async def bot_stats(client, message):
    pending = await queue_col.count_documents({"status": "pending"})
    processing = await queue_col.count_documents({"status": "processing"})
    users_count = await total_user()
    text = (
        "📊 <b>BOT STATS</b>\n\n"
        f"• Users: <code>{users_count}</code>\n"
        f"• Pending Jobs: <code>{pending}</code>\n"
        f"• Processing Jobs: <code>{processing}</code>\n"
        f"• Workers: <code>{WORKERS}</code>\n"
        f"• Edit Delay: <code>{EDIT_DELAY}s</code>\n"
        f"• Mode: Persistent Queue\n"
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML)

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
                await asyncio.sleep(0.2)
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
async def settings_cmd(client, message):
    await user_settings(
        client,
        user=message.from_user,
        send_func=message.reply_text
    )

async def user_settings(client: Client,*,user,send_func,):
    user_id = user.id
    channels = await get_user_channels(user_id)
    if not channels:
        return await send_func("You haven’t added me to any channels yet!")
    valid_channels = []
    removed_titles = []
    async def check_channel(ch):
        ch_id = ch.get("channel_id")
        ch_title = ch.get("channel_title", str(ch_id))
        try:
            member = await client.get_chat_member(ch_id, "me")
            if _is_admin_member(member):
                try:
                    chat = await client.get_chat(ch_id)
                    ch_title = getattr(chat, "title", ch_title)
                except:
                    pass
                return {"valid": True, "channel_id": ch_id, "channel_title": ch_title}
            else:
                await users.update_one({"_id": user_id}, {"$pull": {"channels": {"channel_id": ch_id}}})
                return {"valid": False, "title": ch_title}
        except (ChatAdminRequired, errors.RPCError):
            await users.update_one({"_id": user_id}, {"$pull": {"channels": {"channel_id": ch_id}}})
            return {"valid": False, "title": ch_title}
        except Exception:
            return {"valid": True, "channel_id": ch_id, "channel_title": ch_title}
    results = await asyncio.gather(*[check_channel(ch) for ch in channels])
    for res in results:
        if res["valid"]:
            valid_channels.append(res)
        else:
            removed_titles.append(res["title"])
    if removed_titles:
        removed_text = "• " + "\n• ".join(removed_titles)
        await send_func(f"⚠️ Removed (no admin/access):\n{removed_text}")
    if not valid_channels:
        return await send_func("No active channels where I am admin.")
    buttons = [[InlineKeyboardButton(ch["channel_title"], callback_data=f"chinfo_{ch['channel_id']}")] for ch in valid_channels]
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_msg")])
    await send_func("📋 Your added channels:", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^close_msg$"))
async def close_message(client, query):
    await query.answer()
    try:
        await query.message.delete()
    except:
        pass
    
@Client.on_message(filters.command("reset") & filters.user(ADMIN))
async def reset_db(client, message):
    await message.reply_text("⚠️ This will delete all users, channels, captions, and settings from the database.\nProcessing...")

    await users.delete_many({})
    await chnl_ids.delete_many({})
    await user_channels.delete_many({})
    CHANNEL_CACHE.clear()

    await message.reply_text("✅ All database records have been deleted successfully!")

@Client.on_message(filters.private & filters.user(ADMIN) & filters.command("queue"))
async def queue_status(client, message):
    total = await queue_col.count_documents({"status": "pending"})
    processing = await queue_col.count_documents({"status": "processing"})
    pipeline = [
        {"$match": {"status": "pending"}},
        {"$group": {"_id": "$chat_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    per_channel = []
    async for row in queue_col.aggregate(pipeline):
        ch_id = row["_id"]
        count = row["count"]
        try:
            chat = await client.get_chat(ch_id)
            name = chat.title
        except:
            name = "Unknown"
        eta_sec = int(count * EDIT_DELAY / WORKERS)
        per_channel.append(
            f"• <b>{name}</b>\n"
            f"  ├ ID: <code>{ch_id}</code>\n"
            f"  ├ Jobs: <code>{count}</code>\n"
            f"  └ ETA: ~{eta_sec//60}m {eta_sec%60}s"
        )
    eta_total = int(total * EDIT_DELAY / WORKERS)
    text = (
        "📥 <b>Caption Queue Status</b>\n\n"
        f"• Pending: <code>{total}</code>\n"
        f"• Processing: <code>{processing}</code>\n"
        f"• Workers: <code>{WORKERS}</code>\n"
        f"• Edit delay: <code>{EDIT_DELAY}s</code>\n"
        f"• Global ETA: ~{eta_total//60}m {eta_total%60}s\n\n"
    )
    if per_channel:
        text += "🔥 <b>Top Busy Channels</b>\n" + "\n".join(per_channel)
    else:
        text += "✅ Queue empty."
    await message.reply_text(text, parse_mode=ParseMode.HTML)

# ---------------- Auto Caption core ----------------
def sanitize_caption_html(text: str) -> str:
    if not text:
        return ""
    allowed_tags = {"b", "i", "u", "s", "code", "pre", "a", "spoiler", "blockquote"}
    def repl(match):
        tag = match.group(1).casefold()
        return match.group(0) if tag in allowed_tags else ""
    return re.sub(r"</?\s*([a-zA-Z0-9]+)(?:\s[^>]*)?>", repl, text)

async def caption_worker(client: Client):
    print("[QUEUE] Persistent worker started")
    while True:
        job = await fetch_next_job()
        if not job:
            await asyncio.sleep(1)
            continue
        try:
            await client.edit_message_caption(
                chat_id=job["chat_id"],
                message_id=job["message_id"],
                caption=job["caption"],
                parse_mode=ParseMode.HTML
            )
            await mark_done(job["_id"])
            await asyncio.sleep(EDIT_DELAY)
        except FloodWait as e:
            await reschedule(job["_id"], delay=e.value + 2)
            await asyncio.sleep(e.value)
        except errors.MessageNotModified:
            await mark_done(job["_id"])
        except Exception as e:
            if job["retries"] >= 5:
                print(f"[DROP] job failed permanently: {job['_id']}")
                await mark_done(job["_id"])
            else:
                await reschedule(job["_id"], delay=10)

@Client.on_message(filters.channel & filters.media)
async def reCap(client, msg):
    if msg.edit_date or not msg.media:
        return
    chnl_id = msg.chat.id
    default_caption = msg.caption or ""
    file_name = None
    file_size = None
    for file_type in ("video", "audio", "document", "voice"):
        obj = getattr(msg, file_type, None)
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
    # Fetch channel settings
    cap_doc = await get_channel_cached(chnl_id)
    cap_template = cap_doc.get("caption") or "{file_name} ({file_size})"
    link_remover_on = bool(cap_doc.get("link_remover", False))
    blocked_words_raw = cap_doc.get("block_words", "")
    suffix = cap_doc.get("suffix", "") or ""
    prefix = cap_doc.get("prefix", "") or ""
    replace_raw = cap_doc.get("replace_words", None)
    # Extract info from caption
    language = extract_language(default_caption)
    year = extract_year(default_caption)
    # Build caption
    try:
        raw_file_name = normalize_series_name(file_name)
        smart_file_name = ""
        if "{smart_file_name}" in cap_template:
            smart_file_name = build_smart_filename(
                base_name=raw_file_name,
                default_caption=default_caption,
                year=year,
                language=language
            )
        new_caption = cap_template.format(
            file_name=raw_file_name,
            smart_file_name=smart_file_name,
            file_size=file_size,
            default_caption=default_caption,
            language=language or "",
            year=year or ""
        )
    except Exception as e:
        print(f"[ERROR] Caption format error: {e}")
        new_caption = cap_template
    if blocked_words_raw:
        new_caption = apply_block_words(new_caption, blocked_words_raw)
    if replace_raw:
        replace_pairs = parse_replace_pairs(replace_raw)
        if replace_pairs:
            new_caption = apply_replacements(new_caption, replace_pairs)
    if link_remover_on:
        new_caption = strip_links_only(new_caption)
    if prefix:
        new_caption = f"{prefix}\n{new_caption}".strip()
    if suffix:
        new_caption = f"{new_caption}\n{suffix}".strip()
    if language and contains_language(raw_file_name, language):
        language = ""
    new_caption = new_caption.strip()
    if "<" in new_caption and ">" in new_caption:
        new_caption = sanitize_caption_html(new_caption)
    await enqueue_caption({
        "chat_id": msg.chat.id,
        "message_id": msg.id,
        "caption": new_caption
    })



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

def contains_language(base_name: str, lang: str) -> bool:
    if not base_name or not lang:
        return False
    base = normalize(base_name)
    for l in lang.split():
        if normalize(l) in base:
            return True
    return False

def extract_language(default_caption: str) -> str:
    if not default_caption:
        return ""
    languages = [
        "Hindi", "English", "Tamil", "Telugu", "Malayalam", "Kannada",
        "Marathi", "Gujarati", "Bengali", "Punjabi", "Urdu",
        "French", "German", "Spanish", "Italian", "Russian",
        "Japanese", "Korean", "Chinese"
    ]
    found = []
    for lang in languages:
        if re.search(rf'\b{lang}\b', default_caption, re.IGNORECASE):
            found.append(lang)
    return " ".join(dict.fromkeys(found))

def normalize_for_matching(text: str) -> str:
    if not text:
        return ""
    text = HTML_A_RE.sub(r'\1', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r'\s+', ' ', text)
    return text.lower().strip()

def html_to_plain_text(text: str) -> str:
    if not text:
        return ""
    text = HTML_A_RE.sub(r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text

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

def build_smart_filename(
    base_name: str,
    default_caption: str,
    year: Optional[str],
    language: Optional[str]
) -> str:
    base_norm = normalize(base_name)
    def has(value: Optional[str]) -> bool:
        return bool(value) and normalize(value) in base_norm
    parts = [base_name]
    se = extract_season_episode(default_caption)
    if se and not has(se):
        parts.append(se)
    if year and not has(year):
        parts.append(year)
    quality = extract_quality(default_caption)
    if quality and not has(quality):
        parts.append(quality)
    audio_langs = extract_audio_languages(default_caption)
    if audio_langs and not contains_language(base_name, audio_langs):
        parts.append(audio_langs)
    sub_tag = extract_subtitle_tag(default_caption)
    if sub_tag and not has(sub_tag):
        parts.append(sub_tag)
    audio = extract_audio_tags(default_caption)
    if audio and not has(audio):
        parts.append(audio)
    codec = extract_codec(default_caption)
    if codec and not has(codec):
        parts.append(codec)
    video_format = extract_format(default_caption)
    if video_format and not has(video_format):
        parts.append(video_format)
    clean = []
    seen = set()
    for p in parts:
        key = normalize(p)
        if key not in seen:
            seen.add(key)
            clean.append(p)
    return " ".join(clean)

def extract_season_episode(text: str) -> Optional[str]:
    patterns = [
        r'\bS\d{1,2}E\d{1,2}\b',
        r'\bS\d{1,2}E\d{1,2}\s*(?:-|–|to)\s*E?\d{1,2}\b',
        r'\bS\d{1,2}\s*(?:Complete|Full)\b',
        r'\bSeason\s*\d+\s*(?:Complete|Full)?\b',
        r'\bE\d{1,2}\s*(?:-|–|to)\s*E\d{1,2}\b',
        r'\bEpisodes?\s*\d+\s*(?:-|–|to)\s*\d+\b',
        r'\bEP?\s*\d{1,3}\b',
        r'\[\s*\d{1,3}\s*(?:-|–|to)\s*\d{1,3}\s*\]'
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return None

def normalize_series_name(name: str) -> str:
    if not name:
        return ""
    name = re.sub(r'\.(mkv|mp4|avi|webm)$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[._\-]+', ' ', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip().title()

def extract_audio_tags(text: str) -> Optional[str]:
    tags = [
        "Dual Audio", "Multi Audio", "5.1", "7.1", "AAC", "DDP", "Atmos"
    ]
    found = []
    for t in tags:
        if re.search(rf'\b{re.escape(t)}\b', text, re.IGNORECASE):
            found.append(t)
    return " ".join(dict.fromkeys(found)) if found else None

def extract_codec(text: str) -> Optional[str]:
    codecs = ["x265", "x264", "HEVC", "AV1"]
    for c in codecs:
        if re.search(rf'\b{c}\b', text, re.IGNORECASE):
            return c
    return None

def extract_subtitle_tag(text: str) -> Optional[str]:
    if not text:
        return None
    subs_langs = extract_subtitle_languages(text)
    if not subs_langs:
        return None
    langs = subs_langs.lower()
    if langs == "english":
        return "ESub"
    if langs == "hindi":
        return "HSub"
    return f"Subs {subs_langs}"

def extract_audio_languages(text: str) -> str:
    if not text:
        return ""
    languages = [
        "Hindi", "English", "Tamil", "Telugu", "Malayalam", "Kannada",
        "Marathi", "Gujarati", "Bengali", "Punjabi", "Urdu",
        "French", "German", "Spanish", "Italian", "Russian",
        "Japanese", "Korean", "Chinese"
    ]
    found = []
    audio_block = re.search(r'(audio|dual audio|multi audio)[^a-z]*([a-z ,/]+)', text, re.IGNORECASE)
    if audio_block:
        block = audio_block.group(2)
        for lang in languages:
            if re.search(rf'\b{lang}\b', block, re.IGNORECASE):
                found.append(lang)
    return " ".join(dict.fromkeys(found))

def extract_subtitle_languages(text: str) -> str:
    if not text:
        return ""
    languages = [
        "Hindi", "English", "Tamil", "Telugu", "Malayalam", "Kannada",
        "Marathi", "Gujarati", "Bengali", "Punjabi", "Urdu",
        "French", "German", "Spanish", "Italian", "Russian",
        "Japanese", "Korean", "Chinese"
    ]
    found = set()
    patterns = [
        r'subtitles?\s*[:\-]\s*([a-z ,/]+)',
        r'subs?\s*[:\-]\s*([a-z ,/]+)'
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            for lang in languages:
                if re.search(rf'\b{lang}\b', m.group(1), re.IGNORECASE):
                    found.add(lang)
    return " ".join(sorted(found, key=str.lower))

def normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', text.lower()).strip()

def extract_quality(text: str) -> Optional[str]:
    match = re.search(r'\b(480p|720p|1080p|2160p|4k)\b', text, re.IGNORECASE)
    return match.group(1) if match else None

def extract_format(text: str) -> Optional[str]:
    match = re.search(r'\b(mkv|mp4|avi|web-dl|hdrip|bluray|webrip)\b', text, re.IGNORECASE)
    return match.group(1) if match else None

def strip_links_and_mentions_keep_text(text: str) -> str:
    if not text:
        return text
    text = MD_LINK_RE.sub(r'\1', text)
    text = TG_USER_LINK_RE.sub(r'\1', text)
    text = URL_RE.sub("", text)
    text = MENTION_RE.sub("", text)
    text = re.sub(r'[ 	]+', ' ', text) 
    return text

def strip_links_only(text: str) -> str:
    if not text:
        return text
    text = MD_LINK_RE.sub(r'\1', text)
    text = TG_USER_LINK_RE.sub(r'\1', text)
    text = HTML_A_RE.sub(r'\1', text)
    text = URL_RE.sub("", text)
    text = MENTION_RE.sub("", text)
    text = re.sub(r'\(\s*\)', '', text)   # ()
    text = re.sub(r'\[\s*\]', '', text)   # []
    text = re.sub(r'\{\s*\}', '', text)   # {}
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def apply_block_words(caption_html: str, raw_blocked: str) -> str:
    if not caption_html or not raw_blocked:
        return caption_html
    plain = caption_html
    blocked_items = [
        item.strip()
        for item in re.split(r"[,\n]+", raw_blocked)
        if item.strip()
    ]
    for item in blocked_items:
        plain = plain.replace(item, "")
    plain = "\n".join(line.rstrip() for line in plain.splitlines())
    plain = "\n".join(line for line in plain.splitlines() if line.strip())
    plain = re.sub(r"[ \t]{2,}", " ", plain)
    return plain.strip()

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

def apply_replacements(text: str, pairs: List[Tuple[str, str]]) -> str:
    if not pairs or not text:
        return text
    new_text = text
    for old, new in pairs:
        if not old:
            continue
        try:
            pattern = re.compile(re.escape(old), flags=re.IGNORECASE)
            new_text = pattern.sub(new, new_text)
            if re.search(re.escape(old), new_text, flags=re.IGNORECASE):
                new_text = re.sub(re.escape(old), new, new_text, flags=re.IGNORECASE)
        except re.error:
            new_text = new_text.replace(old, new)
    new_text = re.sub(r'[ 	]+', ' ', new_text).strip()
    return new_text

# ---------------- Function Handler ----------------
@Client.on_message(filters.private)
async def capture_user_input(client, message):
    user_id = message.from_user.id
    active_users = (
        set(bot_data.get("caption_set", {})) |
        set(bot_data.get("block_words_set", {})) |
        set(bot_data.get("replace_words_set", {})) |
        set(bot_data.get("prefix_set", {})) |
        set(bot_data.get("suffix_set", {}))
    )
    if user_id not in active_users:
        return
    text = (
        message.text.html if message.text else
        message.caption.html if message.caption else
        ""
    )
    if not text.strip():
        return

    # ---------- CAPTION ----------
    if user_id in bot_data["caption_set"]:
        session = bot_data["caption_set"].pop(user_id)
        channel_id = session["channel_id"]
        instr_msg_id = session["instr_msg_id"]
        await updateCap(channel_id, text)
        if channel_id in CHANNEL_CACHE:
            CHANNEL_CACHE[channel_id]["caption"] = text
        await client.delete_messages(user_id, message.id)
        await client.edit_message_text(
            chat_id=user_id,
            message_id=instr_msg_id,
            text="✅ Caption updated successfully!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("↩ Back", callback_data=f"back_to_captionmenu_{channel_id}")]]
            )
        )
        return

    # ---------- BLOCK WORDS ----------
    if user_id in bot_data["block_words_set"]:
        session = bot_data["block_words_set"].pop(user_id)
        channel_id = session["channel_id"]
        instr_msg_id = session["instr_msg_id"]
        old_words = await get_block_words(channel_id)
        combined = f"{old_words.rstrip()}\n{text.strip()}" if old_words else text.strip()
        await set_block_words(channel_id, combined)
        await client.delete_messages(user_id, message.id)
        await client.edit_message_text(
            chat_id=user_id,
            message_id=instr_msg_id,
            text="✅ Blocked words updated!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("↩ Back", callback_data=f"back_to_blockwords_{channel_id}")]]
            )
        )
        return

    # ---------- REPLACE WORDS ----------
    if user_id in bot_data["replace_words_set"]:
        session = bot_data["replace_words_set"].pop(user_id)
        channel_id = session["channel_id"]
        instr_msg_id = session["instr_msg_id"]
        old_replace = await get_replace_words(channel_id)
        combined = f"{old_replace.rstrip()}\n{text.strip()}" if old_replace else text.strip()
        await set_replace_words(channel_id, combined)
        await client.delete_messages(user_id, message.id)
        await client.edit_message_text(
            chat_id=user_id,
            message_id=instr_msg_id,
            text="✅ Replace words updated!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("↩ Back", callback_data=f"back_to_replace_{channel_id}")]]
            )
        )
        return

    # ---------- PREFIX ----------
    if user_id in bot_data["prefix_set"]:
        session = bot_data["prefix_set"].pop(user_id)
        channel_id = session["channel_id"]
        instr_msg_id = session["instr_msg_id"]
        old_suffix, old_prefix = await get_suffix_prefix(channel_id)
        final_text = f"{old_prefix.rstrip()}\n{text.strip()}" if old_prefix else text.strip()
        await set_prefix(channel_id, final_text)
        if channel_id in CHANNEL_CACHE:
            CHANNEL_CACHE[channel_id]["prefix"] = final_text
        await client.delete_messages(user_id, message.id)
        await client.edit_message_text(
            chat_id=user_id,
            message_id=instr_msg_id,
            text="✅ Prefix updated!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("↩ Back", callback_data=f"back_to_suffixprefix_{channel_id}")]]
            )
        )
        return

    # ---------- SUFFIX ----------
    if user_id in bot_data["suffix_set"]:
        session = bot_data["suffix_set"].pop(user_id)
        channel_id = session["channel_id"]
        instr_msg_id = session["instr_msg_id"]
        old_suffix, _ = await get_suffix_prefix(channel_id)
        final_text = f"{old_suffix.rstrip()}\n{text.strip()}" if old_suffix else text.strip()
        await set_suffix(channel_id, final_text)
        if channel_id in CHANNEL_CACHE:
            CHANNEL_CACHE[channel_id]["suffix"] = final_text
        await client.delete_messages(user_id, message.id)
        await client.edit_message_text(
            chat_id=user_id,
            message_id=instr_msg_id,
            text="✅ Suffix updated!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("↩ Back", callback_data=f"back_to_suffixprefix_{channel_id}")]]
            )
        )
        return

    # ================= FILE FORWARD SKIP HANDLER =================
    if user_id in FF_SESSIONS:
        session = FF_SESSIONS[user_id]
        if session.get("expires") and session["expires"] < time.time():
            FF_SESSIONS.pop(user_id, None)
            await message.reply_text("⏰ Session expired.\nStart again using /file_forward")
            return
        if session.get("step") == "skip":
            raw = (message.text or "").strip()
            msg_id = extract_msg_id_from_text(raw)
            if msg_id is None:
                await message.reply_text(
                    "❌ Invalid message.\n\n"
                    "Send:\n"
                    "• Telegram message link\n"
                    "• OR message ID number"
                )
                return
            session["skip"] = int(msg_id)
            session["step"] = "queue"
            await message.reply_text("✅ OK!\n🚚 Forwarding will start…")
            await enqueue_forward_jobs(client, user_id)
            return


