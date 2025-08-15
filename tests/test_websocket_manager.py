"""Tests for WebSocket Manager"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from websocket_manager import WebSocketManager


class TestWebSocketManager:
    """Test WebSocket Manager functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.ws_manager = WebSocketManager(testnet=True)
    
    def test_initialization(self):
        """Test WebSocket manager initialization"""
        assert self.ws_manager.testnet == True
        assert self.ws_manager.is_connected == False
        assert self.ws_manager.reconnect_attempts == 0
        assert len(self.ws_manager.subscriptions) == 0
    
    def test_subscription_storage(self):
        """Test subscription tracking"""
        symbol = "BTCUSDT"
        
        # Mock the ws_public to avoid actual connection
        self.ws_manager.ws_public = Mock()
        
        # Subscribe to orderbook
        self.ws_manager.subscribe_orderbook(symbol, depth=50)
        
        # Check subscription is stored
        assert f"orderbook_{symbol}" in self.ws_manager.subscriptions
        assert self.ws_manager.subscriptions[f"orderbook_{symbol}"]["symbol"] == symbol
    
    def test_data_storage(self):
        """Test data storage in manager"""
        symbol = "BTCUSDT"
        
        # Store test orderbook data
        test_orderbook = {
            "bids": [[100, 1], [99, 2]],
            "asks": [[101, 1], [102, 2]],
            "timestamp": 1234567890,
            "update_id": 1
        }
        
        self.ws_manager.orderbook_data[symbol] = test_orderbook
        
        # Retrieve data
        retrieved = self.ws_manager.get_orderbook(symbol)
        assert retrieved == test_orderbook
    
    def test_message_queue(self):
        """Test message queue functionality"""
        # Add messages to queue
        for i in range(5):
            self.ws_manager.message_queue.append({
                "type": "test",
                "data": f"message_{i}"
            })
        
        # Check queue
        messages = self.ws_manager.get_message_queue(limit=3)
        assert len(messages) == 3
        assert messages[-1]["data"] == "message_4"
    
    @patch('websocket_manager.BybitWebSocket')
    def test_connect(self, mock_ws_class):
        """Test connection establishment"""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        
        self.ws_manager.connect()
        
        # Check connection flag
        assert self.ws_manager.is_connected == True
        assert self.ws_manager.reconnect_attempts == 0
    
    def test_disconnect(self):
        """Test disconnection"""
        # Mock connections
        self.ws_manager.ws_public = Mock()
        self.ws_manager.ws_private = Mock()
        self.ws_manager.is_connected = True
        
        # Add some subscriptions
        self.ws_manager.subscriptions["test"] = {"type": "test"}
        
        # Disconnect
        self.ws_manager.disconnect()
        
        # Check state
        assert self.ws_manager.is_connected == False
        assert len(self.ws_manager.subscriptions) == 0
        assert self.ws_manager.ws_public.exit.called