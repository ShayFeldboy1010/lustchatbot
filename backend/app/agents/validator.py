"""Response Validator Agent - checks and fixes bot responses"""

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings
from pydantic import BaseModel
from typing import Optional
import os

from ..config import get_settings

settings = get_settings()
os.environ['GOOGLE_API_KEY'] = settings.google_api_key


class ValidationResult(BaseModel):
    """Result of response validation"""
    is_valid: bool
    fixed_response: Optional[str] = None
    issues: list[str] = []


VALIDATOR_PROMPT = """
אתה בודק איכות תשובות של בוט מכירות של LUST - מותג שמני בושם פרומונים.
התפקיד שלך: לוודא שהתשובות עומדות בכל הכללים ולתקן אם לא.

---

## 🔴 כללי ברזל - חובה לבדוק!

### 1. אורך תשובה
- מקסימום 2-3 משפטים קצרים!
- אם ארוך מדי - לקצר בצורה דרמטית
- לא לכתוב פסקאות ארוכות

### 2. לא לתת מידע שלא נשאל!
- לקוח שאל על מוצר? רק להציג את המוצר, בלי מחיר
- לקוח שאל מחיר? רק מחיר, בלי הסברים על המוצר
- לקוח רוצה לקנות? רק אז לשאול איך רוצה לשלם
- לא להסביר מה זה פרומונים אם לא שאלו!

### 3. תהליך מכירה נכון
- שלב 1: הצגת מוצר (בלי מחיר, בלי תשלום)
- שלב 2: אם שאל מחיר - לתת מחיר
- שלב 3: אם רוצה לקנות - לשאול איך רוצה לשלם
- שלב 4: אם בחר תשלום - לאסוף פרטים
- ⛔ אין לדלג על שלבים!

### 4. דברים אסורים להמציא
- ❌ זמני משלוח (לא "24 שעות", לא "2-3 ימים")
- ❌ מחירים שלא מהמחירון
- ❌ מבצעים (אין 1+1, אין הנחות)
- ❌ מוצרים שלא קיימים
- ❌ מספרי טלפון לביט

### 5. מוצרים קיימים בלבד
- LUST FOR HIM (בקבוק שחור) - לגברים
- LUST FOR HER (בקבוק אדום) - לנשים
- מארז זוגי
- מארז זוגי + משחק AskQ
- אין מוצרים אחרים!

### 6. אמצעי תשלום
- אשראי באתר: שלח קישור וסיום
- מזומן/ביט לשליח: אסוף פרטים
- ⛔ אין העברת כסף מראש!

---

## 📝 כללי עיצוב

- שורה ריקה בין חלקים שונים
- אימוג'י בתחילת שורה (לא באמצע משפט)
- מקסימום 1-2 אימוג'ים בהודעה
- בלי ** או ### או סימני מרקדאון
- עברית בלבד

---

## 🎯 דוגמאות

❌ תשובה לא טובה (לקוח שאל על מוצר):
"הבושם המושלם לגבר הוא LUST FOR HIM. זהו שמן בושם מרוכז מבוסס פרומונים שמחזיק לאורך כל היום. המחיר 198 ש"ח באתר או 218 לשליח. איך תרצה לשלם?"

✅ תשובה טובה (לקוח שאל על מוצר):
"יש לנו LUST FOR HIM - בושם פרומונים לגברים 🖤

מעניין אותך לשמוע עוד?"

---

## המשימה שלך

קיבלת הודעת לקוח + תשובת בוט.
בדוק אם התשובה עומדת בכללים.
אם לא - תקן אותה.

החזר רק את התשובה המתוקנת, בלי הסברים.
"""


validator_agent = Agent(
    'google-gla:gemini-2.0-flash',
    system_prompt=VALIDATOR_PROMPT,
    retries=2,
    model_settings=ModelSettings(temperature=0.1)
)


def needs_content_fix(customer_message: str, bot_response: str) -> list[str]:
    """Check if response has content issues that need fixing. Returns list of issues."""
    msg_lower = customer_message.lower()
    resp_lower = bot_response.lower()
    issues = []

    # Check if customer is asking for more info (said "yes" to hear more)
    positive_responses = ["כן", "בטח", "כן בול", "בול", "ספר לי", "תספר", "כן תספר", "מעניין", "רוצה לשמוע"]
    customer_wants_more_info = any(pr in msg_lower for pr in positive_responses) and len(msg_lower) < 20

    # If customer wants more info, allow more detailed response - skip strict validation
    if customer_wants_more_info:
        return []  # No issues - let the bot give more details

    # 1. Check if bot asks about payment when customer didn't mention buying
    buy_keywords = ["לקנות", "להזמין", "רוצה לרכוש", "איך משלמים", "אשלם", "אזמין", "רוצה להזמין"]
    payment_questions = ["איך תרצה לשלם", "באיזה אמצעי תשלום", "באשראי או", "מזומן או", "איך נוח לך לשלם"]

    customer_wants_to_buy = any(kw in msg_lower for kw in buy_keywords)
    bot_asks_payment = any(pq in resp_lower for pq in payment_questions)

    if bot_asks_payment and not customer_wants_to_buy:
        issues.append("שואל על תשלום למרות שלקוח לא ביקש לקנות")

    # 2. Check if bot gives price when not asked - but allow if customer wants more info
    price_keywords = ["מה המחיר", "כמה זה עולה", "כמה עולה", "מחיר"]
    price_in_response = "ש\"ח" in resp_lower or "שח" in resp_lower or "₪" in resp_lower

    customer_asked_price = any(pk in msg_lower for pk in price_keywords)
    if price_in_response and not customer_asked_price and not customer_wants_to_buy:
        issues.append("נותן מחיר למרות שלקוח לא שאל")

    # 3. Check if bot explains pheromones when not asked
    pheromone_explanations = ["פרומונים הם", "פרומונים זה", "חומרים כימיים", "משפיעים על", "מושכים"]
    asked_about_pheromones = "פרומונים" in msg_lower and ("מה" in msg_lower or "איך" in msg_lower or "למה" in msg_lower)
    bot_explains_pheromones = any(pe in resp_lower for pe in pheromone_explanations)

    if bot_explains_pheromones and not asked_about_pheromones:
        issues.append("מסביר על פרומונים למרות שלא שאלו")

    # 4. Check for invented delivery times
    delivery_times = ["24 שעות", "תוך יום", "2-3 ימים", "יומיים", "שלושה ימים", "עד 48", "תוך שבוע"]
    if any(dt in resp_lower for dt in delivery_times):
        issues.append("המציא זמני משלוח")

    # 5. Check for invented promotions
    promo_keywords = ["1+1", "2+2", "מבצע", "הנחה", "הטבה", "חינם", "מתנה"]
    if any(pk in resp_lower for pk in promo_keywords):
        issues.append("המציא מבצע או הנחה")

    # 6. Check response is too long (more than 50 words)
    word_count = len(bot_response.split())
    if word_count > 50:
        issues.append(f"תשובה ארוכה מדי ({word_count} מילים)")

    return issues


async def validate_and_fix_response(
    customer_message: str,
    bot_response: str
) -> str:
    """
    Validate bot response and fix if needed.

    Args:
        customer_message: The original customer message
        bot_response: The bot's generated response

    Returns:
        The validated/fixed response
    """
    # Check for content issues
    issues = needs_content_fix(customer_message, bot_response)

    # Quick checks - if response is already short and no issues, skip validation
    lines = [l for l in bot_response.strip().split('\n') if l.strip()]
    word_count = len(bot_response.split())

    # If response is very short (under 25 words), few lines, and no issues - skip
    if word_count < 25 and len(lines) <= 3 and not issues:
        return bot_response

    # Response needs validation
    issues_hint = ""
    if issues:
        issues_list = "\n".join([f"- {issue}" for issue in issues])
        issues_hint = f"""
⚠️ בעיות שזוהו:
{issues_list}

תקן את הבעיות האלה!
"""
        print(f"🔍 Validator detected issues: {issues}")

    validation_prompt = f"""
הודעת הלקוח:
"{customer_message}"

תשובת הבוט:
"{bot_response}"
{issues_hint}
בדוק את התשובה ותקן אם צריך:
1. קצר ל-2-3 משפטים מקסימום
2. הסר שאלות על תשלום אם הלקוח לא ביקש לקנות
3. הסר מחירים אם לא שאלו
4. הסר הסברים שלא נשאלו
5. הסר זמני משלוח שהומצאו
6. שמור על עיצוב נקי עם שורות ריקות

אם הלקוח רק שאל על מוצר - סיים בשאלה כמו "רוצה לשמוע עוד?" או "מעניין אותך?"

החזר רק את התשובה המתוקנת, בלי הסברים.
"""

    try:
        result = await validator_agent.run(validation_prompt)
        fixed_response = getattr(result, 'data', None) or getattr(result, 'output', None) or str(result)

        # Clean up the response
        fixed_response = fixed_response.strip()

        # Remove any markdown that might have slipped through
        fixed_response = fixed_response.replace('**', '').replace('###', '').replace('##', '').replace('#', '')

        print(f"✅ Validator: Response validated/fixed")
        print(f"   Original length: {len(bot_response)} chars, {word_count} words")
        print(f"   Fixed length: {len(fixed_response)} chars, {len(fixed_response.split())} words")

        return fixed_response

    except Exception as e:
        print(f"⚠️ Validator error: {e}, returning original response")
        return bot_response
