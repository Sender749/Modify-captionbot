import motor.motor_asyncio
from info import *

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DB)
db = client.captions_with_chnl
chnl_ids = db.chnl_ids
users = db.users
user_channels = db.user_channels 

# ---------------- Caption functions ----------------
async def addCap(chnl_id, caption):
    dets = {"chnl_id": chnl_id, "caption": caption}
    await chnl_ids.insert_one(dets)

async def updateCap(chnl_id, caption):
    await chnl_ids.update_one({"chnl_id": chnl_id}, {"$set": {"caption": caption}})

async def get_channel_caption(chnl_id: int):
    return await chnl_ids.find_one({"chnl_id": chnl_id})

async def delete_channel_caption(chnl_id: int):
    await chnl_ids.delete_one({"chnl_id": chnl_id})

# ---------------- User functions ----------------
async def insert(user_id):
    user_det = {"_id": user_id}
    try:
        await users.insert_one(user_det)
    except:
        pass
        
async def total_user():
    user = await users.count_documents({})
    return user

async def getid():
    all_users = users.find({})
    return all_users

async def delete(id):
    await users.delete_one(id)
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
