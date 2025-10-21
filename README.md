# Perp DEX Aggregator

A real-time perpetual futures DEX aggregator that provides price feeds and order routing across Hyperliquid and Lighter DEX protocols.

## Features

- Real-time price aggregation from Hyperliquid and Lighter
- WebSocket connections for live market data
- REST API for trading operations
- Order routing and execution simulation
- Position management and analytics
- Redis caching for performance
- Docker containerization

## Project Structure

```
app/
├── main.py                 # FastAPI application entry point
├── core/
│   ├── config.py          # Application configuration
│   └── redis.py           # Redis client wrapper
├── models/
│   └── market_data.py     # Data models and schemas
├── services/
│   └── dex_connector.py   # DEX WebSocket connectors
├── websocket/
│   └── manager.py         # WebSocket connection management
└── api/
    ├── routes.py          # Main API router
    └── endpoints/         # API endpoint modules
        ├── health.py      # Health check endpoints
        ├── prices.py      # Price data endpoints
        ├── trading.py     # Trading endpoints
        ├── positions.py   # Position management
        └── websocket.py   # WebSocket endpoint
```

## Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd perp-dex-aggregator
   cp .env.example .env
   ```

2. **Run with Docker**:
   ```bash
   docker-compose up --build
   ```

3. **Or run locally**:
   ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

## API Endpoints

### Health
- `GET /api/v1/health/` - Basic health check
- `GET /api/v1/health/detailed` - Detailed system status

### Prices
- `GET /api/v1/prices/aggregated/{pair}` - Get aggregated price for pair
- `GET /api/v1/prices/pairs` - List available trading pairs
- `GET /api/v1/prices/stats` - Price aggregation statistics

### Trading
- `POST /api/v1/trading/route` - Calculate optimal order routing
- `POST /api/v1/trading/simulate` - Simulate order execution
- `GET /api/v1/trading/dex-status` - DEX connection status

### Positions
- `GET /api/v1/positions/` - Get user positions
- `GET /api/v1/positions/analytics/summary` - Position analytics

### WebSocket
- `WS /api/v1/ws/connect` - Real-time price updates

## WebSocket Usage

Connect to `/api/v1/ws/connect` and send:

```json
{
  "action": "subscribe",
  "pair": "BTC-USD"
}
```

Receive price updates:
```json
{
  "type": "price_update",
  "data": {
    "pair": "BTC-USD",
    "best_bid": 45000,
    "best_ask": 45010,
    "best_bid_dex": "hyperliquid",
    "best_ask_dex": "lighter",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

## Development

The application is structured for easy extension:

- Add new DEX connectors in `services/dex_connector.py`
- Extend data models in `models/market_data.py`
- Add new API endpoints in `api/endpoints/`
- Configure settings in `core/config.py`

## Current Status

This is a foundational implementation with:
- ✅ Project structure and configuration
- ✅ WebSocket management framework
- ✅ DEX connector interfaces
- ✅ REST API endpoints
- ✅ Docker containerization
- 🔄 Mock data for development
- ⏳ Actual DEX integration (needs API documentation)
- ⏳ Database integration
- ⏳ Authentication system
- ⏳ Order execution

## Next Steps

1. Implement actual Hyperliquid and Lighter WebSocket protocols
2. Add database models and migrations
3. Implement real order execution
4. Add comprehensive testing
5. Add monitoring and logging
6. Implement authentication system