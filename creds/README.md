# Google Credentials Setup

## Google Sheets Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable the Google Sheets API
4. Create a service account
5. Download the JSON key file
6. Rename it to `sheets.json` and place it in this directory
7. Share your Google Sheet with the service account email

## Gmail Setup (Optional)
For email notifications, you can either:
1. Use the Gmail API (recommended for production)
2. Use SMTP with app passwords
3. Use a third-party service like SendGrid

The current implementation is a placeholder - you'll need to implement the actual email sending logic based on your preferred method.
