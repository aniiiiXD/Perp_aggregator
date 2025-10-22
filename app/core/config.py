"""
Configuration Management

Pydantic-based configuration system that loads settings from environment variables
with validation and default values.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/perp_dex",
        description="Database connection URL"
    )
    
    # Redis Configuration
    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )
    
    # DEX WebSocket URLs
    HYPERLIQUID_WS_URL: str = Field(
        default="wss://api.hyperliquid.xyz/ws",
        description="Hyperliquid WebSocket URL"
    )
    LIGHTER_WS_URL: str = Field(
        default="wss://api.lighter.xyz/ws",
        description="Lighter WebSocket URL"
    )
    TRADEXYZ_WS_URL: str = Field(
        default="wss://api.trade.xyz/ws",
        description="Trade.xyz WebSocket URL"
    )
    
    # Cache TTL Settings (seconds)
    PRICE_CACHE_TTL: int = Field(
        default=1,
        description="Price data cache TTL in seconds"
    )
    ROUTE_CACHE_TTL: int = Field(
        default=10,
        description="Route cache TTL in seconds"
    )
    
    # WebSocket Configuration
    WS_HEARTBEAT_INTERVAL: int = Field(
        default=30,
        description="WebSocket heartbeat interval in seconds"
    )
    WS_RECONNECT_DELAY: int = Field(
        default=5,
        description="WebSocket reconnection delay in seconds"
    )
    WS_MAX_RECONNECT_ATTEMPTS: int = Field(
        default=10,
        description="Maximum WebSocket reconnection attempts"
    )
    
    # CORS Settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins"
    )
    
    # API Configuration
    API_V1_PREFIX: str = Field(
        default="/api/v1",
        description="API version 1 prefix"
    )
    
    # Security Settings
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT tokens"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )
    
    # Logging Configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=100,
        description="Rate limit per minute per client"
    )
    
    # Circuit Breaker Settings
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(
        default=5,
        description="Circuit breaker failure threshold"
    )
    CIRCUIT_BREAKER_TIMEOUT: int = Field(
        default=60,
        description="Circuit breaker timeout in seconds"
    )
    
    @validator('ALLOWED_ORIGINS', pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @validator('LOG_LEVEL')
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'LOG_LEVEL must be one of {valid_levels}')
        return v.upper()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings