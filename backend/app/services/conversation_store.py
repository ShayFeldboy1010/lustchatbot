"""Persistent storage for WhatsApp conversations.

Best-effort by design: every write is wrapped so a MongoDB hiccup can never
raise into (or delay) the live customer-facing webhook response.
"""

from datetime import datetime, timezone

from .mongodb import get_collection

COLLECTION_NAME = "conversations"
# Per-customer control state (e.g. whether a human has taken the chat over from
# the bot). One document per phone, keyed by _id = phone.
STATE_COLLECTION = "conversation_state"


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


async def get_last_known_name(phone: str):
    """Return the most recent non-empty name stored for this phone, or None."""
    try:
        collection = get_collection(COLLECTION_NAME)
        doc = await collection.find_one(
            {"phone": phone, "name": {"$nin": [None, ""]}},
            sort=[("timestamp", -1)],
        )
        return doc.get("name") if doc else None
    except Exception as e:
        print(f"Failed to look up name for {phone}: {e}")
        return None


async def set_bot_paused(phone: str, paused: bool, reason: str = "agent") -> None:
    """Pause (human takeover) or resume the bot for one customer.

    `reason` records who paused it: "agent" (someone replied from the dashboard)
    or "escalation" (the bot handed the customer to a human).
    """
    try:
        collection = get_collection(STATE_COLLECTION)
        fields = {"bot_paused": paused, "updated_at": datetime.now(timezone.utc)}
        if paused:
            fields["paused_by"] = reason
        await collection.update_one({"_id": phone}, {"$set": fields}, upsert=True)
    except Exception as e:
        print(f"Failed to set bot_paused={paused} for {phone}: {e}")


async def set_ordered(phone: str, ordered: bool = True) -> None:
    """Flag that this customer has completed an order/reservation."""
    try:
        collection = get_collection(STATE_COLLECTION)
        await collection.update_one(
            {"_id": phone},
            {"$set": {"ordered": ordered, "ordered_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
    except Exception as e:
        print(f"Failed to set ordered={ordered} for {phone}: {e}")


async def set_handled(phone: str, handled: bool) -> None:
    """Mark a conversation as handled (the dashboard's check mark), or undo it.

    Handled only hides the chat until the customer writes again: the dashboard
    compares handled_at with the customer's latest message.
    """
    try:
        collection = get_collection(STATE_COLLECTION)
        update = (
            {"$set": {"handled_at": datetime.now(timezone.utc)}}
            if handled
            else {"$unset": {"handled_at": ""}}
        )
        await collection.update_one({"_id": phone}, update, upsert=True)
    except Exception as e:
        print(f"Failed to set handled={handled} for {phone}: {e}")


async def get_state(phone: str) -> dict:
    """Return the control-state document for one phone ({} if none/error)."""
    try:
        collection = get_collection(STATE_COLLECTION)
        return await collection.find_one({"_id": phone}) or {}
    except Exception as e:
        print(f"Failed to read state for {phone}: {e}")
        return {}


async def get_states(phones) -> dict:
    """Return {phone: state_doc} for many phones in one query ({} on error)."""
    phones = list(phones)
    if not phones:
        return {}
    try:
        collection = get_collection(STATE_COLLECTION)
        docs = await collection.find({"_id": {"$in": phones}}).to_list(length=len(phones))
        return {d["_id"]: d for d in docs}
    except Exception as e:
        print(f"Failed to read states: {e}")
        return {}


async def ensure_indexes() -> None:
    """Create indexes on the conversations collection. Idempotent, safe on every startup."""
    try:
        collection = get_collection(COLLECTION_NAME)
        await collection.create_index("phone")
        await collection.create_index([("timestamp", -1)])
    except Exception as e:
        print(f"Failed to ensure conversation indexes: {e}")
