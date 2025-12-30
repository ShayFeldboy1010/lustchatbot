"""Test Google Sheets Connection"""
import os
from dotenv import load_dotenv

load_dotenv(override=True)

import gspread
from google.oauth2.service_account import Credentials

# Settings
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

creds_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH', './credentials.json')
spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
sheet_name = os.getenv('GOOGLE_SHEETS_SHEET_NAME', 'Lust leads')

print(f"Testing Google Sheets connection...")
print(f"Credentials path: {creds_path}")
print(f"Spreadsheet ID: {spreadsheet_id}")
print(f"Sheet name: {sheet_name}")
print("-" * 50)

# Check if credentials file exists
if not os.path.exists(creds_path):
    print(f"❌ Credentials file not found at: {creds_path}")
    exit(1)
else:
    print(f"✅ Credentials file found")

try:
    # Load credentials
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    print(f"✅ Credentials loaded")
    print(f"   Service account email: {creds.service_account_email}")

    # Authorize gspread
    client = gspread.authorize(creds)
    print(f"✅ Authorized with Google")

    # Try to open spreadsheet
    print(f"\n🔍 Opening spreadsheet...")
    sheet = client.open_by_key(spreadsheet_id)
    print(f"✅ Spreadsheet opened: {sheet.title}")

    # List all worksheets
    worksheets = sheet.worksheets()
    print(f"\n📁 Available worksheets:")
    for ws in worksheets:
        print(f"   - {ws.title}")

    # Try to open specific worksheet
    print(f"\n🔍 Opening worksheet '{sheet_name}'...")
    try:
        worksheet = sheet.worksheet(sheet_name)
        print(f"✅ Worksheet opened: {worksheet.title}")

        # Get row count
        all_values = worksheet.get_all_values()
        print(f"   Total rows: {len(all_values)}")

        # Show header row
        if all_values:
            print(f"   Header columns: {all_values[0]}")

    except gspread.exceptions.WorksheetNotFound:
        print(f"❌ Worksheet '{sheet_name}' not found!")
        print(f"   Available worksheets: {[ws.title for ws in worksheets]}")

    print(f"\n✅ Google Sheets test completed successfully!")

except gspread.exceptions.SpreadsheetNotFound:
    print(f"\n❌ Spreadsheet not found!")
    print(f"   Make sure the spreadsheet is shared with: {creds.service_account_email}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
