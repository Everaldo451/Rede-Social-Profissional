import os

from pymongo import MongoClient


mongo_client = MongoClient(
    os.getenv("MONGO_URI", "mongodb://mongodb:27017")
)


def get_mongo_client() -> MongoClient:
    """Return the shared MongoDB client."""
    return mongo_client
