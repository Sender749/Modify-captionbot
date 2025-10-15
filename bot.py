from pyrogram import Client
import asyncio
from info import *
from body.database import (
    addCap, set_block_words, set_prefix, set_suffix,
    set_replace_words, set_link_remover_status,
    get_channel_caption, add_user_channel
)

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
        await self.startup_check()  
        self.force_channel = FORCE_SUB

        if FORCE_SUB:
            try:
                link = await self.export_chat_invite_link(FORCE_SUB)
                self.invitelink = link
            except Exception as e:
                print(e)
                print("Make sure bot is admin in the force sub channel")
                self.force_channel = None

        print(f"{me.first_name} Iꜱ Sᴛᴀʀᴛᴇᴅ.....✨️")
        await self.send_message(ADMIN, f"**{me.first_name}  Iꜱ Sᴛᴀʀᴛᴇᴅ.....✨️**")

    async def startup_check(self):
        """Check all channels where bot is admin when starting"""
        await asyncio.sleep(2)
        print("[INFO] Scanning all available channels for admin rights...")

        async for dialog in self.get_dialogs():
            chat = dialog.chat
            if chat.type == "channel":
                try:
                    member = await self.get_chat_member(chat.id, "me")
                    if member.status in ("administrator", "creator"):
                        # Save to DB (under default admin for now)
                        owner_id = ADMIN  # optional fallback if you want manual linking
                        await add_user_channel(owner_id, chat.id, chat.title or "Unnamed Channel")

                        existing = await get_channel_caption(chat.id)
                        if not existing:
                            await addCap(chat.id, DEF_CAP)
                            await set_block_words(chat.id, [])
                            await set_prefix(chat.id, "")
                            await set_suffix(chat.id, "")
                            await set_replace_words(chat.id, "")
                            await set_link_remover_status(chat.id, False)
                        print(f"[SYNC] Found admin access to channel: {chat.title} ({chat.id})")
                except Exception:
                    continue

        print("[INFO] Channel scan completed ✅")

    async def stop(self, *args):
        await super().stop()
        print("[INFO] Bot stopped ❌")


Bot().run()
