"""Admin API Router for debugging and management"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from ..services.memory import conversation_memory
from ..services.mongodb import check_connection as check_mongo
from ..tools.escalation import get_escalation_history

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    mongo_status = await check_mongo()

    return {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "mongodb": "connected" if mongo_status else "disconnected"
        }
    }


@router.get("/sessions")
async def list_sessions():
    """
    List all active chat sessions.
    """
    sessions = conversation_memory.get_all_sessions()
    return {
        "total": len(sessions),
        "sessions": sessions
    }


@router.get("/escalations")
async def list_escalations(limit: int = 100, session_id: Optional[str] = None):
    """
    List escalation history.

    Args:
        limit: Maximum number of records to return
        session_id: Filter by session ID
    """
    escalations = await get_escalation_history(session_id=session_id, limit=limit)
    return {
        "total": len(escalations),
        "escalations": escalations
    }


@router.get("/stats")
async def get_stats():
    """
    Get system statistics.
    """
    sessions = conversation_memory.get_all_sessions()
    escalations = await get_escalation_history(limit=1000)

    total_messages = sum(s.get('message_count', 0) for s in sessions)

    return {
        "active_sessions": len(sessions),
        "total_messages": total_messages,
        "total_escalations": len(escalations),
        "escalation_rate": len(escalations) / max(len(sessions), 1)
    }


@router.post("/clear-all-sessions")
async def clear_all_sessions():
    """
    Clear all chat sessions. Use with caution.
    """
    sessions = conversation_memory.get_all_sessions()
    count = len(sessions)

    for session in sessions:
        conversation_memory.clear_session(session['session_id'])

    return {
        "status": "cleared",
        "sessions_cleared": count
    }
