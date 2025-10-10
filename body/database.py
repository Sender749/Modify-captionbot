import motor.motor_asyncio
from info import *

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DB)
db = client.captions_with_chnl
chnl_ids = db.chnl_ids
users = db.users
user_channels = db.user_channels 

# ---------------- User functions ----------------
async def insert_user(user_id: int):
    """Add user to DB if not exists"""
    try:
        await users.update_one({"_id": user_id}, {"$setOnInsert": {"channels": []}}, upsert=True)
    except:
        pass

async def total_user():
    return await users.count_documents({})

async def get_all_users():
    return users.find({})

async def delete_user(user_id):
    await users.delete_one({"_id": user_id})

# ---------------- Channel functions ----------------
async def add_channel(user_id: int, channel_id: int, channel_title: str):
    """Add channel to user channels"""
    await users.update_one(
        {"_id": user_id},
        {"$addToSet": {"channels": {"channel_id": channel_id, "channel_title": channel_title}}},
        upsert=True
    )

async def get_user_channels(user_id: int):
    """Get all channels added by user"""
    user = await users.find_one({"_id": user_id})
    return user.get("channels", []) if user else []

# ---------------- Caption functions ----------------
async def addCap(chnl_id: int, caption: str):
    dets = {"chnl_id": chnl_id, "caption": caption}
    await chnl_ids.insert_one(dets)

async def updateCap(chnl_id: int, caption: str):
    await chnl_ids.update_one({"chnl_id": chnl_id}, {"$set": {"caption": caption}})

async def get_channel_caption(chnl_id: int):
    return await chnl_ids.find_one({"chnl_id": chnl_id})

async def delete_channel_caption(chnl_id: int):
    await chnl_ids.delete_one({"chnl_id": chnl_id})
