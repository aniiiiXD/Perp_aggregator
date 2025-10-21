"""
Application configuration settings
"""
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Perp DEX Aggregator"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/perp_dex"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # DEX Configuration
    HYPERLIQUID_WS_URL: str = "wss://api.hyperliquid.xyz/ws"
    LIGHTER_WS_URL: str = "wss://api.lighter.xyz/ws"
    
    # Cache TTL (seconds)
    PRICE_CACHE_TTL: int = 1  # 1 second for aggregated prices
    ROUTE_CACHE_TTL: int = 10  # 10 seconds for route calculations
    
    # WebSocket Configuration
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_RECONNECT_DELAY: int = 5
    WS_MAX_RECONNECT_ATTEMPTS: int = 10
    
    class Config:
        env_file = ".env"


settings = Settings()