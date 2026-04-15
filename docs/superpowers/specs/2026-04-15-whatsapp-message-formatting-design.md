# WhatsApp Message Formatting Redesign — Design Spec

**Date:** 2026-04-15
**Author:** Shay (via Claude)
**Status:** Approved — ready for implementation plan
**Scope:** Sales agent message output only. No architectural changes.

---

## Problem

The bot's responses on WhatsApp are factually correct but visually heavy and hard to scan. Concrete issues observed in production screenshots:

1. Walls of text with no visual rhythm — multiple topics (product, features, shipping, trial, promo, CTA) jammed into one message block.
2. URL-encoded Hebrew links render as gibberish (`%D7%91%D7%95%D7%A9%D7%9D-...`) instead of readable text.
3. No use of WhatsApp-native formatting (`*bold*`, `•` bullets, empty-line paragraph breaks).
4. Long numbered lists and markdown headers (`###`, `**`, `|` tables) that WhatsApp does not render.

The information itself is accurate and useful — the delivery is the problem.

## Goal

Keep the current content and one-message-per-response structure. Change only how the bot formats that content so WhatsApp renders it as a clean, scannable message.

## Non-goals

- Changing agent logic, RAG, escalation flow, order saving, or the Google Sheets integration.
- Splitting responses into multiple WhatsApp messages (considered as Approach A — user chose B).
- Restructuring session storage or any infrastructure.

---

## Design

### 1. WhatsApp formatting rules (enforced via system prompt)

| Rule | Specification |
|---|---|
| Bold for key info | `*LUST FOR HIM*`, `*198 ₪*` — single asterisks (WhatsApp native) |
| Bullets | `•` only. Not `-`, not `1.`, not emojis-as-bullets. |
| Paragraph break | One empty line between distinct ideas |
| Emoji | Use as section markers, not decoration. Max 2 emojis per message. |
| Line budget | Target 6–8 lines per message (soft limit in prompt); hard cap 10 lines enforced in code |
| Ending | Every response ends with a short question or CTA on its own line |
| URLs | On their own line, not inline. Use Hebrew/clean URL (see §4). |
| Forbidden syntax | `**bold**`, `###`, markdown tables `\|`, HTML |

### 2. Standard message structure

```
[emoji] *[Product Name]* — [one-line hook]

[1 sentence hook about benefit]

*[Section label]:*
• point 1
• point 2

*מחיר:* [price] ₪

[short question]
```

### 3. Reference example (before / after)

**Before:**
```
הבושם שלנו לגברים הוא ה-LUST FOR HIM 🖤

זה לא בושם רגיל, אלא שמן בושם מרוכז מבוסס פרומונים
(ספציפית Androstadienone), שנועד לחזק את הנוכחות
והביטחון העצמי שלך וליצור מגנטיות ומשיכה.

מה הריח שלו?
הוא בניחוח ארומטי-מימי, חזק ומרענן מאוד:
   תווי ראש: אשכולית, מנדרינה ותווים ימיים.
   תווי אמצע: עלי דפנה ויסמין.
   תווי בסיס: ענבר אפור, עץ גואיאק, אזוב אלונים ופצ'ולי.
...
```

**After:**
```
🖤 *LUST FOR HIM*
שמן בושם פרומונים לגברים

*הריח:* ארומטי-מימי, חזק ומרענן
• אשכולית ומנדרינה
• יסמין ועלי דפנה
• ענבר ופצ'ולי

*נפח:* 10 מ"ל (שקול ל-50 ספריי)
*מחיר באתר:* ‎198 ₪ (או 230 ₪ במזומן לשליח)

מה מעניין אותך — להזמין או עוד פרטים?
```

### 4. URL cleanup

Replace URL-encoded product links in `backend/data/lust_knowledge_base.md` with clean URLs.

Preferred order:
1. Canonical English slug URL from Shopify, if the product handle has one (e.g., `https://mylustshop.com/products/lust-for-him`).
2. Otherwise, decoded Hebrew URL (`https://mylustshop.com/products/בושם-פרומונים-לגברים`). WhatsApp displays Hebrew URLs correctly; browsers handle them natively.

Affected lines in the KB: `105`, `106`, `107`, `108`.

### 5. Post-processing safety net

Add a `format_for_whatsapp(text: str) -> str` function in `backend/app/agents/sales_agent.py` (or a new `backend/app/services/message_formatter.py`). Responsibilities:

- Convert `**bold**` → `*bold*` (already partially handled; generalize).
- Strip `###` markdown headers, `|` tables, and HTML tags.
- Preserve `*single-asterisk bold*`.
- Enforce a hard cap of 10 non-empty lines. If exceeded, keep the first ~8 lines (truncating at the last sentence boundary) and append a generic fallback CTA: `\n\nרוצה לשמוע עוד? 😊`. The prompt is required to end responses with a CTA (see §1, "Ending"), so this branch should rarely fire in practice — it exists as a safety net for when the model over-generates.

This function runs after the agent produces text and before `whatsapp_service.send_text_message()` is called.

### 6. Scope of prompt changes

File: `backend/app/agents/prompts.py`

- Replace the "⚡ כללי פורמט - קריטי!" section with the new WhatsApp rules (§1).
- Replace existing good/bad examples with the ones in §3.
- Add the standard message structure (§2) as a reference template.
- Leave all other sections (identity, iron rules, sales flow, escalation, no-invent lists) untouched.

### 7. Testing strategy

Manual verification via the production chat endpoint with at least these queries:

1. "ספר לי על FOR HIM" — expects formatted product description matching §3.
2. "מה המחירים?" — expects compact price summary, not a table.
3. "שלח לי קישור" — expects URL alone on its own line.
4. "מה זה פרומונים?" — expects short explanation, not a lecture.
5. Order flow happy path — expects clean order summary with `*bold*` labels.

For each, verify the rendered WhatsApp message (screenshot) matches the design.

Add one lightweight unit test for `format_for_whatsapp()` covering: `**` → `*`, header stripping, line cap enforcement.

---

## Out of scope (tracked for later)

These items were identified in the CTO review but are deliberately not addressed in this spec:

- Sessions persistence to MongoDB
- WhatsApp webhook HMAC signature verification
- Rate limiting
- Google Sheets race condition
- CORS, admin auth, CI/CD, Docker hardening
- Message splitting / multi-message responses (Approach A)

Each will be its own spec when prioritized.

---

## Acceptance criteria

- [ ] System prompt updated per §1, §2, §3.
- [ ] KB URLs updated per §4.
- [ ] `format_for_whatsapp()` implemented and wired into the send path.
- [ ] All 5 manual test queries produce WhatsApp messages that pass visual review.
- [ ] Unit test for `format_for_whatsapp()` passes.
- [ ] Deployed to Render, verified end-to-end in real WhatsApp.
