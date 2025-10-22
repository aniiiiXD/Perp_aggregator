"""
Market Data Endpoints

This module provides endpoints for retrieving market data including
tickers, orderbooks, trades, and candlestick data.

Endpoints:
- GET /ticker/{symbol} - Get ticker data for a symbol
- GET /orderbook/{symbol} - Get orderbook data
- GET /trades/{symbol} - Get recent trades
- GET /klines/{symbol} - Get candlestick data
- GET /symbols - Get available symbols
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta
import logging

from app.models.unified import MarketData, Trade
from app.models.enums import VenueEnum, OrderSide, IntervalType
from app.core.exceptions import VenueConnectionError, MarketDataError

logger = logging.getLogger(__name__)

router = APIRouter()


class TickerResponse(BaseModel):
    """Response model for ticker data"""
    venue: VenueEnum
    symbol: str
    bid_price: Optional[Decimal]
    ask_price: Optional[Decimal]
    bid_size: Optional[Decimal]
    ask_size: Optional[Decimal]
    last_price: Optional[Decimal]
    mid_price: Optional[Decimal]
    spread: Optional[Decimal]
    spread_percentage: Optional[Decimal]
    volume_24h: Optional[Decimal]
    high_24h: Optional[Decimal]
    low_24h: Optional[Decimal]
    change_24h: Optional[Decimal]
    change_24h_percent: Optional[Decimal]
    funding_rate: Optional[Decimal]
    next_funding_time: Optional[datetime]
    open_interest: Optional[Decimal]
    timestamp: datetime
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class OrderBookLevel(BaseModel):
    """Order book price level"""
    price: Decimal
    size: Decimal
    
    class Config:
        json_encoders = {
            Decimal: str
        }


class OrderBookResponse(BaseModel):
    """Response model for orderbook data"""
    venue: VenueEnum
    symbol: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TradeResponse(BaseModel):
    """Response model for trade data"""
    venue: VenueEnum
    symbol: str
    trade_id: str
    side: OrderSide
    price: Decimal
    quantity: Decimal
    notional_value: Decimal
    timestamp: datetime
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class KlineResponse(BaseModel):
    """Response model for candlestick data"""
    symbol: str
    venue: VenueEnum
    interval: IntervalType
    open_time: datetime
    close_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    trades_count: int
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


# Dependency to get orchestrator (placeholder)
async def get_orchestrator():
    """Get the main orchestrator instance"""
    # TODO: Implement dependency injection for orchestrator
    return None


@router.get("/ticker/{symbol}", response_model=TickerResponse)
async def get_ticker(
    symbol: str,
    venue: VenueEnum = Query(..., description="Venue to get ticker from"),
    orchestrator=Depends(get_orchestrator)
):
    """
    Get ticker data for a symbol from a specific venue.
    
    Args:
        symbol: Trading symbol (e.g., BTC-PERP)
        venue: Venue to query
        
    Returns:
        Current ticker data including prices, volume, and statistics
    """
    try:
        # TODO: Get market data via orchestrator
        # market_data = await orchestrator.get_market_data(venue, symbol)
        
        # Placeholder market data
        market_data = MarketData(
            venue=venue,
            symbol=symbol,
            bid_price=Decimal("50950.5"),
            ask_price=Decimal("51000.0"),
            bid_size=Decimal("2.5"),
            ask_size=Decimal("1.8"),
            last_price=Decimal("50975.0"),
            volume_24h=Decimal("125000.0"),
            high_24h=Decimal("52000.0"),
            low_24h=Decimal("49500.0"),
            change_24h=Decimal("1475.0"),
            change_24h_percent=Decimal("2.98"),
            funding_rate=Decimal("0.0001"),
            next_funding_time=datetime.utcnow() + timedelta(hours=4),
            open_interest=Decimal("85000.0")
        )
        
        logger.info(f"Retrieved ticker for {symbol} on {venue.value}")
        
        return TickerResponse(
            venue=market_data.venue,
            symbol=market_data.symbol,
            bid_price=market_data.bid_price,
            ask_price=market_data.ask_price,
            bid_size=market_data.bid_size,
            ask_size=market_data.ask_size,
            last_price=market_data.last_price,
            mid_price=market_data.mid_price,
            spread=market_data.spread,
            spread_percentage=market_data.spread_percentage,
            volume_24h=market_data.volume_24h,
            high_24h=market_data.high_24h,
            low_24h=market_data.low_24h,
            change_24h=market_data.change_24h,
            change_24h_percent=market_data.change_24h_percent,
            funding_rate=market_data.funding_rate,
            next_funding_time=market_data.next_funding_time,
            open_interest=market_data.open_interest,
            timestamp=market_data.timestamp
        )
        
    except MarketDataError as e:
        logger.warning(f"Market data error: {e.message}")
        raise HTTPException(status_code=404, detail=e.message)
    except VenueConnectionError as e:
        logger.error(f"Venue connection error: {e.message}")
        raise HTTPException(status_code=503, detail=f"Venue {e.venue} is unavailable")
    except Exception as e:
        logger.error(f"Error getting ticker for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get ticker data")


@router.get("/orderbook/{symbol}", response_model=OrderBookResponse)
async def get_orderbook(
    symbol: str,
    venue: VenueEnum = Query(..., description="Venue to get orderbook from"),
    depth: int = Query(20, ge=1, le=100, description="Number of price levels to return"),
    orchestrator=Depends(get_orchestrator)
):
    """
    Get orderbook data for a symbol.
    
    Args:
        symbol: Trading symbol
        venue: Venue to query
        depth: Number of price levels to return (max 100)
        
    Returns:
        Current orderbook with bids and asks
    """
    try:
        # TODO: Get orderbook via orchestrator
        # orderbook = await orchestrator.get_orderbook(venue, symbol, depth)
        
        # Placeholder orderbook data
        base_price = Decimal("51000")
        tick_size = Decimal("0.5")
        
        # Generate bids (below base price)
        bids = []
        for i in range(depth):
            price = base_price - (tick_size * (i + 1))
            size = Decimal("0.5") + (Decimal("0.1") * i)
            bids.append(OrderBookLevel(price=price, size=size))
        
        # Generate asks (above base price)
        asks = []
        for i in range(depth):
            price = base_price + (tick_size * (i + 1))
            size = Decimal("0.4") + (Decimal("0.1") * i)
            asks.append(OrderBookLevel(price=price, size=size))
        
        orderbook = OrderBookResponse(
            venue=venue,
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=datetime.utcnow()
        )
        
        logger.info(f"Retrieved orderbook for {symbol} on {venue.value} (depth: {depth})")
        return orderbook
        
    except MarketDataError as e:
        logger.warning(f"Market data error: {e.message}")
        raise HTTPException(status_code=404, detail=e.message)
    except VenueConnectionError as e:
        logger.error(f"Venue connection error: {e.message}")
        raise HTTPException(status_code=503, detail=f"Venue {e.venue} is unavailable")
    except Exception as e:
        logger.error(f"Error getting orderbook for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get orderbook data")


@router.get("/trades/{symbol}", response_model=List[TradeResponse])
async def get_recent_trades(
    symbol: str,
    venue: VenueEnum = Query(..., description="Venue to get trades from"),
    limit: int = Query(100, ge=1, le=1000, description="Number of trades to return"),
    orchestrator=Depends(get_orchestrator)
):
    """
    Get recent trades for a symbol.
    
    Args:
        symbol: Trading symbol
        venue: Venue to query
        limit: Number of trades to return (max 1000)
        
    Returns:
        List of recent trades
    """
    try:
        # TODO: Get recent trades via orchestrator
        # trades = await orchestrator.get_recent_trades(venue, symbol, limit)
        
        # Placeholder trades
        trades = []
        base_price = Decimal("51000")
        base_time = datetime.utcnow()
        
        for i in range(min(limit, 50)):  # Generate up to 50 placeholder trades
            price_variation = Decimal(str((i % 20) - 10)) * Decimal("0.5")  # ±10 * 0.5
            trade = Trade(
                venue=venue,
                symbol=symbol,
                trade_id=f"trade_{venue.value}_{i}",
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                price=base_price + price_variation,
                quantity=Decimal("0.1") + (Decimal("0.05") * (i % 10)),
                timestamp=base_time - timedelta(seconds=i * 5)
            )
            trades.append(trade)
        
        logger.info(f"Retrieved {len(trades)} trades for {symbol} on {venue.value}")
        
        return [
            TradeResponse(
                venue=trade.venue,
                symbol=trade.symbol,
                trade_id=trade.trade_id,
                side=trade.side,
                price=trade.price,
                quantity=trade.quantity,
                notional_value=trade.notional_value,
                timestamp=trade.timestamp
            )
            for trade in trades
        ]
        
    except MarketDataError as e:
        logger.warning(f"Market data error: {e.message}")
        raise HTTPException(status_code=404, detail=e.message)
    except VenueConnectionError as e:
        logger.error(f"Venue connection error: {e.message}")
        raise HTTPException(status_code=503, detail=f"Venue {e.venue} is unavailable")
    except Exception as e:
        logger.error(f"Error getting trades for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get trade data")


@router.get("/klines/{symbol}", response_model=List[KlineResponse])
async def get_klines(
    symbol: str,
    venue: VenueEnum = Query(..., description="Venue to get klines from"),
    interval: IntervalType = Query(IntervalType.ONE_HOUR, description="Kline interval"),
    limit: int = Query(100, ge=1, le=1000, description="Number of klines to return"),
    start_time: Optional[datetime] = Query(None, description="Start time for klines"),
    end_time: Optional[datetime] = Query(None, description="End time for klines"),
    orchestrator=Depends(get_orchestrator)
):
    """
    Get candlestick/kline data for a symbol.
    
    Args:
        symbol: Trading symbol
        venue: Venue to query
        interval: Kline interval (1m, 5m, 1h, 1d, etc.)
        limit: Number of klines to return (max 1000)
        start_time: Start time for historical data
        end_time: End time for historical data
        
    Returns:
        List of candlestick data
    """
    try:
        # TODO: Get klines via orchestrator
        # klines = await orchestrator.get_klines(
        #     venue, symbol, interval, limit, start_time, end_time
        # )
        
        # Placeholder klines
        klines = []
        base_price = Decimal("51000")
        base_time = end_time or datetime.utcnow()
        
        # Calculate interval in minutes
        interval_minutes = {
            IntervalType.ONE_MINUTE: 1,
            IntervalType.FIVE_MINUTES: 5,
            IntervalType.FIFTEEN_MINUTES: 15,
            IntervalType.THIRTY_MINUTES: 30,
            IntervalType.ONE_HOUR: 60,
            IntervalType.FOUR_HOURS: 240,
            IntervalType.ONE_DAY: 1440,
            IntervalType.ONE_WEEK: 10080
        }.get(interval, 60)
        
        for i in range(min(limit, 100)):  # Generate up to 100 klines
            open_time = base_time - timedelta(minutes=interval_minutes * (i + 1))
            close_time = base_time - timedelta(minutes=interval_minutes * i)
            
            # Generate realistic OHLC data
            open_price = base_price + (Decimal(str(i % 20 - 10)) * Decimal("5"))
            price_range = Decimal("50")
            high_price = open_price + (price_range * Decimal("0.6"))
            low_price = open_price - (price_range * Decimal("0.4"))
            close_price = open_price + (Decimal(str((i + 5) % 20 - 10)) * Decimal("3"))
            
            kline = KlineResponse(
                symbol=symbol,
                venue=venue,
                interval=interval,
                open_time=open_time,
                close_time=close_time,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=Decimal("1000") + (Decimal(str(i % 50)) * Decimal("20")),
                trades_count=100 + (i % 50)
            )
            klines.append(kline)
        
        # Reverse to get chronological order
        klines.reverse()
        
        logger.info(f"Retrieved {len(klines)} klines for {symbol} on {venue.value}")
        return klines
        
    except MarketDataError as e:
        logger.warning(f"Market data error: {e.message}")
        raise HTTPException(status_code=404, detail=e.message)
    except VenueConnectionError as e:
        logger.error(f"Venue connection error: {e.message}")
        raise HTTPException(status_code=503, detail=f"Venue {e.venue} is unavailable")
    except Exception as e:
        logger.error(f"Error getting klines for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get kline data")


@router.get("/symbols", response_model=List[Dict[str, Any]])
async def get_all_symbols(
    venue: Optional[VenueEnum] = Query(None, description="Filter by venue"),
    orchestrator=Depends(get_orchestrator)
):
    """
    Get all available trading symbols across venues.
    
    Args:
        venue: Filter symbols by specific venue
        
    Returns:
        List of available symbols with metadata
    """
    try:
        # TODO: Get symbols via orchestrator
        # symbols = await orchestrator.get_all_symbols(venue)
        
        # Placeholder symbols
        base_symbols = [
            {"symbol": "BTC-PERP", "base": "BTC", "quote": "USD", "type": "perpetual"},
            {"symbol": "ETH-PERP", "base": "ETH", "quote": "USD", "type": "perpetual"},
            {"symbol": "SOL-PERP", "base": "SOL", "quote": "USD", "type": "perpetual"},
            {"symbol": "AVAX-PERP", "base": "AVAX", "quote": "USD", "type": "perpetual"},
            {"symbol": "MATIC-PERP", "base": "MATIC", "quote": "USD", "type": "perpetual"},
        ]
        
        venues_to_include = [venue] if venue else list(VenueEnum)
        symbols = []
        
        for sym in base_symbols:
            for ven in venues_to_include:
                symbol_info = {
                    **sym,
                    "venue": ven.value,
                    "status": "active",
                    "min_order_size": "0.001",
                    "max_order_size": "1000000",
                    "tick_size": "0.1" if sym["base"] == "BTC" else "0.01",
                    "maker_fee": "0.0002",
                    "taker_fee": "0.0005"
                }
                symbols.append(symbol_info)
        
        logger.info(f"Retrieved {len(symbols)} symbols")
        return symbols
        
    except Exception as e:
        logger.error(f"Error getting symbols: {e}")
        raise HTTPException(status_code=500, detail="Failed to get symbols")


@router.get("/funding-rates")
async def get_funding_rates(
    venue: Optional[VenueEnum] = Query(None, description="Filter by venue"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    orchestrator=Depends(get_orchestrator)
):
    """
    Get current funding rates for perpetual contracts.
    
    Args:
        venue: Filter by specific venue
        symbol: Filter by specific symbol
        
    Returns:
        Current funding rates and next funding times
    """
    try:
        # TODO: Get funding rates via orchestrator
        # funding_rates = await orchestrator.get_funding_rates(venue, symbol)
        
        # Placeholder funding rates
        symbols = [symbol] if symbol else ["BTC-PERP", "ETH-PERP", "SOL-PERP"]
        venues = [venue] if venue else list(VenueEnum)
        
        funding_rates = []
        for sym in symbols:
            for ven in venues:
                rate_info = {
                    "symbol": sym,
                    "venue": ven.value,
                    "funding_rate": "0.0001",
                    "funding_rate_percentage": "0.01",
                    "next_funding_time": (datetime.utcnow() + timedelta(hours=4)).isoformat(),
                    "funding_interval": "8h",
                    "predicted_rate": "0.00008"
                }
                funding_rates.append(rate_info)
        
        logger.info(f"Retrieved funding rates for {len(funding_rates)} contracts")
        return {"funding_rates": funding_rates}
        
    except Exception as e:
        logger.error(f"Error getting funding rates: {e}")
        raise HTTPException(status_code=500, detail="Failed to get funding rates")