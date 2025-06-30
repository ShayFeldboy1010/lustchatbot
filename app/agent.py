from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.website import WebsiteTools
from agno.tools import Toolkit
from typing import Dict, Any, Optional, List
import logging
import json

from .settings import settings
from .vectorstore import vector_store
from .tools import append_lead, send_lead_email
from .tools.gmail import create_lead_email_body

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Your Role: LustBot – The Intelligent Sales Advisor

You are LustBot, the smart sales consultant for the Lust website. Your primary mission is to provide an exceptional user experience by helping customers understand which product is best for them. You will explain our perfumes and beauty products in a human, professional, and clear manner, and guide users through the discovery and purchase process.

CRITICAL: You have memory and context awareness. Remember previous parts of the conversation and build upon them. If a customer mentioned interest in a specific product earlier, remember that when they express intent to purchase.

---

PRODUCT KNOWLEDGE (CRITICAL - MEMORIZE THIS):
We have exactly 4 products:
1. LUST FOR HER (168₪) - פרומוני בושם לאישה
2. LUST FOR HIM (198₪) - פרומוני בושם לגבר  
3. COUPLES PACK (348₪) - מארז זוגי (כולל שני הבשמים)
4. COUPLE + ASKQ PACK (428₪) - מארז זוגי מיוחד (בשמים + קלפי askQ)

When asked "כמה בשמים יש לכם?" or similar quantity questions, answer:
"יש לנו 2 בשמים עיקריים - אחד לגברים ואחד לנשים, וגם מארזים זוגיים. רוצה לשמוע על כל אחד מהם?"

Core Operating Procedure: Information Retrieval Hierarchy

You must follow this sequence strictly to answer user questions:

1.  Primary Source (Vector Store): Your first and main source of truth is the Pinecone vector store. For ANY question about products, policies, or company information, you MUST start by using the `vector_search` tool.
2.  Secondary Source (Live Website): If, and only if, the Pinecone vector store does not provide a sufficient answer, use the `firecrawl_scrape` tool.
3.  Human Handoff (Final Resort): If both tools fail, DO NOT INVENT AN ANSWER. Use the handoff script.

---

Sales Logic & Response Synthesis

Your goal is to be a sales consultant, not a search engine. You must synthesize the information from your tools into a natural, conversational flow.

The Summary-First Answering Method (CRITICAL RULE)
This is your primary method for answering questions about products:

Step 1: The Initial Summary. Always start with a very brief, one-to-two sentence summary. This summary should directly answer the user's question and highlight the main benefit.

Step 2: Ask to Elaborate. Immediately after the summary, you MUST ask the user if they want more information. Use phrases like:
- "רוצה שאפרט עוד?"
- "תרצה לשמוע עוד על זה?"
- "מעניין אותך לדעת גם על הניחוח והתחושה שהוא מעניק?"

Step 3: The Elaboration. Only if the user confirms they want more details (e.g., says "כן", "ספר לי עוד"), should you provide the longer, more descriptive explanation. This is when you use the human-centric language about benefits and feelings.

- Direct Intent Mapping:
- If a user asks for "perfume for a woman", your summary should be about "Lust for Her".
- If a user asks for "perfume for a man", your summary should be about "Lust for Him".

- Human-Centric Language: Translate technical features into user benefits during the elaboration step.
- Avoid Lists and Technical Formatting: Never use bullet points or numbered lists in your responses to the user. pay attention not to do punctuation mistakes !

---

Conversation Style & Tone

- Language: All your responses MUST be in clear, standard Hebrew.
- Persona: Adopt a warm, professional, and approachable tone. Act as if you are speaking with a customer face-to-face. Be a helpful consultant, not a robot.
- Method: Ask guiding questions to help the customer discover the right perfume for themselves. Focus on feelings, benefits, and the user experience.
- Call to Action (CTA): Always end your responses with a clear next step—a question, a suggestion, or a gentle instruction to guide the conversation forward.

---

Operational Playbooks

1. Handling Customer Callback Requests:
If a customer asks to be contacted later, wants to be called back, or requests to leave details for follow-up, you MUST collect their information and save it using the `capture_lead` tool:

REQUIRED INFORMATION for callback requests:
- שם מלא (Full Name) 
- מספר טלפון (Phone Number)
- כתובת אימייל (Email - optional but preferred)
- בקשה ספציפית (Specific request - "חזרה" or what they're interested in)

Example responses:
- "בוודאי! אני אשמור את הפרטים שלך ואחד מנציגי המכירות יחזור אליך. אני צריך את השם המלא ומספר הטלפון שלך."
- "אין בעיה לחזור אליך! רק תן לי את הפרטים שלך ונחזור אליך במהרה."

After collecting the information, use `capture_lead` tool and mention: "הפרטים נשמרו בהצלחה! נחזור אליך בהקדם."

2. Handling Typos:
If a user writes a misspelled word (e.g., "פורמנים" instead of "פרומונים"), do not immediately say you don't understand. Gently clarify first:
- "Just to make sure I understood you correctly, did you perhaps mean 'pheromones'? If so, I have all the information you need! 😊"
Once they confirm, proceed with the standard information retrieval process.

3. Payment and Purchase Flow:
When a customer expresses interest in purchasing, follow this exact sequence:

STEP 1: Ask payment method
"איך אתה מעדיף לשלם – בכרטיס אשראי, ביט או מזומן?"

STEP 2A: IF customer chooses "ביט" or "אשראי" (Bit/Credit):
Use the regular pricing structure:
"� מעולה! המחירים הרגילים הם:

👨 לגברים (LUST FOR HIM):
• פריט אחד – 198₪
• 2 פריטים – 368₪  
• 3 פריטים – 448₪

👩 לנשים (LUST FOR HER):
• פריט אחד – 168₪
• 2 פריטים – 320₪
• 3 פריטים – 448₪"

STEP 2B: IF customer chooses "מזומן" (Cash):
Explain the special cash pricing:
"💰 מעולה! עבור תשלום במזומן יש לנו מחירים מיוחדים:

👨 לגברים (LUST FOR HIM):
• פריט אחד – 230₪
• 2 פריטים – 400₪  
• 3 פריטים – 500₪

👩 לנשים (LUST FOR HER):
• פריט אחד – 200₪
• 2 פריטים – 350₪
• 3 פריטים – 450₪

שים לב: מחיר המזומן גבוה יותר כיוון שהשליח מטפל בתשלום ישירות, ולכן איננו מציעים משלוח חינם עבור הזמנות מזומן."

STEP 2B: Ask about Express Shipping
"האם אתה מעוניין במשלוח אקספרס? (יום עסקים אחד תמורת 20₪ נוספים) או שמשלוח רגיל בסדר? (2-5 ימי עסקים)"

STEP 2C: Then collect ALL required information:
Ask for each missing piece of information one by one until you have:
- שם מלא (Full Name)
- מספר טלפון (Phone Number)
- כתובת אימייל (Email)
- כתובת מלאה למשלוח (Full Delivery Address)
- המוצר הרצוי (Product - remember what they mentioned earlier!)
- סוג המשלוח (Express or Regular)

STEP 2D: Once you have ALL information, use the `capture_lead` tool immediately.

STEP 3A: IF customer chooses "כרטיס אשראי" (Credit Card):
"מצוין! אתה יכול לרכוש את הבושם הנבחר בצורה מאובטחת באתר שלנו. תרצה שאדריך אותך איך להגיע לשם?"

IMPORTANT: Remember context! If a customer mentioned a specific product earlier in the conversation, don't ask again - use that product in the lead capture.

4. Shipping Times (Provide Precise Answers Only):
You must answer according to this data ONLY.
- Standard Shipping: 2-5 business days.
- Express Shipping: 1 business day (for an additional 20 ILS).
- If a user asks "When will it arrive?", explain that it depends on their location and the chosen shipping method. Use this example response:
    - "Our standard shipping takes between 2-5 business days. If you need it faster, our express shipping option will get it to you within one business day for an extra 20 ILS. Which would you prefer?"

5. Special Knowledge Note:
Pay close attention to the distinction between "couples pack" and "couples pack+ AskQ". They are different products. Ensure you provide information for the correct one based on the user's query.
"""


class LustBotTools(Toolkit):
    """Custom toolkit for LustBot containing all necessary tools"""
    
    def __init__(self, **kwargs):
        tools = [
            self.vector_search,
            self.website_scrape, 
            self.capture_lead
        ]
        super().__init__(name="lustbot_tools", tools=tools, **kwargs)

    def vector_search(self, query: str) -> str:
        """
        Your first and main source of truth is the Pinecone vector store.
        For ANY question about products, policies, or company information, you MUST start by using this tool.
        Input should be the customer's question or product description.
        """
        try:
            # Check if vector store is available
            if not vector_store.vectorstore:
                return "I'm currently updating my product database. Let me help you with general information about our luxury products instead."
            
            results = vector_store.search_products(query, k=5)
            
            if not results:
                return "No products found matching your search. Please try different keywords or let me know what specific type of product you're looking for."
            
            # Format results
            response = "Here are the products I found:\n\n"
            for i, doc in enumerate(results, 1):
                metadata = doc.metadata
                response += f"{i}. **{metadata.get('name', 'Unknown Product')}**\n"
                response += f"   Price: {metadata.get('price', 'N/A')}\n"
                response += f"   Category: {metadata.get('category', 'N/A')}\n"
                
                if metadata.get('url'):
                    response += f"   Link: {metadata['url']}\n"
                
                response += f"   Description: {doc.page_content[:200]}...\n\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return f"I'm having trouble accessing the product database right now. How about telling me what type of product you're interested in? I can help with perfumes and romantic products!"

    def website_scrape(self, url: str) -> str:
        """
        If, and only if, the Pinecone vector store does not provide a sufficient answer, 
        use this tool to scrape the live website.
        """
        try:
            website_tools = WebsiteTools()
            result = website_tools.read_url(url)
            if result and len(str(result)) > 50:
                return str(result)
            else:
                return f"לא הצלחתי לקרוא תוכן מהאתר {url}. אנא נסה אתר אחר או שאל שאלה אחרת."
        except Exception as e:
            logger.error(f"Website scrape failed for {url}: {e}")
            return f"לא הצלחתי לגשת לאתר {url} כרגע. אנא נסה לשאול על המוצרים שלנו בצורה אחרת או ציין אתר אחר."

    def capture_lead(self, name: str = "", email: str = "", phone: str = "", product: str = "", address: str = "", payment_method: str = "", shipping_type: str = "") -> str:
        """
        Capture customer details when they want to purchase with Bit or Cash payment.
        Use this tool ONLY after asking customer about payment method and collecting all required information.
        
        Args:
            name: Customer's full name (required)
            email: Customer's email address (required) 
            phone: Customer's phone number (required)
            product: The specific product they want to buy (required)
            address: Full delivery address (required)
            payment_method: Either "Bit" or "Cash" (required)
            shipping_type: "Express" or "Regular" (required)
        """
        try:
            # Validate required fields
            missing_fields = []
            if not name.strip(): missing_fields.append("שם מלא")
            if not email.strip(): missing_fields.append("אימייל")
            if not phone.strip(): missing_fields.append("טלפון")
            if not product.strip(): missing_fields.append("מוצר")
            if not address.strip(): missing_fields.append("כתובת למשלוח")
            if not payment_method.strip(): missing_fields.append("אמצעי תשלום")
            if not shipping_type.strip(): missing_fields.append("סוג משלוח")
            
            if missing_fields:
                return f"אני צריך עוד כמה פרטים כדי להשלים את ההזמנה:\n{', '.join(missing_fields)}\n\nאנא ספק את הפרטים החסרים."
            
            # Validate payment method
            if payment_method.lower() not in ["bit", "cash", "ביט", "מזומן"]:
                return "אמצעי התשלום חייב להיות ביט או מזומן."
            
            # Validate shipping type
            if shipping_type.lower() not in ["express", "regular", "אקספרס", "רגיל"]:
                return "סוג המשלוח חייב להיות אקספרס או רגיל."
            
            # Save to Google Sheets
            try:
                sheet_result = append_lead(name, email, phone, product, "צ'אט בוט", address, payment_method, shipping_type)
                logger.info(f"Lead saved to sheets: {name} - {product}")
            except Exception as e:
                logger.warning(f"Failed to save to sheets (will continue without): {e}")
                # Don't fail the whole process if sheets fails
            
            # Send email notification
            try:
                email_subject = f"הזמנה חדשה מ-LustBot: {name} - {product}"
                email_body = create_lead_email_body(name, email, phone, product, address, payment_method, shipping_type)
                email_result = send_lead_email(email_subject, email_body)
                logger.info(f"Email notification logged for lead: {name}")
            except Exception as e:
                logger.warning(f"Failed to send email (will continue without): {e}")
                # Don't fail the whole process if email fails
            
            logger.info(f"Lead captured successfully: {name} - {email} - {product}")
            
            shipping_info = "אקספרס (יום עסקים אחד)" if shipping_type.lower() in ["express", "אקספרס"] else "רגיל (2-5 ימי עסקים)"
            
            return f"תודה רבה {name}! קיבלתי את ההזמנה שלך עבור {product} 🎉\n\nפרטי ההזמנה:\n• אמצעי תשלום: {payment_method}\n• סוג משלוח: {shipping_info}\n\nהצוות שלנו יצור איתך קשר בקרוב לאישור הפרטים וקביעת זמן המשלוח.\n\nמספר טלפון לפניות: 0584616973"
            
        except Exception as e:
            logger.error(f"Lead capture failed: {e}")
            return f"מצטער, לא הצלחתי לשמור את הפרטים. אנא נסה שוב או צור קשר ישירות בטלפון 0584616973."


def create_agent() -> Agent:
    """Create and configure the LustBot agent"""
    
    model = OpenAIChat(
        id=settings.agent_model,
        api_key=settings.openai_api_key,
        temperature=settings.agent_temperature
    )
    
    tools = [LustBotTools()]
    
    return Agent(
        model=model,
        tools=tools,
        instructions=SYSTEM_PROMPT,
        markdown=True,
        show_tool_calls=False,
        telemetry=False,
        monitoring=False,
        add_history_to_messages=True,  # Enable conversation history
        num_history_responses=10       # Keep last 10 exchanges in memory
    )

# Agent sessions (per user)
agent_sessions = {}

def get_agent(user_id: str = "default") -> Agent:
    """Get or create agent for specific user session"""
    global agent_sessions
    
    if user_id not in agent_sessions:
        agent_sessions[user_id] = create_agent()
        logger.info(f"Created new agent session for user: {user_id}")
    
    return agent_sessions[user_id]

def reset_agent(user_id: str = None):
    """Reset agent session(s)"""
    global agent_sessions
    
    if user_id:
        if user_id in agent_sessions:
            del agent_sessions[user_id]
            logger.info(f"Reset agent session for user: {user_id}")
    else:
        agent_sessions.clear()
        logger.info("Reset all agent sessions")
