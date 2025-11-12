from pymongo import MongoClient
import certifi
from core.config import settings

client = MongoClient(settings.MONGO_URI, tlsCAFile=certifi.where())
db = client[settings.MONGO_DB_NAME]
assets_collection = db["assets"]
