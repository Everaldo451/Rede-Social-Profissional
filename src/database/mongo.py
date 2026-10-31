import os

from pymongo import MongoClient
from pymongo.database import Database


mongo_client = MongoClient(
    os.getenv("MONGO_URI", "mongodb://mongodb:27017")
)
mongo_database = mongo_client.get_default_database(
    default=os.getenv("MONGO_DATABASE", "rede_social")
)


def get_mongo_database() -> Database:
    """Return the configured MongoDB database."""
    return mongo_database
