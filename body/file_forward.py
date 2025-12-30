import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from body.database import *

FF_SESSIONS = {}

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
    """
    Collect all media AFTER skip_id by probing message IDs forward.
    Does NOT use get_history (bots are not allowed).
    """

    s = FF_SESSIONS[uid]

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

        # no job -> idle
        if not job:
            await asyncio.sleep(1)
            continue

        msg_id = job.get("msg_id")
        print(f"[FORWARD] processing msg_id={msg_id}")

        try:
            await client.copy_message(
                chat_id=job["dst"],
                from_chat_id=job["src"],
                message_id=msg_id
            )

            # success
            await forward_done(job["_id"])

            # update UI
            await update_forward_progress(client, job)

            # small base delay to smooth bursts
            await asyncio.sleep(BASE_DELAY)

        # -------- FLOOD WAIT --------
        except FloodWait as e:
            delay = int(e.value) + 2

            # exponential backoff by retry count
            retries = job.get("retries", 0)
            delay += min(60, retries * 2)

            # anti-thundering herd (small random jitter)
            delay += int(time.time()) % 3

            print(f"[FORWARD] FloodWait {e.value}s -> reschedule after {delay}s")

            await forward_retry(job["_id"], delay)

            # DO NOT sleep entire FloodWait — free worker
            await asyncio.sleep(1)

        # -------- OTHER ERRORS --------
        except Exception as ex:
            print(f"[FORWARD ERROR] {repr(ex)} on msg {msg_id}")

            retries = job.get("retries", 0)

            if retries >= 5:
                # give up after 5 attempts
                await forward_done(job["_id"])
                continue

            # mild delay then retry
            await forward_retry(job["_id"], 10)
            await asyncio.sleep(1)

# ---------- PROGRESS ----------
async def update_forward_progress(client: Client, job):
    total = await forward_queue.count_documents({
        "src": job["src"],
        "dst": job["dst"]
    }) + 1
    remaining = await forward_queue.count_documents({
        "src": job["src"],
        "dst": job["dst"]
    })
    sent = total - remaining
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
    if s:
        await forward_queue.delete_many({
            "src": s["source"],
            "dst": s["destination"]
        })
    await query.message.edit_text("❌ **Forwarding cancelled successfully.**")




