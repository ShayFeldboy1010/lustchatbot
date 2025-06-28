from langchain.memory import ConversationBufferMemory
from langchain.schema import BaseMessage
from typing import Dict, Any, List


class LustBotMemory:
    """Enhanced conversation memory for LustBot"""
    
    def __init__(self, k: int = 3):
        self.memory = ConversationBufferMemory(
            k=k,
            return_messages=True,
            memory_key="chat_history",
            output_key="output"
        )
        self.user_context = {}
    
    def add_user_message(self, message: str):
        """Add user message to memory"""
        self.memory.chat_memory.add_user_message(message)
    
    def add_ai_message(self, message: str):
        """Add AI message to memory"""
        self.memory.chat_memory.add_ai_message(message)
    
    def get_memory_variables(self) -> Dict[str, Any]:
        """Get memory variables for agent"""
        return self.memory.load_memory_variables({})
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]):
        """Save conversation context"""
        self.memory.save_context(inputs, outputs)
    
    def clear_memory(self):
        """Clear conversation memory"""
        self.memory.clear()
        self.user_context = {}
    
    def set_user_context(self, key: str, value: Any):
        """Set user context information"""
        self.user_context[key] = value
    
    def get_user_context(self, key: str, default=None):
        """Get user context information"""
        return self.user_context.get(key, default)
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation"""
        messages = self.memory.chat_memory.messages
        if not messages:
            return "No conversation history"
        
        summary = "Recent conversation:\n"
        for msg in messages[-6:]:  # Last 6 messages
            role = "User" if msg.type == "human" else "Assistant"
            summary += f"{role}: {msg.content[:100]}...\n"
        
        return summary
