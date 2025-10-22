"""
Main Orchestrator

The Main Orchestrator is the central coordinator of the trading terminal,
responsible for routing requests to appropriate venue clients and managing
the overall system state.

Key Responsibilities:
1. Request Routing - Direct trading requests to the correct venue client
2. Venue Management - Initialize, monitor, and manage venue connections
3. Load Balancing - Distribute requests across healthy venues
4. Circuit Breaking - Prevent cascading failures when venues are down
5. State Coordination - Maintain consistent state across all components
6. Error Handling - Provide graceful degradation and error recovery
7. Performance Monitoring - Track latency, success rates, and throughput

Architecture:
- Factory pattern for venue client creation
- Strategy pattern for routing decisions
- Observer pattern for state change notifications
- Circuit breaker pattern for fault tolerance
- Command pattern for request processing

The orchestrator maintains:
- Registry of active venue clients
- Health status of each venue
- Performance metrics and statistics
- Circuit breaker states
- Request routing rules
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from app.core.config import settings
from app.core.exceptions import (
    TradingTerminalException, VenueConnectionError, CircuitBreakerError,
    OrderValidationError, OrderNotFoundError
)
from app.models.unified import UnifiedOrder, Position, Balance, MarketData, VenueStatus
from app.models.enums import VenueEnum, OrderStatus, ConnectionStatus
from app.orchestrator.event_bus import EventBus
from app.orchestrator.portfolio_aggregator import PortfolioAggregator
from app.clients.base_client import BaseClient
from app.core.events import OrderEvent, SystemEvent

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Circuit breaker implementation for venue fault tolerance.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failures exceeded threshold, requests blocked
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerError("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        return (datetime.utcnow() - self.last_failure_time).total_seconds() > self.timeout
    
    def _on_success(self):
        """Handle successful request"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed request"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class VenueManager:
    """
    Manages individual venue clients and their health status.
    
    Responsibilities:
    - Initialize venue clients
    - Monitor venue health
    - Handle venue reconnection
    - Track performance metrics
    """
    
    def __init__(self, venue: VenueEnum, client: BaseClient, event_bus: EventBus):
        self.venue = venue
        self.client = client
        self.event_bus = event_bus
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            timeout=settings.CIRCUIT_BREAKER_TIMEOUT
        )
        
        # Status tracking
        self.status = VenueStatus(
            venue=venue,
            connection_status=ConnectionStatus.DISCONNECTED,
            api_status=ConnectionStatus.DISCONNECTED,
            websocket_status=ConnectionStatus.DISCONNECTED
        )
        
        # Performance metrics
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_latency = 0.0
        self.last_request_time = None
        
        # Health monitoring
        self._health_check_task = None
        self._is_monitoring = False
    
    async def initialize(self) -> bool:
        """Initialize venue client and start monitoring"""
        try:
            # Initialize client
            await self.client.initialize()
            
            # Update status
            self.status.connection_status = ConnectionStatus.CONNECTED
            self.status.api_status = ConnectionStatus.CONNECTED
            self.status.last_success = datetime.utcnow()
            
            # Start health monitoring
            self._is_monitoring = True
            self._health_check_task = asyncio.create_task(self._health_monitor())
            
            logger.info(f"Venue {self.venue} initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize venue {self.venue}: {e}")
            self.status.connection_status = ConnectionStatus.ERROR
            self.status.last_error = str(e)
            self.status.last_error_time = datetime.utcnow()
            return False
    
    async def shutdown(self) -> None:
        """Shutdown venue client and stop monitoring"""
        try:
            self._is_monitoring = False
            
            if self._health_check_task and not self._health_check_task.done():
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            if self.client:
                await self.client.shutdown()
            
            self.status.connection_status = ConnectionStatus.DISCONNECTED
            logger.info(f"Venue {self.venue} shutdown completed")
            
        except Exception as e:
            logger.error(f"Error shutting down venue {self.venue}: {e}")
    
    async def execute_with_circuit_breaker(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker and metrics tracking"""
        start_time = datetime.utcnow()
        self.request_count += 1
        self.last_request_time = start_time
        
        try:
            result = await self.circuit_breaker.call(func, *args, **kwargs)
            
            # Update success metrics
            self.success_count += 1
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.total_latency += latency
            self.status.latency_ms = self.total_latency / self.success_count
            self.status.success_rate = (self.success_count / self.request_count) * 100
            
            return result
            
        except Exception as e:
            # Update error metrics
            self.error_count += 1
            self.status.error_count = self.error_count
            self.status.last_error = str(e)
            self.status.last_error_time = datetime.utcnow()
            self.status.success_rate = (self.success_count / self.request_count) * 100
            
            raise
    
    async def _health_monitor(self) -> None:
        """Background task to monitor venue health"""
        while self._is_monitoring:
            try:
                # Check API health
                api_healthy = await self.client.health_check()
                self.status.api_status = ConnectionStatus.CONNECTED if api_healthy else ConnectionStatus.ERROR
                
                # Check WebSocket health
                ws_healthy = await self.client.websocket_health_check()
                self.status.websocket_status = ConnectionStatus.CONNECTED if ws_healthy else ConnectionStatus.ERROR
                
                # Update overall status
                if api_healthy and ws_healthy:
                    self.status.connection_status = ConnectionStatus.CONNECTED
                    self.status.last_success = datetime.utcnow()
                else:
                    self.status.connection_status = ConnectionStatus.ERROR
                
                self.status.last_check = datetime.utcnow()
                
                # Publish status update
                await self._publish_status_update()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Health monitor error for {self.venue}: {e}")
                self.status.connection_status = ConnectionStatus.ERROR
                self.status.last_error = str(e)
                await asyncio.sleep(30)
    
    async def _publish_status_update(self) -> None:
        """Publish venue status update to event bus"""
        try:
            event = SystemEvent(
                event_id=str(uuid.uuid4()),
                event_type="venue_status_update",
                timestamp=datetime.utcnow(),
                venue=self.venue,
                component=f"venue_{self.venue.value}",
                status=self.status.connection_status.value,
                message=f"Venue {self.venue} status update",
                data=self.status.to_dict()
            )
            await self.event_bus.publish_system_event(event)
        except Exception as e:
            logger.error(f"Failed to publish status update for {self.venue}: {e}")
    
    @property
    def is_healthy(self) -> bool:
        """Check if venue is healthy and available"""
        return (
            self.status.connection_status == ConnectionStatus.CONNECTED and
            self.circuit_breaker.state != "OPEN"
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get venue performance metrics"""
        return {
            'venue': self.venue.value,
            'request_count': self.request_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': self.status.success_rate,
            'average_latency_ms': self.status.latency_ms,
            'circuit_breaker_state': self.circuit_breaker.state,
            'last_request_time': self.last_request_time.isoformat() if self.last_request_time else None
        }


class MainOrchestrator:
    """
    Central coordinator for the trading terminal.
    
    The MainOrchestrator serves as the primary entry point for all trading
    operations, routing requests to appropriate venue clients while providing
    fault tolerance, load balancing, and performance monitoring.
    
    Key Features:
    1. Venue Management - Initialize and manage all venue clients
    2. Request Routing - Route requests based on venue selection and health
    3. Load Balancing - Distribute load across healthy venues
    4. Circuit Breaking - Prevent cascading failures
    5. State Management - Maintain consistent system state
    6. Event Coordination - Publish system events and status updates
    7. Performance Monitoring - Track metrics and health across all venues
    
    Request Flow:
    1. Validate request parameters
    2. Select target venue (explicit or load-balanced)
    3. Check venue health and circuit breaker status
    4. Route request to venue client
    5. Handle response and update metrics
    6. Publish relevant events
    7. Return unified response
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.venue_managers: Dict[VenueEnum, VenueManager] = {}
        self.portfolio_aggregator: Optional[PortfolioAggregator] = None
        self._is_initialized = False
        self._shutdown_event = asyncio.Event()
        
        # Request routing configuration
        self._default_venue = VenueEnum.HYPERLIQUID  # Default venue for load balancing
        self._load_balancing_enabled = True
        self._routing_rules: Dict[str, VenueEnum] = {}  # Symbol-specific routing
        
        # System metrics
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._start_time = datetime.utcnow()
    
    async def initialize(self) -> None:
        """
        Initialize the orchestrator and all venue clients.
        
        Initialization process:
        1. Create venue client instances
        2. Initialize each venue manager
        3. Set up portfolio aggregator
        4. Start background monitoring tasks
        5. Publish system startup event
        """
        try:
            logger.info("Initializing Main Orchestrator...")
            
            # Initialize venue managers
            await self._initialize_venues()
            
            # Initialize portfolio aggregator
            self.portfolio_aggregator = PortfolioAggregator(
                venue_managers=self.venue_managers,
                event_bus=self.event_bus
            )
            await self.portfolio_aggregator.initialize()
            
            # Start background tasks
            asyncio.create_task(self._system_monitor())
            
            self._is_initialized = True
            
            # Publish startup event
            await self._publish_system_event("orchestrator_started", "Main orchestrator initialized successfully")
            
            logger.info("Main Orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Main Orchestrator: {e}")
            raise TradingTerminalException(f"Orchestrator initialization failed: {e}")
    
    async def shutdown(self) -> None:
        """
        Gracefully shutdown the orchestrator and all components.
        
        Shutdown process:
        1. Signal shutdown to all components
        2. Wait for active requests to complete
        3. Shutdown venue managers
        4. Shutdown portfolio aggregator
        5. Publish system shutdown event
        """
        try:
            logger.info("Shutting down Main Orchestrator...")
            
            self._shutdown_event.set()
            
            # Shutdown portfolio aggregator
            if self.portfolio_aggregator:
                await self.portfolio_aggregator.shutdown()
            
            # Shutdown venue managers
            for venue_manager in self.venue_managers.values():
                await venue_manager.shutdown()
            
            # Publish shutdown event
            await self._publish_system_event("orchestrator_shutdown", "Main orchestrator shutdown completed")
            
            self._is_initialized = False
            logger.info("Main Orchestrator shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during orchestrator shutdown: {e}")
    
    # Trading Operations
    async def place_order(self, order: UnifiedOrder) -> UnifiedOrder:
        """
        Place an order through the appropriate venue client.
        
        Process:
        1. Validate order parameters
        2. Select target venue
        3. Check venue health
        4. Route to venue client
        5. Update order with response
        6. Publish order event
        7. Return updated order
        """
        try:
            self._total_requests += 1
            
            # Validate order
            self._validate_order(order)
            
            # Select venue
            venue = order.venue
            venue_manager = self._get_venue_manager(venue)
            
            # Execute order placement with circuit breaker
            result = await venue_manager.execute_with_circuit_breaker(
                venue_manager.client.place_order,
                order
            )
            
            # Update metrics
            self._successful_requests += 1
            
            # Publish order event
            await self._publish_order_event(result, "order_placed")
            
            logger.info(f"Order placed successfully: {result.client_order_id}")
            return result
            
        except Exception as e:
            self._failed_requests += 1
            logger.error(f"Failed to place order: {e}")
            
            # Update order status
            order.status = OrderStatus.REJECTED
            order.updated_at = datetime.utcnow()
            
            # Publish failure event
            await self._publish_order_event(order, "order_rejected", str(e))
            
            raise
    
    async def cancel_order(self, venue: VenueEnum, order_id: str) -> bool:
        """
        Cancel an order on the specified venue.
        
        Args:
            venue: Target venue
            order_id: Order ID to cancel
            
        Returns:
            bool: True if cancellation successful
        """
        try:
            self._total_requests += 1
            
            venue_manager = self._get_venue_manager(venue)
            
            # Execute cancellation with circuit breaker
            result = await venue_manager.execute_with_circuit_breaker(
                venue_manager.client.cancel_order,
                order_id
            )
            
            self._successful_requests += 1
            
            # Publish cancellation event
            await self._publish_system_event(
                "order_cancelled",
                f"Order {order_id} cancelled on {venue.value}"
            )
            
            logger.info(f"Order cancelled successfully: {order_id}")
            return result
            
        except Exception as e:
            self._failed_requests += 1
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise
    
    async def get_positions(self, venue: Optional[VenueEnum] = None) -> List[Position]:
        """
        Get positions from specified venue or all venues.
        
        Args:
            venue: Specific venue (all venues if None)
            
        Returns:
            List of positions
        """
        try:
            if venue:
                # Get positions from specific venue
                venue_manager = self._get_venue_manager(venue)
                return await venue_manager.execute_with_circuit_breaker(
                    venue_manager.client.get_positions
                )
            else:
                # Get positions from all venues via portfolio aggregator
                return await self.portfolio_aggregator.get_all_positions()
                
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise
    
    async def get_balances(self, venue: Optional[VenueEnum] = None) -> List[Balance]:
        """
        Get balances from specified venue or all venues.
        
        Args:
            venue: Specific venue (all venues if None)
            
        Returns:
            List of balances
        """
        try:
            if venue:
                # Get balances from specific venue
                venue_manager = self._get_venue_manager(venue)
                return await venue_manager.execute_with_circuit_breaker(
                    venue_manager.client.get_balances
                )
            else:
                # Get balances from all venues via portfolio aggregator
                return await self.portfolio_aggregator.get_all_balances()
                
        except Exception as e:
            logger.error(f"Failed to get balances: {e}")
            raise
    
    async def get_market_data(self, venue: VenueEnum, symbol: str) -> MarketData:
        """
        Get market data for a symbol from specified venue.
        
        Args:
            venue: Target venue
            symbol: Trading symbol
            
        Returns:
            Market data
        """
        try:
            venue_manager = self._get_venue_manager(venue)
            return await venue_manager.execute_with_circuit_breaker(
                venue_manager.client.get_market_data,
                symbol
            )
            
        except Exception as e:
            logger.error(f"Failed to get market data for {symbol}: {e}")
            raise
    
    # Venue Management
    async def _initialize_venues(self) -> None:
        """Initialize all venue managers"""
        # Note: In a real implementation, you would import and instantiate
        # the actual venue client classes here
        
        venues_to_initialize = [
            VenueEnum.HYPERLIQUID,
            VenueEnum.LIGHTER,
            VenueEnum.TRADEXYZ
        ]
        
        for venue in venues_to_initialize:
            try:
                # Create venue client (placeholder - would use actual client classes)
                client = self._create_venue_client(venue)
                
                # Create venue manager
                venue_manager = VenueManager(venue, client, self.event_bus)
                
                # Initialize venue
                if await venue_manager.initialize():
                    self.venue_managers[venue] = venue_manager
                    logger.info(f"Venue {venue} initialized successfully")
                else:
                    logger.warning(f"Failed to initialize venue {venue}")
                    
            except Exception as e:
                logger.error(f"Error initializing venue {venue}: {e}")
    
    def _create_venue_client(self, venue: VenueEnum) -> BaseClient:
        """Create venue-specific client instance"""
        # Placeholder implementation
        # In real implementation, this would return actual venue client instances
        from app.clients.base_client import BaseClient
        return BaseClient()  # This would be venue-specific client
    
    def _get_venue_manager(self, venue: VenueEnum) -> VenueManager:
        """Get venue manager for specified venue"""
        if venue not in self.venue_managers:
            raise VenueConnectionError(venue.value, "Venue not available")
        
        venue_manager = self.venue_managers[venue]
        if not venue_manager.is_healthy:
            raise VenueConnectionError(venue.value, "Venue is unhealthy")
        
        return venue_manager
    
    def _validate_order(self, order: UnifiedOrder) -> None:
        """Validate order parameters"""
        if not order.symbol:
            raise OrderValidationError("symbol", "Symbol is required")
        
        if order.quantity <= 0:
            raise OrderValidationError("quantity", "Quantity must be positive")
        
        if order.venue not in self.venue_managers:
            raise OrderValidationError("venue", f"Venue {order.venue} not supported")
    
    # Event Publishing
    async def _publish_order_event(self, order: UnifiedOrder, event_type: str, error: str = None) -> None:
        """Publish order-related event"""
        try:
            event = OrderEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                timestamp=datetime.utcnow(),
                venue=order.venue,
                order_id=order.order_id or "",
                client_order_id=order.client_order_id,
                status=order.status,
                symbol=order.symbol,
                side=order.side.value,
                order_type=order.order_type.value,
                quantity=order.quantity,
                price=order.price,
                filled_quantity=order.filled_quantity,
                average_fill_price=order.average_fill_price,
                fee=order.fee,
                error_message=error
            )
            await self.event_bus.publish_order_event(event)
        except Exception as e:
            logger.error(f"Failed to publish order event: {e}")
    
    async def _publish_system_event(self, event_type: str, message: str, data: Dict[str, Any] = None) -> None:
        """Publish system-level event"""
        try:
            event = SystemEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                timestamp=datetime.utcnow(),
                venue=VenueEnum.HYPERLIQUID,  # System events use default venue
                component="main_orchestrator",
                status="info",
                message=message,
                data=data
            )
            await self.event_bus.publish_system_event(event)
        except Exception as e:
            logger.error(f"Failed to publish system event: {e}")
    
    # Background Tasks
    async def _system_monitor(self) -> None:
        """Monitor overall system health and performance"""
        while not self._shutdown_event.is_set():
            try:
                # Collect system metrics
                metrics = self.get_system_metrics()
                
                # Log metrics periodically
                logger.info(f"System metrics: {metrics}")
                
                # Check for unhealthy venues
                unhealthy_venues = [
                    venue for venue, manager in self.venue_managers.items()
                    if not manager.is_healthy
                ]
                
                if unhealthy_venues:
                    logger.warning(f"Unhealthy venues detected: {unhealthy_venues}")
                    await self._publish_system_event(
                        "unhealthy_venues",
                        f"Unhealthy venues: {unhealthy_venues}",
                        {"venues": [v.value for v in unhealthy_venues]}
                    )
                
                await asyncio.sleep(60)  # Monitor every minute
                
            except Exception as e:
                logger.error(f"System monitor error: {e}")
                await asyncio.sleep(60)
    
    # Status and Metrics
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        uptime = (datetime.utcnow() - self._start_time).total_seconds()
        
        venue_metrics = {}
        for venue, manager in self.venue_managers.items():
            venue_metrics[venue.value] = manager.get_metrics()
        
        return {
            'uptime_seconds': uptime,
            'total_requests': self._total_requests,
            'successful_requests': self._successful_requests,
            'failed_requests': self._failed_requests,
            'success_rate': (self._successful_requests / max(self._total_requests, 1)) * 100,
            'active_venues': len([m for m in self.venue_managers.values() if m.is_healthy]),
            'total_venues': len(self.venue_managers),
            'venue_metrics': venue_metrics,
            'portfolio_aggregator_healthy': self.portfolio_aggregator.health_check() if self.portfolio_aggregator else False
        }
    
    def get_venue_status(self, venue: VenueEnum) -> Optional[VenueStatus]:
        """Get status for specific venue"""
        if venue in self.venue_managers:
            return self.venue_managers[venue].status
        return None
    
    def get_all_venue_statuses(self) -> Dict[str, VenueStatus]:
        """Get status for all venues"""
        return {
            venue.value: manager.status
            for venue, manager in self.venue_managers.items()
        }
    
    def health_check(self) -> bool:
        """Check overall orchestrator health"""
        if not self._is_initialized:
            return False
        
        # Check if at least one venue is healthy
        healthy_venues = sum(1 for manager in self.venue_managers.values() if manager.is_healthy)
        
        return (
            healthy_venues > 0 and
            (self.portfolio_aggregator.health_check() if self.portfolio_aggregator else True)
        )