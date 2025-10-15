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
    if "caption_set" in bot_data and user_id in bot_data["caption_set"]:
        bot_data["caption_set"].pop(user_id, None)
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
    user_id = query.from_user.id
    if "caption_set" in bot_data and user_id in bot_data["caption_set"]:
        bot_data["caption_set"].pop(user_id, None)
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


@Client.on_callback_query(filters.regex(r"^addwords_(-?\d+)$"))
async def set_block_words_message(client, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id
    bot_data.get("block_words_set", {}).pop(user_id, None)
    await safe_delete(query.message)
    instr = await client.send_message(
        chat_id=user_id,
        text=(
            "🚫 Send me the **blocked words** for this channel.\n"
            "Separate words using commas or newlines.\n\n"
            "Example:\n"
            "<code>spam, fake, scam</code>\n\n"
        ),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("↩ Back", callback_data=f"back_to_blockwords_{channel_id}")]]
        )
    )

    bot_data.setdefault("block_words_set", {})[user_id] = {
        "channel_id": channel_id,
        "instr_msg_id": instr.id
    }


@Client.on_callback_query(filters.regex(r"^back_to_blockwords_(-?\d+)$"))
async def back_to_blockwords_menu(client, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id
    bot_data.get("block_words_set", {}).pop(user_id, None)
    await set_words_menu(client, query)


@Client.on_callback_query(filters.regex(r"^delwords_(-?\d+)$"))
async def delete_blocked_words(client, query):
    channel_id = int(query.matches[0].group(1))
    await delete_block_words(channel_id)
    chat = await client.get_chat(channel_id)
    chat_title = getattr(chat, "title", str(channel_id))
    buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"setwords_{channel_id}")]]
    await query.message.edit_text(
        f"✅ **All blocked words deleted successfully.**\n\n📛 **Channel:** {chat_title}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ======================== Suffix & Prefix Menu ==================================
@Client.on_callback_query(filters.regex(r'^set_suffixprefix_(-?\d+)$'))
async def suffix_prefix_menu(client, query):
    channel_id = int(query.matches[0].group(1))
    chat = await client.get_chat(channel_id)
    chat_title = getattr(chat, "title", str(channel_id))
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

@Client.on_callback_query(filters.regex(r"^back_to_suffixprefix_(-?\d+)$"))
async def back_to_suffixprefix_menu(client, query):
    channel_id = int(query.matches[0].group(1))
    await suffix_prefix_menu(client, query)

@Client.on_callback_query(filters.regex(r'^set_suf_(-?\d+)$'))
async def set_suffix_message(client, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id
    await safe_delete(query.message)

    instr = await client.send_message(
        chat_id=user_id,
        text="🖋️ Send the suffix text you want to add to your captions.",
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
        text="✍️ Send the prefix text you want to add to your captions.",
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
@Client.on_callback_query(filters.regex(r"^setreplace_(-?\d+)$"))
async def set_replace_menu(client, query):
    channel_id = int(query.matches[0].group(1))
    chat = await client.get_chat(channel_id)
    chat_title = getattr(chat, "title", str(channel_id))

    replace_dict = await get_replace_words(channel_id)
    replace_text = "None set yet."

    if replace_dict:
        if isinstance(replace_dict, dict):
            replace_text = "\n".join(f"{old} → {new}" for old, new in replace_dict.items())
        elif isinstance(replace_dict, list):
            replace_text = "\n".join(f"{pair[0]} → {pair[1]}" for pair in replace_dict if len(pair) == 2)

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


@Client.on_callback_query(filters.regex(r"^addreplace_(-?\d+)$"))
async def set_replace_words_message(client, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id
    bot_data.get("replace_words_set", {}).pop(user_id, None)
    await safe_delete(query.message)
    instr = await client.send_message(
        chat_id=user_id,
        text=(
            "🔤 Send me the **replace words** for this channel.\n"
            "Use format: `old new, another_old another_new`\n\n"
            "Example:\n"
            "<code>spam scam, fake real</code>\n\n"
        ),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("↩ Back", callback_data=f"back_to_replace_{channel_id}")]]
        )
    )

    bot_data.setdefault("replace_words_set", {})[user_id] = {
        "channel_id": channel_id,
        "instr_msg_id": instr.id
    }


@Client.on_callback_query(filters.regex(r"^back_to_replace_(-?\d+)$"))
async def back_to_replace_menu(client, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id
    bot_data.get("replace_words_set", {}).pop(user_id, None)
    await set_replace_menu(client, query)


@Client.on_callback_query(filters.regex(r"^delreplace_(-?\d+)$"))
async def delete_replace_words(client, query):
    channel_id = int(query.matches[0].group(1))
    await delete_replace_words(channel_id)
    chat = await client.get_chat(channel_id)
    chat_title = getattr(chat, "title", str(channel_id))

    buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"setreplace_{channel_id}")]]
    await query.message.edit_text(
        f"✅ **All replace words deleted successfully.**\n\n📛 **Channel:** {chat_title}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ======================== Link Remover ==================================
@Client.on_callback_query(filters.regex(r'^togglelink_(-?\d+)$'))
async def toggle_link_remover(client, query):
    channel_id = int(query.matches[0].group(1))
    current_status = await get_link_remover_status(channel_id)
    new_status = not current_status
    await set_link_remover_status(channel_id, new_status)
    await channel_settings(client, query)
