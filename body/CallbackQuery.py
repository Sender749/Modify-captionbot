from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from body.database import *
from info import *
from Script import script
from body.Caption import bot_data 
from pyrogram.errors import RPCError, ChatAdminRequired, ChatWriteForbidden

FONT_TXT = script.FONT_TXT

async def safe_delete(msg):
    try:
        await msg.delete()
    except:
        pass

def _is_admin_member(member):
    return member.status in ("administrator", "creator")

@Client.on_callback_query(filters.regex(r'^chinfo_(-?\d+)$'))
async def channel_settings(client, query):
    channel_id = int(query.matches[0].group(1))

    try:
        chat = await client.get_chat(channel_id)
        chat_title = getattr(chat, "title", str(channel_id))
    except Exception:
        chat_title = str(channel_id)
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

    await query.message.edit_text(f"⚙️ Manage channel: **{chat_title}**",reply_markup=InlineKeyboardMarkup(buttons))

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
            if member.status in ("administrator", "creator"):
                valid.append(ch)
            else:
                removed.append(ch_title)
        except ChatAdminRequired:
            removed.append(ch_title)
        except Exception as e:
            print(f"[WARN] Error checking {ch_id}: {e}")
            continue  

    if removed:
        removed_text = "• " + "\n• ".join(removed)
        await query.message.reply_text(f"⚠️ Lost access in:\n{removed_text}")

    if not valid:
        return await query.message.edit_text("No active channels found where I’m admin.")

    buttons = [[InlineKeyboardButton(ch['channel_title'], callback_data=f"chinfo_{ch['channel_id']}")] for ch in valid]
    await query.message.edit_text("📋 Your added channels:", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r'^close_msg$'))
async def close_message(client, query):
    await safe_delete(query.message)

# ===================== CAPTION MENU =====================
@Client.on_callback_query(filters.regex(r'^setcap_(-?\d+)$'))
async def set_caption_menu(client, query):
    channel_id = int(query.matches[0].group(1))

    chat = await client.get_chat(channel_id)
    chat_title = getattr(chat, "title", str(channel_id))

    caption_data = await get_channel_caption(channel_id)
    current_caption = caption_data["caption"] if caption_data else None
    caption_display = f"📝 **Current Caption:**\n{current_caption}" if current_caption else "📝 **Current Caption:** None set yet."

    buttons = [
        [InlineKeyboardButton("🆕 Set Caption", callback_data=f"setcapmsg_{channel_id}"),
         InlineKeyboardButton("❌ Delete Caption", callback_data=f"delcap_{channel_id}")],
        [InlineKeyboardButton("🔤 Caption Font", callback_data=f"capfont_{channel_id}")],
        [InlineKeyboardButton("↩ Back", callback_data=f"chinfo_{channel_id}")]
    ]

    text = (
        f"⚙️ **Channel:** {chat_title}\n"
        f"{caption_display}\n\n"
        f"Choose what you want to do 👇"
    )

    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r'^setcapmsg_(-?\d+)$'))
async def set_caption_message(client, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id
    await safe_delete(query.message)

    instr = await client.send_message(
        chat_id=user_id,
        text=(
            "📌 Send me the caption for this channel.\n\n"
            "You can use these placeholders:\n"
            "<code>{file_name}</code> - File name\n"
            "<code>{file_size}</code> - File size\n"
            "<code>{default_caption}</code> - Original caption\n"
            "<code>{language}</code> - Language\n"
            "<code>{year}</code> - Year\n\n"
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
    await delete_channel_caption(channel_id)

    buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"setcap_{channel_id}")]]
    await query.message.edit_text(f"✅ Caption deleted. Now using default caption.", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r'^capfont_(-?\d+)$'))
async def caption_font(client, query):
    channel_id = int(query.matches[0].group(1))
    current_cap = await get_channel_caption(channel_id)
    cap_txt = current_cap["caption"] if current_cap else "No custom caption set."

    buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"setcap_{channel_id}")]]
    text = f"📝 Current Caption: {cap_txt}\n\n🖋️ Available Fonts:\n\n{FONT_TXT}"
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))


# ========== SET WORDS REMOVER MENU ==========================================
@Client.on_callback_query(filters.regex(r"^setwords_(-?\d+)$"))
async def set_words_menu(client, query):
    channel_id = int(query.matches[0].group(1))
    blocked_words = await get_block_words(channel_id)
    words_text = ", ".join(blocked_words) if blocked_words else "No blocked words set."

    buttons = [
        [InlineKeyboardButton("📝 Set Block Words", callback_data=f"addwords_{channel_id}"),
         InlineKeyboardButton("🗑️ Delete Block Words", callback_data=f"delwords_{channel_id}")],
        [InlineKeyboardButton("↩ Back", callback_data=f"chinfo_{channel_id}")]
    ]

    await query.message.edit_text(
        f"📛 **Channel:** `{channel_title}`\n\n🚫 **Blocked Words:**\n{words_text}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex(r'^addwords_(-?\d+)$'))
async def set_block_words_message(client, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id

    try:
        await safe_delete(query.message)
    except Exception:
        pass

    instr = await client.send_message(
        chat_id=user_id,
        text="🚫 Send blocked words for this channel (separate words with commas or newlines).\n\nSend /cancel to abort.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩ Back", callback_data=f"setwords_{channel_id}")]])
    )

    bot_data.setdefault("block_words_set", {})[user_id] = {
        "channel_id": channel_id,
        "instr_msg_id": instr.id
    }


@Client.on_callback_query(filters.regex(r"^delwords_(-?\d+)$"))
async def delete_blocked_words(client, query):
    channel_id = int(query.matches[0].group(1))
    await delete_block_words(channel_id)
    buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"setwords_{channel_id}")]]
    await query.message.edit_text("✅ All blocked words deleted successfully.",reply_markup=InlineKeyboardMarkup(buttons))


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

    text = f"📌 Channel: {chat_title}\n\nCurrent Suffix: {suffix or 'None'}\nCurrent Prefix: {prefix or 'None'}"
    try:
        await query.message.delete()
    except Exception:
        pass
    await client.send_message(query.from_user.id, text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r'^set_suf_(-?\d+)$'))
async def set_suffix_message(client, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id
    await safe_delete(query.message)

    instr = await client.send_message(
        chat_id=user_id,
        text="🖋️ Send the suffix text you want to add to your captions.\n\nUse /cancel to abort.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("↩ Back", callback_data=f"chinfo_{channel_id}")]]
        )
    )
    bot_data.setdefault("suffix_set", {})[user_id] = {
        "channel_id": channel_id,
        "instr_msg_id": instr.id
    }
@Client.on_callback_query(filters.regex(r'^set_pre_(-?\d+)$'))
async def set_prefix_message(client, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id
    await safe_delete(query.message)

    instr = await client.send_message(
        chat_id=user_id,
        text="✍️ Send the prefix text you want to add to your captions.\n\nUse /cancel to abort.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("↩ Back", callback_data=f"chinfo_{channel_id}")]]
        )
    )
    bot_data.setdefault("prefix_set", {})[user_id] = {
        "channel_id": channel_id,
        "instr_msg_id": instr.id
    }
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
        [InlineKeyboardButton("📝 Set Replace Words", callback_data=f"do_replace_{channel_id}"),
         InlineKeyboardButton("❌ Delete Replace Words", callback_data=f"del_replace_{channel_id}")],
        [InlineKeyboardButton("↩ Back", callback_data=f"chinfo_{channel_id}")]
    ]

    text = f"📢 **Channel:** {chat_title}\n\n"
    text += "🔄 **Current Replace Words:**\n"
    text += f"{replace_words if replace_words else 'None'}"

    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r'^do_replace_(-?\d+)$'))
async def set_replace_message(client, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id
    await safe_delete(query.message)

    instr = await client.send_message(
        chat_id=user_id,
        text="🧩 Send replace words (format: old1:new1, old2:new2, ...)\n\nUse /cancel to abort.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("↩ Back", callback_data=f"chinfo_{channel_id}")]]
        )
    )
    bot_data.setdefault("replace_words_set", {})[user_id] = {
        "channel_id": channel_id,
        "instr_msg_id": instr.id
    }
@Client.on_callback_query(filters.regex(r'^del_replace_(-?\d+)$'))
async def delete_replace_words(client, query):
    channel_id = int(query.matches[0].group(1))
    await delete_replace_words(channel_id)  
    await safe_delete(query.message)
    await client.send_message(query.from_user.id, f"✅ All replace words deleted for channel {channel_id}.",
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩ Back", callback_data=f"setreplace_{channel_id}")]]))

# ======================== Link Remover ==================================
@Client.on_callback_query(filters.regex(r'^togglelink_(-?\d+)$'))
async def toggle_link_remover(client, query):
    channel_id = int(query.matches[0].group(1))
    current_status = await get_link_remover_status(channel_id)
    new_status = not current_status
    await set_link_remover_status(channel_id, new_status)
    await channel_settings(client, query)
