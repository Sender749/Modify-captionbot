import asyncio
import time
import uuid
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from body.database import *

FF_SESSIONS = {}
CANCELLED_SESSIONS = set()
FORWARD_WORKERS = 2
BASE_DELAY = 0.6

# ---------- START WORKERS ----------
def on_bot_start(client: Client):
    for _ in range(FORWARD_WORKERS):
        asyncio.create_task(forward_worker(client))

# ---------- SOURCE ----------
@Client.on_callback_query(filters.regex(r"^ff_src_(-?\d+)$"))
async def ff_src(client, query):
    uid = query.from_user.id
    s = FF_SESSIONS.get(uid)
    if not s:
        return

    src = int(query.matches[0].group(1))
    s["source"] = src
    s["source_title"] = next(x["channel_title"] for x in s["channels"] if x["channel_id"] == src)
    s["channels"] = [x for x in s["channels"] if x["channel_id"] != src]
    s["step"] = "dst"

    kb = [[InlineKeyboardButton(x["channel_title"], callback_data=f"ff_dst_{x['channel_id']}")] for x in s["channels"]]
    kb.append([InlineKeyboardButton("❌ Cancel", callback_data="ff_cancel")])

    await query.message.edit_text(
        "📥 **Select DESTINATION channel**",
        reply_markup=InlineKeyboardMarkup(kb)
    )


# ---------- DEST ----------
@Client.on_callback_query(filters.regex(r"^ff_dst_(-?\d+)$"))
async def ff_dst(client, query):
    uid = query.from_user.id
    s = FF_SESSIONS.get(uid)
    if not s:
        return
    dst = int(query.matches[0].group(1))
    s["destination"] = dst
    s["destination_title"] = next(
        x["channel_title"] for x in s["channels"] if x["channel_id"] == dst
    )
    s["step"] = "skip"
    s["chat_id"] = query.message.chat.id
    s["msg_id"] = query.message.id
    s["expires"] = time.time() + 900   # 15 minutes
    await query.message.edit_text(
        "⏭ <b>Send MESSAGE LINK or MESSAGE ID to skip upto</b>\n\n"
        "Example:\n"
        "`https://t.me/c/1815162626/2458`\n\n"
        "• Forwarding starts <b>AFTER</b> this message\n"
        "• Session expires in <b>15 minutes</b>",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Cancel", callback_data="ff_cancel")]]
        ),
        disable_web_page_preview=True
    )

# ---------- ENQUEUE ----------
async def enqueue_forward_jobs(client: Client, uid: int):
    s = FF_SESSIONS[uid]
    if "session_id" not in s:
        s["session_id"] = str(uuid.uuid4())
    session_id = s["session_id"]
    src = s["source"]
    dst = s["destination"]
    skip_id = int(s["skip"])

    print(f"[FF] START ENQUEUE src={src} dst={dst} skip={skip_id}")

    s["total"] = 0
    msg_id = skip_id + 1

    # internal safety stop (prevents infinite loop only)
    consecutive_missing = 0
    MAX_CONSECUTIVE_MISSING = 500

    while True:
        try:
            msg = await client.get_messages(src, msg_id)
        except Exception:
            msg = None

        # -------- no such message id --------
        if not msg:
            consecutive_missing += 1

            if consecutive_missing >= MAX_CONSECUTIVE_MISSING:
                print("[FF] stopping: too many missing IDs ahead")
                break

            msg_id += 1
            continue

        # reset gap counter
        consecutive_missing = 0

        # -------- visible but not media --------
        if not msg.media:
            msg_id += 1
            continue

        # -------- enqueue --------
        await enqueue_forward({
            "user_id": uid,
            "src": src,
            "dst": dst,
            "msg_id": msg.id,
            "chat_id": s["chat_id"],
            "ui_msg": s["msg_id"],
            "source_title": s["source_title"],
            "destination_title": s["destination_title"],
            "session_id": session_id,
            "total": 0
        })

        s["total"] += 1
        msg_id += 1

    # store total count for progress display
    await forward_queue.update_many(
        {"src": src, "dst": dst, "total": 0},
        {"$set": {"total": s["total"]}}
    )

    print(f"[FF] ENQUEUED TOTAL = {s['total']}")

    # final UI update
    await client.edit_message_text(
        s["chat_id"],
        s["msg_id"],
        (
            "🚚 <b>Forwarding started</b>\n\n"
            f"📤 {s['source_title']}\n"
            f"📥 {s['destination_title']}\n"
            f"📦 Total files: <code>{s['total']}</code>"
        ),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Cancel", callback_data="ff_cancel")]]
        )
    )

# ---------- WORKER ----------
async def forward_worker(client: Client):
    print("[FORWARD] worker started")

    while True:
        job = await fetch_forward_job()

        if not job:
            await asyncio.sleep(1)
            continue

        session_id = job.get("session_id")

        # cancelled? drop silently
        if session_id in CANCELLED_SESSIONS:
            await forward_done(job["_id"])
            continue

        msg_id = job.get("msg_id")

        try:
            # check again just before sending
            if session_id in CANCELLED_SESSIONS:
                await forward_done(job["_id"])
                continue

            await client.copy_message(
                chat_id=job["dst"],
                from_chat_id=job["src"],
                message_id=msg_id
            )

            await forward_done(job["_id"])
            await update_forward_progress(client, job)
            await asyncio.sleep(BASE_DELAY)

        except FloodWait as e:
            delay = int(e.value) + 2
            retries = job.get("retries", 0)
            delay += min(60, retries * 2)

            await forward_retry(job["_id"], delay)
            await asyncio.sleep(1)

        except Exception:
            await forward_done(job["_id"])
            await asyncio.sleep(0.5)


# ---------- PROGRESS ----------
async def update_forward_progress(client: Client, job):
    session = job.get("session_id")
    total = await forward_queue.count_documents(
        {"session_id": session}
    ) + 1
    remaining = await forward_queue.count_documents(
        {"session_id": session}
    )
    sent = total - remaining
    if session in CANCELLED_SESSIONS:
        return
    text = (
        "🚚 <b>Forwarding in progress…</b>\n\n"
        f"📤 <b>Source:</b> {job['source_title']}\n"
        f"📥 <b>Destination:</b> {job['destination_title']}\n\n"
        f"📦 <b>Sent:</b> <code>{sent}</code>\n"
        f"🗂 <b>Total:</b> <code>{total}</code>\n"
    )
    try:
        await client.edit_message_text(
            job["chat_id"],
            job["ui_msg"],
            text,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Cancel", callback_data="ff_cancel")]]
            )
        )
    except:
        pass
    if sent >= total:
        try:
            await client.edit_message_text(
                job["chat_id"],
                job["ui_msg"],
                (
                    "✅ <b>Forwarding completed</b>\n\n"
                    f"📤 <b>Source:</b> {job['source_title']}\n"
                    f"📥 <b>Destination:</b> {job['destination_title']}\n\n"
                    f"📦 <b>Total files forwarded:</b> <code>{total}</code>"
                )
            )
        except:
            pass

# ---------- CANCEL ----------
@Client.on_callback_query(filters.regex("^ff_cancel$"))
async def ff_cancel(client, query):
    uid = query.from_user.id

    s = FF_SESSIONS.pop(uid, None)

    if not s:
        await query.message.edit_text("❌ Nothing to cancel.")
        return

    session_id = s.get("session_id")

    if session_id:
        CANCELLED_SESSIONS.add(session_id)

        remaining = await forward_queue.count_documents(
            {"session_id": session_id}
        )

        total = s.get("total", 0)
        sent = max(total - remaining, 0)

        await forward_queue.delete_many(
            {"session_id": session_id}
        )

        await query.message.edit_text(
            "🛑 <b>Forwarding cancelled</b>\n\n"
            f"📦 <b>Files sent:</b> <code>{sent}</code>\n"
            f"🗂 <b>Initially detected:</b> <code>{total}</code>"
        )
    else:
        await query.message.edit_text("🛑 Cancelled.")





