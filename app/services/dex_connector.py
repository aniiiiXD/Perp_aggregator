"""
DEX connector service for managing WebSocket connections
"""
import asyncio
import json
import logging
from typing import Dict, Optional, Callable
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from app.core.config import settings
from app.models.market_data import DEXType, PriceData
from app.websocket.manager import WebSocketManager

logger = logging.getLogger(__name__)


class DEXConnector:
    """Base DEX WebSocket connector"""
    
    def __init__(self, dex_type: DEXType, ws_url: str, ws_manager: WebSocketManager):
        self.dex_type = dex_type
        self.ws_url = ws_url
        self.ws_manager = ws_manager
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.subscribed_pairs: set = set()
        
    async def connect(self):
        """Connect to DEX WebSocket"""
        try:
            self.websocket = await websockets.connect(self.ws_url)
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info(f"Connected to {self.dex_type} WebSocket")
            
            # Start listening for messages
            asyncio.create_task(self._listen())
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.dex_type}: {e}")
            await self._handle_reconnect()
            
    async def disconnect(self):
        """Disconnect from WebSocket"""
        self.is_connected = False
        if self.websocket:
            await self.websocket.close() 
            logger.info(f"Disconnected from {self.dex_type}")
            
    async def subscribe_to_pair(self, pair: str):
        """Subscribe to price updates for a trading pair"""
        if not self.is_connected or not self.websocket:
            logger.warning(f"Cannot subscribe to {pair} - {self.dex_type} not connected")
            return
            
        try:
            subscribe_msg = self._build_subscribe_message(pair)
            await self.websocket.send(json.dumps(subscribe_msg))
            self.subscribed_pairs.add(pair)
            logger.info(f"Subscribed to {pair} on {self.dex_type}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {pair} on {self.dex_type}: {e}")
            
    def _build_subscribe_message(self, pair: str) -> dict:
        """Build subscription message (DEX-specific implementation needed)"""
        # This is a placeholder - each DEX will have its own format
        return {
            "method": "subscribe",
            "params": {
                "channel": "ticker",
                "symbol": pair
            }
        }
        
    async def _listen(self):
        """Listen for WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from {self.dex_type}: {message}")
                except Exception as e:
                    logger.error(f"Error handling message from {self.dex_type}: {e}")
                    
        except ConnectionClosed:
            logger.warning(f"{self.dex_type} connection closed")
            self.is_connected = False
            await self._handle_reconnect()
        except Exception as e:
            logger.error(f"Error in {self.dex_type} listener: {e}")
            self.is_connected = False
            await self._handle_reconnect()
            
    async def _handle_message(self, data: dict):
        """Handle incoming WebSocket message (DEX-specific implementation needed)"""
        # This is a placeholder - each DEX will parse messages differently
        logger.debug(f"Received message from {self.dex_type}: {data}")
        
    async def _handle_reconnect(self):
        """Handle reconnection logic"""
        if self.reconnect_attempts >= settings.WS_MAX_RECONNECT_ATTEMPTS:
            logger.error(f"Max reconnection attempts reached for {self.dex_type}")
            return
            
        self.reconnect_attempts += 1
        delay = min(settings.WS_RECONNECT_DELAY * (2 ** self.reconnect_attempts), 60)
        
        logger.info(f"Reconnecting to {self.dex_type} in {delay} seconds (attempt {self.reconnect_attempts})")
        await asyncio.sleep(delay)
        await self.connect()


class HyperliquidConnector(DEXConnector):
    """Hyperliquid-specific WebSocket connector"""
    
    def __init__(self, ws_manager: WebSocketManager):
        super().__init__(DEXType.HYPERLIQUID, settings.HYPERLIQUID_WS_URL, ws_manager)
        
    def _build_subscribe_message(self, pair: str) -> dict:
        """Build Hyperliquid subscription message"""
        return {
            "method": "subscribe",
            "subscription": {
                "type": "l2Book",
                "coin": pair
            }
        }
        
    async def _handle_message(self, data: dict):
        """Handle Hyperliquid WebSocket message"""
        try:
            # Parse Hyperliquid message format
            if data.get("channel") == "l2Book":
                price_data = self._parse_price_data(data)
                if price_data:
                    await self.ws_manager.broadcast_price_update(price_data)
        except Exception as e:
            logger.error(f"Error parsing Hyperliquid message: {e}")
            
    def _parse_price_data(self, data: dict) -> Optional[PriceData]:
        """Parse Hyperliquid price data"""
        # Placeholder implementation - needs actual Hyperliquid format
        return None


class LighterConnector(DEXConnector):
    """Lighter-specific WebSocket connector"""
    
    def __init__(self, ws_manager: WebSocketManager):
        super().__init__(DEXType.LIGHTER, settings.LIGHTER_WS_URL, ws_manager)
        
    def _build_subscribe_message(self, pair: str) -> dict:
        """Build Lighter subscription message"""
        return {
            "id": 1,
            "method": "subscribe",
            "params": [f"{pair}@ticker"]
        }
        
    async def _handle_message(self, data: dict):
        """Handle Lighter WebSocket message"""
        try:
            # Parse Lighter message format
            if "stream" in data and "ticker" in data["stream"]:
                price_data = self._parse_price_data(data)
                if price_data:
                    await self.ws_manager.broadcast_price_update(price_data)
        except Exception as e:
            logger.error(f"Error parsing Lighter message: {e}")
            
    def _parse_price_data(self, data: dict) -> Optional[PriceData]:
        """Parse Lighter price data"""
        # Placeholder implementation - needs actual Lighter format
        return None


class DEXConnectorService:
    """Service to manage all DEX connections"""
    
    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
        self.connectors: Dict[DEXType, DEXConnector] = {
            DEXType.HYPERLIQUID: HyperliquidConnector(ws_manager),
            DEXType.LIGHTER: LighterConnector(ws_manager)
        }
        
    async def start_connections(self):
        """Start all DEX connections"""
        tasks = []
        for connector in self.connectors.values():
            tasks.append(connector.connect())
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def stop_connections(self):
        """Stop all DEX connections"""
        tasks = []
        for connector in self.connectors.values():
            tasks.append(connector.disconnect())
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def subscribe_to_pair(self, pair: str):
        """Subscribe to a trading pair on all DEXs"""
        tasks = []
        for connector in self.connectors.values():
            tasks.append(connector.subscribe_to_pair(pair))
        await asyncio.gather(*tasks, return_exceptions=True)
        
    def get_connection_status(self) -> Dict[str, bool]:
        """Get connection status for all DEXs"""
        return {
            dex_type.value: connector.is_connected
            for dex_type, connector in self.connectors.items()
        }