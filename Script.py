import os

class script(object):

    START_TXT = """<b>Hᴇʟʟᴏ {mention}\n
ɪ ᴀᴍ ᴛʜᴇ ᴍᴏꜱᴛ ᴘᴏᴡᴇʀꜰᴜʟ ᴀᴜᴛᴏ ᴄᴀᴘᴛɪᴏɴ ʙᴏᴛ ᴡɪᴛʜ ᴘʀᴇᴍɪᴜᴍ ꜰᴇᴀᴛᴜʀᴇꜱ, ᴊᴜsᴛ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ cʜᴀɴɴᴇʟ ᴀɴᴅ ᴇɴᴊᴏʏ
</b>
"""

    NEW_USER_TXT = (
    "👤 <b>New User Started the Bot</b>\n\n"
    "🙋‍♂️ <b>User:</b> {user}\n"
    "🆔 <b>User ID:</b> <code>{user_id}</code>"
)

    NEW_CHANNEL_TXT = (
    "📥 <b>Bot Added to Channel</b>\n\n"
    "👤 <b>By User:</b> {owner_name} (<code>{owner_id}</code>)\n"
    "📢 <b>Channel:</b> {channel_name}\n"
    "🆔 <b>Channel ID:</b> <code>{channel_id}</code>"
)

    HELP_TEXT = """
✨ **How to Use This Bot**

1️⃣ **Add Bot to Channel**  
→ Add this bot to your channel as **Admin** with all permissions.  

2️⃣ **Open Settings**  
→ After adding, go to `/settings`  
→ Select your channel from the list.

3️⃣ **Customize Channel Caption**  
🖊️ Set a default caption for all uploaded media.

4️⃣ **Replace Words**  
✏️ Automatically replace specific words in captions.  
Example: `old new, hello hi`

5️⃣ **Block Words**  
🚫 Remove unwanted or bad words from captions.

6️⃣ **Prefix & Suffix**  
🔠 Add text before (prefix) or after (suffix) the caption.

7️⃣ **Link Remover**  
🔗 Turn **ON/OFF** automatic link removal from captions.

✅ That’s it!  
Your channel captions will now be fully automatic ✨
"""

    ABOUT_TXT = """<b>╔════❰ ᴀᴜᴛᴏ ᴄᴀᴘᴛɪᴏɴ ʙᴏᴛ ❱═❍⊱❁
║╭━━━━━━━━━━━━━━━➣
║┣⪼📃ʙᴏᴛ : <a href='https://t.me/CustomCaptionBot'>Auto Caption</a>
║┣⪼👦Cʀᴇᴀᴛᴏʀ : <a href='https://t.me/Silicon_Official'>Sɪʟɪᴄᴏɴ Dᴇᴠᴇʟᴏᴘᴇʀ ⚠️</a>
║┣⪼🤖Uᴘᴅᴀᴛᴇ : <a href='https://t.me/Silicon_Bot_Update'>Sɪʟɪᴄᴏɴ Bᴏᴛᴢ™</a>
║┣⪼📡Hᴏsᴛᴇᴅ ᴏɴ : ʜᴇʀᴏᴋᴜ 
║┣⪼🗣️Lᴀɴɢᴜᴀɢᴇ : Pʏᴛʜᴏɴ3
║┣⪼📚Lɪʙʀᴀʀʏ : Pʏʀᴏɢʀᴀᴍ 2.11.6
║┣⪼🗒️Vᴇʀsɪᴏɴ : 2.0.8 [ᴍᴏsᴛ sᴛᴀʙʟᴇ]
║╰━━━━━━━━━━━━━━━➣
╚══════════════════❍⊱❁</b>"""

    FONT_TXT = """🔰 About Caption Font

➢ Bold Text
☞ <code>&lt;b&gt;{file_name}&lt;/b&gt;</code>

➢ Spoiler Text
☞ <code>&lt;spoiler&gt;{file_name}&lt;/spoiler&gt;</code>

➢ Preformatted Text
☞ <code>&lt;pre&gt;{file_name}&lt;/pre&gt;</code>

➢ Block Quote Text
☞ <code>&lt;blockquote&gt;{file_name}&lt;/blockquote&gt;</code>
☞ <code>&lt;blockquote expandable&gt;{file_name}&lt;/blockquote&gt;</code>

➢ Italic Text
☞ <code>&lt;i&gt;{file_name}&lt;/i&gt;</code>

➢ Underline Text
☞ <code>&lt;u&gt;{file_name}&lt;/u&gt;</code>

➢ Strike Text
☞ <code>&lt;s&gt;{file_name}&lt;/s&gt;</code>

➢ Mono Text
☞ <code>&lt;code&gt;{file_name}&lt;/code&gt;</code>

➢ Hyperlink Text
☞ <code>&lt;a href="https://t.me/Navex_Movies"&gt;{file_name}&lt;/a&gt;</code>
"""
