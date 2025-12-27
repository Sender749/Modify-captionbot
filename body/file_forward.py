import asyncio
import time
from collections import defaultdict, deque
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from body.database import *

FF_SESSIONS = {}
FORWARD_QUEUE = defaultdict(deque)   # key: source_channel_id -> deque[jobs]
FORWARD_ORDER = deque()              # round-robin order of channels
FORWARD_LOCK = asyncio.Lock()
FORWARD_WORKERS = 2        # safe default
BASE_DELAY = 0.6           # safe Telegram rate

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

@Client.on_callback_query(filters.regex(r"^ff_src_(-?\d+)$"))
async def ff_src(client, query):
    uid = query.from_user.id
    s = FF_SESSIONS.get(uid)
    if not s:
        return
    src = int(query.matches[0].group(1))
    s["source"] = src
    s["source_title"] = next(
        x["channel_title"] for x in s["channels"] if x["channel_id"] == src
    )
    s["channels"] = [x for x in s["channels"] if x["channel_id"] != src]
    s["step"] = "dst"
    kb = [
        [InlineKeyboardButton(ch["channel_title"], callback_data=f"ff_dst_{ch['channel_id']}")]
        for ch in s["channels"]
    ]
    kb.append([InlineKeyboardButton("❌ Cancel", callback_data="ff_cancel")])
    await query.message.edit_text(
        "📥 **Select DESTINATION channel**",
        reply_markup=InlineKeyboardMarkup(kb)
    )

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
    await query.message.edit_text(
        "⏭ **How many FIRST (oldest) messages to SKIP?**\n\n"
        "• Send `0` to skip none\n"
        "• Example: `249`\n\n"
        "📌 Skipping starts from TOP"
    )

@Client.on_message(filters.private & filters.regex(r"^\d+$"))
async def ff_skip(client, message):
    uid = message.from_user.id
    s = FF_SESSIONS.get(uid)
    if not s or s.get("step") != "skip":
        return
    skip = int(message.text)
    s["skip"] = skip
    s["step"] = "queue"
    await enqueue_forward_jobs(client, uid)

async def enqueue_forward_jobs(client, uid):
    s = FF_SESSIONS[uid]
    src = s["source"]
    dst = s["destination"]
    skip = s["skip"]
    total = 0
    idx = 0
    async with FORWARD_LOCK:
        async for msg in client.get_chat_history(src, reverse=True):
            if not msg.media:
                continue
            idx += 1
            if idx <= skip:
                continue
            job = {
                "user": uid,
                "src": src,
                "dst": dst,
                "msg_id": msg.id,
                "source_title": s["source_title"],
                "destination_title": s["destination_title"],
                "chat_id": s["chat_id"],
                "ui_msg": s["msg_id"],
                "done": 0,
                "total": None,
                "start": time.time()
            }
            FORWARD_QUEUE[src].append(job)
            if src not in FORWARD_ORDER:
                FORWARD_ORDER.append(src)
            total += 1
        for q in FORWARD_QUEUE[src]:
            q["total"] = total
    await client.edit_message_text(
        s["chat_id"],
        s["msg_id"],
        f"🚚 **Forwarding started**\n\n"
        f"📤 {s['source_title']}\n"
        f"📥 {s['destination_title']}\n\n"
        f"📦 Total files: `{total}`",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Cancel", callback_data="ff_cancel")]]
        )
    )

async def forward_worker(client: Client):
    print("[FORWARD] Worker started")
    while True:
        job = None
        async with FORWARD_LOCK:
            if FORWARD_ORDER:
                ch = FORWARD_ORDER.popleft()
                q = FORWARD_QUEUE.get(ch)

                if q:
                    job = q.popleft()
                    if q:
                        FORWARD_ORDER.append(ch)
                    else:
                        FORWARD_QUEUE.pop(ch, None)
        if not job:
            await asyncio.sleep(0.5)
            continue
        try:
            await client.copy_message(
                chat_id=job["dst"],
                from_chat_id=job["src"],
                message_id=job["msg_id"]
            )

            job["done"] += 1
            await update_progress(client, job)
            await asyncio.sleep(BASE_DELAY)
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            async with FORWARD_LOCK:
                FORWARD_QUEUE[job["src"]].appendleft(job)
                if job["src"] not in FORWARD_ORDER:
                    FORWARD_ORDER.append(job["src"])
        except Exception:
            await asyncio.sleep(2)

async def update_progress(client, job):
    done = job["done"]
    total = job["total"]
    elapsed = time.time() - job["start"]
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

@Client.on_callback_query(filters.regex("^ff_cancel$"))
async def ff_cancel(client, query):
    uid = query.from_user.id
    FF_SESSIONS.pop(uid, None)
    await query.message.edit_text("❌ Forwarding cancelled.")

def on_bot_start(client: Client):
    for _ in range(FORWARD_WORKERS):
        asyncio.create_task(forward_worker(client))
