"""
FastAPI Entry Point for Unified Trading Terminal

This is the main application entry point that initializes the FastAPI app,
sets up middleware, includes routers, and configures the application lifecycle.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.redis import redis_client
from app.api.routes import api_router
from app.orchestrator.main_orchestrator import MainOrchestrator
from app.orchestrator.event_bus import EventBus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
orchestrator: MainOrchestrator = None
event_bus: EventBus = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events"""
    global orchestrator, event_bus
    
    # Startup
    logger.info("Starting Unified Trading Terminal...")
    
    # Initialize Redis connection
    await redis_client.initialize()
    
    # Initialize event bus
    event_bus = EventBus(redis_client)
    await event_bus.initialize()
    
    # Initialize main orchestrator
    orchestrator = MainOrchestrator(event_bus)
    await orchestrator.initialize()
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Unified Trading Terminal...")
    
    if orchestrator:
        await orchestrator.shutdown()
    
    if event_bus:
        await event_bus.shutdown()
    
    await redis_client.close()
    
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Unified Trading Terminal",
    description="Single interface for trading across multiple DEXs",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "redis": await redis_client.health_check(),
            "orchestrator": orchestrator.health_check() if orchestrator else False
        }
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Unified Trading Terminal API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )