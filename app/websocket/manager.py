"""
WebSocket connection manager for real-time client communication
"""
import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

from app.core.redis import redis_client
from app.models.market_data import PriceData, AggregatedPrice

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # connection_id -> set of pairs
        
    async def connect(self, websocket: WebSocket, connection_id: str):
        """Accept new WebSocket connection"""    
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.subscriptions[connection_id] = set()
        logger.info(f"WebSocket connection established: {connection_id}")
        
    def disconnect(self, connection_id: str):
        """Remove WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.subscriptions:
            del self.subscriptions[connection_id]
        logger.info(f"WebSocket connection closed: {connection_id}")
        
    async def send_personal_message(self, message: dict, connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                self.disconnect(connection_id)
                
    async def broadcast_to_subscribers(self, message: dict, pair: str):
        """Broadcast message to all subscribers of a trading pair"""
        disconnected = []
        
        for connection_id, subscribed_pairs in self.subscriptions.items():
            if pair in subscribed_pairs:
                try:
                    websocket = self.active_connections[connection_id]
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error broadcasting to {connection_id}: {e}")
                    disconnected.append(connection_id)
                    
        # Clean up disconnected connections
        for connection_id in disconnected:
            self.disconnect(connection_id)
            
    def subscribe_to_pair(self, connection_id: str, pair: str):
        """Subscribe connection to trading pair updates"""
        if connection_id in self.subscriptions:
            self.subscriptions[connection_id].add(pair)
            logger.info(f"Connection {connection_id} subscribed to {pair}")
            
    def unsubscribe_from_pair(self, connection_id: str, pair: str):
        """Unsubscribe connection from trading pair updates"""
        if connection_id in self.subscriptions:
            self.subscriptions[connection_id].discard(pair)
            logger.info(f"Connection {connection_id} unsubscribed from {pair}")
            
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)
        
    def get_pair_subscriber_count(self, pair: str) -> int:
        """Get number of subscribers for a trading pair"""
        count = 0
        for subscribed_pairs in self.subscriptions.values():
            if pair in subscribed_pairs:
                count += 1
        return count


class WebSocketManager:
    """High-level WebSocket manager with price aggregation"""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.price_cache: Dict[str, Dict[str, PriceData]] = {}  # pair -> dex -> price_data
        
    async def handle_connection(self, websocket: WebSocket, connection_id: str):
        """Handle new WebSocket connection"""
        await self.connection_manager.connect(websocket, connection_id)
        
        try:
            while True:
                # Wait for messages from client
                data = await websocket.receive_text()
                await self._handle_client_message(data, connection_id)
                
        except WebSocketDisconnect:
            self.connection_manager.disconnect(connection_id)
        except Exception as e:
            logger.error(f"WebSocket error for {connection_id}: {e}")
            self.connection_manager.disconnect(connection_id)
            
    async def _handle_client_message(self, message: str, connection_id: str):
        """Handle message from WebSocket client"""
        try:
            data = json.loads(message)
            action = data.get("action")
            
            if action == "subscribe":
                pair = data.get("pair")
                if pair:
                    self.connection_manager.subscribe_to_pair(connection_id, pair)
                    # Send current price if available
                    await self._send_current_price(connection_id, pair)
                    
            elif action == "unsubscribe":
                pair = data.get("pair")
                if pair:
                    self.connection_manager.unsubscribe_from_pair(connection_id, pair)
                    
            elif action == "ping":
                await self.connection_manager.send_personal_message(
                    {"type": "pong", "timestamp": data.get("timestamp")},
                    connection_id
                )
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from client {connection_id}: {message}")
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
            
    async def _send_current_price(self, connection_id: str, pair: str):
        """Send current aggregated price to client"""
        if pair in self.price_cache:
            aggregated = await self._calculate_aggregated_price(pair)
            if aggregated:
                message = {
                    "type": "price_update",
                    "data": aggregated.dict()
                }
                await self.connection_manager.send_personal_message(message, connection_id)
                
    async def broadcast_price_update(self, price_data: PriceData):
        """Broadcast price update from DEX"""
        pair = price_data.pair
        dex = price_data.dex.value
        
        # Update price cache
        if pair not in self.price_cache:
            self.price_cache[pair] = {}
        self.price_cache[pair][dex] = price_data
        
        # Cache in Redis
        cache_key = f"price:{pair}:{dex}"
        await redis_client.set(cache_key, price_data.dict(), ttl=60)
        
        # Calculate aggregated price
        aggregated = await self._calculate_aggregated_price(pair)
        if aggregated:
            # Cache aggregated price
            agg_cache_key = f"aggregated_price:{pair}"
            await redis_client.set(agg_cache_key, aggregated.dict(), ttl=1)
            
            # Broadcast to subscribers
            message = {
                "type": "price_update",
                "data": aggregated.dict()
            }
            await self.connection_manager.broadcast_to_subscribers(message, pair)
            
            # Publish to Redis for other instances
            await redis_client.publish(f"price_updates:{pair}", aggregated.dict())
            
    async def _calculate_aggregated_price(self, pair: str) -> AggregatedPrice:
        """Calculate aggregated price from all DEX sources"""
        if pair not in self.price_cache or not self.price_cache[pair]:
            return None
            
        sources = list(self.price_cache[pair].values())
        if not sources:
            return None
            
        # Find best bid (highest) and best ask (lowest)
        best_bid = max(sources, key=lambda x: x.bid)
        best_ask = min(sources, key=lambda x: x.ask)
        
        return AggregatedPrice(
            pair=pair,
            best_bid=best_bid.bid,
            best_ask=best_ask.ask,
            best_bid_dex=best_bid.dex,
            best_ask_dex=best_ask.dex,
            sources=sources
        )
        
    async def get_aggregated_price(self, pair: str) -> AggregatedPrice:
        """Get current aggregated price for a pair"""
        # Try cache first
        cache_key = f"aggregated_price:{pair}"
        cached = await redis_client.get(cache_key)
        if cached:
            return AggregatedPrice(**cached)
            
        # Calculate from current data
        return await self._calculate_aggregated_price(pair)
        
    def get_stats(self) -> dict:
        """Get WebSocket manager statistics"""
        return {
            "active_connections": self.connection_manager.get_connection_count(),
            "cached_pairs": len(self.price_cache),
            "pair_stats": {
                pair: {
                    "dex_count": len(dex_prices),
                    "subscribers": self.connection_manager.get_pair_subscriber_count(pair)
                }
                for pair, dex_prices in self.price_cache.items()
            }
        }