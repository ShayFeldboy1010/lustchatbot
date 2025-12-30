"""MongoDB Connection Service"""

from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

from ..config import get_settings

settings = get_settings()

# Sync client (for vector store)
_sync_client: Optional[MongoClient] = None

# Async client (for other operations)
_async_client: Optional[AsyncIOMotorClient] = None


def get_sync_client() -> MongoClient:
    """Get synchronous MongoDB client"""
    global _sync_client

    if _sync_client is None:
        _sync_client = MongoClient(settings.mongodb_uri)

    return _sync_client


def get_async_client() -> AsyncIOMotorClient:
    """Get asynchronous MongoDB client"""
    global _async_client

    if _async_client is None:
        _async_client = AsyncIOMotorClient(settings.mongodb_uri)

    return _async_client


def get_database(async_client: bool = True):
    """Get database instance"""
    if async_client:
        client = get_async_client()
    else:
        client = get_sync_client()

    return client[settings.mongodb_database]


def get_collection(collection_name: str = None, async_client: bool = True):
    """Get collection instance"""
    db = get_database(async_client)
    return db[collection_name or settings.mongodb_collection]


async def check_connection() -> bool:
    """Check if MongoDB connection is healthy"""
    try:
        client = get_async_client()
        await client.admin.command('ping')
        return True
    except Exception as e:
        print(f"MongoDB connection error: {e}")
        return False


def close_connections():
    """Close all MongoDB connections"""
    global _sync_client, _async_client

    if _sync_client:
        _sync_client.close()
        _sync_client = None

    if _async_client:
        _async_client.close()
        _async_client = None
