import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import logging
import os
from typing import Optional
from ..settings import settings

logger = logging.getLogger(__name__)


class GoogleSheetsClient:
    """Google Sheets client for lead management"""
    
    def __init__(self):
        self.client = None
        self.sheet = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google Sheets client"""
        try:
            logger.info("Attempting to initialize Google Sheets client...")
            
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            logger.info(f"Using credentials file: {settings.google_sheets_credentials_path}")
            
            if not os.path.exists(settings.google_sheets_credentials_path):
                raise FileNotFoundError(f"Credentials file not found: {settings.google_sheets_credentials_path}")
            
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                settings.google_sheets_credentials_path, 
                scope
            )
            
            logger.info("Service account credentials loaded successfully")
            
            self.client = gspread.authorize(creds)
            
            # Use the new sheets_id from settings
            sheet_id = settings.google_sheets_id or settings.sheet_id
            if not sheet_id:
                raise ValueError("No Google Sheets ID configured")
                
            logger.info(f"Attempting to open sheet with ID: {sheet_id}")
            
            self.sheet = self.client.open_by_key(sheet_id).sheet1
            
            logger.info("Successfully connected to Google Sheets")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            # Don't raise here, let the system continue without sheets
            self.client = None
            self.sheet = None
    
    def append_row(self, values: list):
        """Append a row to the sheet"""
        try:
            if not self.sheet:
                raise Exception("Google Sheets not properly initialized")
                
            self.sheet.append_row(values)
            logger.info(f"Successfully appended row to sheet: {values}")
        except Exception as e:
            logger.error(f"Failed to append row to sheet: {e}")
            raise
    
    def ensure_headers(self):
        """Ensure the sheet has the correct headers"""
        try:
            if not self.sheet:
                logger.warning("Sheet not initialized, cannot ensure headers")
                return
                
            # Get the first row to check if headers exist
            first_row = self.sheet.row_values(1)
            
            expected_headers = [
                "תאריך ושעה",
                "שם", 
                "אימייל",
                "טלפון",
                "מוצר רצוי",
                "שיטת קשר",
                "כתובת",
                "אמצעי תשלום", 
                "סוג משלוח",
                "סטטוס"
            ]
            
            # If first row is empty or doesn't match, add headers
            if not first_row or len(first_row) != len(expected_headers):
                logger.info("Adding headers to Google Sheet")
                if first_row:
                    # Insert new row at the top
                    self.sheet.insert_row(expected_headers, 1)
                else:
                    # Add headers to empty sheet
                    self.sheet.append_row(expected_headers)
                    
        except Exception as e:
            logger.warning(f"Could not ensure headers: {e}")
            # Continue anyway


# Global client instance
sheets_client = None


def get_sheets_client():
    """Get or create sheets client"""
    global sheets_client
    if sheets_client is None:
        try:
            sheets_client = GoogleSheetsClient()
        except Exception as e:
            logger.error(f"Failed to create sheets client: {e}")
            # Return None instead of raising
            return None
    return sheets_client


def append_lead(name: str, email: str, phone: str, product: str, method: str = "Chat", address: str = "", payment_method: str = "", shipping_type: str = "") -> str:
    """
    Append a new lead to Google Sheets
    
    Args:
        name: Customer name
        email: Customer email
        phone: Customer phone
        product: Product interest
        method: Contact method (default: Chat)
        address: Customer address
        payment_method: Payment method (Bit/Cash)
        shipping_type: Shipping type (Express/Regular)
    
    Returns:
        Success/error message
    """
    try:
        client = get_sheets_client()
        if not client:
            return "Failed to connect to Google Sheets"
        
        # Ensure headers are present
        client.ensure_headers()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row_data = [
            timestamp,
            name,
            email, 
            phone,
            product,
            method,
            address,
            payment_method,
            shipping_type,
            "חדש"  # Status in Hebrew
        ]
        
        client.append_row(row_data)
        
        logger.info(f"New lead added: {name} - {email} - {product} - {payment_method} - {shipping_type}")
        return f"Successfully saved lead information for {name}"
        
    except Exception as e:
        error_msg = f"Failed to save lead: {str(e)}"
        logger.error(error_msg)
        return error_msg
