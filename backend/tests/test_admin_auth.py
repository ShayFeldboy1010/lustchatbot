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
        # Aggregation output = one row per customer (docs keyed by _id).
        return FakeCursor([d for d in self._docs if "_id" in d])

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
        "last_role": "bot",
        "last_escalated_at": datetime.now(timezone.utc),
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
        passed &= assert_equal('<span class="badge">דורש תשומת לב</span>' in response.text, True, "escalated badge rendered")
        passed &= assert_equal('data-section="attention"' in response.text, True, "attention section rendered")

        # Thread view also requires auth
        response = client.get("/admin/chat/972500000001")
        passed &= assert_equal(response.status_code, 401, "thread view requires auth too")

        response = client.get("/admin/chat/972500000001", auth=("admin", "test-secret-123"))
        passed &= assert_equal(response.status_code, 200, "thread view accepts correct password")
        passed &= assert_equal("&lt;script&gt;alert(2)&lt;/script&gt;" in response.text, True, "chat thread content HTML-escaped")
        passed &= assert_equal("<script>alert(2)</script>" in response.text, False, "raw script tag not present in chat thread")

    passed &= test_classify()
    return 0 if passed else 1


def test_classify() -> bool:
    from datetime import timedelta
    from app.routers.admin_ui import _classify, _group_customers

    now = datetime.utcnow()
    hour = timedelta(hours=1)
    passed = True

    def row(**kw):
        base = {"_id": "1", "last_timestamp": now - hour, "last_role": "bot",
                "ordered": False, "bot_paused": False}
        base.update(kw)
        return base

    passed &= assert_equal(_classify(row(last_escalated_at=now - hour), now), "attention",
                           "open escalation needs attention")
    passed &= assert_equal(_classify(row(last_escalated_at=now - 2 * hour, last_agent_at=now - hour), now),
                           "active", "agent reply clears escalation")
    passed &= assert_equal(_classify(row(last_escalated_at=now - timedelta(days=30),
                                         last_timestamp=now - timedelta(days=30)), now),
                           "older", "stale escalation is not attention")
    passed &= assert_equal(_classify(row(bot_paused=True, last_role="customer"), now), "attention",
                           "paused chat with unanswered customer needs attention")
    passed &= assert_equal(_classify(row(ordered=True, last_timestamp=now - timedelta(days=20)), now),
                           "orders", "ordered customer lands in orders")
    passed &= assert_equal(_classify(row(), now), "active", "recent chat is active")
    passed &= assert_equal(_classify(row(last_timestamp=now - timedelta(days=5)), now), "older",
                           "old chat is older")

    passed &= assert_equal(_classify(row(last_card_link_at=now - hour, last_timestamp=now - timedelta(days=5)), now),
                           "card_link", "customer who got a card link lands in card_link")
    passed &= assert_equal(_classify(row(ordered=True, last_card_link_at=now - hour), now), "orders",
                           "an order beats a card link")
    passed &= assert_equal(_classify(row(last_escalated_at=now - 2 * hour, last_customer_at=now - 2 * hour,
                                         handled_at=now - hour), now),
                           "done", "handled chat moves to done, even over an open escalation")
    passed &= assert_equal(_classify(row(last_customer_at=now - hour, handled_at=now - 2 * hour), now),
                           "active", "customer writing after handled brings the chat back")

    # Regression: many escalated customers must not hide everything else.
    rows = [row(_id=str(i), last_escalated_at=now - hour) for i in range(60)]
    rows += [row(_id="o", ordered=True), row(_id="a")]
    for r in rows:
        r["section"] = _classify(r, now)
    groups = _group_customers(rows)
    passed &= assert_equal((len(groups["attention"]), len(groups["orders"]), len(groups["active"])),
                           (60, 1, 1), "orders and active chats survive a flood of escalations")
    return passed


if __name__ == "__main__":
    sys.exit(main())
