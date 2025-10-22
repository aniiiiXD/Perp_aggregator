"""
Base Client Abstract Class

This module defines the abstract base class that all venue clients must implement.
It provides a consistent interface for trading operations across different DEXs.

The BaseClient defines the contract that all venue-specific implementations must follow,
ensuring that the orchestrator can interact with any venue using the same interface.

Key Methods:
- Trading operations (place_order, cancel_order)
- Data retrieval (get_positions, get_balances, get_market_data)
- WebSocket management (subscribe_market_data, websocket_health_check)
- Health monitoring (health_check)
- Lifecycle management (initialize, shutdown)

Each venue client inherits from this base class and implements venue-specific logic
while maintaining the unified interface.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from decimal import Decimal

from app.models.unified import UnifiedOrder, Position, Balance, MarketData, Trade
from app.models.enums import VenueEnum


class BaseClient(ABC):
    """
    Abstract base class for all venue clients.
    
    This class defines the interface that all venue-specific clients must implement.
    It ensures consistency across different DEX integrations and provides a unified
    API for the orchestrator to interact with any venue.
    
    Subclasses must implement all abstract methods to provide venue-specific
    functionality while maintaining the same interface.
    """
    
    def __init__(self, venue: VenueEnum):
        """
        Initialize the base client.
        
        Args:
            venue: The venue this client represents
        """
        self.venue = venue
        self._is_initialized = False
        self._is_connected = False
    
    # Lifecycle Management
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the client and establish connections.
        
        This method should:
        - Set up API connections
        - Initialize WebSocket connections
        - Authenticate with the venue
        - Start background tasks
        - Set _is_initialized = True on success
        
        Raises:
            VenueConnectionError: If initialization fails
            AuthenticationError: If authentication fails
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """
        Gracefully shutdown the client.
        
        This method should:
        - Close WebSocket connections
        - Cancel background tasks
        - Clean up resources
        - Set _is_initialized = False
        """
        pass
    
    # Health Monitoring
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the client is healthy and operational.
        
        Returns:
            bool: True if healthy, False otherwise
            
        This should check:
        - API connectivity
        - Authentication status
        - Recent error rates
        - Response times
        """
        pass
    
    @abstractmethod
    async def websocket_health_check(self) -> bool:
        """
        Check if WebSocket connections are healthy.
        
        Returns:
            bool: True if WebSocket is connected and healthy, False otherwise
        """
        pass
    
    # Trading Operations
    @abstractmethod
    async def place_order(self, order: UnifiedOrder) -> UnifiedOrder:
        """
        Place an order on the venue.
        
        Args:
            order: Unified order object with order details
            
        Returns:
            UnifiedOrder: Updated order with venue response data
            
        Raises:
            OrderValidationError: If order parameters are invalid
            InsufficientBalanceError: If insufficient balance
            VenueConnectionError: If venue is unavailable
            
        The implementation should:
        1. Validate order parameters for the venue
        2. Convert unified order to venue-specific format
        3. Submit order to venue API
        4. Convert response back to unified format
        5. Update order status and venue-specific data
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order.
        
        Args:
            order_id: Venue-specific order ID to cancel
            
        Returns:
            bool: True if cancellation successful, False otherwise
            
        Raises:
            OrderNotFoundError: If order doesn't exist
            VenueConnectionError: If venue is unavailable
        """
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> Optional[UnifiedOrder]:
        """
        Get the current status of an order.
        
        Args:
            order_id: Venue-specific order ID
            
        Returns:
            UnifiedOrder: Current order status, None if not found
            
        Raises:
            VenueConnectionError: If venue is unavailable
        """
        pass
    
    # Data Retrieval
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Get all current positions.
        
        Returns:
            List[Position]: List of current positions in unified format
            
        Raises:
            VenueConnectionError: If venue is unavailable
            AuthenticationError: If authentication fails
            
        The implementation should:
        1. Fetch positions from venue API
        2. Convert to unified Position format
        3. Calculate derived fields (PnL, notional value, etc.)
        """
        pass
    
    @abstractmethod
    async def get_balances(self) -> List[Balance]:
        """
        Get all account balances.
        
        Returns:
            List[Balance]: List of balances in unified format
            
        Raises:
            VenueConnectionError: If venue is unavailable
            AuthenticationError: If authentication fails
        """
        pass
    
    @abstractmethod
    async def get_market_data(self, symbol: str) -> MarketData:
        """
        Get current market data for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., "BTC-PERP")
            
        Returns:
            MarketData: Current market data in unified format
            
        Raises:
            MarketDataError: If market data unavailable
            VenueConnectionError: If venue is unavailable
        """
        pass
    
    @abstractmethod
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """
        Get recent trades for a symbol.
        
        Args:
            symbol: Trading symbol
            limit: Maximum number of trades to return
            
        Returns:
            List[Trade]: Recent trades in unified format
            
        Raises:
            MarketDataError: If trade data unavailable
            VenueConnectionError: If venue is unavailable
        """
        pass
    
    # WebSocket Operations
    @abstractmethod
    async def subscribe_market_data(self, symbols: List[str]) -> bool:
        """
        Subscribe to real-time market data for symbols.
        
        Args:
            symbols: List of symbols to subscribe to
            
        Returns:
            bool: True if subscription successful, False otherwise
            
        The implementation should:
        1. Establish WebSocket connection if not already connected
        2. Send subscription messages for the symbols
        3. Set up message handlers for incoming data
        4. Publish market data events to the event bus
        """
        pass
    
    @abstractmethod
    async def unsubscribe_market_data(self, symbols: List[str]) -> bool:
        """
        Unsubscribe from real-time market data.
        
        Args:
            symbols: List of symbols to unsubscribe from
            
        Returns:
            bool: True if unsubscription successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def subscribe_order_updates(self) -> bool:
        """
        Subscribe to real-time order status updates.
        
        Returns:
            bool: True if subscription successful, False otherwise
            
        The implementation should:
        1. Subscribe to order update WebSocket channel
        2. Set up handlers for order status changes
        3. Publish order events to the event bus
        """
        pass
    
    @abstractmethod
    async def subscribe_position_updates(self) -> bool:
        """
        Subscribe to real-time position updates.
        
        Returns:
            bool: True if subscription successful, False otherwise
            
        The implementation should:
        1. Subscribe to position update WebSocket channel
        2. Set up handlers for position changes
        3. Publish position events to the event bus
        """
        pass
    
    # Utility Methods
    @abstractmethod
    async def get_symbols(self) -> List[str]:
        """
        Get list of available trading symbols.
        
        Returns:
            List[str]: Available symbols on this venue
        """
        pass
    
    @abstractmethod
    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get detailed information about a trading symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dict containing symbol information (min size, tick size, etc.)
        """
        pass
    
    # Properties
    @property
    def is_initialized(self) -> bool:
        """Check if client is initialized"""
        return self._is_initialized
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._is_connected
    
    @property
    def venue_name(self) -> str:
        """Get venue name"""
        return self.venue.value
    
    # Helper methods that subclasses can override
    def _validate_symbol(self, symbol: str) -> bool:
        """
        Validate if symbol is supported by this venue.
        
        Args:
            symbol: Symbol to validate
            
        Returns:
            bool: True if valid, False otherwise
            
        Subclasses should override this with venue-specific validation.
        """
        return bool(symbol and isinstance(symbol, str))
    
    def _validate_order_size(self, symbol: str, size: Decimal) -> bool:
        """
        Validate if order size meets venue requirements.
        
        Args:
            symbol: Trading symbol
            size: Order size
            
        Returns:
            bool: True if valid, False otherwise
            
        Subclasses should override this with venue-specific validation.
        """
        return size > 0
    
    def _validate_order_price(self, symbol: str, price: Optional[Decimal]) -> bool:
        """
        Validate if order price meets venue requirements.
        
        Args:
            symbol: Trading symbol
            price: Order price (None for market orders)
            
        Returns:
            bool: True if valid, False otherwise
            
        Subclasses should override this with venue-specific validation.
        """
        return price is None or price > 0