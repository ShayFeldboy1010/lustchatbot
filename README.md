# 🔥 LustBot - AI Sales Assistant for Lust Perfumes

An intelligent sales assistant chatbot designed specifically for Lust pheromone perfumes. Built with FastAPI, Agno AI framework, and modern web technologies.

## ✨ Features

- **AI-Powered Sales Assistant**: Natural Hebrew conversation with product expertise
- **Vector Search**: Semantic search through product database using Pinecone
- **Lead Capture**: Automatic lead collection and Google Sheets integration
- **Web Scraping**: Dynamic content fetching with Agno WebsiteTools
- **Email Notifications**: Automated lead notifications
- **Professional UI**: Modern, responsive chat interface

## 🚀 Quick Start

### 1. Clone and Setup
```bash
cd lustbot/
cp .env.example .env
# Edit .env with your API keys
```

### 2. Install Dependencies
```bash
make install
```

### 3. Configure Environment Variables
```bash
# Required API keys in .env
OPENAI_API_KEY=your_openai_key
PINECONE_API_KEY=your_pinecone_key
FIRECRAWL_KEY=your_firecrawl_key
GOOGLE_SHEET_ID=your_sheet_id
```

### 4. Add Product Data
```bash
# Place your product CSV in data/lust_products.csv
# CSV should have columns: id, name, description, price, category, url, features, brand
```

### 5. Run Development Server
```bash
make run-dev
```

Visit: http://localhost:8001

## 📁 Project Structure

```
lustbot/
├── app/
│   ├── main.py          # FastAPI application
│   ├── settings.py      # Configuration
│   ├── agent.py         # LangChain agent
│   ├── memory.py        # Conversation memory
│   ├── vectorstore.py   # Pinecone integration
│   ├── tools/           # External integrations
│   │   ├── firecrawl.py # Web scraping
│   │   ├── sheets.py    # Google Sheets
│   │   └── gmail.py     # Email notifications
│   └── schemas/         # Pydantic models
├── data/
│   └── lust_products.csv # Product database
├── frontend/            # Chat interface
├── creds/              # Google service credentials
├── requirements.txt
├── Makefile
└── README.md
```

## 🛠️ Development Commands

```bash
# Development server
make run-dev

# Production server  
make run-prod

# Code quality
make lint
make format

# Load product data
make load-data

# Reset agent memory
make reset-agent

# Clean temporary files
make clean
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
# AI Services
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_ENV=us-east1-gcp

# External APIs
FIRECRAWL_KEY=...

# Google Services
GOOGLE_SHEET_ID=...
```

### Google Sheets Setup
1. Create a Google Cloud project
2. Enable Sheets API
3. Create service account credentials
4. Download JSON key to `creds/sheets.json`
5. Share your sheet with the service account email

### Product CSV Format
```csv
id,name,description,price,category,url,features,brand,in_stock
1,"Product Name","Description","$99.99","Category","https://...","Feature1,Feature2","Brand",true
```

## 🤖 Agent Capabilities

The LustBot agent can:
- **Search Products**: Find products using semantic similarity
- **Capture Leads**: Collect customer information for follow-up
- **Scrape Web**: Get additional product information
- **Send Notifications**: Email alerts for new leads

## 🔌 API Endpoints

- `POST /lustbot` - Chat with the bot
- `GET /health` - Health check
- `POST /admin/load-products` - Reload product database
- `GET /admin/agent-reset` - Clear agent memory
- `GET /docs` - API documentation (development only)

## 🎨 Frontend

The chat interface is located in `frontend/` directory:
- `index.html` - Main chat page
- `style.css` - Styling
- `script.js` - Chat functionality

## 📊 Monitoring & Logs

Logs are output to console and include:
- Chat conversations
- Product searches
- Lead captures
- Error tracking

## 🚀 Deployment

### Option 1: Render
1. Create `render.yaml` (see deployment docs)
2. Connect GitHub repository
3. Set environment variables

### Option 2: Docker
```bash
make docker-build
make docker-run
```

### Option 3: Traditional Server
```bash
make run-prod  # Uses Gunicorn
```

## 🔒 Security

- Environment variables for all secrets
- CORS configuration for production
- Input validation with Pydantic
- Error handling and logging

## 📈 Performance

- Vector search with Pinecone for fast product lookup
- Conversation memory management (k=3 messages)
- Async HTTP clients for external APIs
- Connection pooling for database operations

## 🛡️ Error Handling

- Graceful API failure recovery
- User-friendly error messages
- Comprehensive logging
- Fallback responses

## 📝 License

This project is proprietary. All rights reserved.

## 🆘 Support

For issues or questions:
1. Check the logs for error details
2. Verify all environment variables are set
3. Ensure all external services are configured
4. Contact the development team

---

**Built with ❤️ for luxury shopping experiences**
