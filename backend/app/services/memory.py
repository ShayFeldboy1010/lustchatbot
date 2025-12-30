"""Conversation Memory Service for session management"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import OrderedDict
import threading


class ConversationMemory:
    """
    In-memory conversation storage with TTL support.
    For production, replace with Redis or similar.
    """

    def __init__(self, max_sessions: int = 1000, session_ttl_hours: int = 24):
        self._sessions: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()
        self.max_sessions = max_sessions
        self.session_ttl = timedelta(hours=session_ttl_hours)

    def _cleanup_expired(self):
        """Remove expired sessions"""
        now = datetime.now()
        expired = []

        for session_id, data in self._sessions.items():
            if now - data.get('last_access', now) > self.session_ttl:
                expired.append(session_id)

        for session_id in expired:
            del self._sessions[session_id]

    def _enforce_max_sessions(self):
        """Remove oldest sessions if over limit"""
        while len(self._sessions) > self.max_sessions:
            self._sessions.popitem(last=False)

    def get_history(self, session_id: str) -> List[dict]:
        """Get conversation history for a session"""
        with self._lock:
            self._cleanup_expired()

            if session_id not in self._sessions:
                return []

            # Update last access time
            self._sessions[session_id]['last_access'] = datetime.now()

            # Move to end (most recently accessed)
            self._sessions.move_to_end(session_id)

            return self._sessions[session_id].get('messages', [])

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Add a message to the conversation history"""
        with self._lock:
            self._cleanup_expired()

            if session_id not in self._sessions:
                self._sessions[session_id] = {
                    'messages': [],
                    'created_at': datetime.now(),
                    'last_access': datetime.now(),
                    'order_completed': False
                }

            self._sessions[session_id]['messages'].append({
                'role': role,
                'content': content,
                'timestamp': datetime.now().isoformat()
            })
            self._sessions[session_id]['last_access'] = datetime.now()

            # Move to end
            self._sessions.move_to_end(session_id)

            self._enforce_max_sessions()

    def clear_session(self, session_id: str) -> bool:
        """Clear a specific session"""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def mark_order_completed(self, session_id: str) -> None:
        """Mark session as having a completed order"""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]['order_completed'] = True

    def is_order_completed(self, session_id: str) -> bool:
        """Check if session already has a completed order"""
        with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id].get('order_completed', False)
            return False

    def get_user_message_count_24h(self, session_id: str) -> int:
        """Count user messages in the last 24 hours"""
        with self._lock:
            if session_id not in self._sessions:
                return 0

            messages = self._sessions[session_id].get('messages', [])
            now = datetime.now()
            cutoff = now - timedelta(hours=24)

            count = 0
            for msg in messages:
                if msg.get('role') == 'user':
                    # Parse timestamp if available
                    ts_str = msg.get('timestamp')
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(ts_str)
                            if ts > cutoff:
                                count += 1
                        except:
                            count += 1  # Count if can't parse timestamp
                    else:
                        count += 1  # Count if no timestamp

            return count

    def save_customer_details(self, session_id: str, details: dict) -> None:
        """Save customer details after order confirmation"""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]['customer_details'] = details

    def get_customer_details(self, session_id: str) -> dict:
        """Get saved customer details"""
        with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id].get('customer_details', {})
            return {}

    def set_pending_escalation(self, session_id: str, pending: bool = True) -> None:
        """Mark session as waiting for escalation problem description"""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]['pending_escalation'] = pending

    def is_pending_escalation(self, session_id: str) -> bool:
        """Check if session is waiting for escalation problem description"""
        with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id].get('pending_escalation', False)
            return False

    def get_session_info(self, session_id: str) -> Optional[dict]:
        """Get session metadata"""
        with self._lock:
            if session_id not in self._sessions:
                return None

            session = self._sessions[session_id]
            return {
                'session_id': session_id,
                'message_count': len(session.get('messages', [])),
                'created_at': session.get('created_at', datetime.now()).isoformat(),
                'last_access': session.get('last_access', datetime.now()).isoformat()
            }

    def get_all_sessions(self) -> List[dict]:
        """Get info for all active sessions"""
        with self._lock:
            self._cleanup_expired()
            return [
                {
                    'session_id': sid,
                    'message_count': len(data.get('messages', [])),
                    'last_access': data.get('last_access', datetime.now()).isoformat()
                }
                for sid, data in self._sessions.items()
            ]


# Global memory instance
conversation_memory = ConversationMemory()
