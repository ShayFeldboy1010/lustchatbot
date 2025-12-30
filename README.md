# LustBot - E-Commerce Chatbot

AI-powered sales and customer service chatbot for MyLastShop, built with Pydantic AI and FastAPI.

## Features

- **AI Sales Agent ("לסטי")**: Hebrew-speaking chatbot powered by Google Gemini
- **Knowledge Base**: MongoDB Atlas vector search for product information
- **Order Management**: Google Sheets integration for order storage
- **Human Escalation**: Automatic detection and handoff to human support
- **Session Memory**: Conversation history persistence
- **Modern Chat UI**: RTL Hebrew support with responsive design

## Quick Start

### Prerequisites

- Python 3.11+
- Google Gemini API key
- OpenAI API key (for embeddings)
- MongoDB Atlas cluster with vector search enabled
- Google Sheets service account credentials

### Installation

1. **Clone and setup**
```bash
cd LustBot-claude\ code
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
```

2. **Configure environment**
```bash
# Edit .env file with your credentials
cp .env.example .env
```

3. **Add Google Sheets credentials**
Place your `credentials.json` file in the project root.

4. **Run the backend**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

5. **Open the frontend**
Open `frontend/index.html` in your browser, or serve it:
```bash
# Using Python's built-in server
cd frontend
python -m http.server 3000
```

Then visit http://localhost:3000

### Docker Deployment

```bash
docker-compose up -d
```

Access the chat at http://localhost

## Project Structure

```
ecommerce-chatbot/
├── backend/
│   ├── app/
│   │   ├── agents/         # Pydantic AI agent
│   │   ├── tools/          # Vector store, Google Sheets, escalation
│   │   ├── models/         # Pydantic models
│   │   ├── services/       # Memory, MongoDB, embeddings
│   │   ├── routers/        # API endpoints
│   │   └── main.py         # FastAPI entry point
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   └── js/
│       ├── api.js
│       └── chat.js
├── docker-compose.yml
├── nginx.conf
└── .env
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send message and get response |
| GET | `/api/history/{session_id}` | Get conversation history |
| DELETE | `/api/history/{session_id}` | Clear session history |
| GET | `/api/admin/health` | Health check |
| GET | `/api/admin/sessions` | List active sessions |
| GET | `/api/admin/escalations` | List escalation history |

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Google Gemini API key |
| `OPENAI_API_KEY` | OpenAI API key for embeddings |
| `MONGODB_URI` | MongoDB Atlas connection string |
| `MONGODB_DATABASE` | Database name |
| `MONGODB_COLLECTION` | Collection name for vector store |
| `MONGODB_VECTOR_INDEX` | Vector search index name |
| `GOOGLE_SHEETS_CREDENTIALS_PATH` | Path to service account JSON |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | Google Sheets ID |
| `GOOGLE_SHEETS_SHEET_NAME` | Sheet name for orders |

### MongoDB Vector Search Setup

Ensure your MongoDB collection has a vector search index:

```json
{
  "mappings": {
    "dynamic": true,
    "fields": {
      "embedding": {
        "dimensions": 1536,
        "similarity": "cosine",
        "type": "knnVector"
      }
    }
  }
}
```

## Escalation Keywords

The bot automatically detects these Hebrew keywords and offers human support:
- אדם, נציג, בן אדם, מנהל
- עזור לי, עזרה, תלונה
- החזר, זיכוי, דחוף
- And more...

## License

Private - MyLastShop
