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
# 6-8 lines; this covers the agent over-generating.
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
    # double spaces) - only spaces/tabs, not newlines.
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
