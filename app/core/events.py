"""
Event Definitions and Models

This module defines all event types used throughout the trading terminal for
inter-component communication via the event bus.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional
from decimal import Decimal
import uuid

from app.models.enums import VenueEnum, OrderStatus


@dataclass
class BaseEvent:
    """Base class for all events"""
    event_id: str
    event_type: str
    timestamp: datetime
    venue: VenueEnum
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return asdict(self)


@dataclass
class OrderEvent(BaseEvent):
    """Event for order-related updates"""
    order_id: str
    client_order_id: str
    status: OrderStatus
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Optional[Decimal]
    filled_quantity: Decimal = Decimal('0')
    average_fill_price: Optional[Decimal] = None
    fee: Optional[Decimal] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = "order_update"


@dataclass
class PositionEvent(BaseEvent):
    """Event for position-related updates"""
    symbol: str
    size: Decimal
    entry_price: Decimal
    mark_price: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    margin_used: Decimal
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = "position_update"


@dataclass
class BalanceEvent(BaseEvent):
    """Event for balance-related updates"""
    asset: str
    total: Decimal
    available: Decimal
    locked: Decimal
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = "balance_update"


@dataclass
class MarketDataEvent(BaseEvent):
    """Event for market data updates"""
    symbol: str
    bid_price: Decimal
    ask_price: Decimal
    bid_size: Decimal
    ask_size: Decimal
    last_price: Optional[Decimal] = None
    volume_24h: Optional[Decimal] = None
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = "market_data_update"


@dataclass
class TradeEvent(BaseEvent):
    """Event for trade execution updates"""
    trade_id: str
    symbol: str
    side: str
    price: Decimal
    quantity: Decimal
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = "trade_update"


@dataclass
class ConnectionEvent(BaseEvent):
    """Event for connection status updates"""
    connection_type: str  # websocket, api, etc.
    status: str  # connected, disconnected, error
    error_message: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = "connection_update"


@dataclass
class SystemEvent(BaseEvent):
    """Event for system-level updates"""
    component: str
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = "system_update"


# Event type constants
class EventTypes:
    ORDER_UPDATE = "order_update"
    POSITION_UPDATE = "position_update"
    BALANCE_UPDATE = "balance_update"
    MARKET_DATA_UPDATE = "market_data_update"
    TRADE_UPDATE = "trade_update"
    CONNECTION_UPDATE = "connection_update"
    SYSTEM_UPDATE = "system_update"


# Event channel constants for Redis pub/sub
class EventChannels:
    ORDERS = "orders"
    POSITIONS = "positions"
    BALANCES = "balances"
    MARKET_DATA = "market_data"
    TRADES = "trades"
    CONNECTIONS = "connections"
    SYSTEM = "system"
    
    # Venue-specific channels
    HYPERLIQUID = "hyperliquid"
    LIGHTER = "lighter"
    TRADEXYZ = "tradexyz"
    
    @classmethod
    def venue_channel(cls, venue: VenueEnum) -> str:
        """Get venue-specific channel name"""
        return venue.value
    
    @classmethod
    def all_channels(cls) -> list:
        """Get all event channels"""
        return [
            cls.ORDERS,
            cls.POSITIONS,
            cls.BALANCES,
            cls.MARKET_DATA,
            cls.TRADES,
            cls.CONNECTIONS,
            cls.SYSTEM,
            cls.HYPERLIQUID,
            cls.LIGHTER,
            cls.TRADEXYZ
        ]