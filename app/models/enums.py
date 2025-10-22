"""
System Enums

This module defines all enums used throughout the trading terminal for
consistent data representation and validation.
"""

from enum import Enum


class VenueEnum(str, Enum):
    """Supported trading venues"""
    HYPERLIQUID = "hyperliquid"
    LIGHTER = "lighter"
    TRADEXYZ = "tradexyz"
    
    @classmethod
    def all_venues(cls):
        """Get all supported venues"""
        return [venue.value for venue in cls]
    
    def __str__(self):
        return self.value


class OrderType(str, Enum):
    """Order types supported across venues"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"
    
    def __str__(self):
        return self.value


class OrderSide(str, Enum):
    """Order sides"""
    BUY = "buy"
    SELL = "sell"
    
    def __str__(self):
        return self.value


class OrderStatus(str, Enum):
    """Order status across all venues"""
    PENDING = "pending"          # Order submitted but not yet confirmed
    OPEN = "open"               # Order confirmed and active
    PARTIALLY_FILLED = "partially_filled"  # Order partially executed
    FILLED = "filled"           # Order completely executed
    CANCELLED = "cancelled"     # Order cancelled by user or system
    REJECTED = "rejected"       # Order rejected by venue
    EXPIRED = "expired"         # Order expired (for time-in-force orders)
    
    def __str__(self):
        return self.value
    
    @classmethod
    def active_statuses(cls):
        """Get statuses that represent active orders"""
        return [cls.PENDING, cls.OPEN, cls.PARTIALLY_FILLED]
    
    @classmethod
    def final_statuses(cls):
        """Get statuses that represent completed orders"""
        return [cls.FILLED, cls.CANCELLED, cls.REJECTED, cls.EXPIRED]


class TimeInForce(str, Enum):
    """Time in force options"""
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate Or Cancel
    FOK = "fok"  # Fill Or Kill
    
    def __str__(self):
        return self.value


class PositionSide(str, Enum):
    """Position sides for futures trading"""
    LONG = "long"
    SHORT = "short"
    
    def __str__(self):
        return self.value


class AssetType(str, Enum):
    """Asset types"""
    SPOT = "spot"
    PERPETUAL = "perpetual"
    FUTURE = "future"
    OPTION = "option"
    
    def __str__(self):
        return self.value


class ConnectionStatus(str, Enum):
    """Connection status for venues and WebSockets"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    
    def __str__(self):
        return self.value


class EventType(str, Enum):
    """Event types for the event bus"""
    ORDER_UPDATE = "order_update"
    POSITION_UPDATE = "position_update"
    BALANCE_UPDATE = "balance_update"
    MARKET_DATA_UPDATE = "market_data_update"
    TRADE_UPDATE = "trade_update"
    CONNECTION_UPDATE = "connection_update"
    SYSTEM_UPDATE = "system_update"
    
    def __str__(self):
        return self.value


class MarketDataType(str, Enum):
    """Market data types"""
    TICKER = "ticker"
    ORDERBOOK = "orderbook"
    TRADES = "trades"
    KLINE = "kline"
    
    def __str__(self):
        return self.value


class IntervalType(str, Enum):
    """Kline/Candlestick intervals"""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"
    
    def __str__(self):
        return self.value