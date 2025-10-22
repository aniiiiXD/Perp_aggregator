"""
Custom Exception Classes

This module defines all custom exceptions used throughout the trading terminal
with proper error codes and user-friendly messages.
"""

from typing import Optional, Dict, Any


class TradingTerminalException(Exception):
    """Base exception for all trading terminal errors"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


class VenueConnectionError(TradingTerminalException):
    """Raised when venue connection fails"""
    
    def __init__(self, venue: str, message: str = None, details: Dict[str, Any] = None):
        self.venue = venue
        message = message or f"Failed to connect to {venue}"
        super().__init__(
            message=message,
            error_code="VENUE_CONNECTION_ERROR",
            details={"venue": venue, **(details or {})}
        )


class AuthenticationError(TradingTerminalException):
    """Raised when authentication fails"""
    
    def __init__(self, venue: str = None, message: str = None, details: Dict[str, Any] = None):
        self.venue = venue
        message = message or f"Authentication failed{f' for {venue}' if venue else ''}"
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details={"venue": venue, **(details or {})} if venue else (details or {})
        )


class OrderValidationError(TradingTerminalException):
    """Raised when order validation fails"""
    
    def __init__(self, field: str = None, message: str = None, details: Dict[str, Any] = None):
        self.field = field
        message = message or f"Order validation failed{f' for field: {field}' if field else ''}"
        super().__init__(
            message=message,
            error_code="ORDER_VALIDATION_ERROR",
            details={"field": field, **(details or {})} if field else (details or {})
        )


class InsufficientBalanceError(TradingTerminalException):
    """Raised when insufficient balance for order"""
    
    def __init__(
        self,
        required: str = None,
        available: str = None,
        asset: str = None,
        details: Dict[str, Any] = None
    ):
        self.required = required
        self.available = available
        self.asset = asset
        
        message = "Insufficient balance"
        if asset:
            message += f" for {asset}"
        if required and available:
            message += f" (required: {required}, available: {available})"
            
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_BALANCE_ERROR",
            details={
                "required": required,
                "available": available,
                "asset": asset,
                **(details or {})
            }
        )


class OrderNotFoundError(TradingTerminalException):
    """Raised when order is not found"""
    
    def __init__(self, order_id: str, venue: str = None, details: Dict[str, Any] = None):
        self.order_id = order_id
        self.venue = venue
        
        message = f"Order {order_id} not found"
        if venue:
            message += f" on {venue}"
            
        super().__init__(
            message=message,
            error_code="ORDER_NOT_FOUND_ERROR",
            details={
                "order_id": order_id,
                "venue": venue,
                **(details or {})
            }
        )


class PositionNotFoundError(TradingTerminalException):
    """Raised when position is not found"""
    
    def __init__(self, symbol: str, venue: str = None, details: Dict[str, Any] = None):
        self.symbol = symbol
        self.venue = venue
        
        message = f"Position for {symbol} not found"
        if venue:
            message += f" on {venue}"
            
        super().__init__(
            message=message,
            error_code="POSITION_NOT_FOUND_ERROR",
            details={
                "symbol": symbol,
                "venue": venue,
                **(details or {})
            }
        )


class MarketDataError(TradingTerminalException):
    """Raised when market data operations fail"""
    
    def __init__(self, symbol: str = None, venue: str = None, message: str = None, details: Dict[str, Any] = None):
        self.symbol = symbol
        self.venue = venue
        
        message = message or "Market data error"
        if symbol:
            message += f" for {symbol}"
        if venue:
            message += f" on {venue}"
            
        super().__init__(
            message=message,
            error_code="MARKET_DATA_ERROR",
            details={
                "symbol": symbol,
                "venue": venue,
                **(details or {})
            }
        )


class WebSocketError(TradingTerminalException):
    """Raised when WebSocket operations fail"""
    
    def __init__(self, venue: str = None, message: str = None, details: Dict[str, Any] = None):
        self.venue = venue
        
        message = message or "WebSocket error"
        if venue:
            message += f" for {venue}"
            
        super().__init__(
            message=message,
            error_code="WEBSOCKET_ERROR",
            details={"venue": venue, **(details or {})} if venue else (details or {})
        )


class RateLimitError(TradingTerminalException):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, venue: str = None, retry_after: int = None, details: Dict[str, Any] = None):
        self.venue = venue
        self.retry_after = retry_after
        
        message = "Rate limit exceeded"
        if venue:
            message += f" for {venue}"
        if retry_after:
            message += f" (retry after {retry_after} seconds)"
            
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            details={
                "venue": venue,
                "retry_after": retry_after,
                **(details or {})
            }
        )


class CircuitBreakerError(TradingTerminalException):
    """Raised when circuit breaker is open"""
    
    def __init__(self, service: str, message: str = None, details: Dict[str, Any] = None):
        self.service = service
        
        message = message or f"Circuit breaker open for {service}"
        
        super().__init__(
            message=message,
            error_code="CIRCUIT_BREAKER_ERROR",
            details={"service": service, **(details or {})}
        )


class ConfigurationError(TradingTerminalException):
    """Raised when configuration is invalid"""
    
    def __init__(self, config_key: str = None, message: str = None, details: Dict[str, Any] = None):
        self.config_key = config_key
        
        message = message or f"Configuration error{f' for {config_key}' if config_key else ''}"
        
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details={"config_key": config_key, **(details or {})} if config_key else (details or {})
        )