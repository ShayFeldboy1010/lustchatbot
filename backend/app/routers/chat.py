"""Chat API Router"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import uuid

from ..models.chat import MessageRequest, MessageResponse, ConversationHistory
from ..agents.sales_agent import process_message
from ..services.memory import conversation_memory
from ..tools.escalation import notify_escalation

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=MessageResponse)
async def chat_endpoint(request: MessageRequest):
    """
    Main chat endpoint. Processes user messages and returns agent responses.

    - Generates session ID if not provided
    - Maintains conversation history
    - Triggers escalation if needed
    """
    # Generate or use existing session ID
    session_id = request.session_id or str(uuid.uuid4())

    # Get conversation history
    history = conversation_memory.get_history(session_id)

    # Process message through agent
    result = await process_message(
        message=request.message,
        session_id=session_id,
        conversation_history=history
    )

    # Update conversation history
    conversation_memory.add_message(session_id, "user", request.message)
    conversation_memory.add_message(session_id, "assistant", result.response)

    # Handle escalation notification
    if result.needs_escalation:
        await notify_escalation(
            session_id=session_id,
            customer_message=request.message,
            reason="Escalation keywords detected"
        )

    return MessageResponse(
        response=result.response,
        session_id=session_id,
        needs_escalation=result.needs_escalation
    )


@router.get("/history/{session_id}", response_model=ConversationHistory)
async def get_history(session_id: str):
    """
    Get conversation history for a session.
    """
    history = conversation_memory.get_history(session_id)
    return ConversationHistory(session_id=session_id, messages=history)


@router.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """
    Clear conversation history for a session.
    """
    success = conversation_memory.clear_session(session_id)
    return {"status": "cleared" if success else "not_found", "session_id": session_id}


@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """
    Get session metadata.
    """
    info = conversation_memory.get_session_info(session_id)
    if not info:
        raise HTTPException(status_code=404, detail="Session not found")
    return info
