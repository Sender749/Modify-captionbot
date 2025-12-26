import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait
from body.database import get_user_channels

# ================= SESSION STORAGE =================
FF_SESSIONS = {}     # user_id -> session
FF_TASKS = {}        # user_id -> asyncio.Task


# ================= HELPERS =================
def progress_bar(done: int, total: int, size: int = 20) -> str:
    if total == 0:
        return "░" * size
    filled = int(size * done / total)
    return "█" * filled + "░" * (size - filled)


def format_time(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


# ================= STEP 1: COMMAND =================
@Client.on_message(filters.private & filters.command("file_forward"))
async def file_forward_cmd(client, message):
    user_id = message.from_user.id
    channels = await get_user_channels(user_id)

    if not channels:
        return await message.reply_text("❌ You don’t have any channels where I’m admin.")

    buttons = [
        [InlineKeyboardButton(ch["channel_title"], callback_data=f"ff_src_{ch['channel_id']}")]
        for ch in channels
    ]
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="ff_cancel")])

    FF_SESSIONS[user_id] = {
        "step": "select_source",
        "channels": channels
    }

    await message.reply_text(
        "📤 **Select SOURCE channel**\n(files will be taken from here)",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ================= STEP 2: SOURCE =================
@Client.on_callback_query(filters.regex(r"^ff_src_(-?\d+)$"))
async def ff_select_source(client, query: CallbackQuery):
    user_id = query.from_user.id
    src_id = int(query.matches[0].group(1))
    session = FF_SESSIONS.get(user_id)

    session["source"] = src_id
    session["source_title"] = next(
        c["channel_title"] for c in session["channels"] if c["channel_id"] == src_id
    )

    remaining = [c for c in session["channels"] if c["channel_id"] != src_id]
    session["channels"] = remaining
    session["step"] = "select_dest"

    buttons = [
        [InlineKeyboardButton(ch["channel_title"], callback_data=f"ff_dst_{ch['channel_id']}")]
        for ch in remaining
    ]
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="ff_cancel")])

    await query.message.edit_text(
        "📥 **Select DESTINATION channel**\n(files will be sent here)",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ================= STEP 3: DESTINATION =================
@Client.on_callback_query(filters.regex(r"^ff_dst_(-?\d+)$"))
async def ff_select_dest(client, query: CallbackQuery):
    user_id = query.from_user.id
    dst_id = int(query.matches[0].group(1))
    session = FF_SESSIONS.get(user_id)

    session["destination"] = dst_id
    session["destination_title"] = next(
        c["channel_title"] for c in session["channels"] if c["channel_id"] == dst_id
    )

    session["step"] = "skip"
    session["chat_id"] = query.message.chat.id
    session["msg_id"] = query.message.id

    await query.message.edit_text(
        "⏭ **How many FIRST (oldest) messages to SKIP?**\n\n"
        "• Example: `249` → skip first 249 messages\n"
        "• Send `0` → don’t skip anything\n\n"
        "📌 Skipping starts from the TOP (oldest messages)"
    )


# ================= STEP 4: SKIP COUNT =================
@Client.on_message(filters.private & filters.text)
async def ff_receive_skip(client, message):
    user_id = message.from_user.id
    session = FF_SESSIONS.get(user_id)

    if not session or session.get("step") != "skip":
        return

    try:
        skip = int(message.text.strip())
        if skip < 0:
            return
    except:
        return

    session["skip"] = skip
    session["step"] = "running"

    task = asyncio.create_task(ff_start_forward(client, user_id))
    FF_TASKS[user_id] = task


# ================= CORE FORWARD =================
async def ff_start_forward(client, user_id):
    session = FF_SESSIONS[user_id]

    src = session["source"]
    dst = session["destination"]
    skip = session["skip"]

    chat_id = session["chat_id"]
    msg_id = session["msg_id"]

    src_name = session["source_title"]
    dst_name = session["destination_title"]

    start_time = time.time()

    # -------- COUNT TOTAL FILES (after skip) --------
    total = 0
    idx = 0
    async for m in client.get_chat_history(src, reverse=True):
        if not m.media:
            continue
        idx += 1
        if idx <= skip:
            continue
        total += 1

    done = 0
    idx = 0

    async for m in client.get_chat_history(src, reverse=True):
        if not m.media:
            continue

        idx += 1
        if idx <= skip:
            continue

        try:
            await m.copy(dst)
            done += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await m.copy(dst)
            done += 1
        except Exception:
            continue

        elapsed = time.time() - start_time
        speed = done / elapsed if elapsed > 0 else 0
        eta = (total - done) / speed if speed > 0 else 0

        bar = progress_bar(done, total)

        text = (
            f"🚚 **File Forwarding**\n\n"
            f"📤 **From:** {src_name}\n"
            f"📥 **To:** {dst_name}\n\n"
            f"{bar}\n"
            f"📦 {done} / {total}\n"
            f"⏱ ETA: {format_time(eta)}"
        )

        try:
            await client.edit_message_text(
                chat_id,
                msg_id,
                text,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("❌ Cancel", callback_data="ff_cancel")]]
                )
            )
        except:
            pass

    await client.edit_message_text(
        chat_id,
        msg_id,
        f"✅ **Forwarding Completed**\n\n"
        f"📤 From: {src_name}\n"
        f"📥 To: {dst_name}\n"
        f"📦 Files forwarded: {done}"
    )

    FF_SESSIONS.pop(user_id, None)
    FF_TASKS.pop(user_id, None)


# ================= CANCEL =================
@Client.on_callback_query(filters.regex("^ff_cancel$"))
async def ff_cancel(client, query: CallbackQuery):
    user_id = query.from_user.id

    task = FF_TASKS.get(user_id)
    if task:
        task.cancel()

    FF_SESSIONS.pop(user_id, None)
    FF_TASKS.pop(user_id, None)

    await query.message.edit_text("❌ **File forwarding cancelled.**")
