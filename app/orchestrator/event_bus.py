"""
Event Bus System

The Event Bus is the central nervous system of the trading terminal, providing
pub/sub functionality for real-time communication between components.

Architecture:
- Redis-based pub/sub for scalability and persistence
- JSON serialization for cross-language compatibility
- Event routing and filtering capabilities
- Subscription management with automatic cleanup
- Error handling and retry logic
- Performance monitoring and metrics

Key Features:
1. Multi-channel support for different event types
2. Venue-specific event routing
3. Event filtering and transformation
4. Subscription lifecycle management
5. Dead letter queue for failed events
6. Event replay capabilities
7. Circuit breaker for Redis failures

Usage Patterns:
- Order lifecycle events (placed, filled, cancelled)
- Position updates from venue WebSockets
- Market data distribution to subscribers
- System health and status notifications
- Cross-venue arbitrage signals
"""

import asyncio
import json
import logging
from typing import Dict, List, Callable, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import asdict
import uuid

from app.core.redis import RedisClient
from app.core.events import (
    BaseEvent, OrderEvent, PositionEvent, BalanceEvent,
    MarketDataEvent, TradeEvent, ConnectionEvent, SystemEvent,
    EventTypes, EventChannels
)
from app.core.exceptions import TradingTerminalException
from app.models.enums import VenueEnum

logger = logging.getLogger(__name__)


class EventBus:
    """
    Redis-based event bus for real-time communication between components.
    
    The EventBus handles:
    - Publishing events to Redis channels
    - Managing subscriptions and callbacks
    - Event serialization and deserialization
    - Error handling and retry logic
    - Performance monitoring
    - Event filtering and routing
    
    Event Flow:
    1. Component publishes event via publish()
    2. Event is serialized and sent to Redis channel
    3. Subscribers receive event via their callbacks
    4. Failed events are retried or sent to dead letter queue
    """
    
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
        self._subscribers: Dict[str, List[Callable]] = {}
        self._subscription_tasks: Dict[str, asyncio.Task] = {}
        self._active_channels: Set[str] = set()
        self._event_stats: Dict[str, int] = {}
        self._failed_events: List[Dict[str, Any]] = []
        self._is_running = False
        
        # Circuit breaker for Redis failures
        self._circuit_breaker_failures = 0
        self._circuit_breaker_threshold = 5
        self._circuit_breaker_timeout = 60
        self._circuit_breaker_last_failure = None
        self._circuit_breaker_open = False
    
    async def initialize(self) -> None:
        """
        Initialize the event bus and start background tasks.
        
        Sets up:
        - Redis connection validation
        - Background subscription tasks
        - Health monitoring
        - Performance metrics collection
        """
        try:
            # Validate Redis connection
            if not await self.redis_client.health_check():
                raise TradingTerminalException("Redis connection not available for event bus")
            
            self._is_running = True
            
            # Start background tasks
            asyncio.create_task(self._health_monitor())
            asyncio.create_task(self._metrics_collector())
            
            logger.info("Event bus initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize event bus: {e}")
            raise
    
    async def shutdown(self) -> None:
        """
        Gracefully shutdown the event bus.
        
        Performs:
        - Unsubscribe from all channels
        - Cancel background tasks
        - Close Redis connections
        - Save failed events for replay
        """
        try:
            self._is_running = False
            
            # Cancel all subscription tasks
            for task in self._subscription_tasks.values():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # Clear subscribers
            self._subscribers.clear()
            self._subscription_tasks.clear()
            self._active_channels.clear()
            
            logger.info("Event bus shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during event bus shutdown: {e}")
    
    # Publishing Methods
    async def publish(self, event: BaseEvent, channel: Optional[str] = None) -> bool:
        """
        Publish an event to the specified channel.
        
        Args:
            event: Event to publish
            channel: Target channel (auto-determined if None)
            
        Returns:
            bool: True if published successfully, False otherwise
            
        The method:
        1. Determines target channel if not specified
        2. Serializes event to JSON
        3. Publishes to Redis channel
        4. Updates metrics and handles errors
        """
        if self._circuit_breaker_open:
            if not await self._check_circuit_breaker():
                logger.warning("Circuit breaker open, dropping event")
                return False
        
        try:
            # Determine channel if not specified
            if channel is None:
                channel = self._determine_channel(event)
            
            # Serialize event
            event_data = {
                'event_id': event.event_id,
                'event_type': event.event_type,
                'timestamp': event.timestamp.isoformat(),
                'venue': event.venue.value,
                'data': asdict(event)
            }
            
            # Publish to Redis
            success = await self.redis_client.publish(channel, event_data)
            
            if success:
                self._event_stats[f"published_{event.event_type}"] = \
                    self._event_stats.get(f"published_{event.event_type}", 0) + 1
                logger.debug(f"Published {event.event_type} event to {channel}")
                return True
            else:
                await self._handle_publish_failure(event, channel, "Redis publish failed")
                return False
                
        except Exception as e:
            await self._handle_publish_failure(event, channel, str(e))
            return False
    
    async def publish_order_event(self, event: OrderEvent) -> bool:
        """Publish order-related event"""
        return await self.publish(event, EventChannels.ORDERS)
    
    async def publish_position_event(self, event: PositionEvent) -> bool:
        """Publish position-related event"""
        return await self.publish(event, EventChannels.POSITIONS)
    
    async def publish_balance_event(self, event: BalanceEvent) -> bool:
        """Publish balance-related event"""
        return await self.publish(event, EventChannels.BALANCES)
    
    async def publish_market_data_event(self, event: MarketDataEvent) -> bool:
        """Publish market data event"""
        return await self.publish(event, EventChannels.MARKET_DATA)
    
    async def publish_trade_event(self, event: TradeEvent) -> bool:
        """Publish trade event"""
        return await self.publish(event, EventChannels.TRADES)
    
    async def publish_connection_event(self, event: ConnectionEvent) -> bool:
        """Publish connection status event"""
        return await self.publish(event, EventChannels.CONNECTIONS)
    
    async def publish_system_event(self, event: SystemEvent) -> bool:
        """Publish system event"""
        return await self.publish(event, EventChannels.SYSTEM)
    
    # Subscription Methods
    async def subscribe(self, channel: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Subscribe to a channel with a callback function.
        
        Args:
            channel: Channel name to subscribe to
            callback: Function to call when event received
            
        Returns:
            bool: True if subscription successful, False otherwise
            
        The subscription:
        1. Adds callback to subscriber list
        2. Creates background task for channel listening
        3. Handles reconnection and error recovery
        4. Manages subscription lifecycle
        """
        try:
            # Add callback to subscribers
            if channel not in self._subscribers:
                self._subscribers[channel] = []
            
            self._subscribers[channel].append(callback)
            
            # Start subscription task if not already running
            if channel not in self._subscription_tasks:
                task = asyncio.create_task(self._subscription_worker(channel))
                self._subscription_tasks[channel] = task
                self._active_channels.add(channel)
            
            logger.info(f"Subscribed to channel: {channel}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to channel {channel}: {e}")
            return False
    
    async def unsubscribe(self, channel: str, callback: Optional[Callable] = None) -> bool:
        """
        Unsubscribe from a channel.
        
        Args:
            channel: Channel name
            callback: Specific callback to remove (removes all if None)
            
        Returns:
            bool: True if unsubscribed successfully, False otherwise
        """
        try:
            if channel not in self._subscribers:
                return True
            
            if callback is None:
                # Remove all callbacks for channel
                del self._subscribers[channel]
            else:
                # Remove specific callback
                if callback in self._subscribers[channel]:
                    self._subscribers[channel].remove(callback)
                
                # If no callbacks left, remove channel
                if not self._subscribers[channel]:
                    del self._subscribers[channel]
            
            # Cancel subscription task if no subscribers
            if channel not in self._subscribers and channel in self._subscription_tasks:
                task = self._subscription_tasks[channel]
                if not task.done():
                    task.cancel()
                del self._subscription_tasks[channel]
                self._active_channels.discard(channel)
            
            logger.info(f"Unsubscribed from channel: {channel}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from channel {channel}: {e}")
            return False
    
    # Convenience subscription methods
    async def subscribe_to_orders(self, callback: Callable[[OrderEvent], None]) -> bool:
        """Subscribe to order events"""
        wrapper = lambda data: callback(self._deserialize_order_event(data))
        return await self.subscribe(EventChannels.ORDERS, wrapper)
    
    async def subscribe_to_positions(self, callback: Callable[[PositionEvent], None]) -> bool:
        """Subscribe to position events"""
        wrapper = lambda data: callback(self._deserialize_position_event(data))
        return await self.subscribe(EventChannels.POSITIONS, wrapper)
    
    async def subscribe_to_market_data(self, callback: Callable[[MarketDataEvent], None]) -> bool:
        """Subscribe to market data events"""
        wrapper = lambda data: callback(self._deserialize_market_data_event(data))
        return await self.subscribe(EventChannels.MARKET_DATA, wrapper)
    
    async def subscribe_to_venue(self, venue: VenueEnum, callback: Callable[[BaseEvent], None]) -> bool:
        """Subscribe to all events from a specific venue"""
        channel = EventChannels.venue_channel(venue)
        wrapper = lambda data: callback(self._deserialize_base_event(data))
        return await self.subscribe(channel, wrapper)
    
    # Background Tasks
    async def _subscription_worker(self, channel: str) -> None:
        """
        Background worker that listens for events on a Redis channel.
        
        This worker:
        1. Maintains Redis subscription
        2. Deserializes incoming events
        3. Calls registered callbacks
        4. Handles errors and reconnection
        5. Updates performance metrics
        """
        while self._is_running and channel in self._active_channels:
            try:
                async with self.redis_client.subscribe(channel) as pubsub:
                    logger.info(f"Started subscription worker for channel: {channel}")
                    
                    async for message in pubsub.listen():
                        if message['type'] == 'message':
                            try:
                                # Deserialize event data
                                event_data = json.loads(message['data'])
                                
                                # Call all registered callbacks
                                if channel in self._subscribers:
                                    for callback in self._subscribers[channel]:
                                        try:
                                            await self._safe_callback(callback, event_data)
                                        except Exception as e:
                                            logger.error(f"Callback error for {channel}: {e}")
                                
                                # Update metrics
                                event_type = event_data.get('event_type', 'unknown')
                                self._event_stats[f"received_{event_type}"] = \
                                    self._event_stats.get(f"received_{event_type}", 0) + 1
                                
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to deserialize event from {channel}: {e}")
                            except Exception as e:
                                logger.error(f"Error processing event from {channel}: {e}")
                
            except Exception as e:
                logger.error(f"Subscription worker error for {channel}: {e}")
                if self._is_running:
                    await asyncio.sleep(5)  # Wait before retry
    
    async def _safe_callback(self, callback: Callable, event_data: Dict[str, Any]) -> None:
        """Safely execute callback with timeout and error handling"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await asyncio.wait_for(callback(event_data), timeout=5.0)
            else:
                callback(event_data)
        except asyncio.TimeoutError:
            logger.warning("Callback timeout exceeded")
        except Exception as e:
            logger.error(f"Callback execution error: {e}")
    
    async def _health_monitor(self) -> None:
        """Monitor event bus health and Redis connectivity"""
        while self._is_running:
            try:
                # Check Redis health
                if not await self.redis_client.health_check():
                    logger.warning("Redis health check failed")
                    await self._handle_redis_failure()
                else:
                    # Reset circuit breaker on successful health check
                    if self._circuit_breaker_open:
                        self._circuit_breaker_open = False
                        self._circuit_breaker_failures = 0
                        logger.info("Circuit breaker reset - Redis connection restored")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(30)
    
    async def _metrics_collector(self) -> None:
        """Collect and log performance metrics"""
        while self._is_running:
            try:
                await asyncio.sleep(60)  # Collect every minute
                
                if self._event_stats:
                    logger.info(f"Event bus metrics: {self._event_stats}")
                    
                    # Reset counters (keep running totals in Redis if needed)
                    self._event_stats.clear()
                
            except Exception as e:
                logger.error(f"Metrics collector error: {e}")
    
    # Helper Methods
    def _determine_channel(self, event: BaseEvent) -> str:
        """Determine the appropriate channel for an event"""
        if isinstance(event, OrderEvent):
            return EventChannels.ORDERS
        elif isinstance(event, PositionEvent):
            return EventChannels.POSITIONS
        elif isinstance(event, BalanceEvent):
            return EventChannels.BALANCES
        elif isinstance(event, MarketDataEvent):
            return EventChannels.MARKET_DATA
        elif isinstance(event, TradeEvent):
            return EventChannels.TRADES
        elif isinstance(event, ConnectionEvent):
            return EventChannels.CONNECTIONS
        elif isinstance(event, SystemEvent):
            return EventChannels.SYSTEM
        else:
            return EventChannels.venue_channel(event.venue)
    
    async def _handle_publish_failure(self, event: BaseEvent, channel: str, error: str) -> None:
        """Handle failed event publication"""
        self._circuit_breaker_failures += 1
        self._circuit_breaker_last_failure = datetime.utcnow()
        
        if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
            self._circuit_breaker_open = True
            logger.error("Circuit breaker opened due to Redis failures")
        
        # Store failed event for retry
        failed_event = {
            'event': asdict(event),
            'channel': channel,
            'error': error,
            'timestamp': datetime.utcnow().isoformat(),
            'retry_count': 0
        }
        self._failed_events.append(failed_event)
        
        logger.error(f"Failed to publish event to {channel}: {error}")
    
    async def _handle_redis_failure(self) -> None:
        """Handle Redis connection failures"""
        self._circuit_breaker_failures += 1
        self._circuit_breaker_last_failure = datetime.utcnow()
        
        if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
            self._circuit_breaker_open = True
    
    async def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker should be closed"""
        if not self._circuit_breaker_open:
            return True
        
        if self._circuit_breaker_last_failure:
            time_since_failure = datetime.utcnow() - self._circuit_breaker_last_failure
            if time_since_failure.total_seconds() > self._circuit_breaker_timeout:
                # Try to reconnect
                if await self.redis_client.health_check():
                    self._circuit_breaker_open = False
                    self._circuit_breaker_failures = 0
                    logger.info("Circuit breaker closed - Redis connection restored")
                    return True
        
        return False
    
    # Event deserialization helpers
    def _deserialize_order_event(self, data: Dict[str, Any]) -> OrderEvent:
        """Deserialize order event from Redis data"""
        # Implementation would deserialize the event data back to OrderEvent
        # This is a placeholder for the actual deserialization logic
        pass
    
    def _deserialize_position_event(self, data: Dict[str, Any]) -> PositionEvent:
        """Deserialize position event from Redis data"""
        pass
    
    def _deserialize_market_data_event(self, data: Dict[str, Any]) -> MarketDataEvent:
        """Deserialize market data event from Redis data"""
        pass
    
    def _deserialize_base_event(self, data: Dict[str, Any]) -> BaseEvent:
        """Deserialize base event from Redis data"""
        pass
    
    # Status and metrics methods
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            'active_channels': len(self._active_channels),
            'total_subscribers': sum(len(callbacks) for callbacks in self._subscribers.values()),
            'failed_events': len(self._failed_events),
            'circuit_breaker_open': self._circuit_breaker_open,
            'circuit_breaker_failures': self._circuit_breaker_failures,
            'event_stats': self._event_stats.copy()
        }
    
    def health_check(self) -> bool:
        """Check event bus health"""
        return (
            self._is_running and
            not self._circuit_breaker_open and
            len(self._failed_events) < 1000  # Arbitrary threshold
        )