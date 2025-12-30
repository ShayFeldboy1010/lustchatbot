"""WhatsApp Business API Service for sending and receiving messages"""

import httpx
from typing import Optional, Dict, Any
import json

from ..config import get_settings

settings = get_settings()

# WhatsApp Cloud API base URL
WHATSAPP_API_URL = "https://graph.facebook.com/v18.0"


class WhatsAppService:
    """Service for interacting with WhatsApp Business Cloud API"""

    def __init__(self):
        self.access_token = settings.whatsapp_access_token
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.business_account_id = settings.whatsapp_business_account_id
        self.verify_token = settings.whatsapp_verify_token

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    async def send_text_message(self, to: str, message: str) -> Dict[str, Any]:
        """
        Send a text message to a WhatsApp user.

        Args:
            to: Phone number with country code (e.g., "972501234567")
            message: Message text to send

        Returns:
            API response as dict
        """
        url = f"{WHATSAPP_API_URL}/{self.phone_number_id}/messages"

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30.0
            )

            if response.status_code != 200:
                print(f"WhatsApp API error: {response.status_code} - {response.text}")

            return response.json()

    async def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark a message as read.

        Args:
            message_id: WhatsApp message ID

        Returns:
            API response as dict
        """
        url = f"{WHATSAPP_API_URL}/{self.phone_number_id}/messages"

        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30.0
            )
            return response.json()

    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verify webhook subscription from Meta.

        Args:
            mode: Should be "subscribe"
            token: Verification token
            challenge: Challenge string to return

        Returns:
            Challenge string if valid, None otherwise
        """
        if mode == "subscribe" and token == self.verify_token:
            return challenge
        return None

    def parse_incoming_message(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse incoming webhook payload to extract message details.

        Args:
            payload: Webhook payload from Meta

        Returns:
            Dict with sender, message_id, message_text, timestamp or None
        """
        try:
            entry = payload.get("entry", [])
            if not entry:
                return None

            changes = entry[0].get("changes", [])
            if not changes:
                return None

            value = changes[0].get("value", {})
            messages = value.get("messages", [])

            if not messages:
                return None

            message = messages[0]

            # Get contact info
            contacts = value.get("contacts", [])
            contact_name = contacts[0].get("profile", {}).get("name", "") if contacts else ""

            return {
                "sender": message.get("from"),
                "sender_name": contact_name,
                "message_id": message.get("id"),
                "message_text": message.get("text", {}).get("body", ""),
                "timestamp": message.get("timestamp"),
                "message_type": message.get("type")
            }

        except (KeyError, IndexError) as e:
            print(f"Error parsing WhatsApp message: {e}")
            return None


# Global service instance
whatsapp_service = WhatsAppService()
