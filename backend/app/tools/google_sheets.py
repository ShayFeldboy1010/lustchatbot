"""Google Sheets Tool for order management"""

import gspread
from google.oauth2.service_account import Credentials
from typing import Optional
import asyncio
import os
import json

from ..config import get_settings
from ..models.order import OrderData

settings = get_settings()

# Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Cached client
_sheets_client: Optional[gspread.Client] = None


def get_sheets_client() -> gspread.Client:
    """Get or create Google Sheets client"""
    global _sheets_client

    if _sheets_client is None:
        # Try to get credentials from JSON environment variable first (for cloud deployment)
        if settings.google_sheets_credentials_json:
            print("Loading Google Sheets credentials from environment variable")
            creds_info = json.loads(settings.google_sheets_credentials_json)
            creds = Credentials.from_service_account_info(
                creds_info,
                scopes=SCOPES
            )
        else:
            # Fall back to file path (for local development)
            creds_path = settings.google_sheets_credentials_path
            if not os.path.isabs(creds_path):
                # Make path relative to the project root (parent of backend)
                # __file__ is in backend/app/tools/google_sheets.py
                # Go up 4 levels: tools -> app -> backend -> project_root
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                creds_path = os.path.join(project_root, creds_path.lstrip('./'))

            print(f"Loading Google Sheets credentials from: {creds_path}")

            creds = Credentials.from_service_account_file(
                creds_path,
                scopes=SCOPES
            )
        _sheets_client = gspread.authorize(creds)

    return _sheets_client


async def save_order_to_sheet(order: OrderData) -> bool:
    """
    Save order data to Google Sheets.

    Args:
        order: OrderData object containing all order information

    Returns:
        True if successful, False otherwise
    """
    try:
        loop = asyncio.get_event_loop()

        def _save():
            client = get_sheets_client()
            sheet = client.open_by_key(settings.google_sheets_spreadsheet_id)
            worksheet = sheet.worksheet(settings.google_sheets_sheet_name)

            # Convert order to row format
            row = order.to_sheet_row()

            # Find the next empty row by getting all values and counting rows
            all_values = worksheet.get_all_values()
            next_row = len(all_values) + 1

            # Insert at the specific next row to ensure we don't overwrite
            worksheet.insert_row(row, next_row, value_input_option='USER_ENTERED')
            print(f"✅ Order saved to Google Sheets row {next_row}")
            return True

        result = await loop.run_in_executor(None, _save)
        return result

    except Exception as e:
        print(f"Error saving to Google Sheets: {e}")
        return False


async def get_order_by_phone(phone: str) -> Optional[dict]:
    """
    Get order information by customer phone number.

    Args:
        phone: Customer phone number

    Returns:
        Order data as dict if found, None otherwise
    """
    try:
        loop = asyncio.get_event_loop()

        def _find():
            client = get_sheets_client()
            sheet = client.open_by_key(settings.google_sheets_spreadsheet_id)
            worksheet = sheet.worksheet(settings.google_sheets_sheet_name)

            # Get all records
            records = worksheet.get_all_records()

            # Find by phone number (assuming phone is in column 4)
            for record in records:
                if record.get('טלפון') == phone or record.get('phone') == phone:
                    return record

            return None

        result = await loop.run_in_executor(None, _find)
        return result

    except Exception as e:
        print(f"Error finding order: {e}")
        return None


async def update_order_status(phone: str, new_status: str) -> bool:
    """
    Update order status by phone number.

    Args:
        phone: Customer phone number
        new_status: New status to set

    Returns:
        True if successful, False otherwise
    """
    try:
        loop = asyncio.get_event_loop()

        def _update():
            client = get_sheets_client()
            sheet = client.open_by_key(settings.google_sheets_spreadsheet_id)
            worksheet = sheet.worksheet(settings.google_sheets_sheet_name)

            # Find the row with the phone number
            all_values = worksheet.get_all_values()
            header = all_values[0] if all_values else []

            # Find phone and status column indices
            phone_col = None
            status_col = None

            for i, col in enumerate(header):
                if col in ['טלפון', 'phone']:
                    phone_col = i
                if col in ['סטטוס', 'status']:
                    status_col = i

            if phone_col is None or status_col is None:
                return False

            # Find the row with matching phone
            for row_idx, row in enumerate(all_values[1:], start=2):
                if len(row) > phone_col and row[phone_col] == phone:
                    # Update status cell
                    worksheet.update_cell(row_idx, status_col + 1, new_status)
                    return True

            return False

        result = await loop.run_in_executor(None, _update)
        return result

    except Exception as e:
        print(f"Error updating order status: {e}")
        return False
