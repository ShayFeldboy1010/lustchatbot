from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class MessageRequest(BaseModel):
    """Request model for sending a chat message"""
    message: str
    session_id: Optional[str] = None


class MessageResponse(BaseModel):
    """Response model for chat messages"""
    response: str
    session_id: str
    needs_escalation: bool = False


class ChatMessage(BaseModel):
    """Individual chat message model"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = None

    def __init__(self, **data):
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = datetime.now()
        super().__init__(**data)


class ConversationHistory(BaseModel):
    """Conversation history model"""
    session_id: str
    messages: List[dict]
