"""
Pydantic schemas for LustBot API
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ChatMessage(BaseModel):
    message: str
    user_id: str = "anonymous"
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    status: str = "success"
    timestamp: datetime = datetime.now()
    metadata: Optional[Dict[str, Any]] = None


class Lead(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    product: str
    method: str = "Chat"
    notes: Optional[str] = None


class Product(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    price: Optional[str] = None
    category: Optional[str] = None
    url: Optional[str] = None
    in_stock: bool = True
    features: Optional[str] = None
    brand: Optional[str] = None


__all__ = ["ChatMessage", "ChatResponse", "Lead", "Product"]
