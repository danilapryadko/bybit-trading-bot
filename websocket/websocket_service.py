"""
WebSocket Service for Application Integration
Manages WebSocket connections and broadcasts updates
"""

import asyncio
import logging
import json
import os
from typing import Dict, Any, List, Set, Optional
from datetime import datetime

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

from .websocket_client import WebSocketClient

logger = logging.getLogger(__name__)

class WebSocketService:
    """Service for managing WebSocket connections and broadcasting updates"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.client = None
            self.redis_client = None
            self.subscribed_symbols = set()
            self.connected_clients = set()
            self.broadcast_task = None
            self.initialized = True
    
    async def initialize(self):
        """Initialize WebSocket service"""
        try:
            # Initialize WebSocket client
            self.client = WebSocketClient(
                api_key=os.getenv('BYBIT_API_KEY'),
                api_secret=os.getenv('BYBIT_API_SECRET'),
                testnet=os.getenv('BYBIT_TESTNET', 'false').lower() == 'true'
            )
            
            # Connect to WebSocket
            await self.client.connect()
            
            # Initialize Redis for pub/sub (optional)
            try:
                if redis:
                    self.redis_client = await redis.from_url(
                        os.getenv('REDIS_URL', "redis://localhost"),
                        encoding="utf-8",
                        decode_responses=True
                    )
                else:
                    logger.warning("Redis module not available")
            except:
                logger.warning("Redis not available, using in-memory broadcasting")
            
            # Register update handler
            self.client.on_update(self._handle_update)
            
            # Subscribe to private channels
            await self.client.subscribe_private_data()
            
            # Start broadcast task
            self.broadcast_task = asyncio.create_task(self._broadcast_loop())
            
            logger.info("WebSocket service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket service: {e}")
            raise
    
    async def subscribe_symbols(self, symbols: List[str]):
        """Subscribe to market data for symbols"""
        new_symbols = set(symbols) - self.subscribed_symbols
        
        if new_symbols:
            await self.client.subscribe_market_data(list(new_symbols))
            self.subscribed_symbols.update(new_symbols)
            logger.info(f"Subscribed to symbols: {new_symbols}")
    
    async def unsubscribe_symbols(self, symbols: List[str]):
        """Unsubscribe from market data for symbols"""
        # This would need implementation in WebSocket manager
        for symbol in symbols:
            if symbol in self.subscribed_symbols:
                self.subscribed_symbols.remove(symbol)
        
        logger.info(f"Unsubscribed from symbols: {symbols}")
    
    async def _handle_update(self, update: Dict[str, Any]):
        """Handle WebSocket update"""
        try:
            # Broadcast via Redis if available
            if self.redis_client:
                channel = f"ws:{update['type']}:{update['symbol']}"
                await self.redis_client.publish(channel, json.dumps(update))
            
            # Direct broadcast to connected clients
            await self._broadcast_to_clients(update)
            
        except Exception as e:
            logger.error(f"Error handling update: {e}")
    
    async def _broadcast_to_clients(self, update: Dict[str, Any]):
        """Broadcast update to all connected clients"""
        if not self.connected_clients:
            return
        
        # Create tasks for all client broadcasts
        tasks = []
        disconnected = set()
        
        for client in self.connected_clients:
            try:
                tasks.append(client.send(update))
            except:
                disconnected.add(client)
        
        # Remove disconnected clients
        self.connected_clients -= disconnected
        
        # Execute all broadcasts concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _broadcast_loop(self):
        """Main broadcast loop for periodic updates"""
        while True:
            try:
                # Broadcast market summaries every second
                await asyncio.sleep(1)
                
                # Get all subscribed symbols
                for symbol in self.subscribed_symbols:
                    summary = self.client.get_market_summary(symbol)
                    
                    if summary.get("last_price"):
                        update = {
                            "type": "market_summary",
                            "symbol": symbol,
                            "data": summary,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        await self._broadcast_to_clients(update)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Broadcast loop error: {e}")
                await asyncio.sleep(5)
    
    def register_client(self, client):
        """Register a client for updates"""
        self.connected_clients.add(client)
        logger.info(f"Client registered. Total clients: {len(self.connected_clients)}")
    
    def unregister_client(self, client):
        """Unregister a client"""
        if client in self.connected_clients:
            self.connected_clients.remove(client)
            logger.info(f"Client unregistered. Total clients: {len(self.connected_clients)}")
    
    def get_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current orderbook for symbol"""
        if self.client:
            return self.client.get_orderbook(symbol)
        return None
    
    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current ticker for symbol"""
        if self.client:
            return self.client.get_ticker(symbol)
        return None
    
    def get_trade_history(self, symbol: str) -> List[Dict[str, Any]]:
        """Get trade history for symbol"""
        if self.client:
            return self.client.get_trade_history(symbol)
        return []
    
    def get_klines(self, symbol: str, interval: str = "1") -> List[Dict[str, Any]]:
        """Get kline data for symbol"""
        if self.client:
            return self.client.get_klines(symbol, interval)
        return []
    
    def get_positions(self) -> Dict[str, Any]:
        """Get all current positions"""
        if self.client:
            return self.client.get_positions()
        return {}
    
    def get_orders(self) -> Dict[str, Any]:
        """Get all current orders"""
        if self.client:
            return self.client.get_orders()
        return {}
    
    def get_wallet_balance(self) -> Dict[str, Any]:
        """Get wallet balance"""
        if self.client:
            return self.client.get_wallet_balance()
        return {}
    
    def get_market_summary(self, symbol: str) -> Dict[str, Any]:
        """Get complete market summary for symbol"""
        if self.client:
            return self.client.get_market_summary(symbol)
        return {}
    
    def get_all_market_summaries(self) -> Dict[str, Any]:
        """Get market summaries for all subscribed symbols"""
        summaries = {}
        
        for symbol in self.subscribed_symbols:
            summaries[symbol] = self.get_market_summary(symbol)
        
        return summaries
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get WebSocket statistics"""
        stats = {
            "subscribed_symbols": list(self.subscribed_symbols),
            "connected_clients": len(self.connected_clients),
            "service_status": "running" if self.client else "stopped"
        }
        
        if self.client:
            stats.update(self.client.get_statistics())
        
        return stats
    
    async def shutdown(self):
        """Shutdown WebSocket service"""
        try:
            # Cancel broadcast task
            if self.broadcast_task:
                self.broadcast_task.cancel()
                await asyncio.gather(self.broadcast_task, return_exceptions=True)
            
            # Disconnect WebSocket
            if self.client:
                await self.client.disconnect()
            
            # Close Redis connection
            if self.redis_client:
                await self.redis_client.close()
            
            logger.info("WebSocket service shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Global service instance
websocket_service = WebSocketService()

async def get_websocket_service() -> WebSocketService:
    """Get WebSocket service instance"""
    if not hasattr(websocket_service, 'client') or websocket_service.client is None:
        await websocket_service.initialize()
    return websocket_service