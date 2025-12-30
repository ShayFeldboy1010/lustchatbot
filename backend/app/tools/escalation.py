"""Escalation Handler for human support handoff"""

from typing import Optional, List
from datetime import datetime
import httpx
import asyncio

from ..config import get_settings

settings = get_settings()


def format_escalation_message(
    customer_name: str,
    customer_phone: str,
    problem_description: str
) -> str:
    """
    Format a nice escalation message for human support.

    Args:
        customer_name: Name of the customer
        customer_phone: Customer's phone number
        problem_description: Description of the issue

    Returns:
        Formatted message string
    """
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")

    message = f"""📞 פנייה חדשה מהבוט

👤 שם: {customer_name or "לא ידוע"}
📱 טלפון: {customer_phone}
❗ בעיה: {problem_description}"""

    return message


async def send_whatsapp_escalation(
    customer_name: str,
    customer_phone: str,
    problem_description: str
) -> bool:
    """
    Send escalation notification via WhatsApp to human support.

    Args:
        customer_name: Name of the customer
        customer_phone: Customer's phone number
        problem_description: Description of the issue

    Returns:
        True if message was sent successfully
    """
    from ..services.whatsapp import whatsapp_service

    support_number = settings.whatsapp_human_support_number
    print(f"📞 Escalation: Sending to support number: {support_number}")
    if not support_number:
        print("No human support WhatsApp number configured")
        return False

    message = format_escalation_message(
        customer_name=customer_name,
        customer_phone=customer_phone,
        problem_description=problem_description
    )

    try:
        result = await whatsapp_service.send_text_message(support_number, message)
        print(f"Escalation sent to human support: {result}")
        return True
    except Exception as e:
        print(f"Failed to send WhatsApp escalation: {e}")
        return False


class EscalationRecord:
    """Record of an escalation event"""

    def __init__(
        self,
        session_id: str,
        customer_message: str,
        customer_phone: Optional[str] = None,
        reason: Optional[str] = None
    ):
        self.session_id = session_id
        self.customer_message = customer_message
        self.customer_phone = customer_phone
        self.reason = reason
        self.timestamp = datetime.now()

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "customer_phone": self.customer_phone,
            "customer_message": self.customer_message,
            "reason": self.reason,
            "type": "escalation"
        }


# In-memory escalation log (replace with database in production)
escalation_log: list = []


async def notify_escalation(
    session_id: str,
    customer_message: str,
    customer_phone: Optional[str] = None,
    webhook_url: Optional[str] = None,
    reason: Optional[str] = None
) -> bool:
    """
    Notify team about escalation via webhook or log.

    Args:
        session_id: The chat session ID
        customer_message: The message that triggered escalation
        customer_phone: Customer's phone number if available
        webhook_url: Optional webhook URL to send notification
        reason: Reason for escalation

    Returns:
        True if notification was sent successfully
    """
    record = EscalationRecord(
        session_id=session_id,
        customer_message=customer_message,
        customer_phone=customer_phone,
        reason=reason
    )

    # Always log locally
    escalation_log.append(record)
    print(f"ESCALATION [{record.timestamp}]: Session {session_id} - {customer_message[:100]}...")

    # Send webhook notification if URL provided
    if webhook_url:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=record.to_dict(),
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception as e:
            print(f"Webhook notification failed: {e}")
            return False

    return True


async def get_escalation_history(
    session_id: Optional[str] = None,
    limit: int = 100
) -> list:
    """
    Get escalation history, optionally filtered by session ID.

    Args:
        session_id: Filter by session ID if provided
        limit: Maximum number of records to return

    Returns:
        List of escalation records as dicts
    """
    records = escalation_log

    if session_id:
        records = [r for r in records if r.session_id == session_id]

    # Sort by timestamp descending and limit
    records = sorted(records, key=lambda x: x.timestamp, reverse=True)[:limit]

    return [r.to_dict() for r in records]


async def send_email_notification(
    to_email: str,
    session_id: str,
    customer_message: str,
    customer_phone: Optional[str] = None
) -> bool:
    """
    Send email notification for escalation (placeholder for email service).

    In production, integrate with SendGrid, AWS SES, or similar service.

    Args:
        to_email: Recipient email address
        session_id: The chat session ID
        customer_message: The message that triggered escalation
        customer_phone: Customer's phone number if available

    Returns:
        True if email was sent successfully
    """
    # Placeholder - implement with actual email service
    print(f"EMAIL ESCALATION to {to_email}:")
    print(f"  Session: {session_id}")
    print(f"  Phone: {customer_phone}")
    print(f"  Message: {customer_message}")

    # In production, use something like:
    # import sendgrid
    # sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)
    # ...

    return True
