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
                time.sleep(1)
                await message.reply_to_message.copy(user['_id'])
                success += 1
            except errors.InputUserDeactivated:
                deactivated +=1
                await delete({"_id": user['_id']})
            except errors.UserIsBlocked:
                blocked +=1
                await delete({"_id": user['_id']})
            except Exception as e:
                failed += 1
                await delete({"_id": user['_id']})
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
async def on_bot_added(bot, update):
    try:
        if update.new_chat_member and update.new_chat_member.user.id == bot.me.id:
            if update.new_chat_member.status == "administrator":
                channel_id = update.chat.id
                channel_title = update.chat.title

                # Save channel to user who added bot
                if update.from_user:
                    await add_channel(update.from_user.id, channel_id, channel_title)
                    try:
                        await bot.send_message(
                            chat_id=update.from_user.id,
                            text=f"✅ Bot is now admin in **{channel_title}**."
                        )
                    except Exception as e:
                        print(f"Failed to send PM: {e}")

    except Exception as e:
        print(f"on_chat_member_updated error: {e}")
