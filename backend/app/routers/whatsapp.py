"""WhatsApp Webhook Router for receiving and responding to messages"""

from fastapi import APIRouter, Request, Response, HTTPException
from typing import Dict, Any
import uuid

from ..services.whatsapp import whatsapp_service
from ..agents.sales_agent import process_message
from ..services.memory import conversation_memory
from ..tools.escalation import send_whatsapp_escalation
from ..agents.prompts import ESCALATION_CONFIRMED

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

# Maximum messages per conversation before auto-escalation to human
MAX_MESSAGES_PER_SESSION = 20

# Message to send when max messages reached
MAX_MESSAGES_ESCALATION_TEXT = """תודה על השיחה! כנראה שלא הצלחתי לעזור לך 😅 מעביר את פנייתך לנציג אנושי

נציג יחזור אליך בהקדם האפשרי!
תודה על הסבלנות 🙏"""

# Track sessions that have been escalated due to message limit
escalated_sessions = set()

# Fixed welcome message for new conversations
WELCOME_MESSAGE = """היי! אני לאסטי, הנציגה של LUST ✨ איך אני יכולה לעזור לך היום?"""


@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Webhook verification endpoint for Meta.
    Meta sends a GET request with hub.mode, hub.verify_token, and hub.challenge.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if not all([mode, token, challenge]):
        raise HTTPException(status_code=400, detail="Missing verification parameters")

    result = whatsapp_service.verify_webhook(mode, token, challenge)

    if result:
        print(f"Webhook verified successfully!")
        return Response(content=challenge, media_type="text/plain")

    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_message(request: Request):
    """
    Receive incoming messages from WhatsApp.
    Processes the message through the sales agent and responds.
    """
    try:
        payload: Dict[str, Any] = await request.json()

        # Parse the incoming message
        message_data = whatsapp_service.parse_incoming_message(payload)

        if not message_data:
            # No message to process (might be a status update)
            return {"status": "ok"}

        # Only process text messages
        if message_data.get("message_type") != "text":
            print(f"Ignoring non-text message type: {message_data.get('message_type')}")
            return {"status": "ok"}

        sender = message_data["sender"]
        message_text = message_data["message_text"]
        message_id = message_data["message_id"]
        sender_name = message_data.get("sender_name", "")

        print(f"Received message from {sender} ({sender_name}): {message_text}")

        # Mark message as read
        await whatsapp_service.mark_as_read(message_id)

        # Use phone number as session ID for WhatsApp
        session_id = f"whatsapp_{sender}"

        # Check if user wants to restart conversation
        if message_text.strip() in ["התחל מחדש", "להתחיל מחדש", "התחלה מחדש"]:
            # Reset the session - remove from escalated and clear memory
            if session_id in escalated_sessions:
                escalated_sessions.remove(session_id)
            conversation_memory.clear_session(session_id)

            # Send welcome message
            await whatsapp_service.send_text_message(sender, WELCOME_MESSAGE)
            conversation_memory.add_message(session_id, "user", message_text)
            conversation_memory.add_message(session_id, "assistant", WELCOME_MESSAGE)
            print(f"Session {session_id} reset by user request")
            return {"status": "ok"}

        # Check if this session was already escalated due to message limit
        if session_id in escalated_sessions:
            # Don't respond - already handed off to human
            print(f"Session {session_id} already escalated, ignoring message")
            return {"status": "ok"}

        # Check if waiting for escalation problem description
        is_pending = conversation_memory.is_pending_escalation(session_id)
        print(f"DEBUG: Session {session_id} - is_pending_escalation: {is_pending}")

        if is_pending:
            # This message is the problem description - send to human support
            conversation_memory.set_pending_escalation(session_id, False)
            escalated_sessions.add(session_id)

            # Send formatted message to human support
            escalation_message = f"""📞 פנייה לנציג

👤 שם: {sender_name or 'לא ידוע'}
📱 טלפון: {sender}
❗ בעיה: {message_text}"""

            await send_whatsapp_escalation(
                customer_name=sender_name or "לא ידוע",
                customer_phone=sender,
                problem_description=message_text
            )

            # Send confirmation to customer
            await whatsapp_service.send_text_message(sender, ESCALATION_CONFIRMED)
            print(f"Escalation completed for {sender} with problem: {message_text}")
            return {"status": "ok"}

        # Get conversation history
        history = conversation_memory.get_history(session_id)

        # Check if this is a new conversation (no history)
        is_new_conversation = len(history) == 0

        # Count user messages in last 24 hours
        user_message_count_24h = conversation_memory.get_user_message_count_24h(session_id)

        # Check if max messages reached in 24h (before adding current message)
        if user_message_count_24h >= MAX_MESSAGES_PER_SESSION:
            # Mark session as escalated
            escalated_sessions.add(session_id)

            # Send escalation message to customer
            await whatsapp_service.send_text_message(sender, MAX_MESSAGES_ESCALATION_TEXT)

            # Build conversation summary for human support
            conversation_summary = "\n".join([
                f"{'לקוח' if msg.get('role') == 'user' else 'בוט'}: {msg.get('content', '')[:100]}"
                for msg in history[-10:]  # Last 10 messages
            ])

            # Send escalation to human support
            await send_whatsapp_escalation(
                customer_name=sender_name or "לא ידוע",
                customer_phone=sender,
                problem_description=f"הגיע למכסת 20 הודעות ב-24 שעות - הועבר אוטומטית\n\nהודעה אחרונה: {message_text}\n\nסיכום שיחה:\n{conversation_summary}"
            )

            print(f"Session {session_id} reached {user_message_count_24h} messages in 24h - escalated to human")
            return {"status": "ok"}

        # For new conversations, send fixed welcome message
        if is_new_conversation:
            # Save the incoming message to history
            conversation_memory.add_message(session_id, "user", message_text)
            conversation_memory.add_message(session_id, "assistant", WELCOME_MESSAGE)

            # Send welcome message
            await whatsapp_service.send_text_message(sender, WELCOME_MESSAGE)
            print(f"Sent welcome message to new user {sender}")
            return {"status": "ok"}

        # Process message through the sales agent
        result = await process_message(
            message=message_text,
            session_id=session_id,
            conversation_history=history
        )

        # Update conversation history
        conversation_memory.add_message(session_id, "user", message_text)
        conversation_memory.add_message(session_id, "assistant", result.response)

        # Handle escalation - set pending and wait for problem description
        if result.needs_escalation:
            conversation_memory.set_pending_escalation(session_id, True)
            print(f"Escalation pending for {sender} - waiting for problem description")

        # Send response via WhatsApp
        await whatsapp_service.send_text_message(sender, result.response)

        print(f"Sent response to {sender}: {result.response[:100]}...")

        return {"status": "ok"}

    except Exception as e:
        print(f"Error processing WhatsApp message: {e}")
        import traceback
        traceback.print_exc()
        # Always return 200 to acknowledge receipt to Meta
        return {"status": "error", "message": str(e)}


@router.get("/status")
async def whatsapp_status():
    """Check WhatsApp integration status"""
    return {
        "status": "configured",
        "phone_number_id": whatsapp_service.phone_number_id,
        "business_account_id": whatsapp_service.business_account_id
    }
