"""
Trading endpoints for order routing and execution
"""
import time
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Request
from app.models.market_data import OrderRequest, RouteResult, DEXType

router = APIRouter()


@router.post("/route", response_model=RouteResult)
async def calculate_route(order_request: OrderRequest, request: Request):
    """Calculate optimal routing for an order"""
    start_time = time.time()
    
    try:
        ws_manager = request.app.state.ws_manager
        aggregated_price = await ws_manager.get_aggregated_price(order_request.pair)
        
        if not aggregated_price:
            raise HTTPException(
                status_code=404, 
                detail=f"Price data not available for {order_request.pair}"
            )
        
        # Determine best execution based on order side
        if order_request.side.value == "long":
            # For long positions, we want the best ask (lowest price to buy)
            recommended_dex = aggregated_price.best_ask_dex
            expected_price = aggregated_price.best_ask
            
            # Find alternative
            alternative_dex = None
            alternative_price = None
            for source in aggregated_price.sources:
                if source.dex != recommended_dex:
                    alternative_dex = source.dex
                    alternative_price = source.ask
                    break
                    
        else:  # short
            # For short positions, we want the best bid (highest price to sell)
            recommended_dex = aggregated_price.best_bid_dex
            expected_price = aggregated_price.best_bid
            
            # Find alternative
            alternative_dex = None
            alternative_price = None
            for source in aggregated_price.sources:
                if source.dex != recommended_dex:
                    alternative_dex = source.dex
                    alternative_price = source.bid
                    break
        
        # Calculate estimated slippage (simplified)
        market_price = aggregated_price.sources[0].last_price
        estimated_slippage = abs(expected_price - market_price) / market_price
        
        calculation_time = (time.time() - start_time) * 1000
        
        return RouteResult(
            pair=order_request.pair,
            recommended_dex=recommended_dex,
            expected_price=expected_price,
            estimated_slippage=estimated_slippage,
            alternative_dex=alternative_dex,
            alternative_price=alternative_price,
            calculation_time_ms=calculation_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating route: {str(e)}")


@router.post("/simulate")
async def simulate_order(order_request: OrderRequest, request: Request):
    """Simulate order execution without actually placing it"""
    try:
        # Calculate routing first
        route_result = await calculate_route(order_request, request)
        
        # Simulate execution details
        execution_simulation = {
            "order": order_request.dict(),
            "routing": route_result.dict(),
            "simulation": {
                "estimated_fill_price": route_result.expected_price,
                "estimated_slippage": route_result.estimated_slippage,
                "estimated_fees": order_request.size * route_result.expected_price * Decimal("0.001"),  # 0.1% fee
                "total_cost": order_request.size * route_result.expected_price,
                "execution_dex": route_result.recommended_dex.value
            },
            "warnings": []
        }
        
        # Add warnings if slippage is high
        if route_result.estimated_slippage > order_request.slippage_tolerance:
            execution_simulation["warnings"].append(
                f"Estimated slippage ({route_result.estimated_slippage:.4f}) exceeds tolerance ({order_request.slippage_tolerance:.4f})"
            )
        
        return execution_simulation
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error simulating order: {str(e)}")


@router.get("/dex-status")
async def get_dex_status(request: Request):
    """Get status of DEX connections for trading"""
    try:
        dex_service = request.app.state.dex_service
        connection_status = dex_service.get_connection_status()
        
        return {
            "dex_connections": connection_status,
            "trading_available": all(connection_status.values()),
            "available_dexs": [dex for dex, status in connection_status.items() if status],
            "unavailable_dexs": [dex for dex, status in connection_status.items() if not status]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching DEX status: {str(e)}")


@router.post("/execute")
async def execute_order(order_request: OrderRequest, request: Request):
    """Execute an order (placeholder implementation)"""
    try:
        # This is a placeholder for actual order execution
        # In a real implementation, this would:
        # 1. Validate the order
        # 2. Calculate routing
        # 3. Submit to the selected DEX
        # 4. Monitor execution
        # 5. Return execution results
        
        route_result = await calculate_route(order_request, request)
        
        return {
            "status": "simulated",
            "message": "Order execution is not implemented yet - this is a simulation",
            "order_id": f"sim_{int(time.time())}",
            "routing": route_result.dict(),
            "execution_details": {
                "dex": route_result.recommended_dex.value,
                "estimated_price": route_result.expected_price,
                "size": order_request.size,
                "side": order_request.side.value
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing order: {str(e)}")