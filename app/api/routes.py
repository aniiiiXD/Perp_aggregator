"""
Main API router configuration
"""
from fastapi import APIRouter

from app.api.endpoints import prices, trading, positions, health, websocket

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(prices.router, prefix="/prices", tags=["prices"])
api_router.include_router(trading.router, prefix="/trading", tags=["trading"])
api_router.include_router(positions.router, prefix="/positions", tags=["positions"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])