"""Test admin panel auth gating and HTML escaping.

Plain Python runnable script (matches existing test_mongodb.py / test_sheets.py convention).
Exits with code 0 if all assertions pass, 1 otherwise.

Run from project root:
    python backend/tests/test_admin_auth.py
"""
import sys
import os
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ["ADMIN_PASSWORD"] = "test-secret-123"

from app.config import get_settings
get_settings.cache_clear()

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def assert_equal(actual, expected, label):
    if actual != expected:
        print(f"❌ FAIL: {label}")
        print(f"   expected: {expected!r}")
        print(f"   actual:   {actual!r}")
        return False
    print(f"✅ PASS: {label}")
    return True


class FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    def sort(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    async def to_list(self, length=None):
        return self._docs


class FakeCollection:
    def __init__(self, docs):
        self._docs = docs

    def aggregate(self, pipeline):
        return FakeCursor(self._docs)

    def find(self, query):
        return FakeCursor([d for d in self._docs if d.get("phone") == query.get("phone")])


def main() -> int:
    passed = True

    # No credentials -> 401
    response = client.get("/admin")
    passed &= assert_equal(response.status_code, 401, "no credentials rejected")

    # Wrong password -> 401
    response = client.get("/admin", auth=("admin", "wrong-password"))
    passed &= assert_equal(response.status_code, 401, "wrong password rejected")

    fake_docs = [{
        "_id": "972500000001",
        "name": "בדיקה",
        "last_message": "<script>alert(1)</script>",
        "last_timestamp": datetime.now(timezone.utc),
        "escalated": True,
    }, {
        "phone": "972500000001",
        "role": "customer",
        "content": "<script>alert(2)</script>",
        "timestamp": datetime.now(timezone.utc),
        "escalated": False,
    }]

    with patch("app.routers.admin_ui.get_collection", return_value=FakeCollection(fake_docs)):
        # Correct password -> 200
        response = client.get("/admin", auth=("admin", "test-secret-123"))
        passed &= assert_equal(response.status_code, 200, "correct password accepted")
        passed &= assert_equal("&lt;script&gt;" in response.text, True, "message content HTML-escaped")
        passed &= assert_equal("<script>alert(1)</script>" in response.text, False, "raw script tag not present")
        passed &= assert_equal("דורש תשומת לב" in response.text, True, "escalated badge rendered")

        # Thread view also requires auth
        response = client.get("/admin/chat/972500000001")
        passed &= assert_equal(response.status_code, 401, "thread view requires auth too")

        response = client.get("/admin/chat/972500000001", auth=("admin", "test-secret-123"))
        passed &= assert_equal(response.status_code, 200, "thread view accepts correct password")
        passed &= assert_equal("&lt;script&gt;alert(2)&lt;/script&gt;" in response.text, True, "chat thread content HTML-escaped")
        passed &= assert_equal("<script>alert(2)</script>" in response.text, False, "raw script tag not present in chat thread")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
