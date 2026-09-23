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
from ..services.memory import conversation_memory
from ..services.whatsapp import whatsapp_service

router = APIRouter(prefix="/admin", tags=["admin-ui"])

security = HTTPBasic()

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

MAX_CUSTOMERS = 500
MAX_MESSAGES = 200

# Sidebar sections, in display order. Every conversation lands in exactly one.
# Keep keys + labels in sync with SECTIONS in admin_dashboard.html's script.
SECTIONS = [
    ("attention", "דורש תשומת לב"),
    ("orders", "סגרו הזמנה ב-WhatsApp"),
    ("card_link", "קיבלו קישור לתשלום באשראי"),
    ("active", "שיחות פעילות"),
    ("older", "שיחות קודמות"),
    ("done", "טופלו ✓"),
]
# A bot/agent message containing a product-page link = the customer chose to
# pay by credit card on the website (the bot's flow ends there).
CARD_LINK_REGEX = r"https?://\S+/products/"
# "Active" = any message in this window. Escalations older than ESCALATION_TTL
# with no agent reply are treated as stale rather than still needing attention.
ACTIVE_WINDOW = timedelta(hours=48)
ESCALATION_TTL = timedelta(days=7)

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


def _chat_handled(state, messages) -> bool:
    last_customer_at = max(
        (m["timestamp"] for m in messages if m.get("role") == "customer" and m.get("timestamp")),
        key=_naive_utc,
        default=None,
    )
    return _is_handled(state.get("handled_at"), last_customer_at)


class SendPayload(BaseModel):
    phone: str
    text: str


class PhonePayload(BaseModel):
    phone: str


class HandledPayload(BaseModel):
    phone: str
    handled: bool = True


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
    """Return the conversation list (one row per customer), newest activity first.

    Each row is annotated with its control state (ordered / bot_paused) from
    conversation_state and with its sidebar `section` (see _classify).
    """
    pipeline = [
        {"$sort": {"timestamp": 1}},
        {"$group": {
            "_id": "$phone",
            "name": {"$last": "$name"},
            "last_message": {"$last": "$content"},
            "last_role": {"$last": "$role"},
            "last_timestamp": {"$last": "$timestamp"},
            # $max skips nulls, so these are "latest escalated / agent message".
            "last_escalated_at": {"$max": {"$cond": [{"$eq": ["$escalated", True]}, "$timestamp", None]}},
            "last_agent_at": {"$max": {"$cond": [{"$eq": ["$role", "agent"]}, "$timestamp", None]}},
            "last_customer_at": {"$max": {"$cond": [{"$eq": ["$role", "customer"]}, "$timestamp", None]}},
            "last_card_link_at": {"$max": {"$cond": [
                {"$and": [
                    {"$in": ["$role", ["bot", "agent"]]},
                    {"$regexMatch": {"input": {"$ifNull": ["$content", ""]}, "regex": CARD_LINK_REGEX}},
                ]},
                "$timestamp",
                None,
            ]}},
        }},
        # Sort and cap by recency only. Never sort by a flag before $limit, or one
        # busy group can push every other conversation out of the list.
        {"$sort": {"last_timestamp": -1}},
        {"$limit": MAX_CUSTOMERS},
    ]
    customers = await collection.aggregate(pipeline).to_list(length=MAX_CUSTOMERS)
    states = await conversation_store.get_states([c["_id"] for c in customers])
    now = datetime.utcnow()
    for c in customers:
        state = states.get(c["_id"], {})
        c["ordered"] = bool(state.get("ordered"))
        c["bot_paused"] = bool(state.get("bot_paused"))
        c["handled_at"] = state.get("handled_at")
        c["section"] = _classify(c, now)
    return customers


def _naive_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _needs_attention(c, now) -> bool:
    """A human should look at this chat now.

    - Open escalation: the bot escalated, and no agent has replied since, within
      ESCALATION_TTL (older ones are stale, not actionable).
    - Waiting on a human: the bot is paused (human takeover) and the customer's
      message is the last one, while WhatsApp still lets us reply (24h).
    """
    escalated_at = _naive_utc(c.get("last_escalated_at"))
    agent_at = _naive_utc(c.get("last_agent_at"))
    if escalated_at and (agent_at is None or agent_at < escalated_at):
        if now - escalated_at < ESCALATION_TTL:
            return True
    last_at = _naive_utc(c.get("last_timestamp"))
    if c.get("bot_paused") and c.get("last_role") == "customer" and last_at:
        if now - last_at < timedelta(hours=24):
            return True
    return False


def _is_handled(handled_at, last_customer_at) -> bool:
    """Marked handled, and the customer hasn't written since."""
    handled_at = _naive_utc(handled_at)
    if not handled_at:
        return False
    last_customer_at = _naive_utc(last_customer_at)
    return last_customer_at is None or handled_at >= last_customer_at


def _classify(c, now) -> str:
    """Pick the one sidebar section a conversation belongs to (first match wins)."""
    if _is_handled(c.get("handled_at"), c.get("last_customer_at")):
        return "done"
    if _needs_attention(c, now):
        return "attention"
    if c.get("ordered"):
        return "orders"
    if c.get("last_card_link_at"):
        return "card_link"
    last_at = _naive_utc(c.get("last_timestamp"))
    if last_at and now - last_at < ACTIVE_WINDOW:
        return "active"
    return "older"


def _group_customers(customers):
    """Split an already-sorted customer list into {section_key: [rows]}."""
    groups = {key: [] for key, _ in SECTIONS}
    for c in customers:
        groups[c["section"]].append(c)
    return groups


def _dashboard_context(customers, error, **chat):
    groups = _group_customers(customers)
    return {
        "customers": customers,
        "sections": [(key, label, groups[key]) for key, label in SECTIONS],
        "messages": chat.get("messages", []),
        "selected_phone": chat.get("selected_phone"),
        "selected_name": chat.get("selected_name"),
        "bot_paused": chat.get("bot_paused", False),
        "ordered": chat.get("ordered", False),
        "handled": chat.get("handled", False),
        "window_open": chat.get("window_open", False),
        "error": error,
    }


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
        request, "admin_dashboard.html", _dashboard_context(customers, error)
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
    return templates.TemplateResponse(
        request,
        "admin_dashboard.html",
        _dashboard_context(
            customers,
            error,
            messages=messages,
            selected_phone=phone,
            selected_name=selected_name,
            bot_paused=bool(state.get("bot_paused")),
            ordered=bool(state.get("ordered")),
            handled=_chat_handled(state, messages),
            window_open=_window_open(messages),
        ),
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
                "section": c["section"],
                "ordered": bool(c.get("ordered")),
                "bot_paused": bool(c.get("bot_paused")),
                "card_link": bool(c.get("last_card_link_at")),
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
        "handled": _chat_handled(state, messages),
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
    # Give the bot a fresh 24h message budget, or a chat escalated for hitting
    # the limit would re-escalate on the customer's very next message.
    conversation_memory.reset_message_limit(f"whatsapp_{phone}")
    return {"ok": True, "bot_paused": False}


@router.post("/api/handled")
async def api_handled(payload: HandledPayload, _: None = Depends(require_admin_auth)):
    """Mark a chat handled (moves it to "done" until the customer writes again), or undo."""
    phone = (payload.phone or "").strip()
    if not phone:
        return JSONResponse({"ok": False, "error": "missing phone"}, status_code=400)
    await conversation_store.set_handled(phone, payload.handled)
    return {"ok": True, "handled": payload.handled}
