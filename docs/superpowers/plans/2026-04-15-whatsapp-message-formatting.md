# WhatsApp Message Formatting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make bot responses render cleanly on WhatsApp by using WhatsApp-native syntax (`*bold*`, `•` bullets, empty-line paragraphs), clean URLs, and a line-cap safety net.

**Architecture:** Prompt-first redesign (`prompts.py`) + post-processing formatter (`sales_agent.py`) + KB URL cleanup (`lust_knowledge_base.md`). No changes to agent logic, RAG, escalation, or infra.

**Tech Stack:** Python 3.13, FastAPI, Pydantic AI, Google Gemini, MongoDB, WhatsApp Cloud API.

**Spec:** `docs/superpowers/specs/2026-04-15-whatsapp-message-formatting-design.md`

---

## File Structure

**Modify:**
- `backend/app/agents/prompts.py` — replace the "כללי פורמט" section and examples (Task 1)
- `backend/data/lust_knowledge_base.md` — replace URL-encoded links with decoded Hebrew URLs (Task 2)
- `backend/app/agents/sales_agent.py` — remove `clean_markdown_formatting()`, import `format_for_whatsapp` from the new module, update two call sites (Task 4)

**Create:**
- `backend/app/services/message_formatter.py` — pure-Python module with only `re` as a dependency; hosts `format_for_whatsapp()` so tests can import it without triggering Pydantic AI / Mongo / Google Sheets initialization (Task 3)
- `backend/tests/test_whatsapp_formatter.py` — runnable Python test script matching existing convention (Task 3)

**Operational (run, not commit):**
- Re-run `backend/scripts/upload_knowledge_base.py` to push the cleaned KB to MongoDB (Task 5)

---

## Task 1: Update system prompt with WhatsApp formatting rules

**Files:**
- Modify: `backend/app/agents/prompts.py` (lines ~101-144, the "כללי פורמט" section and no-invent rules area)

- [ ] **Step 1: Read the current section that will be replaced**

Open `backend/app/agents/prompts.py` and locate the block starting at `### ⚡ כללי פורמט - קריטי!` (currently around line 101) through the end of the `### ⛔ דברים לא להמציא!` section (around line 144).

- [ ] **Step 2: Replace that block with the new WhatsApp-native rules**

In `backend/app/agents/prompts.py`, replace everything from `### ⚡ כללי פורמט - קריטי!` through and including `### ⛔ דברים לא להמציא!` with the following Hebrew content (preserve exact indentation — inside the triple-quoted `SALES_AGENT_SYSTEM_PROMPT` string):

```
### ⚡ כללי פורמט - קריטי ל-WhatsApp!

ההודעות מוצגות ב-WhatsApp. חובה להשתמש בפורמט נייטיבי של WhatsApp בלבד.

**כללי פורמט - חובה לציית:**
- **הדגשה:** *כוכבית אחת* לטקסט מודגש (זה מה ש-WhatsApp מזהה). אסור `**שתי כוכביות**`.
- **רשימות:** רק התו `•` (נקודה) בתחילת שורה. אסור `-`, אסור `1.` או מספור, אסור אימוג'י כתחליף.
- **פסקאות:** שורה ריקה אחת בין רעיונות שונים.
- **אורך:** 6 עד 8 שורות להודעה. מעל 10 שורות = פסול.
- **אימוג'י:** מקסימום 2 לכל הודעה. רק כסמן לחלק חדש (בתחילת שורה), לא כקישוט.
- **קישור:** בשורה משלו, לא באמצע טקסט.
- **סיום:** כל תשובה מסתיימת בשאלה קצרה או קריאה לפעולה (CTA) בשורה נפרדת.
- **אסור בתכלית:** `**` (שתי כוכביות), `###` (כותרות markdown), `|` (טבלאות), HTML.

**מבנה סטנדרטי להודעה:**

```
[אימוג'י] *[שם מוצר]* — [תיאור של שורה אחת]

[משפט אחד על התועלת / hook]

*[תווית לחלק]:*
• נקודה 1
• נקודה 2

*מחיר:* [סכום] ₪

[שאלה קצרה]
```

**דוגמה למבנה נכון (נקי וקריא):**
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

**דוגמה לפסול (לא להעתיק!):**
```
הבושם שלנו לגברים הוא ה-LUST FOR HIM 🖤

זה לא בושם רגיל, אלא שמן בושם מרוכז מבוסס פרומונים (ספציפית Androstadienone), שנועד לחזק...
[עוד 8 שורות של טקסט רציף]
```
הבעיה: פסקה רציפה ארוכה, בלי פורמט WhatsApp, קשה לסריקה.

**כללים נוספים:**
- עברית בלבד
- לא להסביר מה זה פרומונים אם לא שאלו!
- לא לתת מחיר אם לא שאלו!
- לא לשאול איך רוצה לשלם אם לא אמר שרוצה לקנות!
- לענות רק על מה שנשאל!

### ⛔ דברים לא להמציא!
- לא להמציא זמני משלוח! (לא "24 שעות", לא "2-3 ימים")
- לא להמציא מידע שלא קיים במאגר!
- רק מידע שחזר מ-search_products_info!
```

- [ ] **Step 3: Verify the change compiles (imports are still valid)**

Run: `cd "/Users/shayFeldboy/Documents/shay/LustBot-claude code" && source venv/bin/activate && python -c "from backend.app.agents.prompts import SALES_AGENT_SYSTEM_PROMPT; print(f'Prompt length: {len(SALES_AGENT_SYSTEM_PROMPT)} chars')"`

Expected: prints a length (should be a few thousand chars), no import errors.

- [ ] **Step 4: Commit**

```bash
cd "/Users/shayFeldboy/Documents/shay/LustBot-claude code"
git add backend/app/agents/prompts.py
git commit -m "$(cat <<'EOF'
Rewrite format rules in system prompt for WhatsApp-native rendering

Replaces the old generic format section with rules that match what
WhatsApp actually renders: *single-asterisk bold*, bullet character,
empty-line paragraphs, max 2 emojis, line budget, CTA at end.
Replaces good/bad examples with the real screenshot case.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Clean URL-encoded links in the knowledge base

**Files:**
- Modify: `backend/data/lust_knowledge_base.md` (lines 105-108, the product links table)

- [ ] **Step 1: Replace the URL-encoded links with decoded Hebrew URLs**

In `backend/data/lust_knowledge_base.md`, find the links table (currently lines 105-108):

```
| LUST FOR HIM | https://mylustshop.com/products/%D7%91%D7%95%D7%A9%D7%9D-%D7%A4%D7%A8%D7%95%D7%9E%D7%95%D7%A0%D7%99%D7%9D-%D7%9C%D7%92%D7%91%D7%A8%D7%99%D7%9D |
| LUST FOR HER | https://mylustshop.com/products/%D7%91%D7%95%D7%A9%D7%9D-%D7%A4%D7%A8%D7%95%D7%9E%D7%95%D7%A0%D7%99%D7%9D-%D7%9C%D7%A0%D7%A9%D7%99%D7%9D |
| מארז זוגי (Couple) | https://mylustshop.com/products/%D7%9E%D7%90%D7%A8%D7%96-%D7%9B%D7%A4%D7%95%D7%9C |
| מארז זוגי + AskQ | https://mylustshop.com/products/%D7%9C%D7%A9%D7%95%D7%91%D7%91%D7%99%D7%9D-%D7%91%D7%9C%D7%91%D7%93 |
```

Replace with:

```
| LUST FOR HIM | https://mylustshop.com/products/בושם-פרומונים-לגברים |
| LUST FOR HER | https://mylustshop.com/products/בושם-פרומונים-לנשים |
| מארז זוגי (Couple) | https://mylustshop.com/products/מארז-כפול |
| מארז זוגי + AskQ | https://mylustshop.com/products/לשובבים-בלבד |
```

- [ ] **Step 2: Verify each URL actually loads (no 404)**

Run each URL through `curl` to confirm Shopify serves the product:

```bash
for url in \
  "https://mylustshop.com/products/בושם-פרומונים-לגברים" \
  "https://mylustshop.com/products/בושם-פרומונים-לנשים" \
  "https://mylustshop.com/products/מארז-כפול" \
  "https://mylustshop.com/products/לשובבים-בלבד"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url")
  echo "$code  $url"
done
```

Expected: all four return `200` (or `301`/`302` which also means the product exists). If any return `404`, stop and report to the user — the decoded URL may not match Shopify's handle. Fall back to the URL-encoded original for that specific product only.

- [ ] **Step 3: Commit**

```bash
cd "/Users/shayFeldboy/Documents/shay/LustBot-claude code"
git add backend/data/lust_knowledge_base.md
git commit -m "$(cat <<'EOF'
Use decoded Hebrew URLs in knowledge base

WhatsApp rendered percent-encoded URLs as long %XX gibberish.
Shopify accepts decoded Hebrew handles and WhatsApp displays them
as readable text. Browsers re-encode on navigation so clicks
still resolve correctly.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Build `format_for_whatsapp()` in a new module with tests (TDD)

**Files:**
- Create: `backend/app/services/message_formatter.py`
- Create: `backend/tests/test_whatsapp_formatter.py`

The formatter lives in its own module so tests can import it in isolation. Importing `sales_agent.py` triggers Pydantic AI agent construction, MongoDB/Google Sheets service imports, and reads env vars — none of that is needed to test a pure-text function.

- [ ] **Step 1: Write the failing test file**

Create `backend/tests/test_whatsapp_formatter.py` with this exact content:

```python
"""Test WhatsApp post-processing formatter.

Plain Python runnable script (matches existing test_mongodb.py / test_sheets.py convention).
Exits with code 0 if all assertions pass, 1 otherwise.

Run from project root:
    python backend/tests/test_whatsapp_formatter.py
"""
import sys
import os

# Add backend/ to sys.path so `from app.services...` works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.message_formatter import format_for_whatsapp


def assert_equal(actual, expected, label):
    if actual != expected:
        print(f"❌ FAIL: {label}")
        print(f"   expected: {expected!r}")
        print(f"   actual:   {actual!r}")
        return False
    print(f"✅ PASS: {label}")
    return True


def main() -> int:
    passed = True

    # Double asterisks collapse to single
    passed &= assert_equal(
        format_for_whatsapp("**LUST FOR HIM**"),
        "*LUST FOR HIM*",
        "double asterisk -> single",
    )

    # Single asterisks are preserved
    passed &= assert_equal(
        format_for_whatsapp("*שלום*"),
        "*שלום*",
        "single asterisk preserved",
    )

    # Markdown headers are stripped
    passed &= assert_equal(
        format_for_whatsapp("### כותרת\nשורה"),
        "כותרת\nשורה",
        "markdown header stripped",
    )

    # Table pipe characters are removed (leaving visible text)
    passed &= assert_equal(
        format_for_whatsapp("| a | b |"),
        "a b",
        "table pipes stripped",
    )

    # HTML tags are stripped
    passed &= assert_equal(
        format_for_whatsapp("<b>bold</b> plain"),
        "bold plain",
        "html tags stripped",
    )

    # Line cap enforced: input >10 non-empty lines gets truncated
    long_input = "\n".join([f"שורה {i}" for i in range(1, 15)])
    result = format_for_whatsapp(long_input)
    non_empty_count = len([line for line in result.split("\n") if line.strip()])
    passed &= assert_equal(
        non_empty_count <= 9,  # 8 kept lines + 1 CTA line
        True,
        f"line cap enforced (got {non_empty_count} non-empty lines)",
    )
    passed &= assert_equal(
        "רוצה לשמוע עוד" in result,
        True,
        "fallback CTA appended when over cap",
    )

    # Under cap: content preserved as-is
    short_input = "שלום\nאיך אפשר לעזור?"
    passed &= assert_equal(
        format_for_whatsapp(short_input),
        short_input,
        "short input unchanged",
    )

    # None input returns empty string
    passed &= assert_equal(
        format_for_whatsapp(None),
        "",
        "None input -> empty string",
    )

    # Whitespace at edges trimmed
    passed &= assert_equal(
        format_for_whatsapp("  hello  \n\n\n"),
        "hello",
        "leading/trailing whitespace trimmed",
    )

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the test and confirm it fails with an ImportError**

Run:
```bash
cd "/Users/shayFeldboy/Documents/shay/LustBot-claude code"
source venv/bin/activate
python backend/tests/test_whatsapp_formatter.py
```

Expected: fails with `ModuleNotFoundError: No module named 'app.services.message_formatter'`.

- [ ] **Step 3: Implement the formatter module**

Create `backend/app/services/message_formatter.py` with this exact content:

```python
"""WhatsApp-native output normalizer.

Runs on every agent response before it is sent to the user. Converts
common markdown patterns the LLM emits into WhatsApp's supported
syntax, strips patterns WhatsApp cannot render, and enforces a hard
line cap to guard against over-generation.

Pure-Python: depends only on ``re``. Safe to import in tests.
"""
from __future__ import annotations

import re

# Hard cap applied after all other normalization. The prompt asks for
# 6–8 lines; this covers the agent over-generating.
MAX_NON_EMPTY_LINES = 10
TRUNCATION_KEEP = 8
FALLBACK_CTA = "רוצה לשמוע עוד? 😊"


def format_for_whatsapp(text: str | None) -> str:
    """Normalize agent output for WhatsApp rendering.

    - Collapses ``**bold**`` to WhatsApp's ``*bold*``.
    - Strips markdown headers (``#``), table pipes (``|``), HTML tags.
    - Enforces a cap of ``MAX_NON_EMPTY_LINES`` non-empty lines; on
      overflow, keeps the first ``TRUNCATION_KEEP`` non-empty lines
      and appends ``FALLBACK_CTA``.
    - Trims whitespace at the edge of every line and the full text.
    """
    if text is None:
        return ""

    # Collapse **bold** -> *bold* BEFORE we touch single asterisks
    text = re.sub(r"\*\*([^*]+)\*\*", r"*\1*", text)

    # Strip markdown headers ("### foo" -> "foo")
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Remove table pipe characters
    text = text.replace("|", "")

    # Collapse runs of horizontal whitespace (the pipe strip can leave
    # double spaces) — only spaces/tabs, not newlines.
    text = re.sub(r"[ \t]+", " ", text)

    # Trim whitespace on each line, then the whole string
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = text.strip()

    # Enforce line cap
    lines = text.split("\n")
    non_empty_count = sum(1 for line in lines if line.strip())
    if non_empty_count > MAX_NON_EMPTY_LINES:
        kept: list[str] = []
        kept_non_empty = 0
        for line in lines:
            if line.strip():
                if kept_non_empty >= TRUNCATION_KEEP:
                    break
                kept_non_empty += 1
            kept.append(line)
        # Drop trailing empty lines from the kept slice
        while kept and not kept[-1].strip():
            kept.pop()
        text = "\n".join(kept) + f"\n\n{FALLBACK_CTA}"

    return text
```

- [ ] **Step 4: Re-run the test and confirm it passes**

Run:
```bash
cd "/Users/shayFeldboy/Documents/shay/LustBot-claude code"
source venv/bin/activate
python backend/tests/test_whatsapp_formatter.py
```

Expected: every assertion prints `✅ PASS` and the script exits with code 0.

- [ ] **Step 5: Commit**

```bash
cd "/Users/shayFeldboy/Documents/shay/LustBot-claude code"
git add backend/app/services/message_formatter.py backend/tests/test_whatsapp_formatter.py
git commit -m "$(cat <<'EOF'
Add message_formatter.format_for_whatsapp() with tests

Pure-Python module that normalizes agent output for WhatsApp:
collapses **bold** to *bold*, strips markdown headers, HTML tags,
and table pipes, and enforces a 10-line cap with a fallback CTA
for agent over-generation. Lives in services/ so tests can import
it without triggering Pydantic AI / Mongo / Sheets initialization.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Wire `format_for_whatsapp()` into the agent send path

**Files:**
- Modify: `backend/app/agents/sales_agent.py` — add new import, replace two call sites, remove the old `clean_markdown_formatting()` function.

- [ ] **Step 1: Add the import**

In `backend/app/agents/sales_agent.py`, locate the import block near the top of the file (after the existing `from ..config import get_settings` import, around line 13). Add:

```python
from ..services.message_formatter import format_for_whatsapp
```

- [ ] **Step 2: Remove the obsolete `clean_markdown_formatting()` function**

Delete lines 57-67 (the whole `def clean_markdown_formatting(text: str) -> str:` function). The new formatter replaces it. Keep the `re` import — it's still used elsewhere in the module (e.g., the markdown cleaning inside tool docstrings).

- [ ] **Step 3: Replace both call sites**

Find the two lines in `backend/app/agents/sales_agent.py` that read:

```python
response_text = clean_markdown_formatting(response_text)
```

(originally at lines 362 and 383). Replace both with:

```python
response_text = format_for_whatsapp(response_text)
```

- [ ] **Step 4: Confirm nothing else references the old name**

Run:
```bash
cd "/Users/shayFeldboy/Documents/shay/LustBot-claude code"
grep -rn "clean_markdown_formatting" backend/ --include="*.py"
```

Expected: no output. If any import or call remains, update it to `format_for_whatsapp` (imported from `..services.message_formatter` where relative imports work, else `from app.services.message_formatter import format_for_whatsapp`) and repeat.

- [ ] **Step 5: Smoke-test that sales_agent still imports cleanly**

Run:
```bash
cd "/Users/shayFeldboy/Documents/shay/LustBot-claude code"
source venv/bin/activate
cd backend && python -c "from app.agents.sales_agent import format_for_whatsapp; print(format_for_whatsapp('**hi**'))"
```

Expected: prints `*hi*` and exits 0. No traceback.

- [ ] **Step 6: Re-run the formatter test**

Run:
```bash
cd "/Users/shayFeldboy/Documents/shay/LustBot-claude code"
source venv/bin/activate
python backend/tests/test_whatsapp_formatter.py
```

Expected: all assertions still pass.

- [ ] **Step 7: Commit**

```bash
cd "/Users/shayFeldboy/Documents/shay/LustBot-claude code"
git add backend/app/agents/sales_agent.py
git commit -m "$(cat <<'EOF'
Wire format_for_whatsapp into sales agent, remove old cleaner

Both response paths (primary and fallback agent) now call the
WhatsApp-aware formatter. The old clean_markdown_formatting()
helper is deleted — its behavior is subsumed and extended by the
new module.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Re-upload the cleaned knowledge base to MongoDB

**Files:** none (operational only)

- [ ] **Step 1: Verify the `.env` points at the new EU cluster**

Run:
```bash
cd "/Users/shayFeldboy/Documents/shay/LustBot-claude code"
grep "^MONGODB_URI=" .env | cut -d@ -f2
```

Expected: output starts with `shay1.q4fugt3.mongodb.net` (the new EU cluster). If it shows `z05uuhz` (the old Bahrain cluster), stop — the migration work done earlier is missing; do not proceed.

- [ ] **Step 2: Run the upload script**

Run:
```bash
cd "/Users/shayFeldboy/Documents/shay/LustBot-claude code"
source venv/bin/activate
python backend/scripts/upload_knowledge_base.py
```

Expected: `✅ Successfully uploaded 8 chunks to MongoDB!` and `Total documents in collection: 8`.

- [ ] **Step 3: Sanity-check that the new URLs are in MongoDB**

Run:
```bash
cd "/Users/shayFeldboy/Documents/shay/LustBot-claude code"
source venv/bin/activate
python - <<'PY'
import os
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()
client = MongoClient(os.environ["MONGODB_URI"])
col = client[os.environ["MONGODB_DATABASE"]][os.environ["MONGODB_COLLECTION"]]
for doc in col.find({"title": {"$regex": "קישורים"}}):
    print(doc.get("text", "")[:500])
PY
```

Expected: the printed text contains `בושם-פרומונים-לגברים` (decoded Hebrew) and does **not** contain `%D7%91%D7%95`. If `%D7` appears, Task 2 didn't save correctly — re-check the KB file.

---

## Task 6: Manual end-to-end verification

**Files:** none (manual verification only)

- [ ] **Step 1: Start the local server**

Run in a dedicated terminal:
```bash
cd "/Users/shayFeldboy/Documents/shay/LustBot-claude code"
source venv/bin/activate
cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8765 --log-level info
```

Leave running. Open a second terminal for the next steps.

- [ ] **Step 2: Run each verification query and inspect the response**

Run all 5 queries from the spec's testing strategy:

```bash
for msg in \
  "ספר לי על FOR HIM" \
  "מה המחירים?" \
  "שלח לי קישור ל-FOR HIM" \
  "מה זה פרומונים?" \
  "רוצה להזמין FOR HIM, לשלם באתר"; do
  echo "====================================="
  echo "Q: $msg"
  echo "-------------------------------------"
  curl -s -X POST http://127.0.0.1:8765/api/chat \
    -H "Content-Type: application/json" \
    -d "{\"message\":\"$msg\",\"session_id\":\"fmt_verify_$(date +%s%N)\"}" \
    --max-time 60 \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('response',''))"
done
```

For each response, visually verify:
- Uses `*bold*` (single asterisks), never `**bold**`.
- Uses `•` for bullets.
- Has empty lines between sections.
- Contains ≤ 2 emojis.
- Is ≤ 10 non-empty lines.
- Ends with a question or CTA.
- If a URL is present, it's on its own line and uses decoded Hebrew (no `%D7`).

Report any response that fails. Do not proceed until all 5 pass.

- [ ] **Step 3: Stop the local server**

In the server terminal, press Ctrl+C. Or from another terminal:
```bash
kill $(lsof -ti:8765) 2>/dev/null; echo stopped
```

- [ ] **Step 4: Push to main (triggers Render auto-deploy)**

```bash
cd "/Users/shayFeldboy/Documents/shay/LustBot-claude code"
git push origin main
```

- [ ] **Step 5: Wait for Render deploy to go live and re-test against production**

Poll until the latest deploy is `live`:

```bash
until [ "$(curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
  "https://api.render.com/v1/services/srv-d59tjvdactks73f0l3qg/deploys?limit=1" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)[0]["deploy"]["status"])')" = "live" ]; do
  echo "deploy not live yet, waiting..."
  sleep 30
done
echo "DEPLOY LIVE"
```

Note: `$RENDER_API_KEY` must be set in your shell — do NOT paste it in a commit. If you don't have it exported, run the script with the key inline: `RENDER_API_KEY=rnd_... until ...`

Then re-run Step 2 against production URL `https://lustchatbot-ahpt.onrender.com`:

```bash
for msg in "ספר לי על FOR HIM" "מה המחירים?" "שלח לי קישור ל-FOR HIM"; do
  echo "Q: $msg"
  curl -s -X POST https://lustchatbot-ahpt.onrender.com/api/chat \
    -H "Content-Type: application/json" \
    -d "{\"message\":\"$msg\",\"session_id\":\"prod_fmt_$(date +%s%N)\"}" \
    --max-time 60 \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('response',''))"
  echo "-----"
done
```

Expected: same visual criteria as Step 2.

- [ ] **Step 6: Real WhatsApp smoke test**

Send "ספר לי על FOR HIM" to the production WhatsApp number from your phone. Screenshot the bot's reply. Confirm the WhatsApp UI renders:
- Bold text (not literal asterisks).
- Bullets (not literal `•` characters shown raw — though this is actually what WhatsApp shows; verify it looks intentional).
- URL as a clickable preview, not as `%D7%` gibberish.

Attach the screenshot to the PR / task summary.

---

## Acceptance checklist (final)

Copy-paste into the final task summary:

- [ ] System prompt rewritten per spec §1–§3 (Task 1)
- [ ] KB URLs decoded and verified loading (Task 2)
- [ ] `format_for_whatsapp()` implemented with passing tests (Task 3)
- [ ] Formatter wired into both send paths, old alias removed (Task 4)
- [ ] KB re-uploaded to EU Mongo; decoded URLs verified in DB (Task 5)
- [ ] All 5 local verification queries pass visual review (Task 6 Step 2)
- [ ] Production deploy is `live` and passes verification (Task 6 Step 5)
- [ ] Real WhatsApp smoke test screenshot attached (Task 6 Step 6)
