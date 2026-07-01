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

# Stable per-contact avatar colors. The same palette + hash is reproduced in the
# dashboard's JS so a contact keeps its color across server render and live polls.
AVATAR_COLORS = [
    "#e17076", "#7bc862", "#65aadd", "#a695e7", "#ee7aae",
    "#6ec9cb", "#f6b445", "#faa774", "#b05a9f", "#5eb069",
]


def avatar_color(phone) -> str:
    total = sum(ord(ch) for ch in str(phone or ""))
    return AVATAR_COLORS[total % len(AVATAR_COLORS)]


templates.env.filters["avatar_color"] = avatar_color


def _time_label(dt) -> str:
    """Format a timestamp exactly as the template does, for live JSON updates."""
    return dt.strftime("%d/%m %H:%M") if dt else ""


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


async def _get_customers(collection):
    """Return the conversation list (one row per customer), escalated pinned first."""
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
    return await collection.aggregate(pipeline).to_list(length=MAX_CUSTOMERS)


@router.get("", response_class=HTMLResponse)
async def list_conversations(request: Request, _: None = Depends(require_admin_auth)):
    collection = get_collection("conversations")
    try:
        customers = await _get_customers(collection)
        error = None
    except Exception as e:
        customers = []
        error = str(e)

    return templates.TemplateResponse(
        request,
        "admin_dashboard.html",
        {
            "customers": customers,
            "messages": [],
            "selected_phone": None,
            "selected_name": None,
            "error": error,
        },
    )


@router.get("/chat/{phone}", response_class=HTMLResponse)
async def view_chat(phone: str, request: Request, _: None = Depends(require_admin_auth)):
    collection = get_collection("conversations")
    error = None
    try:
        customers = await _get_customers(collection)
    except Exception as e:
        customers = []
        error = str(e)

    try:
        cursor = collection.find({"phone": phone}).sort("timestamp", -1).limit(MAX_MESSAGES)
        messages = await cursor.to_list(length=MAX_MESSAGES)
        messages.reverse()
    except Exception as e:
        messages = []
        error = error or str(e)

    # Prefer the name stored on the messages; fall back to the sidebar row.
    selected_name = next((m.get("name") for m in reversed(messages) if m.get("name")), None)
    if not selected_name:
        selected_name = next((c.get("name") for c in customers if c["_id"] == phone), None)

    return templates.TemplateResponse(
        request,
        "admin_dashboard.html",
        {
            "customers": customers,
            "messages": messages,
            "selected_phone": phone,
            "selected_name": selected_name,
            "error": error,
        },
    )


# ---------------------------------------------------------------------------
# JSON endpoints polled by the dashboard for live updates (no page refresh).
# ---------------------------------------------------------------------------

@router.get("/api/conversations")
async def api_conversations(_: None = Depends(require_admin_auth)):
    collection = get_collection("conversations")
    try:
        customers = await _get_customers(collection)
    except Exception as e:
        return {"error": str(e), "customers": []}
    return {
        "customers": [
            {
                "phone": c["_id"],
                "name": c.get("name") or "",
                "last_message": c.get("last_message") or "",
                "escalated": bool(c.get("escalated")),
                "time_label": _time_label(c.get("last_timestamp")),
            }
            for c in customers
        ]
    }


@router.get("/api/messages/{phone}")
async def api_messages(phone: str, _: None = Depends(require_admin_auth)):
    collection = get_collection("conversations")
    try:
        cursor = collection.find({"phone": phone}).sort("timestamp", -1).limit(MAX_MESSAGES)
        messages = await cursor.to_list(length=MAX_MESSAGES)
        messages.reverse()
    except Exception as e:
        return {"error": str(e), "messages": []}
    return {
        "messages": [
            {
                "role": m.get("role") or "customer",
                "content": m.get("content") or "",
                "escalated": bool(m.get("escalated")),
                "time_label": _time_label(m.get("timestamp")),
            }
            for m in messages
        ]
    }
