"""
Portfolio Aggregator

The Portfolio Aggregator consolidates data from all venue clients to provide
a unified view of the user's portfolio across multiple DEXs.

Key Features:
1. Position Aggregation - Combine positions from all venues
2. Balance Consolidation - Aggregate balances across venues
3. PnL Calculation - Calculate total and per-venue PnL
4. Risk Metrics - Compute portfolio-level risk metrics
5. Real-time Updates - Subscribe to venue events for live updates
6. Data Normalization - Ensure consistent data formats
7. Conflict Resolution - Handle data inconsistencies

Architecture:
- Observer pattern for real-time updates
- Strategy pattern for aggregation methods
- Cache layer for performance optimization
- Event-driven updates from venue clients

The aggregator maintains:
- Consolidated position view
- Total portfolio value
- Asset allocation breakdown
- Risk exposure metrics
- Performance statistics
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict
import uuid

from app.models.unified import Position, Balance, UnifiedOrder
from app.models.enums import VenueEnum, OrderStatus
from app.orchestrator.event_bus import EventBus
from app.core.events import PositionEvent, BalanceEvent, OrderEvent
from app.core.exceptions import TradingTerminalException

logger = logging.getLogger(__name__)


class PortfolioMetrics:
    """Portfolio-level metrics and calculations"""
    
    def __init__(self):
        self.total_value_usd = Decimal('0')
        self.total_pnl = Decimal('0')
        self.total_unrealized_pnl = Decimal('0')
        self.total_realized_pnl = Decimal('0')
        self.total_margin_used = Decimal('0')
        self.asset_allocation: Dict[str, Decimal] = {}
        self.venue_allocation: Dict[str, Decimal] = {}
        self.position_count = 0
        self.active_order_count = 0
        self.last_updated = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            'total_value_usd': str(self.total_value_usd),
            'total_pnl': str(self.total_pnl),
            'total_unrealized_pnl': str(self.total_unrealized_pnl),
            'total_realized_pnl': str(self.total_realized_pnl),
            'total_margin_used': str(self.total_margin_used),
            'asset_allocation': {k: str(v) for k, v in self.asset_allocation.items()},
            'venue_allocation': {k: str(v) for k, v in self.venue_allocation.items()},
            'position_count': self.position_count,
            'active_order_count': self.active_order_count,
            'last_updated': self.last_updated.isoformat()
        }


class PositionAggregator:
    """
    Aggregates positions across venues with conflict resolution.
    
    Handles:
    - Position consolidation by symbol
    - Cross-venue position netting
    - Conflict resolution for duplicate positions
    - Real-time position updates
    """
    
    def __init__(self):
        self.positions: Dict[str, Dict[VenueEnum, Position]] = defaultdict(dict)
        self.consolidated_positions: Dict[str, Position] = {}
        self.last_update: Dict[str, datetime] = {}
    
    def add_position(self, position: Position) -> None:
        """Add or update a position"""
        symbol = position.symbol
        venue = position.venue
        
        # Store venue-specific position
        self.positions[symbol][venue] = position
        self.last_update[f"{symbol}_{venue.value}"] = datetime.utcnow()
        
        # Recalculate consolidated position
        self._consolidate_position(symbol)
    
    def remove_position(self, symbol: str, venue: VenueEnum) -> None:
        """Remove a position"""
        if symbol in self.positions and venue in self.positions[symbol]:
            del self.positions[symbol][venue]
            
            if not self.positions[symbol]:
                # No positions left for this symbol
                del self.positions[symbol]
                if symbol in self.consolidated_positions:
                    del self.consolidated_positions[symbol]
            else:
                # Recalculate consolidated position
                self._consolidate_position(symbol)
    
    def _consolidate_position(self, symbol: str) -> None:
        """Consolidate positions for a symbol across venues"""
        if symbol not in self.positions:
            return
        
        venue_positions = self.positions[symbol]
        if not venue_positions:
            return
        
        # Calculate consolidated metrics
        total_size = Decimal('0')
        total_notional = Decimal('0')
        total_unrealized_pnl = Decimal('0')
        total_realized_pnl = Decimal('0')
        total_margin_used = Decimal('0')
        
        # Use the most recent position for base data
        latest_position = max(venue_positions.values(), key=lambda p: p.updated_at)
        
        for position in venue_positions.values():
            total_size += position.size
            total_notional += position.abs_size * position.mark_price
            total_unrealized_pnl += position.unrealized_pnl
            total_realized_pnl += position.realized_pnl
            total_margin_used += position.margin_used
        
        # Calculate weighted average entry price
        weighted_entry_price = Decimal('0')
        total_abs_size = Decimal('0')
        
        for position in venue_positions.values():
            if position.abs_size > 0:
                weighted_entry_price += position.entry_price * position.abs_size
                total_abs_size += position.abs_size
        
        if total_abs_size > 0:
            weighted_entry_price = weighted_entry_price / total_abs_size
        else:
            weighted_entry_price = latest_position.entry_price
        
        # Create consolidated position
        consolidated = Position(
            venue=VenueEnum.HYPERLIQUID,  # Use default venue for consolidated view
            symbol=symbol,
            size=total_size,
            entry_price=weighted_entry_price,
            mark_price=latest_position.mark_price,  # Use latest mark price
            unrealized_pnl=total_unrealized_pnl,
            realized_pnl=total_realized_pnl,
            margin_used=total_margin_used,
            side=latest_position.side,
            leverage=latest_position.leverage,
            asset_type=latest_position.asset_type,
            opened_at=min(p.opened_at for p in venue_positions.values() if p.opened_at),
            updated_at=datetime.utcnow(),
            venue_data={
                'consolidated': True,
                'venue_count': len(venue_positions),
                'venues': [v.value for v in venue_positions.keys()]
            }
        )
        
        self.consolidated_positions[symbol] = consolidated
    
    def get_all_positions(self) -> List[Position]:
        """Get all consolidated positions"""
        return list(self.consolidated_positions.values())
    
    def get_venue_positions(self, venue: VenueEnum) -> List[Position]:
        """Get positions for a specific venue"""
        positions = []
        for symbol_positions in self.positions.values():
            if venue in symbol_positions:
                positions.append(symbol_positions[venue])
        return positions
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get consolidated position for a symbol"""
        return self.consolidated_positions.get(symbol)


class BalanceAggregator:
    """
    Aggregates balances across venues.
    
    Handles:
    - Balance consolidation by asset
    - Cross-venue balance summation
    - USD value calculation
    - Real-time balance updates
    """
    
    def __init__(self):
        self.balances: Dict[str, Dict[VenueEnum, Balance]] = defaultdict(dict)
        self.consolidated_balances: Dict[str, Balance] = {}
        self.last_update: Dict[str, datetime] = {}
    
    def add_balance(self, balance: Balance) -> None:
        """Add or update a balance"""
        asset = balance.asset
        venue = balance.venue
        
        # Store venue-specific balance
        self.balances[asset][venue] = balance
        self.last_update[f"{asset}_{venue.value}"] = datetime.utcnow()
        
        # Recalculate consolidated balance
        self._consolidate_balance(asset)
    
    def remove_balance(self, asset: str, venue: VenueEnum) -> None:
        """Remove a balance"""
        if asset in self.balances and venue in self.balances[asset]:
            del self.balances[asset][venue]
            
            if not self.balances[asset]:
                # No balances left for this asset
                del self.balances[asset]
                if asset in self.consolidated_balances:
                    del self.consolidated_balances[asset]
            else:
                # Recalculate consolidated balance
                self._consolidate_balance(asset)
    
    def _consolidate_balance(self, asset: str) -> None:
        """Consolidate balances for an asset across venues"""
        if asset not in self.balances:
            return
        
        venue_balances = self.balances[asset]
        if not venue_balances:
            return
        
        # Sum balances across venues
        total_balance = Decimal('0')
        total_available = Decimal('0')
        total_locked = Decimal('0')
        total_usd_value = Decimal('0')
        
        latest_balance = max(venue_balances.values(), key=lambda b: b.updated_at)
        
        for balance in venue_balances.values():
            total_balance += balance.total
            total_available += balance.available
            total_locked += balance.locked
            if balance.usd_value:
                total_usd_value += balance.usd_value
        
        # Create consolidated balance
        consolidated = Balance(
            venue=VenueEnum.HYPERLIQUID,  # Use default venue for consolidated view
            asset=asset,
            total=total_balance,
            available=total_available,
            locked=total_locked,
            usd_value=total_usd_value if total_usd_value > 0 else None,
            updated_at=datetime.utcnow(),
            venue_data={
                'consolidated': True,
                'venue_count': len(venue_balances),
                'venues': [v.value for v in venue_balances.keys()]
            }
        )
        
        self.consolidated_balances[asset] = consolidated
    
    def get_all_balances(self) -> List[Balance]:
        """Get all consolidated balances"""
        return list(self.consolidated_balances.values())
    
    def get_venue_balances(self, venue: VenueEnum) -> List[Balance]:
        """Get balances for a specific venue"""
        balances = []
        for asset_balances in self.balances.values():
            if venue in asset_balances:
                balances.append(asset_balances[venue])
        return balances
    
    def get_balance(self, asset: str) -> Optional[Balance]:
        """Get consolidated balance for an asset"""
        return self.consolidated_balances.get(asset)


class PortfolioAggregator:
    """
    Main portfolio aggregator that consolidates data from all venues.
    
    The PortfolioAggregator serves as the central hub for portfolio data,
    providing a unified view of positions, balances, and metrics across
    all connected venues.
    
    Key Responsibilities:
    1. Data Aggregation - Consolidate positions and balances
    2. Real-time Updates - Subscribe to venue events
    3. Metrics Calculation - Compute portfolio-level metrics
    4. Risk Management - Track exposure and risk metrics
    5. Performance Monitoring - Calculate returns and performance
    6. Data Validation - Ensure data consistency and accuracy
    
    Event Handling:
    - Position updates from venue WebSockets
    - Balance changes from trading activity
    - Order status changes affecting portfolio
    - Market data updates for valuation
    """
    
    def __init__(self, venue_managers: Dict[VenueEnum, Any], event_bus: EventBus):
        self.venue_managers = venue_managers
        self.event_bus = event_bus
        
        # Aggregators
        self.position_aggregator = PositionAggregator()
        self.balance_aggregator = BalanceAggregator()
        
        # Metrics and state
        self.metrics = PortfolioMetrics()
        self.active_orders: Dict[str, UnifiedOrder] = {}
        
        # Event subscriptions
        self._subscription_tasks: List[asyncio.Task] = []
        self._is_running = False
        
        # Update tracking
        self._last_full_update = None
        self._update_interval = 30  # seconds
        self._force_update_event = asyncio.Event()
    
    async def initialize(self) -> None:
        """
        Initialize the portfolio aggregator.
        
        Sets up:
        - Event subscriptions for real-time updates
        - Initial data loading from all venues
        - Background update tasks
        - Metrics calculation
        """
        try:
            logger.info("Initializing Portfolio Aggregator...")
            
            # Subscribe to relevant events
            await self._setup_event_subscriptions()
            
            # Load initial data
            await self._load_initial_data()
            
            # Start background tasks
            self._is_running = True
            self._subscription_tasks.append(
                asyncio.create_task(self._periodic_update_task())
            )
            self._subscription_tasks.append(
                asyncio.create_task(self._metrics_calculation_task())
            )
            
            logger.info("Portfolio Aggregator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Portfolio Aggregator: {e}")
            raise TradingTerminalException(f"Portfolio aggregator initialization failed: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the portfolio aggregator"""
        try:
            logger.info("Shutting down Portfolio Aggregator...")
            
            self._is_running = False
            
            # Cancel background tasks
            for task in self._subscription_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # Unsubscribe from events
            await self._cleanup_event_subscriptions()
            
            logger.info("Portfolio Aggregator shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during portfolio aggregator shutdown: {e}")
    
    # Data Access Methods
    async def get_all_positions(self) -> List[Position]:
        """Get all consolidated positions"""
        return self.position_aggregator.get_all_positions()
    
    async def get_venue_positions(self, venue: VenueEnum) -> List[Position]:
        """Get positions for a specific venue"""
        return self.position_aggregator.get_venue_positions(venue)
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get consolidated position for a symbol"""
        return self.position_aggregator.get_position(symbol)
    
    async def get_all_balances(self) -> List[Balance]:
        """Get all consolidated balances"""
        return self.balance_aggregator.get_all_balances()
    
    async def get_venue_balances(self, venue: VenueEnum) -> List[Balance]:
        """Get balances for a specific venue"""
        return self.balance_aggregator.get_venue_balances(venue)
    
    async def get_balance(self, asset: str) -> Optional[Balance]:
        """Get consolidated balance for an asset"""
        return self.balance_aggregator.get_balance(asset)
    
    async def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Get current portfolio metrics"""
        await self._calculate_metrics()
        return self.metrics
    
    async def get_active_orders(self) -> List[UnifiedOrder]:
        """Get all active orders across venues"""
        return list(self.active_orders.values())
    
    # Event Handling
    async def _setup_event_subscriptions(self) -> None:
        """Set up event subscriptions for real-time updates"""
        try:
            # Subscribe to position updates
            await self.event_bus.subscribe_to_positions(self._handle_position_event)
            
            # Subscribe to balance updates
            await self.event_bus.subscribe(
                "balances",
                self._handle_balance_event
            )
            
            # Subscribe to order updates
            await self.event_bus.subscribe_to_orders(self._handle_order_event)
            
            logger.info("Event subscriptions set up successfully")
            
        except Exception as e:
            logger.error(f"Failed to set up event subscriptions: {e}")
            raise
    
    async def _cleanup_event_subscriptions(self) -> None:
        """Clean up event subscriptions"""
        try:
            # Unsubscribe from all channels
            await self.event_bus.unsubscribe("positions")
            await self.event_bus.unsubscribe("balances")
            await self.event_bus.unsubscribe("orders")
            
        except Exception as e:
            logger.error(f"Error cleaning up event subscriptions: {e}")
    
    async def _handle_position_event(self, event: PositionEvent) -> None:
        """Handle position update events"""
        try:
            # Create Position object from event data
            position = Position(
                venue=event.venue,
                symbol=event.symbol,
                size=event.position_data.size,
                entry_price=event.position_data.entry_price,
                mark_price=event.position_data.mark_price,
                unrealized_pnl=event.position_data.unrealized_pnl,
                realized_pnl=event.position_data.realized_pnl,
                margin_used=event.position_data.margin_used,
                updated_at=event.timestamp
            )
            
            # Update position aggregator
            if position.size == 0:
                self.position_aggregator.remove_position(position.symbol, position.venue)
            else:
                self.position_aggregator.add_position(position)
            
            # Trigger metrics recalculation
            self._force_update_event.set()
            
            logger.debug(f"Processed position event for {event.symbol} on {event.venue}")
            
        except Exception as e:
            logger.error(f"Error handling position event: {e}")
    
    async def _handle_balance_event(self, event_data: Dict[str, Any]) -> None:
        """Handle balance update events"""
        try:
            # Deserialize balance event
            # This is a placeholder - actual implementation would deserialize properly
            venue = VenueEnum(event_data.get('venue'))
            asset = event_data.get('asset')
            
            # Create Balance object
            balance = Balance(
                venue=venue,
                asset=asset,
                total=Decimal(str(event_data.get('total', '0'))),
                available=Decimal(str(event_data.get('available', '0'))),
                locked=Decimal(str(event_data.get('locked', '0'))),
                updated_at=datetime.utcnow()
            )
            
            # Update balance aggregator
            self.balance_aggregator.add_balance(balance)
            
            # Trigger metrics recalculation
            self._force_update_event.set()
            
            logger.debug(f"Processed balance event for {asset} on {venue}")
            
        except Exception as e:
            logger.error(f"Error handling balance event: {e}")
    
    async def _handle_order_event(self, event: OrderEvent) -> None:
        """Handle order update events"""
        try:
            # Update active orders tracking
            if event.status in [OrderStatus.PENDING, OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]:
                # Create or update active order
                order = UnifiedOrder(
                    symbol=event.symbol,
                    side=event.side,
                    order_type=event.order_type,
                    quantity=event.quantity,
                    price=event.price,
                    venue=event.venue,
                    client_order_id=event.client_order_id,
                    order_id=event.order_id,
                    status=event.status,
                    filled_quantity=event.filled_quantity,
                    average_fill_price=event.average_fill_price,
                    fee=event.fee,
                    updated_at=event.timestamp
                )
                self.active_orders[event.client_order_id] = order
            else:
                # Remove completed orders
                if event.client_order_id in self.active_orders:
                    del self.active_orders[event.client_order_id]
            
            # Update metrics
            self.metrics.active_order_count = len(self.active_orders)
            
            logger.debug(f"Processed order event for {event.client_order_id}")
            
        except Exception as e:
            logger.error(f"Error handling order event: {e}")
    
    # Data Loading and Updates
    async def _load_initial_data(self) -> None:
        """Load initial data from all venues"""
        try:
            logger.info("Loading initial portfolio data...")
            
            # Load positions and balances from all venues
            for venue, manager in self.venue_managers.items():
                if manager.is_healthy:
                    try:
                        # Load positions
                        positions = await manager.client.get_positions()
                        for position in positions:
                            self.position_aggregator.add_position(position)
                        
                        # Load balances
                        balances = await manager.client.get_balances()
                        for balance in balances:
                            self.balance_aggregator.add_balance(balance)
                        
                        logger.info(f"Loaded data from {venue}: {len(positions)} positions, {len(balances)} balances")
                        
                    except Exception as e:
                        logger.warning(f"Failed to load initial data from {venue}: {e}")
            
            # Calculate initial metrics
            await self._calculate_metrics()
            self._last_full_update = datetime.utcnow()
            
            logger.info("Initial portfolio data loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading initial data: {e}")
            raise
    
    async def _periodic_update_task(self) -> None:
        """Periodic task to refresh data from venues"""
        while self._is_running:
            try:
                # Wait for update interval or force update event
                try:
                    await asyncio.wait_for(
                        self._force_update_event.wait(),
                        timeout=self._update_interval
                    )
                    self._force_update_event.clear()
                except asyncio.TimeoutError:
                    pass  # Regular periodic update
                
                # Refresh data from venues
                await self._refresh_venue_data()
                
            except Exception as e:
                logger.error(f"Error in periodic update task: {e}")
                await asyncio.sleep(self._update_interval)
    
    async def _refresh_venue_data(self) -> None:
        """Refresh data from all healthy venues"""
        try:
            for venue, manager in self.venue_managers.items():
                if manager.is_healthy:
                    try:
                        # Refresh positions
                        positions = await manager.client.get_positions()
                        
                        # Update position aggregator
                        current_symbols = set()
                        for position in positions:
                            self.position_aggregator.add_position(position)
                            current_symbols.add(position.symbol)
                        
                        # Remove positions that no longer exist
                        existing_symbols = set(
                            symbol for symbol, venue_positions in self.position_aggregator.positions.items()
                            if venue in venue_positions
                        )
                        
                        for symbol in existing_symbols - current_symbols:
                            self.position_aggregator.remove_position(symbol, venue)
                        
                    except Exception as e:
                        logger.warning(f"Failed to refresh data from {venue}: {e}")
            
            self._last_full_update = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error refreshing venue data: {e}")
    
    async def _metrics_calculation_task(self) -> None:
        """Background task to calculate portfolio metrics"""
        while self._is_running:
            try:
                await self._calculate_metrics()
                await asyncio.sleep(10)  # Calculate metrics every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in metrics calculation task: {e}")
                await asyncio.sleep(10)
    
    async def _calculate_metrics(self) -> None:
        """Calculate portfolio-level metrics"""
        try:
            # Reset metrics
            self.metrics = PortfolioMetrics()
            
            # Calculate position metrics
            positions = self.position_aggregator.get_all_positions()
            for position in positions:
                self.metrics.total_unrealized_pnl += position.unrealized_pnl
                self.metrics.total_realized_pnl += position.realized_pnl
                self.metrics.total_margin_used += position.margin_used
                self.metrics.total_value_usd += position.notional_value
                
                # Asset allocation
                asset = position.symbol.split('-')[0] if '-' in position.symbol else position.symbol
                self.metrics.asset_allocation[asset] = \
                    self.metrics.asset_allocation.get(asset, Decimal('0')) + position.notional_value
            
            # Calculate venue allocation
            for venue, manager in self.venue_managers.items():
                venue_positions = self.position_aggregator.get_venue_positions(venue)
                venue_value = sum(pos.notional_value for pos in venue_positions)
                if venue_value > 0:
                    self.metrics.venue_allocation[venue.value] = venue_value
            
            # Calculate totals
            self.metrics.total_pnl = self.metrics.total_unrealized_pnl + self.metrics.total_realized_pnl
            self.metrics.position_count = len(positions)
            self.metrics.active_order_count = len(self.active_orders)
            self.metrics.last_updated = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
    
    # Utility Methods
    def health_check(self) -> bool:
        """Check portfolio aggregator health"""
        return (
            self._is_running and
            self._last_full_update is not None and
            (datetime.utcnow() - self._last_full_update).total_seconds() < 300  # 5 minutes
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get portfolio summary"""
        return {
            'total_positions': len(self.position_aggregator.get_all_positions()),
            'total_balances': len(self.balance_aggregator.get_all_balances()),
            'active_orders': len(self.active_orders),
            'metrics': self.metrics.to_dict(),
            'last_update': self._last_full_update.isoformat() if self._last_full_update else None,
            'health_status': self.health_check()
        }