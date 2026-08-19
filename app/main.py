"""Main FastAPI application entrypoint."""

from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title="Inboxio",
    description="Personal Gmail Intelligence Agent",
    version="0.1.0",
)


@app.get("/")
def health_check():
    """Root health check endpoint."""
    return {
        "status": "healthy",
        "app": "Inboxio",
        "version": "0.1.0",
    }
