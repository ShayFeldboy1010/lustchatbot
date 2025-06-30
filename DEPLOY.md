# 🚀 Deploy LustBot to Render

## Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **GitHub Repository**: Push this project to a GitHub repository
3. **API Keys**: Gather all required API keys

## Required Environment Variables

Set these in Render's environment variables section:

### Essential Keys
```
OPENAI_API_KEY=sk-your-openai-api-key
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=lust-products
GOOGLE_SHEETS_SPREADSHEET_ID=your-google-sheets-id
```

### Google Sheets Credentials
For Google Sheets integration, you need to:
1. Create a service account in Google Cloud Console
2. Download the JSON credentials file
3. Either:
   - **Option A**: Upload the JSON file to your repo as `creds/sheets.json` (not recommended for production)
   - **Option B**: Set the entire JSON content as an environment variable `GOOGLE_APPLICATION_CREDENTIALS_JSON` and modify the app to read from it

### Optional Keys
```
FIRECRAWL_API_KEY=your-firecrawl-key (if using web scraping)
DEBUG=False
```

## Deployment Steps

### Method 1: Using Render Dashboard

1. **Connect Repository**
   - Go to Render Dashboard
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Configure Service**
   - Name: `lustbot`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `./start.sh`

3. **Set Environment Variables**
   - Add all required environment variables from above
   - Set `PORT` to be managed by Render (usually auto-detected)

4. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment to complete

### Method 2: Using render.yaml (Infrastructure as Code)

1. **Push render.yaml**
   - The included `render.yaml` file contains service configuration
   - Render will auto-detect and use this configuration

2. **Set Environment Variables**
   - Still need to set environment variables manually in dashboard
   - Or use Render's environment sync features

## Post-Deployment

1. **Load Products**
   - Visit `https://your-app.onrender.com/admin/load-products`
   - This will populate the Pinecone vector database

2. **Test the Bot**
   - Visit `https://your-app.onrender.com`
   - Test the chat functionality

3. **Verify Integrations**
   - Test lead capture (should save to Google Sheets)
   - Test product search
   - Test email notifications

## Troubleshooting

### Common Issues

1. **Build Failures**
   - Check that all dependencies in `requirements.txt` are available
   - Verify Python version compatibility

2. **Environment Variables**
   - Ensure all required env vars are set
   - Check for typos in variable names

3. **Google Sheets Issues**
   - For Render deployment, set `GOOGLE_APPLICATION_CREDENTIALS_JSON` environment variable
   - Copy the ENTIRE content of your service account JSON file (including curly braces)
   - Example: `{"type": "service_account", "project_id": "your-project", "private_key_id": "...", ...}`
   - Verify service account has access to the spreadsheet
   - Check that the spreadsheet ID is correct

4. **Pinecone Issues**
   - Ensure the index exists with correct dimensions
   - Verify API key and environment are correct

### Logs
- Check Render logs for detailed error messages
- Look for startup errors in the application logs

## Security Notes

- Never commit real API keys to Git
- Use Render's secret management for sensitive data
- Enable HTTPS (Render provides this automatically)
- Consider rate limiting for production use

## Performance

- Render's free tier may have cold starts
- Consider upgrading to paid tier for production use
- Monitor memory and CPU usage
