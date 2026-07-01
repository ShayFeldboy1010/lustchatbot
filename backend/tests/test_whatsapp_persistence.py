"""Test that the WhatsApp webhook persists messages via conversation_store.

Plain Python runnable script (matches existing test_mongodb.py / test_sheets.py convention).
Exits with code 0 if all assertions pass, 1 otherwise.

Run from project root (requires a valid .env - this boots the real FastAPI app):
    python backend/tests/test_whatsapp_persistence.py
"""
import sys
import os
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient

from app.main import app
from app.routers import whatsapp
from app.services.memory import conversation_memory
from app.agents.sales_agent import ChatResponse

client = TestClient(app)


def assert_equal(actual, expected, label):
    if actual != expected:
        print(f"❌ FAIL: {label}")
        print(f"   expected: {expected!r}")
        print(f"   actual:   {actual!r}")
        return False
    print(f"✅ PASS: {label}")
    return True


def make_payload(sender: str, sender_name: str, text: str) -> dict:
    return {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": sender,
                        "id": "wamid.test",
                        "type": "text",
                        "text": {"body": text},
                        "timestamp": "1700000000",
                    }],
                    "contacts": [{"profile": {"name": sender_name}}],
                }
            }]
        }]
    }


def main() -> int:
    passed = True
    sender = "972500000001"
    sender_name = "בדיקה"
    session_id = f"whatsapp_{sender}"

    with patch.object(whatsapp.whatsapp_service, "send_text_message", new=AsyncMock(return_value={})), \
         patch.object(whatsapp.whatsapp_service, "mark_as_read", new=AsyncMock(return_value=None)), \
         patch("app.services.conversation_store.save_message", new=AsyncMock()) as mock_save:

        # Scenario 1: brand-new conversation -> two saves, neither escalated
        conversation_memory.clear_session(session_id)
        response = client.post("/api/whatsapp/webhook", json=make_payload(sender, sender_name, "שלום"))
        passed &= assert_equal(response.status_code, 200, "new-conversation webhook returns 200")
        passed &= assert_equal(mock_save.await_count, 2, "new conversation saves customer + bot messages")
        first_call = mock_save.await_args_list[0]
        passed &= assert_equal(first_call.args[2], "customer", "first save is customer role")
        passed &= assert_equal(first_call.kwargs.get("escalated", False), False, "welcome flow not escalated")

        mock_save.reset_mock()

        # Scenario 2: existing conversation where the agent requests escalation
        conversation_memory.clear_session(session_id)
        conversation_memory.add_message(session_id, "user", "שאלה קודמת")
        conversation_memory.add_message(session_id, "assistant", "תשובה קודמת")

        with patch("app.routers.whatsapp.process_message", new=AsyncMock(
            return_value=ChatResponse(response="אעביר אותך לנציג", needs_escalation=True)
        )):
            response = client.post("/api/whatsapp/webhook", json=make_payload(sender, sender_name, "אני רוצה לדבר עם בן אדם"))

        passed &= assert_equal(response.status_code, 200, "escalation webhook returns 200")
        passed &= assert_equal(mock_save.await_count, 2, "escalation turn saves customer + bot messages")
        customer_call = mock_save.await_args_list[0]
        passed &= assert_equal(customer_call.args[2], "customer", "escalation turn: first save is customer role")
        passed &= assert_equal(customer_call.kwargs.get("escalated"), True, "customer message flagged escalated=True")
        bot_call = mock_save.await_args_list[1]
        passed &= assert_equal(bot_call.kwargs.get("escalated", False), False, "bot reply never flagged escalated")

    conversation_memory.clear_session(session_id)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
