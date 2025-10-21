"""
Redis client configuration and utilities
"""
import json
import logging
from typing import Any, Optional
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client wrapper"""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
            
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")
            
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set a key-value pair with optional TTL"""
        if not self.redis:
            raise RuntimeError("Redis not connected")
            
        serialized_value = json.dumps(value) if not isinstance(value, str) else value
        
        if ttl:
            await self.redis.setex(key, ttl, serialized_value)
        else:
            await self.redis.set(key, serialized_value)
            
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        if not self.redis:
            raise RuntimeError("Redis not connected")
            
        value = await self.redis.get(key)
        if value is None:
            return None
            
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
            
    async def delete(self, key: str):
        """Delete a key"""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        await self.redis.delete(key)
        
    async def publish(self, channel: str, message: Any):
        """Publish message to channel"""
        if not self.redis:
            raise RuntimeError("Redis not connected")
            
        serialized_message = json.dumps(message) if not isinstance(message, str) else message
        await self.redis.publish(channel, serialized_message)
        
    async def subscribe(self, channel: str):
        """Subscribe to channel"""
        if not self.redis:
            raise RuntimeError("Redis not connected")
            
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        return pubsub


# Global Redis client instance
redis_client = RedisClient()