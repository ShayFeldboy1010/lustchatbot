# WhatsApp Conversation Persistence & Admin Viewer — Design Spec

**Date:** 2026-07-01
**Author:** Shay (via Claude)
**Status:** Approved — ready for implementation plan
**Scope:** Persist customer conversations to MongoDB; add a minimal read-only admin panel on the same server; fix the Logfire observability gap in production.

---

## Problem

Investigation surfaced three related gaps:

1. Conversation history is never persisted anywhere durable. `ConversationMemory` (`backend/app/services/memory.py`) is a pure in-process `OrderedDict`, whose own docstring says "For production, replace with Redis or similar." Any restart, redeploy, or scale event on Render wipes it instantly. There is no way today for the business owners to review past customer conversations.
2. Escalations (`backend/app/tools/escalation.py`, `escalation_log`) are similarly in-memory only and never surfaced anywhere the owners would see them — despite keyword-based escalation detection already running on every message.
3. Logfire tracing only configures itself when `LOGFIRE_TOKEN` is present in the process environment (`backend/app/agents/sales_agent.py:19-32`), but `render.yaml` never declares that variable, so production traces never reach the Logfire dashboard even though the code is correct.

The owners have no way to see what customers are saying to the bot, or to know when a conversation needs a human to step in.

## Goal

Give the business owners a simple, password-protected, same-server page where they can see customer conversations (grouped by name + phone number) and immediately spot ones that may need a human to intervene — without touching the bot's live request-handling behavior or performance.

## Non-goals

- No changes to agent logic, RAG, order flow, or the Google Sheets integration.
- No reply-from-panel capability — owners already reply via their own WhatsApp Business app/number.
- No mark-as-resolved / escalation lifecycle workflow (v1 is read-only).
- No search or date filtering beyond escalated-first sorting (v1).
- No change to the existing in-memory `ConversationMemory` used for live agent context — it stays exactly as-is; Mongo persistence is purely additive.

---

## Design

### 1. Data model

New MongoDB collection `conversations` in the existing `ecommerce` database (same cluster as the RAG store, separate collection — no interaction with `data-for-ai`).

One document per message:

```
{
  phone: str,          # WhatsApp sender id, e.g. "972501234567"
  name: str,            # WhatsApp profile display name; "" if unavailable
  role: "customer" | "bot",
  content: str,
  timestamp: datetime,  # UTC
  escalated: bool        # true only on the specific message that triggered escalation
}
```

Indexes: `phone` (thread lookups), `timestamp` descending (recency sort / list truncation). Pure append log — no updates, no unique constraint.

### 2. Write path

New `backend/app/services/conversation_store.py`:

```python
async def save_message(phone: str, name: str, role: str, content: str, escalated: bool = False) -> None
```

Called from `backend/app/routers/whatsapp.py`'s `receive_message()` alongside (not instead of) the existing `conversation_memory.add_message()` calls — once for the inbound customer message, once for the outbound bot reply.

Wrapped in try/except; any Mongo error is logged and swallowed. This call must never raise into the webhook handler or delay the WhatsApp response — persistence is strictly best-effort relative to the live chat.

`name` is sourced from the already-parsed `sender_name` (`whatsapp.py:77`, originally read from the incoming payload at `whatsapp.py:138-139`) — currently discarded after each request; this wires it through to storage instead.

`escalated=True` is set only on the customer message that contains the keyword(s) triggering escalation (existing detection around `whatsapp.py` lines ~128/182 and `escalation.py`). It is not retroactively applied to earlier messages in the thread.

### 3. Admin pages

FastAPI + Jinja2 templates (bundled with FastAPI, no new frontend framework, no build step), with a small inline `<style>` block — minimal and readable, no JS required for read-only pages.

- `GET /admin` — one row per distinct customer: name, phone, last message preview, last message time. A conversation is treated as "needs attention" if **any** of its messages has `escalated=True`; those rows are pinned to the top with a visible badge. Remaining rows sorted by most recent activity. List capped to the 50 most recently active customers (v1).
- `GET /admin/chat/{phone}` — full thread for one customer, chronological, chat-bubble layout, customer vs. bot visually distinct (alignment/color). Capped to the most recent 200 messages (v1).

Both routes live in the existing FastAPI app on the existing Render service — no separate deploy, no new domain.

### 4. Auth

`fastapi.security.HTTPBasic` dependency applied to both `/admin` and `/admin/chat/{phone}`. The submitted password is compared via `secrets.compare_digest()` against a new `ADMIN_PASSWORD` env var; the username field is accepted but not meaningfully validated (single shared password, per decision). Incorrect or missing credentials return `401` with a `WWW-Authenticate: Basic` challenge, which triggers the browser's native login prompt — no custom login page needed.

`ADMIN_PASSWORD` is added to `render.yaml` as `sync: false` (value set manually in the Render dashboard, never committed to the repo).

### 5. Logfire fix (bundled — one-line, same deploy)

Add `LOGFIRE_TOKEN` (`sync: false`) to `render.yaml`'s `envVars`, and set the actual token value in the Render dashboard for the `lustbot-api` service. No code changes needed — `sales_agent.py` already reads the variable correctly; production was simply never given a value.

### 6. Error handling

- Mongo write failure on the hot path (webhook): logged and swallowed; the customer-facing response is unaffected (§2).
- Mongo read failure on `/admin` or `/admin/chat/{phone}`: render a plain "couldn't load conversations right now" message instead of a raw 500.
- Missing `name`: display the phone number alone — no placeholder text like "Unknown".

### 7. Testing strategy

- Unit test for `save_message()` with a mocked Mongo collection: asserts document shape, asserts a raised Mongo exception is caught and does not propagate.
- Unit test for the Basic Auth dependency: correct password → 200, wrong/missing password → 401.
- Manual verification: send a real WhatsApp test message, confirm it appears on `/admin` and in the thread view within seconds; trigger an escalation keyword, confirm the badge appears on that conversation.

---

## Out of scope (tracked for later)

- Reply-from-admin-panel capability.
- Mark-as-resolved / escalation lifecycle management.
- Search, filtering, or pagination beyond the v1 caps.
- Multi-user admin accounts / role-based access.
- Retention/TTL policy on the `conversations` collection — not needed yet at expected volume (see cost note), revisit if the free MongoDB tier's 512MB limit is approached.

---

## Acceptance criteria

- [ ] `conversations` collection defined and written to on every inbound/outbound WhatsApp message.
- [ ] `sender_name` wired through from webhook parsing into stored messages.
- [ ] The message that triggers escalation is flagged `escalated=True` and its conversation shows a badge in the admin list.
- [ ] `/admin` and `/admin/chat/{phone}` both require `ADMIN_PASSWORD` Basic Auth.
- [ ] `LOGFIRE_TOKEN` added to `render.yaml`; Logfire dashboard shows live production traces after deploy.
- [ ] Existing in-memory `ConversationMemory` behavior unchanged — bot's live responses unaffected.
- [ ] Unit tests for `save_message()` and admin auth pass.
- [ ] Deployed to Render, verified end-to-end: a real WhatsApp message appears in the admin panel.
