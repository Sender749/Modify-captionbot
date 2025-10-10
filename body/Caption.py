import asyncio, re, os, sys
from pyrogram import *
from info import *
from Script import script
from .database import *
from pyrogram.errors import FloodWait
from pyrogram.types import *
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

@Client.on_message(filters.command("start") & filters.private)
async def strtCap(bot, message):
    user_id = int(message.from_user.id)
    await insert_user(user_id)
    bot_me = await bot.get_me()
    bot_username = bot_me.username

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(
            "➕️ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ ➕️", url=f"https://t.me/{bot_username}?startchannel=true"
        )],
         [InlineKeyboardButton("Hᴇʟᴘ", callback_data="help"),
          InlineKeyboardButton("Aʙᴏᴜᴛ", callback_data="about")],
         [InlineKeyboardButton("🌐 Uᴘᴅᴀᴛᴇ", url="https://t.me/Silicon_Bot_Update"),
          InlineKeyboardButton("📜 Sᴜᴘᴘᴏʀᴛ", url="https://t.me/Silicon_Botz")]]
    )

    await message.reply_photo(
        photo=SILICON_PIC,
        caption=f"<b>Hᴇʟʟᴏ {message.from_user.mention}\n\nI am auto caption bot with custom caption.</b>",
        reply_markup=keyboard
    )

@Client.on_message(filters.private & filters.user(ADMIN)  & filters.command(["total_users"]))
async def all_db_users_here(client,message):
    silicon = await message.reply_text("Please Wait....")
    silicon_botz = await total_user()
    await silicon.edit(f"Tᴏᴛᴀʟ Usᴇʀ :- `{silicon_botz}`")

@Client.on_message(filters.private & filters.user(ADMIN) & filters.command(["broadcast"]))
async def broadcast(bot, message):
    if (message.reply_to_message):
        silicon = await message.reply_text("Geting All ids from database..\n Please wait")
        all_users = await getid()
        tot = await total_user()
        success = 0
        failed = 0
        deactivated = 0
        blocked = 0
        await silicon.edit(f"ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ...")
        async for user in all_users:
            try:
                await asyncio.sleep(1)
                await message.reply_to_message.copy(user['_id'])
                success += 1
            except errors.InputUserDeactivated:
                deactivated +=1
                await delete_user(user['_id'])
            except errors.UserIsBlocked:
                blocked +=1
                await delete_user(user['_id'])
            except Exception as e:
                failed += 1
                await delete_user(user['_id'])
                pass
            try:
                await silicon.edit(f"<u>ʙʀᴏᴀᴅᴄᴀsᴛ ᴘʀᴏᴄᴇssɪɴɢ</u>\n\n• ᴛᴏᴛᴀʟ ᴜsᴇʀs: {tot}\n• sᴜᴄᴄᴇssғᴜʟ: {success}\n• ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs: {blocked}\n• ᴅᴇʟᴇᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛs: {deactivated}\n• ᴜɴsᴜᴄᴄᴇssғᴜʟ: {failed}")
            except FloodWait as e:
                await asyncio.sleep(e.value)
        await silicon.edit(f"<u>ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</u>\n\n• ᴛᴏᴛᴀʟ ᴜsᴇʀs: {tot}\n• sᴜᴄᴄᴇssғᴜʟ: {success}\n• ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs: {blocked}\n• ᴅᴇʟᴇᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛs: {deactivated}\n• ᴜɴsᴜᴄᴄᴇssғᴜʟ: {failed}")

@Client.on_message(filters.private & filters.user(ADMIN) & filters.command("restart"))
async def restart_bot(b, m):
    silicon = await b.send_message(text="**🔄 𝙿𝚁𝙾𝙲𝙴𝚂𝚂𝙴𝚂 𝚂𝚃𝙾𝙿𝙴𝙳. 𝙱𝙾𝚃 𝙸𝚂 𝚁𝙴𝚂𝚃𝙰𝚁𝚃𝙸𝙽𝙶...**", chat_id=m.chat.id)       
    await asyncio.sleep(3)
    await silicon.edit("**✅️ 𝙱𝙾𝚃 𝙸𝚂 𝚁𝙴𝚂𝚃𝙰𝚁𝚃𝙴𝙳. 𝙽𝙾𝚆 𝚈𝙾𝚄 𝙲𝙰𝙽 𝚄𝚂𝙴 𝙼𝙴**")
    os.execl(sys.executable, sys.executable, *sys.argv)

@Client.on_message(filters.command("set_cap") & filters.channel)
async def setCap(bot, message):
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
async def delCap(bot, message):
    chnl_id = message.chat.id
    await delete_channel_caption(chnl_id)
    await message.reply("✅ Caption deleted, bot will use default caption now.")

@Client.on_message(filters.command("settings") & filters.private)
async def user_settings(bot, message):
    user_id = message.from_user.id
    channels = await get_user_channels(user_id)
    
    if not channels:
        return await message.reply_text("You haven’t added me to any channels yet!")

    buttons = [[InlineKeyboardButton(ch['channel_title'], callback_data=f"chinfo_{ch['channel_id']}")] for ch in channels]

    await message.reply_text(
        "📋 Your added channels:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ---------------- Auto Caption ----------------

def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB"]
    i = 0
    while size >= 1024.0 and i < len(units)-1:
        size /= 1024.0
        i += 1
    return "%.2f %s" % (size, units[i])

def extract_language(default_caption):
    pattern = r'\b(Hindi|English|Tamil|Telugu|Malayalam|Kannada|Hin)\b'
    langs = set(re.findall(pattern, default_caption, re.IGNORECASE))
    return ", ".join(sorted(langs, key=str.lower)) if langs else "Hindi-English"

def extract_year(default_caption):
    match = re.search(r'\b(19\d{2}|20\d{2})\b', default_caption)
    return match.group(1) if match else None

@Client.on_message(filters.channel)
async def reCap(bot, message):
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

@Client.on_callback_query(filters.regex(r'^start$'))
async def start(bot, query):
    try:
        # Get bot username dynamically
        bot_me = await bot.get_me()
        bot_username = bot_me.username

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "➕️ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ ➕️",
                        url=f"https://t.me/{bot_username}?startchannel=true"
                    )
                ],
                [
                    InlineKeyboardButton("Hᴇʟᴘ", callback_data="help"),
                    InlineKeyboardButton("Aʙᴏᴜᴛ", callback_data="about")
                ],
                [
                    InlineKeyboardButton("🌐 Uᴘᴅᴀᴛᴇ", url="https://t.me/Silicon_Bot_Update"),
                    InlineKeyboardButton("📜 Sᴜᴘᴘᴏʀᴛ", url="https://t.me/Silicon_Botz")
                ]
            ]
        )

        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention),
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

    except Exception as e:
        print(f"Error in start callback: {e}")

@Client.on_callback_query(filters.regex(r'^help'))
async def help(bot, query):
    await query.message.edit_text(
        text=script.HELP_TXT,
        reply_markup=InlineKeyboardMarkup(
            [[
            InlineKeyboardButton('About', callback_data='about')
            ],[
            InlineKeyboardButton('↩ ʙᴀᴄᴋ', callback_data='start')
            ]]
        ),
        disable_web_page_preview=True    
)


@Client.on_callback_query(filters.regex(r'^about'))
async def about(bot, query):
    await query.message.edit_text(
        text=script.ABOUT_TXT,
        reply_markup=InlineKeyboardMarkup(
            [[
            InlineKeyboardButton('ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴍᴇ ❓', callback_data='help')
            ],[
            InlineKeyboardButton('↩ ʙᴀᴄᴋ', callback_data='start')
            ]]
        ),
        disable_web_page_preview=True 

)

@Client.on_chat_member_updated()
async def on_bot_chat_member_update(bot, update):
    try:
        bot_id = (await bot.get_me()).id
        # Only handle updates about our bot
        if update.new_chat_member.user.id != bot_id:
            return

        channel_id = update.chat.id
        channel_title = update.chat.title

        # Bot added or promoted
        if update.new_chat_member.status in ["administrator", "member"]:
            if update.from_user:
                await add_channel(update.from_user.id, channel_id, channel_title)
                try:
                    await bot.send_message(
                        chat_id=update.from_user.id,
                        text=f"✅ Bot is now admin in **{channel_title}**."
                    )
                except Exception as e:
                    print(f"Failed to send PM: {e}")

        # Bot removed or demoted
        elif update.new_chat_member.status in ["left", "kicked"]:
            # Remove channel from all users
            async for user in users.find({"channels.channel_id": channel_id}):
                updated_channels = [ch for ch in user.get("channels", []) if ch["channel_id"] != channel_id]
                await users.update_one({"_id": user["_id"]}, {"$set": {"channels": updated_channels}})
                # Notify user (optional)
                try:
                    await bot.send_message(
                        chat_id=user["_id"],
                        text=f"⚠️ Bot was removed or lost admin in **{channel_title}**. Channel removed from your list."
                    )
                except Exception:
                    pass

    except Exception as e:
        print(f"on_chat_member_updated error: {e}")

# ---------------- Channel Buttons -------------------------------------------------------
@Client.on_callback_query(filters.regex(r'^chinfo_(\d+)$'))
async def channel_settings(bot, query):
    channel_id = int(query.matches[0].group(1))
    
    buttons = [
        [InlineKeyboardButton("Set Caption", callback_data=f"setcap_{channel_id}")],
        [InlineKeyboardButton("Set Words Remover", callback_data=f"setwords_{channel_id}")],
        [InlineKeyboardButton("Set Suffix & Prefix", callback_data=f"setsuffix_{channel_id}")],
        [InlineKeyboardButton("Set Replace Words", callback_data=f"setreplace_{channel_id}")],
        [InlineKeyboardButton("Link Remover (On/Off)", callback_data=f"linkrem_{channel_id}")],
        [InlineKeyboardButton("Remove Channel", callback_data=f"removechan_{channel_id}")],
        [InlineKeyboardButton("↩ Back", callback_data="back_channels"),
         InlineKeyboardButton("❌ Close", callback_data="close_msg")]
    ]
    
    await query.message.edit_text(
        f"⚙️ Manage your channel: **{channel_id}**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex(r'^back_channels$'))
async def back_to_channels(bot, query):
    user_id = query.from_user.id
    channels = await get_user_channels(user_id)
    
    if not channels:
        return await query.message.edit_text("You haven’t added me to any channels yet!")
    
    buttons = [[InlineKeyboardButton(ch['channel_title'], callback_data=f"chinfo_{ch['channel_id']}")] for ch in channels]
    
    await query.message.edit_text(
        "📋 Your added channels:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex(r'^close_msg$'))
async def close_message(bot, query):
    try:
        await query.message.delete()
    except Exception:
        pass

@Client.on_callback_query(filters.regex(r'^removechan_(\d+)$'))
async def remove_channel(bot, query):
    channel_id = int(query.matches[0].group(1))
    user_id = query.from_user.id

    # Remove channel from user DB
    user = await users.find_one({"_id": user_id})
    if user:
        updated_channels = [ch for ch in user.get("channels", []) if ch["channel_id"] != channel_id]
        await users.update_one({"_id": user_id}, {"$set": {"channels": updated_channels}})

    await query.message.edit_text(f"✅ Channel removed from your list.")


# ---------------- Set Caption Menu ----------------
@Client.on_callback_query(filters.regex(r'^setcap_(\d+)$'))
async def set_caption_menu(bot, query):
    channel_id = int(query.matches[0].group(1))

    buttons = [
        [InlineKeyboardButton("1️⃣ Set Caption", callback_data=f"setcapmsg_{channel_id}")],
        [InlineKeyboardButton("2️⃣ Delete Caption", callback_data=f"delcap_{channel_id}")],
        [InlineKeyboardButton("3️⃣ Caption Font", callback_data=f"capfont_{channel_id}")],
        [InlineKeyboardButton("↩ Back", callback_data=f"chinfo_{channel_id}")]
    ]

    await query.message.edit_text(
        "✏️ Choose an action for this channel:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ---------------- Set Caption Message ----------------
@Client.on_callback_query(filters.regex(r'^setcapmsg_(\d+)$'))
async def set_caption_message(bot, query):
    channel_id = int(query.matches[0].group(1))
    
    # Send instructions
    msg = await bot.send_message(
        chat_id=query.from_user.id,
        text=("📌 Send me the caption for this channel.\n\n"
              "You can use the following placeholders:\n"
              "{file_name} - File name\n"
              "{file_size} - File size\n"
              "{default_caption} - Original caption\n"
              "{language} - Language\n"
              "{year} - Year")
    )

    # Store info in user session
    if "caption_set" not in bot_data:
        bot_data["caption_set"] = {}
    bot_data["caption_set"][query.from_user.id] = {"channel_id": channel_id, "msg_id": msg.id}


# ---------------- Set Caption -----------------------------------
@Client.on_message(filters.private)
async def capture_caption(bot, message):
    user_id = message.from_user.id
    
    if "caption_set" in bot_data and user_id in bot_data["caption_set"]:
        channel_id = bot_data["caption_set"][user_id]["channel_id"]
        
        # Save the caption to DB
        caption_text = message.text
        if await get_channel_caption(channel_id):
            await updateCap(channel_id, caption_text)
        else:
            await addCap(channel_id, caption_text)

        # Delete user's message
        try:
            await message.delete()
        except:
            pass

        # Send confirmation with back button
        buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"setcap_{channel_id}")]]
        await bot.send_message(
            chat_id=user_id,
            text="✅ Caption successfully updated.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        # Clear session
        del bot_data["caption_set"][user_id]


@Client.on_callback_query(filters.regex(r'^delcap_(\d+)$'))
async def delete_caption(bot, query):
    channel_id = int(query.matches[0].group(1))
    await delete_channel_caption(channel_id)

    buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"setcap_{channel_id}")]]
    await query.message.edit_text(
        "✅ Caption deleted successfully. Now using default caption.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Client.on_callback_query(filters.regex(r'^capfont_(\d+)$'))
async def caption_font(bot, query):
    from Script import FONT_TXT

    channel_id = int(query.matches[0].group(1))
    buttons = [[InlineKeyboardButton("↩ Back", callback_data=f"setcap_{channel_id}")]]

    await query.message.edit_text(
        f"🖋️ Available fonts:\n\n{FONT_TXT}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )




