from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn
import logging
from .settings import settings
from .agent import get_agent
from .vectorstore import vector_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="LustBot API",
    description="AI Shopping Assistant for Luxury Products",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Mount static files (frontend)
app.mount("/static", StaticFiles(directory="frontend"), name="static")


class ChatMessage(BaseModel):
    message: str
    user_id: str = "anonymous"


class ChatResponse(BaseModel):
    reply: str
    status: str = "success"


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the frontend HTML"""
    try:
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Frontend not found</h1><p>Please make sure frontend files are in the frontend/ directory</p>",
            status_code=404
        )


@app.post("/lustbot", response_model=ChatResponse)
async def lustbot_chat(request: ChatMessage):
    """
    Main LustBot chat endpoint
    
    Args:
        request: Chat message from user
        
    Returns:
        ChatResponse with bot reply
    """
    try:
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        logger.info(f"Received message from {request.user_id}: {request.message[:100]}...")
        
        # Get agent for this user session and process message
        agent = get_agent(request.user_id)
        response = agent.run(request.message)
        
        # Extract the content from the agno response
        reply = response.content if hasattr(response, 'content') else str(response)
        
        logger.info(f"Generated reply: {reply[:100]}...")
        
        return ChatResponse(reply=reply, status="success")
        
    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        return ChatResponse(
            reply="I apologize, but I'm experiencing technical difficulties. Please try again later.",
            status="error"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "LustBot",
        "version": "1.0.0"
    }


@app.post("/admin/load-products")
async def load_products():
    """Admin endpoint to reload product database"""
    try:
        success = vector_store.load_products_from_csv()
        if success:
            return {"status": "success", "message": "Products loaded successfully"}
        else:
            return {"status": "error", "message": "Failed to load products"}
    except Exception as e:
        logger.error(f"Product loading failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/agent-reset")
async def reset_agent_endpoint():
    """Admin endpoint to reset agent memory"""
    try:
        from .agent import reset_agent
        reset_agent()
        return {"status": "success", "message": "Agent reset successfully"}
    except Exception as e:
        logger.error(f"Agent reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info("🚀 Starting LustBot...")
    
    # Initialize vector store with products (optional)
    if settings.pinecone_api_key and settings.pinecone_api_key != "temp-placeholder":
        try:
            vector_store.load_products_from_csv()
            logger.info("✅ Product database loaded")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load products: {e}")
    else:
        logger.info("ℹ️ Running without Pinecone vector store")
    
    # Initialize agent
    try:
        get_agent("startup_test")
        logger.info("✅ LustBot agent initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize agent: {e}")
    
    logger.info(f"🌐 LustBot is running on http://{settings.host}:{settings.port}")
    logger.info(f"📚 API Docs available at http://{settings.host}:{settings.port}/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info("👋 Shutting down LustBot...")


def main():
    """Main entry point"""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        access_log=True
    )


if __name__ == "__main__":
    main()
