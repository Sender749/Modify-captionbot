from pyrogram import Client, errors
from info import *

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Auto Cap",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=200,
            plugins={"root": "body"},
            sleep_threshold=15,
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.force_channel = FORCE_SUB

        if FORCE_SUB:
            try:
                link = await self.export_chat_invite_link(FORCE_SUB)
                self.invitelink = link
            except Exception as e:
                print(e)
                print("Make Sure Bot admin in force sub channel")
                self.force_channel = None

        try:
            await self.get_chat(int(LOG_CH))
            await self.get_chat(int(DUMP_CH))
            print("✅ Log and Dump channels cached successfully.")
        except errors.PeerIdInvalid:
            print("⚠️ Peer ID invalid for LOG_CH or DUMP_CH — Make sure bot is admin in both.")
        except Exception as e:
            print(f"⚠️ Error caching log/dump channels: {e}")

        # ---- BOT START MESSAGE ----
        print(f"{me.first_name} Iꜱ Sᴛᴀʀᴛᴇᴅ.....✨️")
        try:
            await self.send_message(ADMIN, f"**{me.first_name} Iꜱ Sᴛᴀʀᴛᴇᴅ.....✨️**")
        except Exception as e:
            print(f"⚠️ Could not send start message to admin: {e}")

Bot().run()
