from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
from config import Config

mongo_client = AsyncIOMotorClient(Config().MONGO_URI)
db = mongo_client['lockonline']
houses = db['houses']
users_collection = db["users"]
payments_collection = db["payments"]

async def ensure_indexes():
    await payments_collection.create_index([("created_at", ASCENDING)])
    await users_collection.create_index([("user_id", ASCENDING)])