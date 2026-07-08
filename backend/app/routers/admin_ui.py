"""Password-protected admin UI for viewing and replying to WhatsApp conversations."""

import os
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from ..config import get_settings
from ..services.mongodb import get_collection
from ..services import conversation_store
from ..services.whatsapp import whatsapp_service

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

# Customers are in Israel; timestamps are stored as naive UTC (Mongo driver
# default). Convert to local Israel time before ever displaying a timestamp.
ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")


def _to_israel(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ISRAEL_TZ)


def israel_time_label(dt) -> str:
    """Format a stored (UTC) timestamp as Israel local time, for template + JSON use."""
    local = _to_israel(dt)
    return local.strftime("%d/%m %H:%M") if local else ""


templates.env.filters["il_time"] = israel_time_label

# Kept as an alias so existing call sites (JSON endpoints) read naturally.
_time_label = israel_time_label


def _window_open(messages) -> bool:
    """Whether WhatsApp's 24h free-form reply window is open for this chat.

    True only if the customer sent an inbound message within the last 24 hours.
    Outside that window WhatsApp rejects free-typed messages (templates only).
    """
    last_in = None
    for m in messages:
        if m.get("role") == "customer" and m.get("timestamp"):
            ts = m["timestamp"]
            if ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)
            if last_in is None or ts > last_in:
                last_in = ts
    if last_in is None:
        return False
    return (datetime.utcnow() - last_in) < timedelta(hours=24)


class SendPayload(BaseModel):
    phone: str
    text: str


class PhonePayload(BaseModel):
    phone: str


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
    """Return the conversation list (one row per customer), grouped:
    escalated ("needs attention") first, then ordered ("reservations"), then
    everything else — each group sorted by most recent activity.

    Each row is annotated with its control state (ordered) from conversation_state.
    """
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
    customers = await collection.aggregate(pipeline).to_list(length=MAX_CUSTOMERS)
    states = await conversation_store.get_states([c["_id"] for c in customers])
    for c in customers:
        c["ordered"] = bool(states.get(c["_id"], {}).get("ordered"))

    def sort_key(c):
        ts = c.get("last_timestamp")
        ts_value = ts.timestamp() if ts else 0
        return (
            0 if c.get("escalated") else 1,
            0 if c.get("ordered") else 1,
            -ts_value,
        )

    customers.sort(key=sort_key)
    return customers


def _group_customers(customers):
    """Split an already-sorted customer list into the three sidebar sections."""
    escalated = [c for c in customers if c.get("escalated")]
    reservations = [c for c in customers if not c.get("escalated") and c.get("ordered")]
    others = [c for c in customers if not c.get("escalated") and not c.get("ordered")]
    return escalated, reservations, others


@router.get("", response_class=HTMLResponse)
async def list_conversations(request: Request, _: None = Depends(require_admin_auth)):
    collection = get_collection("conversations")
    try:
        customers = await _get_customers(collection)
        error = None
    except Exception as e:
        customers = []
        error = str(e)

    escalated_customers, reservation_customers, other_customers = _group_customers(customers)

    return templates.TemplateResponse(
        request,
        "admin_dashboard.html",
        {
            "customers": customers,
            "escalated_customers": escalated_customers,
            "reservation_customers": reservation_customers,
            "other_customers": other_customers,
            "messages": [],
            "selected_phone": None,
            "selected_name": None,
            "bot_paused": False,
            "ordered": False,
            "window_open": False,
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

    state = await conversation_store.get_state(phone)
    escalated_customers, reservation_customers, other_customers = _group_customers(customers)

    return templates.TemplateResponse(
        request,
        "admin_dashboard.html",
        {
            "customers": customers,
            "escalated_customers": escalated_customers,
            "reservation_customers": reservation_customers,
            "other_customers": other_customers,
            "messages": messages,
            "selected_phone": phone,
            "selected_name": selected_name,
            "bot_paused": bool(state.get("bot_paused")),
            "ordered": bool(state.get("ordered")),
            "window_open": _window_open(messages),
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
                "ordered": bool(c.get("ordered")),
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
    state = await conversation_store.get_state(phone)
    return {
        "messages": [
            {
                "role": m.get("role") or "customer",
                "content": m.get("content") or "",
                "escalated": bool(m.get("escalated")),
                "time_label": _time_label(m.get("timestamp")),
            }
            for m in messages
        ],
        "bot_paused": bool(state.get("bot_paused")),
        "ordered": bool(state.get("ordered")),
        "window_open": _window_open(messages),
    }


# ---------------------------------------------------------------------------
# Two-way messaging: reply to a customer and control the bot takeover state.
# ---------------------------------------------------------------------------

@router.post("/api/send")
async def api_send(payload: SendPayload, _: None = Depends(require_admin_auth)):
    """Send a manual WhatsApp reply and pause the bot for this customer."""
    phone = (payload.phone or "").strip()
    text = (payload.text or "").strip()
    if not phone or not text:
        return JSONResponse({"ok": False, "error": "חסר טקסט או מספר"}, status_code=400)

    try:
        resp = await whatsapp_service.send_text_message(phone, text)
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"שגיאת שליחה: {e}"}, status_code=502)

    # The Cloud API returns {"error": {...}} on failure (e.g. outside the 24h window).
    if isinstance(resp, dict) and resp.get("error"):
        err = resp["error"]
        message = err.get("message") if isinstance(err, dict) else str(err)
        return JSONResponse({"ok": False, "error": message or "השליחה נכשלה"}, status_code=502)

    # Persist as a human/agent message (keep the customer's known name) and take
    # this conversation over from the bot.
    name = await conversation_store.get_last_known_name(phone)
    await conversation_store.save_message(phone, name, "agent", text)
    await conversation_store.set_bot_paused(phone, True)
    return {"ok": True, "bot_paused": True}


@router.post("/api/resume")
async def api_resume(payload: PhonePayload, _: None = Depends(require_admin_auth)):
    """Hand the conversation back to the bot."""
    phone = (payload.phone or "").strip()
    if not phone:
        return JSONResponse({"ok": False, "error": "missing phone"}, status_code=400)
    await conversation_store.set_bot_paused(phone, False)
    return {"ok": True, "bot_paused": False}
