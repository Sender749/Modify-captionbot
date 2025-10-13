import asyncio
import re
import os
import sys
from typing import Tuple, List, Dict, Optional
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
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
        old = chat_member_update.old_chat_member
        chat = chat_member_update.chat

        # Check if the bot itself was promoted to admin
        if new.user and new.user.is_self:
            if new.status in ("administrator", "creator"):
                owner = chat_member_update.from_user
                owner_id = owner.id if owner else None

                # Save channel info in DB
                if owner_id:
                    await add_user_channel(
                        owner_id,
                        chat.id,
                        chat.title or "Unnamed Channel"
                    )

                    # Send confirmation message to the user
                    try:
                        await client.send_message(
                            owner_id,
                            f"✅ Successfully added to <b>{chat.title}</b> as admin!",
                        )
                    except Exception as e:
                        print(f"Could not message owner: {e}")

    except Exception as e:
        print(f"Error in when_added_as_admin: {e}")


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
    print("Channels from DB:", channels)

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
        except Exception:
            await users.update_one({"_id": user_id}, {"$pull": {"channels": {"channel_id": ch_id}}})
            removed_titles.append(ch_title)

    if removed_titles:
        removed_text = "• " + "\n• ".join(removed_titles)
        await message.reply_text(f"⚠️ Some channels were removed from your list because I lost access or admin rights:\n\n{removed_text}")

    if not valid_channels:
        return await message.reply_text("No active channels found where I am still admin.")

    buttons = [[InlineKeyboardButton(ch["channel_title"], callback_data=f"chinfo_{ch['channel_id']}")] for ch in valid_channels]
    await message.reply_text("📋 Your added channels:", reply_markup=InlineKeyboardMarkup(buttons))


# ---------------- Auto Caption core ----------------
@Client.on_message(filters.channel)
async def reCap(client, message):
    """
    Main auto-caption editing flow when bot detects media in a channel.
    Applies prefix, suffix, blocked words removal, replacements and link remover.
    """
    chnl_id = message.chat.id
    default_caption = message.caption or ""

    # Only act on messages that contain media types we care about
    if not message.media:
        return

    # find the media object to get file_name & file_size
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

    # Fetch configuration from DB (single call if possible)
    cap_doc = await chnl_ids.find_one({"chnl_id": chnl_id}) or {}
    cap_template = cap_doc.get("caption") or DEF_CAP
    link_remover_on = bool(cap_doc.get("link_remover", False))
    blocked_words = cap_doc.get("block_words", []) or []
    suffix = cap_doc.get("suffix", "") or ""
    prefix = cap_doc.get("prefix", "") or ""
    replace_raw = cap_doc.get("replace_words", None)

    # Build caption from template
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
        # if formatting fails, fallback to default template or the stored raw caption
        print("Caption template format error:", e)
        new_caption = (cap_doc.get("caption") or DEF_CAP)

    # Apply replacements
    replace_pairs = parse_replace_pairs(replace_raw) if replace_raw else []
    if replace_pairs:
        new_caption = apply_replacements(new_caption, replace_pairs)

    # Remove blocked words
    if blocked_words:
        new_caption = apply_block_words(new_caption, blocked_words)

    # Apply link remover behavior
    if link_remover_on:
        # Keep display text from markdown/html links but remove url and mentions
        new_caption = strip_links_and_mentions_keep_text(new_caption)
    # If link_remover_off we do nothing about links

    # Add prefix & suffix if present
    if prefix:
        new_caption = f"{prefix}\n\n{new_caption}".strip()
    if suffix:
        new_caption = f"{new_caption}\n\n{suffix}".strip()

    # Final cleanup (no duplicate spaces)
    new_caption = re.sub(r'\s+\n', '\n', new_caption).strip()

    try:
        # Use same parse_mode as saved caption - stored caption likely contains HTML tags.
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
    name = _status_name(member_obj)
    return ("administrator" in name) or ("creator" in name) or ("owner" in name)


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

# Markdown/HTML link patterns to extract display text: [text](url) and <a href="...">text</a> and tg://user links
MD_LINK_RE = re.compile(r'\[([^\]]+)\]\((?:https?:\/\/[^\)]+|tg:\/\/[^\)]+)\)', flags=re.IGNORECASE)
HTML_A_RE = re.compile(r'<a\s+[^>]*href=["\'](?:https?:\/\/|tg:\/)[^"\']+["\'][^>]*>(.*?)</a>', flags=re.IGNORECASE)
TG_USER_LINK_RE = re.compile(r'\[([^\]]+)\]\(tg:\/\/user\?id=\d+\)', flags=re.IGNORECASE)

def strip_links_and_mentions_keep_text(text: str) -> str:
    """
    Remove links but keep display text for Markdown/HTML links where possible.
    Also remove bare mentions @username.
    """
    if not text:
        return text

    # Convert markdown links [text](url) -> text
    text = MD_LINK_RE.sub(r'\1', text)
    # Convert telegram user links in markdown -> text
    text = TG_USER_LINK_RE.sub(r'\1', text)
    # Convert html <a href="...">text</a> -> text
    text = HTML_A_RE.sub(r'\1', text)
    # Remove plain URLs (but if URL words are same as display text we already handled)
    text = URL_RE.sub("", text)
    # Remove mentions like @username
    text = MENTION_RE.sub("", text)
    # Clean multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def remove_mentions_only(text: str) -> str:
    if not text:
        return text
    # Remove mentions and tg user links entirely
    text = MENTION_RE.sub("", text)
    text = TG_USER_LINK_RE.sub("", text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def apply_block_words(text: str, blocked: List[str]) -> str:
    """Remove blocked words occurrences (word boundaries) case-insensitive."""
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


def parse_replace_pairs(raw: str) -> List[Tuple[str, str]]:
    """
    Parse replacement pairs stored as raw string by user.
    Expected format (flexible):
      old1 new1, old2 new2
    or each pair on new line:
      old1 new1
      old2 new2
    Returns list of (old, new).
    """
    if not raw:
        return []
    pairs = []
    # normalize separators to comma
    raw = raw.replace('\n', ',')
    items = [p.strip() for p in raw.split(',') if p.strip()]
    for item in items:
        # split by whitespace into exactly two parts (old and new)
        parts = item.split()
        if len(parts) >= 2:
            old = parts[0]
            new = " ".join(parts[1:])
            pairs.append((old, new))
    return pairs

def apply_replacements(text: str, pairs: List[Tuple[str, str]]) -> str:
    if not pairs or not text:
        return text
    new_text = text
    # apply simple case-insensitive replacement preserving other text
    # We'll replace word occurrences and also substrings (user expects simple old->new)
    for old, new in pairs:
        if not old:
            continue
        # Use regex to replace whole words and also occurrences; try whole word first
        try:
            # replace whole words case-insensitive
            pattern = re.compile(r'\b' + re.escape(old) + r'\b', flags=re.IGNORECASE)
            new_text = pattern.sub(new, new_text)
            # fallback: replace any substring occurrences (if any remain)
            if re.search(re.escape(old), new_text, flags=re.IGNORECASE):
                new_text = re.sub(re.escape(old), new, new_text, flags=re.IGNORECASE)
        except re.error:
            # fallback naive replace
            new_text = new_text.replace(old, new)
    new_text = re.sub(r'\s+', ' ', new_text).strip()
    return new_text

# ---------------- Interactive flows (capture handlers) ----------------
@Client.on_message(filters.private)
async def capture_caption(client, message):
    user_id = message.from_user.id
    if "caption_set" not in bot_data or user_id not in bot_data["caption_set"]:
        return

    session = bot_data["caption_set"][user_id]
    channel_id = session["channel_id"]
    instr_msg_id = session.get("instr_msg_id")
    caption_text = message.text or message.caption or ""
    caption_text = caption_text.strip() if isinstance(caption_text, str) else ""

    if not caption_text:
        try:
            await message.delete()
        except Exception:
            pass
        await client.send_message(user_id, "❌ Please send valid caption text (plain text only).")
        return

    try:
        existing = await get_channel_caption(channel_id)
        if existing:
            await updateCap(channel_id, caption_text)
        else:
            await addCap(channel_id, caption_text)
    except Exception as e:
        print("Error saving caption:", e)

    try:
        await message.delete()
    except Exception:
        pass

    if instr_msg_id:
        try:
            await client.delete_messages(chat_id=user_id, message_ids=instr_msg_id)
        except Exception:
            pass

    buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"setcap_{channel_id}")]]
    try:
        await client.send_message(
            user_id,
            "✅ Caption successfully updated!",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        print("Error sending confirmation message:", e)

    bot_data["caption_set"].pop(user_id, None)


@Client.on_message(filters.private)
async def capture_block_words(client, message):
    user_id = message.from_user.id
    if "block_words_set" not in bot_data or user_id not in bot_data["block_words_set"]:
        return

    session = bot_data["block_words_set"][user_id]
    channel_id = session["channel_id"]
    instr_msg_id = session.get("instr_msg_id")

    # Cancel command
    if message.text and message.text.strip().lower() == "/cancel":
        if instr_msg_id:
            try:
                await client.delete_messages(user_id, instr_msg_id)
            except Exception:
                pass
        await message.reply_text(
            "❌ Process canceled.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩ Back", callback_data=f"setwords_{channel_id}")]])
        )
        bot_data["block_words_set"].pop(user_id, None)
        return

    text = message.text.strip() if message.text else ""
    if not text:
        await message.reply_text("Please send valid text.")
        return

    # accept comma separated
    words = [w.strip() for w in re.split(r'[,\n]+', text) if w.strip()]
    try:
        await set_block_words(channel_id, words)
    except Exception as e:
        print("Error saving blocked words:", e)

    try:
        await client.delete_messages(user_id, [message.id, instr_msg_id])
    except Exception:
        pass

    buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"setwords_{channel_id}")]]
    await client.send_message(user_id, "✅ Blocked words updated successfully.", reply_markup=InlineKeyboardMarkup(buttons))

    bot_data["block_words_set"].pop(user_id, None)


@Client.on_message(filters.private)
async def capture_suffix_prefix(client, message):
    user_id = message.from_user.id

    # Suffix flow
    if "suffix_set" in bot_data and user_id in bot_data["suffix_set"]:
        session = bot_data["suffix_set"][user_id]
        channel_id = session["channel_id"]
        instr_msg_id = session.get("instr_msg_id")

        if message.text and message.text.strip().lower() == "/cancel":
            await client.send_message(user_id, "❌ Process canceled.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩ Back", callback_data=f"set_suffixprefix_{channel_id}")]]))
            bot_data["suffix_set"].pop(user_id, None)
            if instr_msg_id:
                await client.delete_messages(user_id, instr_msg_id)
            return

        suffix_text = message.text.strip()
        await set_suffix(channel_id, suffix_text)
        try:
            await client.delete_messages(user_id, [message.id, instr_msg_id])
        except Exception:
            pass
        await client.send_message(user_id, "✅ Suffix set successfully.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩ Back", callback_data=f"set_suffixprefix_{channel_id}")]]))
        bot_data["suffix_set"].pop(user_id, None)
        return

    # Prefix flow
    if "prefix_set" in bot_data and user_id in bot_data["prefix_set"]:
        session = bot_data["prefix_set"][user_id]
        channel_id = session["channel_id"]
        instr_msg_id = session.get("instr_msg_id")

        if message.text and message.text.strip().lower() == "/cancel":
            await client.send_message(user_id, "❌ Process canceled.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩ Back", callback_data=f"set_suffixprefix_{channel_id}")]]))
            bot_data["prefix_set"].pop(user_id, None)
            if instr_msg_id:
                await client.delete_messages(user_id, instr_msg_id)
            return

        prefix_text = message.text.strip()
        await set_prefix(channel_id, prefix_text)
        try:
            await client.delete_messages(user_id, [message.id, instr_msg_id])
        except Exception:
            pass
        await client.send_message(user_id, "✅ Prefix set successfully.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩ Back", callback_data=f"set_suffixprefix_{channel_id}")]]))
        bot_data["prefix_set"].pop(user_id, None)
        return


@Client.on_message(filters.private)
async def capture_replace_words(client, message):
    user_id = message.from_user.id
    if user_id not in bot_data.get("replace_words_set", {}):
        return

    session = bot_data["replace_words_set"][user_id]
    channel_id = session["channel_id"]
    instr_msg_id = session.get("instr_msg_id")

    # Cancel
    if message.text and message.text.strip().lower() == "/cancel":
        try:
            await message.delete()
            if instr_msg_id:
                await client.delete_messages(user_id, instr_msg_id)
        except Exception:
            pass
        await client.send_message(user_id, "❌ Replace words process cancelled.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩ Back", callback_data=f"setreplace_{channel_id}")]]))
        bot_data["replace_words_set"].pop(user_id, None)
        return

    text = message.text.strip() if message.text else ""
    if not text:
        await message.reply_text("Please send replace pairs in the expected format.")
        return

    # Save to DB as raw text (we'll parse when applying)
    try:
        await set_replace_words(channel_id, text)
    except Exception as e:
        print("Error setting replace words:", e)

    try:
        await message.delete()
        if instr_msg_id:
            await client.delete_messages(user_id, instr_msg_id)
    except Exception:
        pass

    await client.send_message(user_id, f"✅ Replace words set successfully for channel {channel_id}.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩ Back", callback_data=f"setreplace_{channel_id}")]]))
    bot_data["replace_words_set"].pop(user_id, None)
