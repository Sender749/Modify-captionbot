import motor.motor_asyncio
from info import *

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DB)
db = client.captions_with_chnl
chnl_ids = db.chnl_ids
users = db.users

async def addCap(chnl_id, caption):
    dets = {"chnl_id": chnl_id, "caption": caption}
    await chnl_ids.insert_one(dets)


async def updateCap(chnl_id, caption):
    await chnl_ids.update_one({"chnl_id": chnl_id}, {"$set": {"caption": caption}})

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

user_channels = db.user_channels  # NEW COLLECTION

async def add_user_channel(user_id, channel_id, channel_title):
    """Add a channel for a user if not exists"""
    existing = await user_channels.find_one({"user_id": user_id, "channel_id": channel_id})
    if not existing:
        await user_channels.insert_one({
            "user_id": user_id,
            "channel_id": channel_id,
            "channel_title": channel_title
        })

async def get_user_channels(user_id):
    """Return list of channels added by a user"""
    cursor = user_channels.find({"user_id": user_id})
    return [doc async for doc in cursor]
