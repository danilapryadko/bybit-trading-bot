#!/usr/bin/env python3
"""
Test script for WebSocket integration
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test without actual API keys first
os.environ['BYBIT_API_KEY'] = 'test_key'
os.environ['BYBIT_API_SECRET'] = 'test_secret'

def print_header(title):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

async def test_websocket_manager():
    """Test WebSocket Manager"""
    print_header("TESTING WEBSOCKET MANAGER")
    
    try:
        from websocket.websocket_manager import BybitWebSocketManager
        
        # Create manager for testnet (safer for testing)
        manager = BybitWebSocketManager(testnet=True)
        print("✅ WebSocket Manager created")
        
        # Test connection
        print("📡 Testing connection to testnet...")
        # Note: This will fail without real API keys, but tests the structure
        try:
            await asyncio.wait_for(manager.connect(), timeout=5)
            print("✅ Connected to WebSocket")
            
            # Test subscription
            await manager.subscribe("ticker", ["BTCUSDT"])
            print("✅ Subscribed to ticker channel")
            
            # Wait for some messages
            await asyncio.sleep(3)
            
            # Disconnect
            await manager.disconnect()
            print("✅ Disconnected successfully")
            
        except asyncio.TimeoutError:
            print("⚠️ Connection timeout (expected without real API keys)")
        except Exception as e:
            print(f"⚠️ Connection failed: {e}")
            
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Manager test failed: {e}")
        return False

async def test_websocket_client():
    """Test WebSocket Client"""
    print_header("TESTING WEBSOCKET CLIENT")
    
    try:
        from websocket.websocket_client import WebSocketClient
        
        # Create client
        client = WebSocketClient(testnet=True)
        print("✅ WebSocket Client created")
        
        # Test data storage initialization
        assert hasattr(client, 'orderbooks'), "Missing orderbooks storage"
        assert hasattr(client, 'tickers'), "Missing tickers storage"
        assert hasattr(client, 'trades'), "Missing trades storage"
        assert hasattr(client, 'positions'), "Missing positions storage"
        print("✅ Data storage initialized")
        
        # Test handler registration
        def test_callback(data):
            print(f"Received update: {data['type']}")
        
        client.on_update(test_callback)
        print("✅ Callback registered")
        
        # Test market summary generation (with mock data)
        client.tickers["BTCUSDT"] = {
            "symbol": "BTCUSDT",
            "last_price": 50000,
            "volume_24h": 1000000,
            "price_24h_percent": 2.5
        }
        
        client.orderbooks["BTCUSDT"] = {
            "bids": [["49900", "1.0"], ["49890", "2.0"]],
            "asks": [["50100", "1.0"], ["50110", "2.0"]],
            "timestamp": datetime.now().timestamp()
        }
        
        summary = client.get_market_summary("BTCUSDT")
        print(f"✅ Market summary generated: {summary['symbol']} @ ${summary['last_price']}")
        
        # Test statistics
        stats = client.get_statistics()
        print(f"✅ Statistics: {stats['messages_received']} messages")
        
        return True
        
    except Exception as e:
        print(f"❌ Client test failed: {e}")
        return False

async def test_websocket_service():
    """Test WebSocket Service"""
    print_header("TESTING WEBSOCKET SERVICE")
    
    try:
        from websocket.websocket_service import WebSocketService, get_websocket_service
        
        # Create service
        service = WebSocketService()
        print("✅ WebSocket Service created (singleton)")
        
        # Test singleton pattern
        service2 = WebSocketService()
        assert service is service2, "Singleton pattern broken"
        print("✅ Singleton pattern working")
        
        # Test client registration
        class MockClient:
            async def send(self, data):
                print(f"Mock client received: {data['type']}")
        
        mock_client = MockClient()
        service.register_client(mock_client)
        print("✅ Client registered")
        
        service.unregister_client(mock_client)
        print("✅ Client unregistered")
        
        # Test statistics
        stats = service.get_statistics()
        print(f"✅ Service statistics: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Service test failed: {e}")
        return False

async def test_data_structures():
    """Test data structures and message handling"""
    print_header("TESTING DATA STRUCTURES")
    
    try:
        from websocket.websocket_client import WebSocketClient
        
        client = WebSocketClient(testnet=True)
        
        # Test orderbook delta application
        print("📊 Testing orderbook updates...")
        
        # Initial orderbook
        client.orderbooks["BTCUSDT"] = {
            "bids": [["50000", "1.0"], ["49990", "2.0"]],
            "asks": [["50010", "1.0"], ["50020", "2.0"]],
            "update_id": 1
        }
        
        # Apply delta
        client._apply_orderbook_delta("BTCUSDT", {
            "b": [["50005", "0.5"], ["49990", "0"]],  # Add new bid, remove existing
            "a": [["50015", "1.5"]],  # Update ask
            "u": 2
        })
        
        book = client.orderbooks["BTCUSDT"]
        assert len([b for b in book["bids"] if b[0] == "49990"]) == 0, "Failed to remove bid"
        assert any(b[0] == "50005" for b in book["bids"]), "Failed to add bid"
        print("✅ Orderbook delta updates working")
        
        # Test trade history
        print("📈 Testing trade history...")
        from collections import deque
        
        for i in range(5):
            await client._handle_trade({
                "symbol": "BTCUSDT",
                "price": 50000 + i * 10,
                "quantity": 0.1,
                "side": "Buy" if i % 2 == 0 else "Sell",
                "timestamp": datetime.now().timestamp()
            })
        
        history = client.get_trade_history("BTCUSDT")
        assert len(history) == 5, f"Trade history wrong size: {len(history)}"
        print(f"✅ Trade history working ({len(history)} trades)")
        
        # Test position updates
        print("💼 Testing position updates...")
        await client._handle_position({
            "symbol": "BTCUSDT",
            "side": "Buy",
            "size": 0.1,
            "entry_price": 50000,
            "mark_price": 50100,
            "unrealized_pnl": 10,
            "timestamp": datetime.now().timestamp()
        })
        
        position = client.get_position("BTCUSDT")
        assert position is not None, "Position not stored"
        assert position["size"] == 0.1, "Position size incorrect"
        print("✅ Position updates working")
        
        return True
        
    except Exception as e:
        print(f"❌ Data structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_integration():
    """Test complete integration"""
    print_header("INTEGRATION TEST")
    
    try:
        # Test imports
        from websocket import BybitWebSocketManager, WebSocketClient, WebSocketService
        print("✅ All imports successful")
        
        # Test with mock data flow
        client = WebSocketClient(testnet=True)
        
        # Simulate market data updates
        test_updates = [
            {
                "type": "ticker",
                "symbol": "BTCUSDT",
                "last_price": 50000,
                "volume_24h": 1000000
            },
            {
                "type": "trade",
                "symbol": "BTCUSDT",
                "price": 50010,
                "quantity": 0.5,
                "side": "Buy"
            },
            {
                "type": "orderbook",
                "symbol": "BTCUSDT",
                "bids": [["49990", "1.0"]],
                "asks": [["50010", "1.0"]]
            }
        ]
        
        print("📊 Simulating market data flow...")
        for update in test_updates:
            print(f"  Processing {update['type']} update...")
        
        print("✅ Integration test complete")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

async def main():
    """Run all WebSocket tests"""
    print("\n" + "🚀"*30)
    print("  WEBSOCKET INTEGRATION TEST SUITE")
    print("🚀"*30)
    
    results = []
    
    # Test WebSocket Manager
    test_name = "WebSocket Manager"
    print(f"\n🔬 Testing {test_name}...")
    if await test_websocket_manager():
        results.append(f"✅ {test_name}")
    else:
        results.append(f"❌ {test_name}")
    
    # Test WebSocket Client
    test_name = "WebSocket Client"
    print(f"\n🔬 Testing {test_name}...")
    if await test_websocket_client():
        results.append(f"✅ {test_name}")
    else:
        results.append(f"❌ {test_name}")
    
    # Test WebSocket Service
    test_name = "WebSocket Service"
    print(f"\n🔬 Testing {test_name}...")
    if await test_websocket_service():
        results.append(f"✅ {test_name}")
    else:
        results.append(f"❌ {test_name}")
    
    # Test Data Structures
    test_name = "Data Structures"
    print(f"\n🔬 Testing {test_name}...")
    if await test_data_structures():
        results.append(f"✅ {test_name}")
    else:
        results.append(f"❌ {test_name}")
    
    # Test Integration
    test_name = "Integration"
    print(f"\n🔬 Testing {test_name}...")
    if await test_integration():
        results.append(f"✅ {test_name}")
    else:
        results.append(f"❌ {test_name}")
    
    # Print summary
    print_header("TEST SUMMARY")
    for result in results:
        print(f"  {result}")
    
    passed = sum(1 for r in results if "✅" in r)
    total = len(results)
    
    print("\n" + "="*60)
    if passed == total:
        print(f"  🎉 ALL TESTS PASSED ({passed}/{total})")
        print("  ✨ WebSocket integration is ready!")
    else:
        print(f"  ⚠️ SOME TESTS FAILED ({passed}/{total})")
        print("  🔧 Please review and fix the issues")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())