"""
Redis Client and Connection Management

This module provides a Redis client wrapper with connection pooling, health checks,
retry logic, and utilities for pub/sub operations used by the event bus.

Key Features:
- Connection pooling for optimal performance
- Health monitoring and automatic reconnection
- Retry logic with exponential backoff
- Pub/sub utilities for event bus integration
- JSON serialization/deserialization helpers
- Connection lifecycle management
"""

import redis.asyncio as redis
import json
import logging
from typing import Any, Dict, Optional, Union, List
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis client wrapper with advanced features for the trading terminal.
    
    This class provides:
    - Connection management with pooling
    - Health monitoring and reconnection
    - Pub/sub functionality for event bus
    - Caching utilities with TTL support
    - JSON serialization helpers
    - Error handling and retry logic
    """
    
    def __init__(self):
        self.pool: Optional[redis.ConnectionPool] = None
        self.client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self._is_connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._reconnect_delay = 1  # Start with 1 second
        
    async def initialize(self) -> None:
        """
        Initialize Redis connection pool and client.
        
        Creates connection pool with optimal settings for high-frequency trading:
        - Connection pooling for concurrent operations
        - Health check intervals
        - Timeout configurations
        """
        try:
            # Create connection pool
            self.pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=20,
                retry_on_timeout=True,
                health_check_interval=30,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Create Redis client
            self.client = redis.Redis(
                connection_pool=self.pool,
                decode_responses=True
            )
            
            # Test connection
            await self.client.ping()
            self._is_connected = True
            self._reconnect_attempts = 0
            
            logger.info("Redis client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            self._is_connected = False
            raise
    
    async def close(self) -> None:
        """Close Redis connections and cleanup resources"""
        try:
            if self.pubsub:
                await self.pubsub.close()
                
            if self.client:
                await self.client.close()
                
            if self.pool:
                await self.pool.disconnect()
                
            self._is_connected = False
            logger.info("Redis client closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}")
    
    async def health_check(self) -> bool:
        """
        Perform health check on Redis connection.
        
        Returns:
            bool: True if Redis is healthy, False otherwise
        """
        try:
            if not self.client:
                return False
                
            await self.client.ping()
            return True
            
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return False
    
    async def reconnect(self) -> bool:
        """
        Attempt to reconnect to Redis with exponential backoff.
        
        Returns:
            bool: True if reconnection successful, False otherwise
        """
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return False
        
        try:
            self._reconnect_attempts += 1
            await asyncio.sleep(self._reconnect_delay)
            
            await self.initialize()
            
            logger.info(f"Redis reconnection successful (attempt {self._reconnect_attempts})")
            return True
            
        except Exception as e:
            self._reconnect_delay = min(self._reconnect_delay * 2, 60)  # Max 60 seconds
            logger.error(f"Redis reconnection failed (attempt {self._reconnect_attempts}): {e}")
            return False
    
    # Caching Operations
    async def set_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set cache value with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            serialized_value = json.dumps(value, default=str)
            
            if ttl:
                await self.client.setex(key, ttl, serialized_value)
            else:
                await self.client.set(key, serialized_value)
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """
        Get cache value and deserialize from JSON.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            value = await self.client.get(key)
            if value is None:
                return None
                
            return json.loads(value)
            
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None
    
    async def delete_cache(self, key: str) -> bool:
        """Delete cache key"""
        try:
            result = await self.client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False
    
    # Pub/Sub Operations for Event Bus
    async def publish(self, channel: str, message: Dict[str, Any]) -> bool:
        """
        Publish message to Redis channel.
        
        Args:
            channel: Redis channel name
            message: Message to publish (will be JSON serialized)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            serialized_message = json.dumps(message, default=str)
            await self.client.publish(channel, serialized_message)
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish to channel {channel}: {e}")
            return False
    
    @asynccontextmanager
    async def subscribe(self, *channels: str):
        """
        Context manager for subscribing to Redis channels.
        
        Args:
            *channels: Channel names to subscribe to
            
        Yields:
            PubSub object for receiving messages
        """
        pubsub = None
        try:
            pubsub = self.client.pubsub()
            await pubsub.subscribe(*channels)
            yield pubsub
            
        except Exception as e:
            logger.error(f"Error in Redis subscription: {e}")
            raise
        finally:
            if pubsub:
                await pubsub.unsubscribe(*channels)
                await pubsub.close()
    
    # Hash Operations for Order/Position Storage
    async def hset_json(self, key: str, field: str, value: Any) -> bool:
        """Set hash field with JSON serialized value"""
        try:
            serialized_value = json.dumps(value, default=str)
            await self.client.hset(key, field, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Failed to set hash {key}:{field}: {e}")
            return False
    
    async def hget_json(self, key: str, field: str) -> Optional[Any]:
        """Get hash field and deserialize from JSON"""
        try:
            value = await self.client.hget(key, field)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.error(f"Failed to get hash {key}:{field}: {e}")
            return None
    
    async def hgetall_json(self, key: str) -> Dict[str, Any]:
        """Get all hash fields and deserialize from JSON"""
        try:
            hash_data = await self.client.hgetall(key)
            result = {}
            for field, value in hash_data.items():
                try:
                    result[field] = json.loads(value)
                except json.JSONDecodeError:
                    result[field] = value
            return result
        except Exception as e:
            logger.error(f"Failed to get hash {key}: {e}")
            return {}
    
    # List Operations for Order History
    async def lpush_json(self, key: str, *values: Any) -> bool:
        """Push JSON serialized values to list"""
        try:
            serialized_values = [json.dumps(value, default=str) for value in values]
            await self.client.lpush(key, *serialized_values)
            return True
        except Exception as e:
            logger.error(f"Failed to push to list {key}: {e}")
            return False
    
    async def lrange_json(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get list range and deserialize from JSON"""
        try:
            values = await self.client.lrange(key, start, end)
            return [json.loads(value) for value in values]
        except Exception as e:
            logger.error(f"Failed to get list range {key}: {e}")
            return []
    
    # Utility Methods
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check existence of key {key}: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set key expiration"""
        try:
            return await self.client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Failed to set expiration for key {key}: {e}")
            return False
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis client is connected"""
        return self._is_connected


# Global Redis client instance
redis_client = RedisClient()