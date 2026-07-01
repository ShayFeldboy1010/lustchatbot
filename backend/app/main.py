"""FastAPI Application Entry Point"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import os

from .config import get_settings
from .routers import chat, admin, whatsapp, admin_ui
from .services.mongodb import close_connections
from .services import conversation_store

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown"""
    # Startup
    print("🚀 Starting E-Commerce Chatbot API...")
    print(f"📊 Debug mode: {settings.debug}")
    # Create indexes in the background — never block startup on MongoDB.
    # uvicorn binds the listening port only AFTER lifespan startup returns, so
    # awaiting a slow/unreachable MongoDB here would delay the port bind past the
    # host's port-scan window and fail the deploy. ensure_indexes swallows its
    # own errors, so a failed background run is harmless.
    app.state.index_task = asyncio.create_task(conversation_store.ensure_indexes())

    yield

    # Shutdown
    print("🛑 Shutting down...")
    close_connections()


# Create FastAPI application
app = FastAPI(
    title="E-Commerce Chatbot API",
    description="AI-powered sales and customer service chatbot for MyLastShop",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(whatsapp.router)
app.include_router(admin_ui.router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "E-Commerce Chatbot API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/admin/health"
    }


# Serve static files
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


# Chat UI route
@app.get("/chat")
async def chat_ui():
    from fastapi.responses import FileResponse
    chat_html = os.path.join(os.path.dirname(__file__), "static", "chat.html")
    return FileResponse(chat_html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
