"""Main Pydantic AI Sales Agent for the e-commerce chatbot"""

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, UserPromptPart, TextPart
from pydantic_ai.settings import ModelSettings
from pydantic import BaseModel
from dataclasses import dataclass
from typing import Optional, List
import os
import re

from .prompts import SALES_AGENT_SYSTEM_PROMPT, ESCALATION_KEYWORDS, ESCALATION_RESPONSE
from ..config import get_settings

settings = get_settings()

# Configure Logfire for observability (optional - only if configured)
try:
    import logfire
    logfire_token = os.environ.get('LOGFIRE_TOKEN')
    if logfire_token:
        print(f"LOGFIRE_TOKEN found (length: {len(logfire_token)}, starts with: {logfire_token[:20]}...)")
        logfire.configure(token=logfire_token, send_to_logfire='if-token-present')
        logfire.instrument_pydantic_ai()
        print("Logfire configured successfully with token")
    else:
        print("LOGFIRE_TOKEN not set - skipping Logfire configuration")
except Exception as e:
    import traceback
    print(f"Logfire configuration error: {e}")
    traceback.print_exc()

# Set API keys for pydantic-ai
os.environ['GOOGLE_API_KEY'] = settings.google_api_key


@dataclass
class ChatDependencies:
    """Dependencies passed to the agent for each run"""
    session_id: str
    customer_phone: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from the chat agent"""
    response: str
    needs_escalation: bool = False
    order_saved: bool = False


def check_escalation(message: str) -> bool:
    """Check if message contains escalation keywords"""
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in ESCALATION_KEYWORDS)


def clean_markdown_formatting(text: str) -> str:
    """Remove markdown formatting like ** and ### from text"""
    # Remove bold formatting **text** -> text
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    # Remove italic formatting *text* -> text
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    # Remove headers ### text -> text
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    # Remove remaining stray asterisks
    text = text.replace('**', '').replace('*', '')
    return text


# Initialize the Pydantic AI Agent with Google Gemini 3 Flash Preview
# Low temperature (0.1) to reduce hallucinations and keep responses factual
sales_agent = Agent(
    'google-gla:gemini-3-flash-preview',
    system_prompt=SALES_AGENT_SYSTEM_PROMPT,
    retries=3,
    deps_type=ChatDependencies,
    model_settings=ModelSettings(temperature=0.1)
)

# Fallback agent using Gemini 2.0 Flash (for when primary model fails)
fallback_agent = Agent(
    'google-gla:gemini-2.0-flash',
    system_prompt=SALES_AGENT_SYSTEM_PROMPT,
    retries=2,
    deps_type=ChatDependencies,
    model_settings=ModelSettings(temperature=0.1)
)


# Import tools - these will be registered with the agent
from ..tools.google_sheets import save_order_to_sheet
from ..tools.vector_store import search_knowledge_base
from ..models.order import OrderData
from ..services.whatsapp import whatsapp_service
from ..services.memory import conversation_memory


async def _search_products_info(query: str) -> str:
    """Internal function for searching knowledge base"""
    try:
        results = await search_knowledge_base(query, top_k=5)
        if results:
            return "\n\n---\n\n".join(results)
        return "לא נמצא מידע רלוונטי במאגר"
    except Exception as e:
        print(f"Knowledge base search error: {e}")
        return "שגיאה בחיפוש במאגר הידע"


@sales_agent.tool
async def search_products_info(
    ctx: RunContext[ChatDependencies],
    query: str
) -> str:
    """
    Search the knowledge base for product information, prices, links, and FAQs.

    ALWAYS use this tool before answering questions about:
    - Products and their details
    - Prices (credit card or cash/bit)
    - Product links for website purchases
    - FAQ answers
    - Shipping and logistics info

    Args:
        query: The search query in Hebrew (e.g., "מחיר LUST FOR HIM", "קישור לאתר", "תווי ריח")

    Returns:
        Relevant information from the knowledge base
    """
    return await _search_products_info(query)


@fallback_agent.tool
async def search_products_info_fallback(
    ctx: RunContext[ChatDependencies],
    query: str
) -> str:
    """
    Search the knowledge base for product information, prices, links, and FAQs.

    ALWAYS use this tool before answering questions about:
    - Products and their details
    - Prices (credit card or cash/bit)
    - Product links for website purchases
    - FAQ answers
    - Shipping and logistics info

    Args:
        query: The search query in Hebrew (e.g., "מחיר LUST FOR HIM", "קישור לאתר", "תווי ריח")

    Returns:
        Relevant information from the knowledge base
    """
    return await _search_products_info(query)


async def _save_order_internal(
    session_id: str,
    customer_name: str,
    customer_phone: str,
    product_name: str,
    quantity: int,
    full_address: str,
    payment_method: str,
    customer_email: str = "",
    delivery_notes: str = ""
) -> str:
    """Internal function for saving orders"""
    # Check if order already completed for this session
    if conversation_memory.is_order_completed(session_id):
        print(f"⚠️ Order already completed for session {session_id}, skipping duplicate save")
        return "ההזמנה שלך כבר נשמרה! 🎉 תודה שקנית מ-LUST"

    try:
        order = OrderData(
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            product_name=product_name,
            quantity=quantity,
            full_address=full_address,
            payment_method=payment_method,
            delivery_notes=delivery_notes
        )
        success = await save_order_to_sheet(order)
        if success:
            # Mark order as completed to prevent duplicates
            conversation_memory.mark_order_completed(session_id)

            # Save customer details so we don't ask again
            conversation_memory.save_customer_details(session_id, {
                'name': customer_name,
                'email': customer_email,
                'phone': customer_phone,
                'address': full_address
            })

            print(f"✅ Order saved and marked complete for session {session_id}")
            # Check if payment is cash/bit - send WhatsApp notification to support
            payment_lower = payment_method.lower()
            is_cash_or_bit = any(method in payment_lower for method in ["מזומן", "ביט", "cash", "bit"])

            if is_cash_or_bit and settings.whatsapp_human_support_number:
                try:
                    email_line = f"\n📧 מייל: {customer_email}" if customer_email else ""
                    notification_message = f"""🛒 הזמנה חדשה - תשלום לשליח!

👤 שם: {customer_name}
📱 טלפון: {customer_phone}{email_line}
📦 מוצר: {product_name}
🔢 כמות: {quantity}
📍 כתובת: {full_address}
💳 אמצעי תשלום: {payment_method}
📝 הערות: {delivery_notes or 'אין'}"""

                    await whatsapp_service.send_text_message(
                        to=settings.whatsapp_human_support_number,
                        message=notification_message
                    )
                    print(f"✅ WhatsApp notification sent to {settings.whatsapp_human_support_number}")
                except Exception as notification_error:
                    print(f"⚠️ Failed to send WhatsApp notification: {notification_error}")
                    # Don't fail the order if notification fails

            return "ההזמנה נשמרה בהצלחה! ✅"
        return "שגיאה בשמירת ההזמנה, אנא נסה שוב"
    except Exception as e:
        return f"שגיאה בשמירת ההזמנה: {str(e)}"


SAVE_ORDER_DOCSTRING = """
    ⛔ CRITICAL: Only call this AFTER showing summary AND receiving explicit confirmation!

    Required flow BEFORE calling this tool:
    1. Show order summary to customer
    2. Ask "הכל נכון? שלח כן לאישור"
    3. Wait for customer to reply "כן" or "מאשר"
    4. Only THEN call this tool

    DO NOT call this tool in the same turn as showing the summary!
    DO NOT call this tool if order was already saved for this session!

    Args:
        customer_name: Full name of the customer
        customer_phone: Customer's phone number
        product_name: Name of the product being ordered
        quantity: Number of items
        full_address: Complete delivery address
        payment_method: Payment method (bit/מזומן/cash)
        customer_email: Customer's email address (OPTIONAL - only if provided by customer)
        delivery_notes: Any notes for the delivery person

    Returns:
        Success or error message
"""


@sales_agent.tool
async def save_order(
    ctx: RunContext[ChatDependencies],
    customer_name: str,
    customer_phone: str,
    product_name: str,
    quantity: int,
    full_address: str,
    payment_method: str,
    customer_email: str = "",
    delivery_notes: str = ""
) -> str:
    """⛔ CRITICAL: Only call this AFTER showing summary AND receiving explicit confirmation!"""
    return await _save_order_internal(
        ctx.deps.session_id, customer_name, customer_phone,
        product_name, quantity, full_address, payment_method, customer_email, delivery_notes
    )

save_order.__doc__ = SAVE_ORDER_DOCSTRING


@fallback_agent.tool
async def save_order_fallback(
    ctx: RunContext[ChatDependencies],
    customer_name: str,
    customer_phone: str,
    product_name: str,
    quantity: int,
    full_address: str,
    payment_method: str,
    customer_email: str = "",
    delivery_notes: str = ""
) -> str:
    """⛔ CRITICAL: Only call this AFTER showing summary AND receiving explicit confirmation!"""
    return await _save_order_internal(
        ctx.deps.session_id, customer_name, customer_phone,
        product_name, quantity, full_address, payment_method, customer_email, delivery_notes
    )

save_order_fallback.__doc__ = SAVE_ORDER_DOCSTRING


def build_message_history(conversation_history: List[dict]) -> List[ModelMessage]:
    """Convert conversation history to pydantic-ai message format"""
    messages: List[ModelMessage] = []

    for msg in conversation_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "user":
            messages.append(
                ModelRequest(parts=[UserPromptPart(content=content)])
            )
        elif role == "assistant":
            messages.append(
                ModelResponse(parts=[TextPart(content=content)])
            )

    return messages


async def process_message(
    message: str,
    session_id: str,
    conversation_history: List[dict]
) -> ChatResponse:
    """
    Process an incoming message and return a response.

    Args:
        message: The user's message
        session_id: Unique session identifier
        conversation_history: List of previous messages in the conversation

    Returns:
        ChatResponse with the agent's response
    """
    # Check for escalation keywords first
    if check_escalation(message):
        return ChatResponse(
            response=ESCALATION_RESPONSE,
            needs_escalation=True
        )

    # Prepare dependencies
    deps = ChatDependencies(session_id=session_id)

    # Convert conversation history to pydantic-ai format
    message_history = build_message_history(conversation_history) if conversation_history else None

    try:
        # Run the primary agent (Gemini 3 Flash Preview)
        result = await sales_agent.run(
            message,
            deps=deps,
            message_history=message_history
        )

        # Get the response text - try different attribute names for compatibility
        response_text = getattr(result, 'data', None) or getattr(result, 'output', None) or str(result)

        # Clean markdown formatting (remove ** and ### etc.)
        response_text = clean_markdown_formatting(response_text)

        return ChatResponse(
            response=response_text,
            needs_escalation=False
        )
    except Exception as e:
        # Log the error
        error_str = str(e)
        print(f"Primary agent (gemini-3-flash-preview) error: {error_str}")

        # Try fallback agent (Gemini 2.0 Flash)
        try:
            print("🔄 Trying fallback agent (gemini-2.0-flash)...")
            result = await fallback_agent.run(
                message,
                deps=deps,
                message_history=message_history
            )

            response_text = getattr(result, 'data', None) or getattr(result, 'output', None) or str(result)
            response_text = clean_markdown_formatting(response_text)

            print("✅ Fallback agent succeeded")
            return ChatResponse(
                response=response_text,
                needs_escalation=False
            )
        except Exception as fallback_error:
            print(f"Fallback agent also failed: {fallback_error}")
            import traceback
            traceback.print_exc()

            return ChatResponse(
                response="מצטער, יש תקלה זמנית 🙏 אנא נסה שוב בעוד כמה רגעים או גלוש באתר שלנו",
                needs_escalation=False
            )
