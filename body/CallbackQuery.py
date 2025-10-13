from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from body.database import *
from info import *
from Script import script
from body.Caption import bot_data 

FONT_TXT = script.FONT_TXT

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from body.database import *
from info import *
from Script import script
from body.Caption import bot_data 

FONT_TXT = script.FONT_TXT

async def safe_delete(msg):
    try:
        await msg.delete()
    except:
        pass

@Client.on_callback_query(filters.regex(r'^chinfo_(-?\d+)$'))
async def channel_settings(client, query):
    user_id = query.from_user.id
    channel_id = int(query.matches[0].group(1))

    try:
        chat = await client.get_chat(channel_id)
        member = await client.get_chat_member(channel_id, "me")
        if not _is_admin_member(member):
            await users.update_one({"_id": user_id}, {"$pull": {"channels": {"channel_id": channel_id}}})
            return await query.message.edit_text(f"⚠️ I am not admin in **{chat.title}** anymore. It was removed from your list.")
    except Exception:
        await users.update_one({"_id": user_id}, {"$pull": {"channels": {"channel_id": channel_id}}})
        return await query.message.edit_text("⚠️ Unable to access this channel. It was removed from your list.")

    # Get current link remover status
    link_status = await get_link_remover_status(channel_id)
    link_text = "Link Remover (ON)" if link_status else "Link Remover (OFF)"

    buttons = [
        [InlineKeyboardButton("📝 Set Caption", callback_data=f"setcap_{channel_id}")],
        [InlineKeyboardButton("🧹 Set Words Remover", callback_data=f"setwords_{channel_id}")],
        [InlineKeyboardButton("🔤 Set Prefix & Suffix", callback_data=f"set_suffixprefix_{channel_id}")],
        [InlineKeyboardButton("🔄 Set Replace Words", callback_data=f"setreplace_{channel_id}")],
        [InlineKeyboardButton(f"🔗 {link_text}", callback_data=f"togglelink_{channel_id}")],
        [InlineKeyboardButton("↩ Back", callback_data="back_channels"),
         InlineKeyboardButton("❌ Close", callback_data="close_msg")]
    ]

    await query.message.edit_text(f"⚙️ Manage channel: **{chat.title}**", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r'^back_channels$'))
async def back_to_channels(client, query):
    user_id = query.from_user.id
    channels = await get_user_channels(user_id)
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
    await safe_delete(query.message)


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

    caption_data = await get_channel_caption(channel_id)
    current_caption = caption_data["caption"] if caption_data else None
    caption_display = f"📝 **Current Caption:**\n{current_caption}" if current_caption else "📝 **Current Caption:** None set yet."

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
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id

    try:
        await query.message.delete()
    except Exception:
        pass

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
            "When you send the caption text, I will save it and delete your message."
        ),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("↩ Back", callback_data=f"back_to_captionmenu_{channel_id}")]]
        )
    )

    bot_data.setdefault("caption_set", {})[user_id] = {
        "channel_id": channel_id,
        "instr_msg_id": instr.id
    }

@Client.on_callback_query(filters.regex(r'^back_to_captionmenu_(-?\d+)$'))
async def back_to_caption_menu(client, query):
    channel_id = int(query.matches[0].group(1))
    await set_caption_menu(client, query) 

@Client.on_callback_query(filters.regex(r'^delcap_(-?\d+)$'))
async def delete_caption(client, query):
    channel_id = int(query.matches[0].group(1))
    
    try:
        ch = await client.get_chat(channel_id)
        ch_title = ch.title
    except Exception:
        ch_title = "Unknown Channel"

    try:
        await delete_channel_caption(channel_id)
    except Exception:
        pass

    buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"setcap_{channel_id}")]]
    text = f"📢 **Channel:** {ch_title}\n\n✅ Caption deleted successfully.\nNow using default caption."
    try:
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r'^capfont_(-?\d+)$'))
async def caption_font(client, query):
    channel_id = int(query.matches[0].group(1))
    
    try:
        ch = await client.get_chat(channel_id)
        ch_title = ch.title
    except Exception:
        ch_title = "Unknown Channel"

    current_cap = await get_channel_caption(channel_id)
    cap_txt = current_cap["caption"] if current_cap else "No custom caption set."

    buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"setcap_{channel_id}")]]
    text = (
        f"📢 **Channel:** {ch_title}\n"
        f"📝 **Current Caption:** {cap_txt}\n\n"
        f"🖋️ **Available Fonts:**\n\n{FONT_TXT}"
    )
    try:
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


# ========== SET WORDS REMOVER MENU ==========================================
@Client.on_callback_query(filters.regex(r"^setwords_(-?\d+)$"))
async def set_words_menu(client, query):
    channel_id = int(query.matches[0].group(1))
    blocked_words = await get_block_words(channel_id)
    words_text = ", ".join(blocked_words) if blocked_words else "No blocked words set."

    buttons = [
        [InlineKeyboardButton("📝 Set Block Words", callback_data=f"addwords_{channel_id}")],
        [InlineKeyboardButton("🗑️ Delete Block Words", callback_data=f"delwords_{channel_id}")],
        [InlineKeyboardButton("↩ Back", callback_data=f"chinfo_{channel_id}")]
    ]

    await query.message.edit_text(
        f"📛 **Channel:** `{channel_id}`\n\n🚫 **Blocked Words:**\n{words_text}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex(r"^addwords_(-?\d+)$"))
async def add_block_words(client, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id

    bot_data.setdefault("block_words_set", {})[user_id] = {"channel_id": channel_id}
    msg = await query.message.edit_text(
        "✏️ Send the words you want to block (use comma to separate words).\n"
        "Use /cancel to cancel this process."
    )
    bot_data["block_words_set"][user_id]["instr_msg_id"] = msg.id

@Client.on_callback_query(filters.regex(r"^delwords_(-?\d+)$"))
async def delete_blocked_words(client, query):
    channel_id = int(query.matches[0].group(1))
    await delete_block_words(channel_id)

    buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"setwords_{channel_id}")]]
    await query.message.edit_text(
        "✅ All blocked words deleted successfully.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from body.database import set_suffix, set_prefix, get_suffix_prefix, delete_suffix, delete_prefix
from body.Caption import bot_data

# ======================== Suffix & Prefix Menu ==================================
@Client.on_callback_query(filters.regex(r'^set_suffixprefix_(-?\d+)$'))
async def suffix_prefix_menu(client, query):
    channel_id = int(query.matches[0].group(1))
    suffix, prefix = await get_suffix_prefix(channel_id)

    buttons = [
        [InlineKeyboardButton("Set Suffix", callback_data=f"set_suf_{channel_id}"),
         InlineKeyboardButton("Del Suffix", callback_data=f"del_suf_{channel_id}")],
        [InlineKeyboardButton("Set Prefix", callback_data=f"set_pre_{channel_id}"),
         InlineKeyboardButton("Del Prefix", callback_data=f"del_pre_{channel_id}")],
        [InlineKeyboardButton("↩ Back", callback_data=f"chinfo_{channel_id}")]
    ]

    text = f"📌 Channel: {channel_id}\n\nCurrent Suffix: {suffix or 'None'}\nCurrent Prefix: {prefix or 'None'}"
    try:
        await query.message.delete()
    except Exception:
        pass
    await client.send_message(query.from_user.id, text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r'^set_suf_(-?\d+)$'))
async def set_suffix_cb(client, query):
    channel_id = int(query.matches[0].group(1))
    try:
        await query.message.delete()
    except Exception:
        pass
    instr = await client.send_message(query.from_user.id, "Send suffix you want to set.\nUse /cancel to cancel this process.")
    bot_data.setdefault("suffix_set", {})[query.from_user.id] = {"channel_id": channel_id, "instr_msg_id": instr.id}

@Client.on_callback_query(filters.regex(r'^set_pre_(-?\d+)$'))
async def set_prefix_cb(client, query):
    channel_id = int(query.matches[0].group(1))
    try:
        await query.message.delete()
    except Exception:
        pass
    instr = await client.send_message(query.from_user.id, "Send prefix you want to set.\nUse /cancel to cancel this process.")
    bot_data.setdefault("prefix_set", {})[query.from_user.id] = {"channel_id": channel_id, "instr_msg_id": instr.id}

@Client.on_callback_query(filters.regex(r'^del_suf_(-?\d+)$'))
async def delete_suffix_cb(client, query):
    channel_id = int(query.matches[0].group(1))
    await delete_suffix(channel_id)
    try:
        await query.message.delete()
    except Exception:
        pass
    await client.send_message(query.from_user.id, "✅ Suffix deleted.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩ Back", callback_data=f"set_suffixprefix_{channel_id}")]]))

@Client.on_callback_query(filters.regex(r'^del_pre_(-?\d+)$'))
async def delete_prefix_cb(client, query):
    channel_id = int(query.matches[0].group(1))
    await delete_prefix(channel_id)
    try:
        await query.message.delete()
    except Exception:
        pass
    await client.send_message(query.from_user.id, "✅ Prefix deleted.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩ Back", callback_data=f"set_suffixprefix_{channel_id}")]]))

# ======================== Replace Words ==================================
@Client.on_callback_query(filters.regex(r'^setreplace_(-?\d+)$'))
async def replace_words_menu(client, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id
    replace_words = await get_replace_words(channel_id)  

    buttons = [
        [InlineKeyboardButton("📝 Set Replace Words", callback_data=f"do_replace_{channel_id}")],
        [InlineKeyboardButton("❌ Delete Replace Words", callback_data=f"del_replace_{channel_id}")],
        [InlineKeyboardButton("↩ Back", callback_data=f"chinfo_{channel_id}")]
    ]

    text = f"📢 **Channel:** {channel_id}\n\n"
    text += "🔄 **Current Replace Words:**\n"
    text += f"{replace_words if replace_words else 'None'}"

    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r'^do_replace_(-?\d+)$'))
async def set_replace_words_start(client, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id

    # Delete previous msg
    try:
        await query.message.delete()
    except: pass

    # Send instruction msg
    msg = await client.send_message(user_id, 
        "✏️ Send multiple replacement pairs in this format:\n"
        "`old_word new_word, another_old another_new`\n"
        "Use /cancel to cancel the process."
    )

    # Store user session
    bot_data.setdefault("replace_words_set", {})[user_id] = {"channel_id": channel_id, "instr_msg_id": msg.id}

@Client.on_callback_query(filters.regex(r'^del_replace_(-?\d+)$'))
async def delete_replace_words(client, query):
    channel_id = int(query.matches[0].group(1))

    await delete_replace_words(channel_id)  # delete from DB

    try: await query.message.delete()
    except: pass

    await client.send_message(query.from_user.id, f"✅ All replace words deleted for channel {channel_id}.",
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩ Back", callback_data=f"setreplace_{channel_id}")]]))

# ======================== Link Remover ==================================
@Client.on_callback_query(filters.regex(r'^togglelink_(-?\d+)$'))
async def toggle_link_remover(client, query):
    channel_id = int(query.matches[0].group(1))

    # Toggle in DB
    current_status = await get_link_remover_status(channel_id)
    new_status = not current_status
    await set_link_remover_status(channel_id, new_status)

    # Update button text
    link_text = "Link Remover (ON)" if new_status else "Link Remover (OFF)"
    buttons = [
        [InlineKeyboardButton(f"🔗 {link_text}", callback_data=f"togglelink_{channel_id}")],
        [InlineKeyboardButton("↩ Back", callback_data=f"chinfo_{channel_id}")]
    ]

    await query.message.edit_text(f"🔗 Link Remover is now {'enabled' if new_status else 'disabled'}.", 
                                  reply_markup=InlineKeyboardMarkup(buttons))
