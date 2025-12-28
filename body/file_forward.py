import asyncio
import time
from collections import defaultdict, deque
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from body.database import *

FF_SESSIONS = {}

FORWARD_WORKERS = 2
BASE_DELAY = 0.6


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
    s["destination_title"] = next(x["channel_title"] for x in s["channels"] if x["channel_id"] == dst)
    s["step"] = "skip"
    s["chat_id"] = query.message.chat.id
    s["msg_id"] = query.message.id
    s["expires"] = time.time() + 900  # in seconds
    await query.message.edit_text(
        "⏭ **Send MESSAGE LINK to skip up to**\n\n"
        "Example:\n"
        "`https://t.me/c/1815162626/2458`\n\n"
        "• Bot will start AFTER that message\n"
        "• Expires in 15 minutes"
    )


# ---------- ENQUEUE ----------
async def enqueue_forward_jobs(client: Client, uid: int):
    s = FF_SESSIONS[uid]
    src = s["source"]
    dst = s["destination"]
    skip_id = s["skip"]
    s["total"] = 0
    async for msg in client.get_chat_history(src, offset_id=skip_id, reverse=True):
        if not msg.media:
            continue
        await enqueue_forward({
            "user_id": uid,
            "src": src,
            "dst": dst,
            "msg_id": msg.id,
            "chat_id": s["chat_id"],
            "ui_msg": s["msg_id"],
            "source_title": s["source_title"],
            "destination_title": s["destination_title"],
            "total": None
        })
        s["total"] += 1
    if s["total"] == 0:
        await client.edit_message_text(
            s["chat_id"],
            s["msg_id"],
            "⚠️ **No files found after this message ID**"
        )
        FF_SESSIONS.pop(uid, None)
        return
    await forward_queue.update_many(
        {"src": src, "dst": dst, "total": None},
        {"$set": {"total": s["total"]}}
    )
    await client.edit_message_text(
        s["chat_id"],
        s["msg_id"],
        f"🚚 **Forwarding started**\n\n"
        f"📤 {s['source_title']}\n"
        f"📥 {s['destination_title']}\n"
        f"📦 Total files: `{total}`",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Cancel", callback_data="ff_cancel")]]
        )
    )

# ---------- WORKER ----------
async def forward_worker(client: Client):
    while True:
        job = await fetch_forward_job()
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

            # auto-clear session when done
            remaining = await forward_queue.count_documents({
                "src": job["src"],
                "dst": job["dst"]
            })
            if remaining == 0:
                FF_SESSIONS.pop(job.get("user_id"), None)

            await asyncio.sleep(BASE_DELAY)

        except FloodWait as e:
            await forward_retry(job["_id"], e.value + 2)
            await asyncio.sleep(e.value)

        except Exception:
            await forward_retry(job["_id"], 5)


# ---------- PROGRESS ----------
async def update_forward_progress(client: Client, job):
    total = job.get("total", 0)
    done = total - await forward_queue.count_documents({
        "src": job["src"],
        "dst": job["dst"]
    })
    elapsed = time.time() - job.get("started", time.time())
    speed = done / elapsed if elapsed else 0
    eta = (total - done) / speed if speed else 0
    text = (
        "🚚 **File Forwarding**\n\n"
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
            f"✅ **Completed**\n\n"
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

# ---------- START WORKERS ----------
def on_bot_start(client: Client):
    for _ in range(FORWARD_WORKERS):
        asyncio.create_task(forward_worker(client))


