"""
Market data models and schemas
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class DEXType(str, Enum):
    """Supported DEX types"""
    HYPERLIQUID = "hyperliquid"
    LIGHTER = "lighter"


class OrderSide(str, Enum):
    """Order side types"""
    LONG = "long"
    SHORT = "short"


class OrderType(str, Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    """Order status types"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PriceData(BaseModel):
    """Price data from a single DEX"""
    pair: str = Field(..., description="Trading pair symbol")
    dex: DEXType = Field(..., description="DEX source")
    bid: Decimal = Field(..., description="Best bid price")
    ask: Decimal = Field(..., description="Best ask price")
    last_price: Decimal = Field(..., description="Last traded price")
    volume_24h: Decimal = Field(..., description="24h trading volume")
    funding_rate: Optional[Decimal] = Field(None, description="Current funding rate")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AggregatedPrice(BaseModel):
    """Aggregated price data across DEXs"""
    pair: str = Field(..., description="Trading pair symbol")
    best_bid: Decimal = Field(..., description="Best bid across all DEXs")
    best_ask: Decimal = Field(..., description="Best ask across all DEXs")
    best_bid_dex: DEXType = Field(..., description="DEX with best bid")
    best_ask_dex: DEXType = Field(..., description="DEX with best ask")
    sources: List[PriceData] = Field(..., description="Source price data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OrderRequest(BaseModel):
    """Order placement request"""
    pair: str = Field(..., description="Trading pair symbol")
    side: OrderSide = Field(..., description="Order side (long/short)")
    size: Decimal = Field(..., gt=0, description="Order size")
    order_type: OrderType = Field(..., description="Order type")
    price: Optional[Decimal] = Field(None, description="Limit price (for limit orders)")
    slippage_tolerance: Decimal = Field(0.01, description="Maximum slippage tolerance")


class RouteResult(BaseModel):
    """Order routing calculation result"""
    pair: str = Field(..., description="Trading pair symbol")
    recommended_dex: DEXType = Field(..., description="Recommended DEX for execution")
    expected_price: Decimal = Field(..., description="Expected execution price")
    estimated_slippage: Decimal = Field(..., description="Estimated slippage")
    alternative_dex: Optional[DEXType] = Field(None, description="Alternative DEX option")
    alternative_price: Optional[Decimal] = Field(None, description="Alternative execution price")
    calculation_time_ms: float = Field(..., description="Route calculation time")


class Position(BaseModel):
    """Trading position"""
    id: str = Field(..., description="Position ID")
    pair: str = Field(..., description="Trading pair symbol")
    dex: DEXType = Field(..., description="DEX where position exists")
    side: OrderSide = Field(..., description="Position side")
    size: Decimal = Field(..., description="Position size")
    entry_price: Decimal = Field(..., description="Average entry price")
    current_price: Decimal = Field(..., description="Current market price")
    unrealized_pnl: Decimal = Field(..., description="Unrealized PnL")
    liquidation_price: Optional[Decimal] = Field(None, description="Liquidation price")
    margin: Decimal = Field(..., description="Margin requirement")
    funding_rate: Optional[Decimal] = Field(None, description="Current funding rate")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Trade(BaseModel):
    """Executed trade record"""
    id: str = Field(..., description="Trade ID")
    pair: str = Field(..., description="Trading pair symbol")
    dex: DEXType = Field(..., description="Execution DEX")
    side: OrderSide = Field(..., description="Trade side")
    size: Decimal = Field(..., description="Trade size")
    price: Decimal = Field(..., description="Execution price")
    fees: Decimal = Field(..., description="Trading fees")
    slippage: Decimal = Field(..., description="Actual slippage")
    execution_time_ms: float = Field(..., description="Execution time")
    timestamp: datetime = Field(default_factory=datetime.utcnow)