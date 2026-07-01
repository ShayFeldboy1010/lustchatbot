"""Persistent storage for WhatsApp conversations.

Best-effort by design: every write is wrapped so a MongoDB hiccup can never
raise into (or delay) the live customer-facing webhook response.
"""

from datetime import datetime, timezone

from .mongodb import get_collection

COLLECTION_NAME = "conversations"


async def save_message(phone: str, name: str, role: str, content: str, escalated: bool = False) -> None:
    """Persist one WhatsApp message. Logs and swallows any failure."""
    try:
        collection = get_collection(COLLECTION_NAME)
        await collection.insert_one({
            "phone": phone,
            "name": name,
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc),
            "escalated": escalated,
        })
    except Exception as e:
        print(f"Failed to persist conversation message for {phone}: {e}")


async def ensure_indexes() -> None:
    """Create indexes on the conversations collection. Idempotent, safe on every startup."""
    try:
        collection = get_collection(COLLECTION_NAME)
        await collection.create_index("phone")
        await collection.create_index([("timestamp", -1)])
    except Exception as e:
        print(f"Failed to ensure conversation indexes: {e}")
