"""
Unified Data Models

This module defines the unified data models used across all venues to provide
a consistent interface regardless of the underlying DEX implementation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
import uuid

from app.models.enums import (
    VenueEnum, OrderType, OrderSide, OrderStatus, TimeInForce,
    PositionSide, AssetType, ConnectionStatus
)


@dataclass
class UnifiedOrder:
    """Unified order model that works across all venues"""
    
    # Required fields
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    venue: VenueEnum
    
    # Optional fields with defaults
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: TimeInForce = TimeInForce.GTC
    client_order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # System fields
    order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal('0')
    remaining_quantity: Optional[Decimal] = None
    average_fill_price: Optional[Decimal] = None
    fee: Optional[Decimal] = None
    fee_asset: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    
    # Additional data from venue
    venue_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing"""
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity
        
        # Validate required fields for certain order types
        if self.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and self.price is None:
            raise ValueError(f"{self.order_type} orders require a price")
        
        if self.order_type in [OrderType.STOP_MARKET, OrderType.STOP_LIMIT] and self.stop_price is None:
            raise ValueError(f"{self.order_type} orders require a stop price")
    
    @property
    def is_active(self) -> bool:
        """Check if order is in an active state"""
        return self.status in OrderStatus.active_statuses()
    
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled"""
        return self.status == OrderStatus.FILLED
    
    @property
    def fill_percentage(self) -> Decimal:
        """Get fill percentage (0-100)"""
        if self.quantity == 0:
            return Decimal('0')
        return (self.filled_quantity / self.quantity) * Decimal('100')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'symbol': self.symbol,
            'side': self.side.value,
            'order_type': self.order_type.value,
            'quantity': str(self.quantity),
            'price': str(self.price) if self.price else None,
            'stop_price': str(self.stop_price) if self.stop_price else None,
            'venue': self.venue.value,
            'client_order_id': self.client_order_id,
            'order_id': self.order_id,
            'status': self.status.value,
            'filled_quantity': str(self.filled_quantity),
            'remaining_quantity': str(self.remaining_quantity),
            'average_fill_price': str(self.average_fill_price) if self.average_fill_price else None,
            'fee': str(self.fee) if self.fee else None,
            'fee_asset': self.fee_asset,
            'time_in_force': self.time_in_force.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'filled_at': self.filled_at.isoformat() if self.filled_at else None,
            'venue_data': self.venue_data
        }


@dataclass
class Position:
    """Unified position model across all venues"""
    
    # Required fields
    venue: VenueEnum
    symbol: str
    size: Decimal  # Positive for long, negative for short
    
    # Price information
    entry_price: Decimal
    mark_price: Decimal
    liquidation_price: Optional[Decimal] = None
    
    # PnL information
    unrealized_pnl: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')
    
    # Margin information
    margin_used: Decimal = Decimal('0')
    margin_ratio: Optional[Decimal] = None
    
    # Position metadata
    side: Optional[PositionSide] = None
    leverage: Optional[Decimal] = None
    asset_type: AssetType = AssetType.PERPETUAL
    
    # Timestamps
    opened_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Additional venue-specific data
    venue_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing"""
        # Determine position side from size
        if self.side is None:
            self.side = PositionSide.LONG if self.size >= 0 else PositionSide.SHORT
    
    @property
    def is_long(self) -> bool:
        """Check if position is long"""
        return self.size > 0
    
    @property
    def is_short(self) -> bool:
        """Check if position is short"""
        return self.size < 0
    
    @property
    def abs_size(self) -> Decimal:
        """Get absolute position size"""
        return abs(self.size)
    
    @property
    def notional_value(self) -> Decimal:
        """Get notional value of position"""
        return self.abs_size * self.mark_price
    
    @property
    def pnl_percentage(self) -> Decimal:
        """Get PnL as percentage of entry value"""
        entry_value = self.abs_size * self.entry_price
        if entry_value == 0:
            return Decimal('0')
        return (self.unrealized_pnl / entry_value) * Decimal('100')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'venue': self.venue.value,
            'symbol': self.symbol,
            'size': str(self.size),
            'side': self.side.value if self.side else None,
            'entry_price': str(self.entry_price),
            'mark_price': str(self.mark_price),
            'liquidation_price': str(self.liquidation_price) if self.liquidation_price else None,
            'unrealized_pnl': str(self.unrealized_pnl),
            'realized_pnl': str(self.realized_pnl),
            'margin_used': str(self.margin_used),
            'margin_ratio': str(self.margin_ratio) if self.margin_ratio else None,
            'leverage': str(self.leverage) if self.leverage else None,
            'asset_type': self.asset_type.value,
            'notional_value': str(self.notional_value),
            'pnl_percentage': str(self.pnl_percentage),
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'updated_at': self.updated_at.isoformat(),
            'venue_data': self.venue_data
        }


@dataclass
class Balance:
    """Unified balance model across all venues"""
    
    # Required fields
    venue: VenueEnum
    asset: str
    total: Decimal
    available: Decimal
    locked: Decimal
    
    # Optional fields
    usd_value: Optional[Decimal] = None
    
    # Timestamps
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Additional venue-specific data
    venue_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def locked_percentage(self) -> Decimal:
        """Get locked balance as percentage of total"""
        if self.total == 0:
            return Decimal('0')
        return (self.locked / self.total) * Decimal('100')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'venue': self.venue.value,
            'asset': self.asset,
            'total': str(self.total),
            'available': str(self.available),
            'locked': str(self.locked),
            'locked_percentage': str(self.locked_percentage),
            'usd_value': str(self.usd_value) if self.usd_value else None,
            'updated_at': self.updated_at.isoformat(),
            'venue_data': self.venue_data
        }


@dataclass
class MarketData:
    """Unified market data model"""
    
    # Required fields
    venue: VenueEnum
    symbol: str
    
    # Price data
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    bid_size: Optional[Decimal] = None
    ask_size: Optional[Decimal] = None
    last_price: Optional[Decimal] = None
    
    # Volume and statistics
    volume_24h: Optional[Decimal] = None
    high_24h: Optional[Decimal] = None
    low_24h: Optional[Decimal] = None
    change_24h: Optional[Decimal] = None
    change_24h_percent: Optional[Decimal] = None
    
    # Funding rate (for perpetuals)
    funding_rate: Optional[Decimal] = None
    next_funding_time: Optional[datetime] = None
    
    # Open interest
    open_interest: Optional[Decimal] = None
    
    # Timestamps
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Additional venue-specific data
    venue_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def spread(self) -> Optional[Decimal]:
        """Get bid-ask spread"""
        if self.bid_price and self.ask_price:
            return self.ask_price - self.bid_price
        return None
    
    @property
    def spread_percentage(self) -> Optional[Decimal]:
        """Get bid-ask spread as percentage"""
        if self.spread and self.bid_price and self.bid_price > 0:
            return (self.spread / self.bid_price) * Decimal('100')
        return None
    
    @property
    def mid_price(self) -> Optional[Decimal]:
        """Get mid price between bid and ask"""
        if self.bid_price and self.ask_price:
            return (self.bid_price + self.ask_price) / Decimal('2')
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'venue': self.venue.value,
            'symbol': self.symbol,
            'bid_price': str(self.bid_price) if self.bid_price else None,
            'ask_price': str(self.ask_price) if self.ask_price else None,
            'bid_size': str(self.bid_size) if self.bid_size else None,
            'ask_size': str(self.ask_size) if self.ask_size else None,
            'last_price': str(self.last_price) if self.last_price else None,
            'mid_price': str(self.mid_price) if self.mid_price else None,
            'spread': str(self.spread) if self.spread else None,
            'spread_percentage': str(self.spread_percentage) if self.spread_percentage else None,
            'volume_24h': str(self.volume_24h) if self.volume_24h else None,
            'high_24h': str(self.high_24h) if self.high_24h else None,
            'low_24h': str(self.low_24h) if self.low_24h else None,
            'change_24h': str(self.change_24h) if self.change_24h else None,
            'change_24h_percent': str(self.change_24h_percent) if self.change_24h_percent else None,
            'funding_rate': str(self.funding_rate) if self.funding_rate else None,
            'next_funding_time': self.next_funding_time.isoformat() if self.next_funding_time else None,
            'open_interest': str(self.open_interest) if self.open_interest else None,
            'timestamp': self.timestamp.isoformat(),
            'venue_data': self.venue_data
        }


@dataclass
class Trade:
    """Unified trade model"""
    
    # Required fields
    venue: VenueEnum
    symbol: str
    trade_id: str
    side: OrderSide
    price: Decimal
    quantity: Decimal
    
    # Optional fields
    fee: Optional[Decimal] = None
    fee_asset: Optional[str] = None
    order_id: Optional[str] = None
    
    # Timestamps
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Additional venue-specific data
    venue_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def notional_value(self) -> Decimal:
        """Get notional value of trade"""
        return self.price * self.quantity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'venue': self.venue.value,
            'symbol': self.symbol,
            'trade_id': self.trade_id,
            'side': self.side.value,
            'price': str(self.price),
            'quantity': str(self.quantity),
            'notional_value': str(self.notional_value),
            'fee': str(self.fee) if self.fee else None,
            'fee_asset': self.fee_asset,
            'order_id': self.order_id,
            'timestamp': self.timestamp.isoformat(),
            'venue_data': self.venue_data
        }


@dataclass
class VenueStatus:
    """Status information for a venue"""
    
    venue: VenueEnum
    connection_status: ConnectionStatus
    api_status: ConnectionStatus
    websocket_status: ConnectionStatus
    
    # Performance metrics
    latency_ms: Optional[float] = None
    success_rate: Optional[float] = None
    
    # Error information
    last_error: Optional[str] = None
    error_count: int = 0
    
    # Timestamps
    last_check: datetime = field(default_factory=datetime.utcnow)
    last_success: Optional[datetime] = None
    last_error_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'venue': self.venue.value,
            'connection_status': self.connection_status.value,
            'api_status': self.api_status.value,
            'websocket_status': self.websocket_status.value,
            'latency_ms': self.latency_ms,
            'success_rate': self.success_rate,
            'last_error': self.last_error,
            'error_count': self.error_count,
            'last_check': self.last_check.isoformat(),
            'last_success': self.last_success.isoformat() if self.last_success else None,
            'last_error_time': self.last_error_time.isoformat() if self.last_error_time else None
        }