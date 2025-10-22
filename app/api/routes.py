"""
Main API Router

This module sets up the main FastAPI router and includes all endpoint routers.
It also configures middleware, exception handlers, and request/response processing.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import logging
import time
import uuid

from app.api.endpoints import venues, trading, positions, market_data, websocket
from app.core.exceptions import TradingTerminalException

logger = logging.getLogger(__name__)

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(venues.router, prefix="/venues", tags=["venues"])
api_router.include_router(trading.router, prefix="/trading", tags=["trading"])
api_router.include_router(positions.router, prefix="/positions", tags=["positions"])
api_router.include_router(market_data.router, prefix="/market-data", tags=["market-data"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])


@api_router.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all API requests with timing and correlation ID"""
    # Generate correlation ID for request tracking
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    
    # Log request
    start_time = time.time()
    logger.info(
        f"Request started: {request.method} {request.url.path} "
        f"[{correlation_id}]"
    )
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"Request completed: {request.method} {request.url.path} "
        f"[{correlation_id}] - {response.status_code} - {process_time:.3f}s"
    )
    
    # Add correlation ID to response headers
    response.headers["X-Correlation-ID"] = correlation_id
    
    return response


@api_router.exception_handler(TradingTerminalException)
async def trading_terminal_exception_handler(request: Request, exc: TradingTerminalException):
    """Handle custom trading terminal exceptions"""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.error(
        f"Trading terminal error: {exc.message} [{correlation_id}] - "
        f"Error code: {exc.error_code}, Details: {exc.details}"
    )
    
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "correlation_id": correlation_id
        }
    )


@api_router.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.warning(
        f"HTTP error: {exc.detail} [{correlation_id}] - "
        f"Status: {exc.status_code}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": exc.detail,
            "correlation_id": correlation_id
        }
    )


@api_router.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.error(
        f"Unexpected error: {str(exc)} [{correlation_id}]",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "correlation_id": correlation_id
        }
    )