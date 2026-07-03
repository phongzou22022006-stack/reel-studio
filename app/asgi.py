"""
ASGI application for FastAPI server.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import config
from app.router import api_router


# Create FastAPI app
app = FastAPI(
    title="Reel Studio API",
    description="Facebook Reels automation with templating & human-in-the-loop workflow",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Application startup."""
    logger.info("Reel Studio API starting up")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown."""
    logger.info("Reel Studio API shutting down")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Reel Studio API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
