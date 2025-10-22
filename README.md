# Unified Trading Terminal

A comprehensive trading platform that provides a single interface for executing trades across multiple decentralized exchanges (DEXs) including Hyperliquid, Lighter, and trade.xyz.

## Features

- **Multi-Venue Trading**: Execute trades across Hyperliquid, Lighter, and trade.xyz from a single interface
- **Real-time Data**: WebSocket connections for live market data, order updates, and position tracking
- **Portfolio Aggregation**: Consolidated view of positions, balances, and PnL across all venues
- **Event-Driven Architecture**: Redis-based event bus for real-time communication between components
- **Circuit Breaker Pattern**: Fault tolerance and graceful degradation when venues are unavailable
- **Comprehensive API**: RESTful endpoints for all trading operations and data retrieval
- **WebSocket Streaming**: Real-time data streams for market data, orders, positions, and portfolio updates

## Architecture

The system follows a microservice architecture with the following key components:

### Core Components

- **Main Orchestrator**: Central coordinator that routes requests to appropriate venue clients
- **Event Bus**: Redis-based pub/sub system for real-time event communication
- **Portfolio Aggregator**: Consolidates data from all venues for unified portfolio view
- **Venue Clients**: Dedicated clients for each DEX (Hyperliquid, Lighter, trade.xyz)

### API Layer

- **Trading Endpoints**: Order placement, cancellation, and management
- **Position Endpoints**: Position tracking and portfolio management
- **Market Data Endpoints**: Real-time and historical market data
- **Venue Endpoints**: Venue selection and status monitoring
- **WebSocket Endpoints**: Real-time data streaming

## Project Structure

```
app/
├── main.py                          # FastAPI entry point
├── core/
│   ├── config.py                    # App configuration
│   ├── redis.py                     # Redis client
│   ├── events.py                    # Event definitions
│   └── exceptions.py                # Custom exceptions
├── models/
│   ├── unified.py                   # Unified models (Order, Position, Balance)
│   └── enums.py                     # Enums (OrderType, OrderSide, VenueEnum)
├── orchestrator/
│   ├── main_orchestrator.py         # Main request router
│   ├── event_bus.py                 # Pub/sub event system
│   └── portfolio_aggregator.py      # Portfolio data aggregation
├── clients/
│   ├── base_client.py               # Abstract base class for all clients
│   ├── hyperliquid/                 # Hyperliquid client implementation
│   ├── lighter/                     # Lighter client implementation
│   └── tradexyz/                    # Trade.xyz client implementation
└── api/
    ├── routes.py                    # Main router
    └── endpoints/
        ├── venues.py                # Venue management
        ├── trading.py               # Order operations
        ├── positions.py             # Position management
        ├── market_data.py           # Market data
        └── websocket.py             # WebSocket endpoints
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd unified-trading-terminal
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Start Redis (required for event bus):
```bash
# Using Docker
docker run -d -p 6379:6379 redis:alpine

# Or install Redis locally
```

6. Start the application:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Configuration

The application uses environment variables for configuration. Key settings include:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `HYPERLIQUID_WS_URL`: Hyperliquid WebSocket URL
- `LIGHTER_WS_URL`: Lighter WebSocket URL
- `TRADEXYZ_WS_URL`: Trade.xyz WebSocket URL (to be configured)
- `PRICE_CACHE_TTL`: Price data cache TTL in seconds
- `WS_HEARTBEAT_INTERVAL`: WebSocket heartbeat interval

## API Documentation

Once the application is running, you can access:

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Key Endpoints

### Trading
- `POST /api/v1/trading/orders` - Place a new order
- `DELETE /api/v1/trading/orders/{order_id}` - Cancel an order
- `GET /api/v1/trading/orders` - Get order history
- `GET /api/v1/trading/orders/active` - Get active orders

### Positions
- `GET /api/v1/positions` - Get all positions
- `GET /api/v1/positions/{symbol}` - Get position for specific symbol
- `POST /api/v1/positions/{symbol}/close` - Close a position

### Market Data
- `GET /api/v1/market-data/ticker/{symbol}` - Get ticker data
- `GET /api/v1/market-data/orderbook/{symbol}` - Get orderbook
- `GET /api/v1/market-data/trades/{symbol}` - Get recent trades

### Venues
- `GET /api/v1/venues` - List available venues
- `GET /api/v1/venues/{venue}/status` - Get venue status
- `POST /api/v1/venues/{venue}/connect` - Connect to venue

### WebSocket Streams
- `ws://localhost:8000/api/v1/ws/market-data` - Real-time market data
- `ws://localhost:8000/api/v1/ws/orders` - Real-time order updates
- `ws://localhost:8000/api/v1/ws/positions` - Real-time position updates
- `ws://localhost:8000/api/v1/ws/portfolio` - Real-time portfolio updates

## Development Status

### Completed Components
- ✅ Project structure and configuration
- ✅ Core models and enums
- ✅ Event bus system with Redis
- ✅ Main orchestrator with circuit breaker pattern
- ✅ Portfolio aggregator
- ✅ Base client interface
- ✅ Complete API endpoints
- ✅ WebSocket streaming endpoints
- ✅ Comprehensive documentation

### TODO - Venue Client Implementations
- 🔄 Hyperliquid client implementation
- 🔄 Lighter client implementation  
- 🔄 Trade.xyz client implementation
- 🔄 WebSocket handlers for each venue
- 🔄 Authentication modules
- 🔄 Data normalization layers

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions and support, please open an issue in the repository or contact the development team.