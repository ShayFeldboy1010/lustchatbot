"""Read-only, password-protected admin UI for viewing WhatsApp conversations."""

import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from ..config import get_settings
from ..services.mongodb import get_collection

router = APIRouter(prefix="/admin", tags=["admin-ui"])

security = HTTPBasic()

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

MAX_CUSTOMERS = 50
MAX_MESSAGES = 200


def require_admin_auth(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    """Reject the request unless the password matches ADMIN_PASSWORD. Fails closed if unset."""
    settings = get_settings()
    correct_password = settings.admin_password
    if not correct_password or not secrets.compare_digest(credentials.password, correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


@router.get("", response_class=HTMLResponse)
async def list_conversations(request: Request, _: None = Depends(require_admin_auth)):
    collection = get_collection("conversations")
    pipeline = [
        {"$sort": {"timestamp": 1}},
        {"$group": {
            "_id": "$phone",
            "name": {"$last": "$name"},
            "last_message": {"$last": "$content"},
            "last_timestamp": {"$last": "$timestamp"},
            "escalated": {"$max": "$escalated"},
        }},
        {"$sort": {"escalated": -1, "last_timestamp": -1}},
        {"$limit": MAX_CUSTOMERS},
    ]
    try:
        customers = await collection.aggregate(pipeline).to_list(length=MAX_CUSTOMERS)
        error = None
    except Exception as e:
        customers = []
        error = str(e)

    return templates.TemplateResponse(
        "admin_conversations.html",
        {"request": request, "customers": customers, "error": error},
    )


@router.get("/chat/{phone}", response_class=HTMLResponse)
async def view_chat(phone: str, request: Request, _: None = Depends(require_admin_auth)):
    collection = get_collection("conversations")
    try:
        cursor = collection.find({"phone": phone}).sort("timestamp", -1).limit(MAX_MESSAGES)
        messages = await cursor.to_list(length=MAX_MESSAGES)
        messages.reverse()
        error = None
    except Exception as e:
        messages = []
        error = str(e)

    return templates.TemplateResponse(
        "admin_chat.html",
        {"request": request, "phone": phone, "messages": messages, "error": error},
    )
