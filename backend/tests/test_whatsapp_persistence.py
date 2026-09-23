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
         patch("app.services.conversation_store.save_message", new=AsyncMock()) as mock_save, \
         patch("app.services.conversation_store.get_state", new=AsyncMock(return_value={})) as mock_state, \
         patch("app.services.conversation_store.set_bot_paused", new=AsyncMock()) as mock_pause, \
         patch("app.routers.whatsapp.send_whatsapp_escalation", new=AsyncMock()):

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

        # Scenario 3: finishing the escalation flow hands the chat to a human in the DB
        conversation_memory.clear_session(session_id)
        conversation_memory.add_message(session_id, "user", "שאלה קודמת")
        conversation_memory.set_escalation_state(session_id, "waiting_problem", {"name": "x", "phone": "y"})
        mock_pause.reset_mock()
        client.post("/api/whatsapp/webhook", json=make_payload(sender, sender_name, "הבעיה שלי"))
        passed &= assert_equal(mock_pause.await_args_list[-1].args[:2] if mock_pause.await_count else None,
                               (sender, True), "escalation pauses the bot persistently")
        passed &= assert_equal(mock_pause.await_args_list[-1].kwargs.get("reason") if mock_pause.await_count else None,
                               "escalation", "pause reason recorded as escalation")

        # Scenario 4: while paused, the bot stays silent but the message is saved
        mock_state.return_value = {"bot_paused": True, "paused_by": "escalation"}
        mock_save.reset_mock(); mock_pause.reset_mock()
        send = whatsapp.whatsapp_service.send_text_message
        send.reset_mock()
        response = client.post("/api/whatsapp/webhook", json=make_payload(sender, sender_name, "יש עדכון?"))
        passed &= assert_equal(response.json().get("bot"), "paused", "paused chat: bot does not reply")
        passed &= assert_equal((send.await_count, mock_save.await_count), (0, 1),
                               "paused chat: nothing sent, customer message saved")

        # Scenario 5: the customer can restart an escalated chat themselves
        send.reset_mock()
        client.post("/api/whatsapp/webhook", json=make_payload(sender, sender_name, "התחל מחדש"))
        passed &= assert_equal(mock_pause.await_args_list[-1].args[:2] if mock_pause.await_count else None,
                               (sender, False), "restart un-pauses an escalated chat")
        passed &= assert_equal(send.await_count, 1, "restart sends the welcome message")

        # Scenario 6: restart does NOT override a human who took over from the dashboard
        mock_state.return_value = {"bot_paused": True, "paused_by": "agent"}
        mock_pause.reset_mock(); send.reset_mock()
        client.post("/api/whatsapp/webhook", json=make_payload(sender, sender_name, "התחל מחדש"))
        passed &= assert_equal((mock_pause.await_count, send.await_count), (0, 0),
                               "restart keeps a human takeover in place")

    conversation_memory.clear_session(session_id)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
