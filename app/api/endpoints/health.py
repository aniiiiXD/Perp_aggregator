"""
Health check endpoints
"""
from fastapi import APIRouter, Request
from app.core.redis import redis_client

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "service": "perp-dex-aggregator"}


@router.get("/detailed")
async def detailed_health_check(request: Request):
    """Detailed health check with service dependencies"""
    health_status = {
        "status": "healthy",
        "service": "perp-dex-aggregator",
        "components": {}
    }
    
    # Check Redis connection
    try:
        await redis_client.redis.ping()
        health_status["components"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health_status["components"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"
    
    # Check DEX connections
    if hasattr(request.app.state, 'dex_service'):
        dex_status = request.app.state.dex_service.get_connection_status()
        health_status["components"]["dex_connections"] = dex_status
        
        if not all(dex_status.values()):
            health_status["status"] = "degraded"
    
    # Check WebSocket manager
    if hasattr(request.app.state, 'ws_manager'):
        ws_stats = request.app.state.ws_manager.get_stats()
        health_status["components"]["websocket"] = {
            "status": "healthy",
            "active_connections": ws_stats["active_connections"],
            "cached_pairs": ws_stats["cached_pairs"]
        }
    
    return health_status