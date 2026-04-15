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
