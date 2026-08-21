"""Main FastAPI application entrypoint."""

from fastapi import FastAPI

from app.core.config import settings
from app.routers.auth import router as auth_router
from app.routers.gmail import router as gmail_router
from app.routers.chat import router as chat_router

app = FastAPI(
    title="Inboxio",
    description="Personal Gmail Intelligence Agent",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(gmail_router)
app.include_router(chat_router)


@app.get("/")
def health_check():
    """Root health check endpoint."""
    return {
        "status": "healthy",
        "app": "Inboxio",
        "version": "0.1.0",
    }
