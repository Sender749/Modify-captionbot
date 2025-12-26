import asyncio, time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait
from body.database import get_user_channels

FF_SESSIONS = {}
FF_TASKS = {}

def bar(d, t, s=20):
    if not t: return "░"*s
    f = int(s*d/t)
    return "█"*f + "░"*(s-f)

def fmt(sec):
    sec = int(sec)
    if sec < 60: return f"{sec}s"
    m, s = divmod(sec, 60)
    if m < 60: return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"

# ---------------- START ----------------
@Client.on_message(filters.private & filters.command("file_forward"))
async def ff_start(c, m):
    uid = m.from_user.id
    ch = await get_user_channels(uid)
    if not ch:
        return await m.reply_text("❌ No admin channels found.")

    FF_SESSIONS[uid] = {"step": "src", "channels": ch}

    kb = [[InlineKeyboardButton(x["channel_title"], callback_data=f"ff_src_{x['channel_id']}")] for x in ch]
    kb.append([InlineKeyboardButton("❌ Cancel", callback_data="ff_cancel")])

    await m.reply_text("📤 Select **SOURCE** channel", reply_markup=InlineKeyboardMarkup(kb))

# ---------------- SOURCE ----------------
@Client.on_callback_query(filters.regex(r"^ff_src_(-?\d+)$"))
async def ff_src(c, q):
    uid = q.from_user.id
    s = FF_SESSIONS[uid]
    src = int(q.matches[0].group(1))

    s["source"] = src
    s["source_title"] = next(x["channel_title"] for x in s["channels"] if x["channel_id"] == src)
    s["channels"] = [x for x in s["channels"] if x["channel_id"] != src]
    s["step"] = "dst"

    kb = [[InlineKeyboardButton(x["channel_title"], callback_data=f"ff_dst_{x['channel_id']}")] for x in s["channels"]]
    kb.append([InlineKeyboardButton("❌ Cancel", callback_data="ff_cancel")])

    await q.message.edit_text("📥 Select **DESTINATION** channel", reply_markup=InlineKeyboardMarkup(kb))

# ---------------- DEST ----------------
@Client.on_callback_query(filters.regex(r"^ff_dst_(-?\d+)$"))
async def ff_dst(c, q):
    uid = q.from_user.id
    s = FF_SESSIONS[uid]
    dst = int(q.matches[0].group(1))

    s["destination"] = dst
    s["destination_title"] = next(x["channel_title"] for x in s["channels"] if x["channel_id"] == dst)
    s["step"] = "skip"
    s["chat_id"] = q.message.chat.id
    s["msg_id"] = q.message.id

    await q.message.edit_text(
        "⏭ How many **FIRST (oldest)** messages to SKIP?\n\n"
        "• Send `0` to skip none\n"
        "• Example: `249`\n\n"
        "📌 Skipping starts from TOP"
    )

# ---------------- SKIP ----------------
@Client.on_message(filters.private & filters.text)
async def ff_skip(c, m):
    uid = m.from_user.id
    s = FF_SESSIONS.get(uid)
    if not s or s["step"] != "skip": return

    try:
        skip = int(m.text.strip())
        if skip < 0: return
    except:
        return

    s["skip"] = skip
    s["step"] = "run"

    t = asyncio.create_task(ff_run(c, uid))
    FF_TASKS[uid] = t

# ---------------- CORE ----------------
async def ff_run(c, uid):
    s = FF_SESSIONS[uid]
    src, dst, skip = s["source"], s["destination"], s["skip"]
    chat_id, msg_id = s["chat_id"], s["msg_id"]

    src_n, dst_n = s["source_title"], s["destination_title"]
    start = time.time()
    delay = 0.4

    total = idx = 0
    async for m in c.get_chat_history(src, reverse=True):
        if m.media:
            idx += 1
            if idx > skip: total += 1

    done = idx = 0

    async for m in c.get_chat_history(src, reverse=True):
        if not m.media: continue
        idx += 1
        if idx <= skip: continue

        try:
            await m.copy(dst)
            await asyncio.sleep(delay)
            done += 1

            if done == 20: delay = 0.6
            elif done == 100: delay = 0.8

        except FloodWait as e:
            await asyncio.sleep(e.value)
            delay += 0.2
            continue
        except:
            continue

        el = time.time() - start
        sp = done / el if el else 0
        eta = (total - done) / sp if sp else 0

        txt = (
            f"🚚 **File Forwarding**\n\n"
            f"📤 {src_n}\n📥 {dst_n}\n\n"
            f"{bar(done, total)}\n"
            f"📦 {done}/{total}\n"
            f"⏱ ETA: {fmt(eta)}"
        )

        try:
            await c.edit_message_text(
                chat_id, msg_id, txt,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("❌ Cancel", callback_data="ff_cancel")]]
                )
            )
        except:
            pass

    await c.edit_message_text(
        chat_id, msg_id,
        f"✅ **Completed**\n\n📤 {src_n}\n📥 {dst_n}\n📦 {done} files"
    )

    FF_SESSIONS.pop(uid, None)
    FF_TASKS.pop(uid, None)

# ---------------- CANCEL ----------------
@Client.on_callback_query(filters.regex("^ff_cancel$"))
async def ff_cancel(c, q):
    uid = q.from_user.id
    t = FF_TASKS.get(uid)
    if t: t.cancel()
    FF_SESSIONS.pop(uid, None)
    FF_TASKS.pop(uid, None)
    await q.message.edit_text("❌ Forwarding cancelled.")
