"""
Main FastAPI application entry point
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import api_router
from app.websocket.manager import WebSocketManager
from app.services.dex_connector import DEXConnectorService
from app.core.redis import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await redis_client.connect()
    
    # Initialize WebSocket manager
    ws_manager = WebSocketManager()
    app.state.ws_manager = ws_manager
    
    # Initialize DEX connector service
    dex_service = DEXConnectorService(ws_manager)
    app.state.dex_service = dex_service
    
    # Start DEX connections
    await dex_service.start_connections()
    
    yield
    
    # Shutdown
    await dex_service.stop_connections()
    await redis_client.disconnect()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Perp DEX Aggregator",
        description="Real-time perpetual futures aggregator for Hyperliquid and Lighter",
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
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )