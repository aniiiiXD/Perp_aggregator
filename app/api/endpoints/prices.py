"""
Price data endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Query
from app.models.market_data import AggregatedPrice, PriceData

router = APIRouter()


@router.get("/aggregated/{pair}", response_model=AggregatedPrice)
async def get_aggregated_price(pair: str, request: Request):
    """Get aggregated price for a trading pair"""
    try:
        ws_manager = request.app.state.ws_manager
        aggregated_price = await ws_manager.get_aggregated_price(pair.upper())
        
        if not aggregated_price:
            raise HTTPException(status_code=404, detail=f"Price data not found for pair {pair}")
            
        return aggregated_price
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching price data: {str(e)}")


@router.get("/pairs", response_model=List[str])
async def get_available_pairs(request: Request):
    """Get list of available trading pairs"""
    try:
        ws_manager = request.app.state.ws_manager
        stats = ws_manager.get_stats()
        
        return list(stats["pair_stats"].keys())
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching pairs: {str(e)}")


@router.get("/stats")
async def get_price_stats(request: Request):
    """Get price aggregation statistics"""
    try:
        ws_manager = request.app.state.ws_manager
        stats = ws_manager.get_stats()
        
        return {
            "total_pairs": len(stats["pair_stats"]),
            "active_connections": stats["active_connections"],
            "pair_details": stats["pair_stats"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@router.get("/history/{pair}")
async def get_price_history(
    pair: str,
    limit: int = Query(100, ge=1, le=1000),
    interval: str = Query("1m", regex="^(1m|5m|15m|1h|4h|1d)$")
):
    """Get historical price data for a trading pair"""
    # Placeholder for historical data - would integrate with database
    return {
        "pair": pair.upper(),
        "interval": interval,
        "data": [],
        "message": "Historical data endpoint - implementation pending"
    }