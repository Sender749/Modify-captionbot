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

# ---------- UI HELPERS ----------
def bar(done, total, size=20):
    if total <= 0:
        return "░" * size
    filled = int(size * done / total)
    return "█" * filled + "░" * (size - filled)

def fmt(sec):
    sec = int(sec)
    if sec < 60:
        return f"{sec}s"
    m, s = divmod(sec, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


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

    src = s["source"]
    dst = s["destination"]
    skip_id = s["skip"]

    s["total"] = 0
    collected = []

    # start scanning immediately after skipped message
    current = skip_id + 1

    # stop after N missing messages in a row → means end of chat reached
    missing_streak = 0
    MAX_MISSING = 30

    while True:
        try:
            msg = await client.get_messages(src, current)
        except Exception:
            msg = None

        if not msg:
            missing_streak += 1
            if missing_streak >= MAX_MISSING:
                break
            current += 1
            continue

        missing_streak = 0

        # collect only messages with media
        if msg.media:
            collected.append(msg)

        current += 1

    # enqueue in oldest → newest order
    for msg in collected:
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

    # nothing found
    if s["total"] == 0:
        await client.edit_message_text(
            s["chat_id"],
            s["msg_id"],
            "⚠️ No media messages found after this message ID."
        )
        FF_SESSIONS.pop(uid, None)
        return

    # store total count in queued docs
    await forward_queue.update_many(
        {"src": src, "dst": dst, "total": 0},
        {"$set": {"total": s["total"]}}
    )

    # UI update
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
        print("[FORWARD] fetched job:", job)
        if not job:
            await asyncio.sleep(1)
            continue
        try:
            await client.copy_message(
                chat_id=job["dst"],
                from_chat_id=job["src"],
                message_id=job["msg_id"]
            )
            await forward_done(job["_id"])
            await update_forward_progress(client, job)
        except FloodWait as e:
            print(f"[FORWARD] FloodWait {e.value}s")
            await forward_retry(job["_id"], e.value + 2)
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"[FORWARD ERROR] {repr(e)} on msg {job['msg_id']}")
            await forward_retry(job["_id"], 5)
        await asyncio.sleep(BASE_DELAY)


# ---------- PROGRESS ----------
async def update_forward_progress(client: Client, job):
    total = job.get("total", 0)
    remaining = await forward_queue.count_documents({
        "src": job["src"],
        "dst": job["dst"]
    })
    done = total - remaining
    elapsed = time.time() - job.get("started", time.time())
    speed = done / elapsed if elapsed else 0
    eta = (total - done) / speed if speed else 0
    text = (
        "🚚 <b>File Forwarding</b>\n\n"
        f"📤 {job['source_title']}\n"
        f"📥 {job['destination_title']}\n\n"
        f"{bar(done, total)}\n"
        f"📦 {done}/{total}\n"
        f"⏱ ETA: {fmt(eta)}"
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
    if done >= total:
        await client.edit_message_text(
            job["chat_id"],
            job["ui_msg"],
            f"✅ <b>Completed</b>\n\n"
            f"📤 {job['source_title']}\n"
            f"📥 {job['destination_title']}\n"
            f"📦 {total} files forwarded"
        )

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




