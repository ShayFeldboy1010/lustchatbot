"""Test the conversation_store persistence module.

Plain Python runnable script (matches existing test_mongodb.py / test_sheets.py convention).
Exits with code 0 if all assertions pass, 1 otherwise.

Run from project root:
    python backend/tests/test_conversation_store.py
"""
import sys
import os
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services import conversation_store


def assert_equal(actual, expected, label):
    if actual != expected:
        print(f"❌ FAIL: {label}")
        print(f"   expected: {expected!r}")
        print(f"   actual:   {actual!r}")
        return False
    print(f"✅ PASS: {label}")
    return True


async def _run() -> bool:
    passed = True

    # Successful insert stores the right shape
    fake_collection = AsyncMock()
    with patch("app.services.conversation_store.get_collection", return_value=fake_collection):
        await conversation_store.save_message("972501234567", "דני", "customer", "שלום", escalated=True)

    passed &= assert_equal(fake_collection.insert_one.await_count, 1, "insert_one called once")
    doc = fake_collection.insert_one.await_args.args[0]
    passed &= assert_equal(doc["phone"], "972501234567", "phone stored")
    passed &= assert_equal(doc["name"], "דני", "name stored")
    passed &= assert_equal(doc["role"], "customer", "role stored")
    passed &= assert_equal(doc["content"], "שלום", "content stored")
    passed &= assert_equal(doc["escalated"], True, "escalated flag stored")
    passed &= assert_equal(isinstance(doc["timestamp"], datetime), True, "timestamp is a datetime")

    # escalated defaults to False
    fake_collection2 = AsyncMock()
    with patch("app.services.conversation_store.get_collection", return_value=fake_collection2):
        await conversation_store.save_message("972501234567", "דני", "bot", "תשובה")
    doc2 = fake_collection2.insert_one.await_args.args[0]
    passed &= assert_equal(doc2["escalated"], False, "escalated defaults to False")

    # Mongo failure is swallowed, never raised
    failing_collection = AsyncMock()
    failing_collection.insert_one.side_effect = Exception("mongo down")
    with patch("app.services.conversation_store.get_collection", return_value=failing_collection):
        try:
            await conversation_store.save_message("972501234567", "דני", "bot", "תשובה")
            passed &= assert_equal(True, True, "exception swallowed, save_message did not raise")
        except Exception:
            passed &= assert_equal(False, True, "exception swallowed, save_message did not raise")

    # ensure_indexes calls create_index twice and never raises on failure
    fake_collection3 = AsyncMock()
    with patch("app.services.conversation_store.get_collection", return_value=fake_collection3):
        await conversation_store.ensure_indexes()
    passed &= assert_equal(fake_collection3.create_index.await_count, 2, "ensure_indexes creates two indexes")

    return passed


def main() -> int:
    passed = asyncio.run(_run())
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
