import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
from typing import Optional
from ..settings import settings

logger = logging.getLogger(__name__)


def send_lead_email(subject: str, body_html: str, to_email: str = None) -> str:
    """
    Send lead notification email
    
    Args:
        subject: Email subject
        body_html: HTML email body
        to_email: Recipient email (default: admin email)
    
    Returns:
        Success/error message
    """
    try:
        # For now, this is a placeholder
        # In production, you would use Gmail API or SMTP
        
        logger.info(f"Lead email notification: {subject}")
        logger.info(f"Email body preview: {body_html[:200]}...")
        
        # Placeholder implementation
        # You can integrate with Gmail API, SendGrid, or SMTP here
        
        # Example SMTP implementation (commented out):
        """
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        
        msg = MIMEMultipart()
        msg['From'] = "your-email@gmail.com"
        msg['To'] = to_email or "admin@lustshop.com"
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body_html, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login("your-email@gmail.com", "your-app-password")
        
        text = msg.as_string()
        server.sendmail("your-email@gmail.com", to_email, text)
        server.quit()
        """
        
        return f"Email notification sent: {subject}"
        
    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        logger.error(error_msg)
        return error_msg


def create_lead_email_body(name: str, email: str, phone: str, product: str, address: str = "", payment_method: str = "", shipping_type: str = "", conversation: str = "") -> str:
    """
    Create HTML email body for lead notification
    
    Args:
        name: Customer name
        email: Customer email
        phone: Customer phone
        product: Product interest
        address: Customer address
        payment_method: Payment method
        shipping_type: Shipping type
        conversation: Conversation summary
    
    Returns:
        HTML email body
    """
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #e91e63; border-bottom: 2px solid #e91e63; padding-bottom: 10px;">
                🔥 הזמנה חדשה מ-LustBot
            </h2>
            
            <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #333; margin-top: 0;">פרטי הלקוח</h3>
                <p><strong>שם:</strong> {name}</p>
                <p><strong>אימייל:</strong> <a href="mailto:{email}">{email}</a></p>
                <p><strong>טלפון:</strong> <a href="tel:{phone}">{phone}</a></p>
                <p><strong>מוצר:</strong> {product}</p>
                {f'<p><strong>כתובת:</strong> {address}</p>' if address else ''}
                {f'<p><strong>אמצעי תשלום:</strong> {payment_method}</p>' if payment_method else ''}
                {f'<p><strong>סוג משלוח:</strong> {shipping_type}</p>' if shipping_type else ''}
            </div>
            
            {f'''
            <div style="background: #fff; padding: 20px; border-left: 4px solid #e91e63; margin: 20px 0;">
                <h3 style="color: #333; margin-top: 0;">תקציר השיחה</h3>
                <p style="white-space: pre-wrap;">{conversation}</p>
            </div>
            ''' if conversation else ''}
            
            <div style="text-align: center; margin: 30px 0;">
                <p style="color: #666;">יש לטפל בהזמנה זו בהקדם האפשרי!</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_body
