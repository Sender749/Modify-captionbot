import asyncio, re, os, sys
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import enums
from info import *
from Script import *
from .database import *

# session storage for conversational flows (set caption)
bot_data = {
    # "caption_set": { user_id: {"channel_id": int, "instr_msg_id": int} }
}


# ---------- helper ----------
def _status_name(member_obj):
    """
    Robustly extract a lower-case status name from a ChatMember-like object.
    Works whether status is a string or an enum.
    """
    status = getattr(member_obj, "status", "")
    # If enum with .value
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


# -------------------- Commands --------------------

@Client.on_message(filters.command("start") & filters.private)
async def strtCap(client, message):
    user_id = int(message.from_user.id)
    await insert_user(user_id)

    bot_me = await client.get_me()
    bot_username = bot_me.username or BOT_USERNAME if "BOT_USERNAME" in globals() else (bot_me.username or "Bot")

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕️ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ ➕️",
                    url=f"https://t.me/{bot_username}?startchannel=true",
                )
            ],
            [InlineKeyboardButton("Hᴇʟᴘ", callback_data="help"),
             InlineKeyboardButton("Aʙᴏᴜᴛ", callback_data="about")],
            [InlineKeyboardButton("🌐 Uᴘᴅᴀᴛᴇ", url="https://t.me/Silicon_Bot_Update"),
             InlineKeyboardButton("📜 Sᴜᴘᴘᴏʀᴛ", url="https://t.me/Silicon_Botz")],
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


@Client.on_message(filters.command("set_cap") & filters.channel)
async def setCap(client, message):
    if len(message.command) < 2:
        return await message.reply(
            "Usage: /set_cap Your caption here.\nYou can use {file_name} for file name, {file_size} for size."
        )
    chnl_id = message.chat.id
    caption = message.text.split(" ", 1)[1]
    if await get_channel_caption(chnl_id):
        await updateCap(chnl_id, caption)
    else:
        await addCap(chnl_id, caption)
    await message.reply(f"✅ New caption set:\n\n{caption}")


@Client.on_message(filters.command("del_cap") & filters.channel)
async def delCap(client, message):
    chnl_id = message.chat.id
    await delete_channel_caption(chnl_id)
    await message.reply("✅ Caption deleted, bot will use default caption now.")


# ---------- SETTINGS: list user channels (validate admin & auto-remove invalid) ----------
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
                valid_channels.append({"channel_id": ch_id, "channel_title": ch_title})
            else:
                # not admin anymore: remove and notify later
                await users.update_one({"_id": user_id}, {"$pull": {"channels": {"channel_id": ch_id}}})
                removed_titles.append(ch_title)
        except Exception:
            # inaccessible / removed channel: remove from db
            await users.update_one({"_id": user_id}, {"$pull": {"channels": {"channel_id": ch_id}}})
            removed_titles.append(ch_title)

    # If any removed, inform the user
    if removed_titles:
        removed_text = "• " + "\n• ".join(removed_titles)
        await message.reply_text(f"⚠️ Some channels were removed from your list because I lost access or admin rights:\n\n{removed_text}")

    if not valid_channels:
        return await message.reply_text("No active channels found where I am still admin.")

    # Build buttons
    buttons = [[InlineKeyboardButton(ch["channel_title"], callback_data=f"chinfo_{ch['channel_id']}")] for ch in valid_channels]
    await message.reply_text("📋 Your added channels:", reply_markup=InlineKeyboardMarkup(buttons))


# ---------------- Auto Caption core helpers ----------------
def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB"]
    i = 0
    while size >= 1024.0 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return "%.2f %s" % (size, units[i])


def extract_language(default_caption):
    pattern = r'\b(Hindi|English|Tamil|Telugu|Malayalam|Kannada|Hin)\b'
    langs = set(re.findall(pattern, default_caption or "", re.IGNORECASE))
    return ", ".join(sorted(langs, key=str.lower)) if langs else "Hindi-English"


def extract_year(default_caption):
    match = re.search(r'\b(19\d{2}|20\d{2})\b', default_caption or "")
    return match.group(1) if match else None


@Client.on_message(filters.channel)
async def reCap(client, message):
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

            try:
                new_caption = cap.format(
                    file_name=file_name, file_size=file_size,
                    default_caption=default_caption, language=language, year=year
                )
                await message.edit_caption(new_caption)
            except errors.FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception as e:
                print(f"Caption edit failed: {e}")


# ---------------- Bot started callback (inline start) ----------------
@Client.on_callback_query(filters.regex(r'^start$'))
async def start_cb(client, query):
    try:
        bot_me = await client.get_me()
        bot_username = bot_me.username or BOT_USERNAME if "BOT_USERNAME" in globals() else (bot_me.username or "Bot")
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("➕️ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ ➕️", url=f"https://t.me/{bot_username}?startchannel=true")],
                [InlineKeyboardButton("Hᴇʟᴘ", callback_data="help"), InlineKeyboardButton("Aʙᴏᴜᴛ", callback_data="about")],
                [InlineKeyboardButton("🌐 Uᴘᴅᴀᴛᴇ", url="https://t.me/Silicon_Bot_Update"),
                 InlineKeyboardButton("📜 Sᴜᴘᴘᴏʀᴛ", url="https://t.me/Silicon_Botz")],
            ]
        )
        await query.message.edit_text(text=script.START_TXT.format(query.from_user.mention), reply_markup=keyboard, disable_web_page_preview=True)
    except Exception as e:
        print("start_cb error:", e)


@Client.on_callback_query(filters.regex(r'^help'))
async def help_cb(client, query):
    await query.message.edit_text(text=script.HELP_TXT, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('About', callback_data='about')], [InlineKeyboardButton('↩ ʙᴀᴄᴋ', callback_data='start')]]), disable_web_page_preview=True)


@Client.on_callback_query(filters.regex(r'^about'))
async def about_cb(client, query):
    await query.message.edit_text(text=script.ABOUT_TXT, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴍᴇ ❓', callback_data='help')], [InlineKeyboardButton('↩ ʙᴀᴄᴋ', callback_data='start')]]), disable_web_page_preview=True)


# ---------------- Chat member updates (promote / demote / removed) ----------------
@Client.on_chat_member_updated()
async def on_bot_chat_member_update(client, update):
    """
    Handle when the bot is promoted/demoted/removed in a chat.
    - If bot becomes admin/creator -> save channel for the user who promoted (if available) and notify them.
    - If bot loses admin / is removed -> remove the channel from all users and notify them.
    """
    try:
        bot_id = (await client.get_me()).id

        # ensure this update refers to bot
        if not getattr(update, "new_chat_member", None):
            return

        # The update new_chat_member might be a ChatMember object
        new_member = update.new_chat_member
        if not getattr(new_member, "user", None):
            return

        if new_member.user.id != bot_id:
            return

        channel_id = update.chat.id
        # safe title extraction
        channel_title = getattr(update.chat, "title", str(channel_id))

        status_name = _status_name(new_member)

        # promoted / added as admin
        if ("administrator" in status_name) or ("creator" in status_name) or ("owner" in status_name):
            # If we know who did the promotion (update.from_user), record channel under that user
            if getattr(update, "from_user", None):
                try:
                    await add_channel(update.from_user.id, channel_id, channel_title)
                    # notify the user
                    try:
                        await client.send_message(update.from_user.id, f"✅ Bot is now admin in **{channel_title}**.")
                    except Exception:
                        pass
                except Exception as e:
                    print("add_channel error:", e)

        # demoted / removed / left
        else:
            # remove channel from all users who had it
            cursor = users.find({"channels.channel_id": channel_id})
            async for user in cursor:
                try:
                    await users.update_one({"_id": user["_id"]}, {"$pull": {"channels": {"channel_id": channel_id}}})
                    # notify the user who had it
                    try:
                        await client.send_message(user["_id"], f"⚠️ Bot was removed or lost admin in **{channel_title}**. Channel removed from your list.")
                    except Exception:
                        pass
                except Exception:
                    pass

    except Exception as e:
        print("on_bot_chat_member_update error:", e)


# ---------------- Channel management callbacks ----------------
@Client.on_callback_query(filters.regex(r'^chinfo_(-?\d+)$'))
async def channel_settings(client, query):
    """
    When user clicks a channel listed in /settings -> show simple menu:
    [Set Caption]
    [↩ Back] [❌ Close]
    Also validate bot admin; if not admin -> remove channel and notify user.
    """
    user_id = query.from_user.id
    channel_id = int(query.matches[0].group(1))

    # validate access & admin status
    try:
        chat = await client.get_chat(channel_id)
        member = await client.get_chat_member(channel_id, "me")
        if not _is_admin_member(member):
            # remove from user's list
            await users.update_one({"_id": user_id}, {"$pull": {"channels": {"channel_id": channel_id}}})
            return await query.message.edit_text(f"⚠️ I am not admin in **{chat.title}** anymore. It was removed from your list.")
    except Exception:
        # inaccessible channel: remove
        await users.update_one({"_id": user_id}, {"$pull": {"channels": {"channel_id": channel_id}}})
        return await query.message.edit_text("⚠️ Unable to access this channel. It was removed from your list.")

    # show simple menu (only set caption + back + close)
    buttons = [
        [InlineKeyboardButton("📝 Set Caption", callback_data=f"setcap_{channel_id}")],
        [InlineKeyboardButton("↩ Back", callback_data="back_channels"),
         InlineKeyboardButton("❌ Close", callback_data="close_msg")]
    ]

    await query.message.edit_text(f"⚙️ Manage channel: **{chat.title}**", reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r'^back_channels$'))
async def back_to_channels(client, query):
    user_id = query.from_user.id
    channels = await get_user_channels(user_id)

    # Re-validate channels (remove invalid)
    valid = []
    removed = []
    for ch in channels:
        ch_id = ch.get("channel_id")
        ch_title = ch.get("channel_title", str(ch_id))
        try:
            member = await client.get_chat_member(ch_id, "me")
            if _is_admin_member(member):
                valid.append(ch)
            else:
                await users.update_one({"_id": user_id}, {"$pull": {"channels": {"channel_id": ch_id}}})
                removed.append(ch_title)
        except Exception:
            await users.update_one({"_id": user_id}, {"$pull": {"channels": {"channel_id": ch_id}}})
            removed.append(ch_title)

    if removed:
        removed_text = "• " + "\n• ".join(removed)
        try:
            await query.message.reply_text(f"⚠️ Removed from your list (no admin/access):\n{removed_text}")
        except Exception:
            pass

    if not valid:
        return await query.message.edit_text("You haven’t added me to any channels where I am admin.")

    buttons = [[InlineKeyboardButton(ch['channel_title'], callback_data=f"chinfo_{ch['channel_id']}")] for ch in valid]
    await query.message.edit_text("📋 Your added channels:", reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r'^close_msg$'))
async def close_message(client, query):
    try:
        await query.message.delete()
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r'^setcap_(-?\d+)$'))
async def set_caption_menu(client, query):
    channel_id = int(query.matches[0].group(1))

    try:
        chat = await client.get_chat(channel_id)
        member = await client.get_chat_member(channel_id, "me")
        if not _is_admin_member(member):
            await users.update_one({"_id": query.from_user.id}, {"$pull": {"channels": {"channel_id": channel_id}}})
            return await query.message.edit_text(f"⚠️ I am not admin in **{chat.title}** anymore. It was removed from your list.")
    except Exception:
        await users.update_one({"_id": query.from_user.id}, {"$pull": {"channels": {"channel_id": channel_id}}})
        return await query.message.edit_text("⚠️ Unable to access this channel. It was removed from your list.")

    # get current caption (if any)
    caption_data = await get_channel_caption(channel_id)
    current_caption = caption_data["caption"] if caption_data else None
    caption_display = f"📝 **Current Caption:**\n{current_caption}" if current_caption else "📝 **Current Caption:** None set yet."

    # Buttons for caption management
    buttons = [
        [InlineKeyboardButton("🆕 Set Caption", callback_data=f"setcapmsg_{channel_id}")],
        [InlineKeyboardButton("❌ Delete Caption", callback_data=f"delcap_{channel_id}")],
        [InlineKeyboardButton("🔤 Caption Font", callback_data=f"capfont_{channel_id}")],
        [InlineKeyboardButton("↩ Back", callback_data=f"chinfo_{channel_id}")]
    ]

    text = (
        f"⚙️ **Channel:** {chat.title}\n"
        f"{caption_display}\n\n"
        f"Choose what you want to do 👇"
    )

    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r'^setcapmsg_(-?\d+)$'))
async def set_caption_message(client, query):
    """
    Ask user (in PM) to send caption text and store session state.
    """
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id

    # send instruction in PM
    try:
        instr = await client.send_message(
            chat_id=user_id,
            text=(
                "📌 Send me the caption for this channel.\n\n"
                "You can use these placeholders:\n"
                "{file_name} - File name\n"
                "{file_size} - File size\n"
                "{default_caption} - Original caption\n"
                "{language} - Language\n"
                "{year} - Year\n\n"
                "When you send the caption text I will save it and delete your message."
            ),
        )
    except Exception as e:
        return await query.answer("❌ Unable to send you a private message. Make sure you started the bot.", show_alert=True)

    # store session
    bot_data.setdefault("caption_set", {})[user_id] = {"channel_id": channel_id, "instr_msg_id": instr.id}

    # acknowledge the callback (edit previous menu or notify)
    try:
        await query.answer("📨 Check your private messages — send the caption there.", show_alert=False)
    except Exception:
        pass


@Client.on_message(filters.private)
async def capture_caption(client, message):
    """
    Capture the user's next private message if they're in a set-caption session.
    Save caption to DB, delete user's message, delete instruction message and notify success.
    """
    user_id = message.from_user.id
    if "caption_set" not in bot_data or user_id not in bot_data["caption_set"]:
        return  # not in a caption set flow

    session = bot_data["caption_set"][user_id]
    channel_id = session["channel_id"]
    instr_msg_id = session.get("instr_msg_id")

    # get caption text from message (accept text or caption)
    caption_text = message.text or message.caption or ""
    caption_text = caption_text.strip() if isinstance(caption_text, str) else ""

    if not caption_text:
        # Accept anything? user may have sent media with no caption; prompt them to send textual caption
        try:
            await message.delete()
        except Exception:
            pass
        await client.send_message(user_id, "Please send the caption text (plain text).")
        return

    # Save to DB (update or insert)
    try:
        existing = await get_channel_caption(channel_id)
        if existing:
            await updateCap(channel_id, caption_text)
        else:
            await addCap(channel_id, caption_text)
    except Exception as e:
        print("Err saving caption:", e)

    # try to delete user's message for cleanliness
    try:
        await message.delete()
    except Exception:
        pass

    # try to delete instruction message
    if instr_msg_id:
        try:
            await client.delete_messages(chat_id=user_id, message_ids=instr_msg_id)
        except Exception:
            pass

    # notify success with Back button to channel settings
    buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"chinfo_{channel_id}")]]
    try:
        await client.send_message(user_id, "✅ Caption successfully updated.", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        pass

    # clear session
    try:
        del bot_data["caption_set"][user_id]
    except Exception:
        bot_data["caption_set"].pop(user_id, None)


@Client.on_callback_query(filters.regex(r'^delcap_(-?\d+)$'))
async def delete_caption(client, query):
    channel_id = int(query.matches[0].group(1))
    try:
        await delete_channel_caption(channel_id)
    except Exception:
        pass

    buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"setcap_{channel_id}")]]
    await query.message.edit_text("✅ Caption deleted successfully. Now using default caption.", reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r'^capfont_(-?\d+)$'))
async def caption_font(client, query):
    channel_id = int(query.matches[0].group(1))
    buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"setcap_{channel_id}")]]
    await query.message.edit_text(f"🖋️ Available fonts:\n\n{FONT_TXT}", reply_markup=InlineKeyboardMarkup(buttons))
