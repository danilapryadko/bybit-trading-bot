"""
WebSocket Client for Real-time Data Integration
Provides high-level interface for application components
"""

import asyncio
import logging
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
import pandas as pd
from collections import deque, defaultdict

from .websocket_manager import BybitWebSocketManager

logger = logging.getLogger(__name__)

class WebSocketClient:
    """High-level WebSocket client for real-time data"""
    
    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = False):
        """
        Initialize WebSocket Client
        
        Args:
            api_key: Bybit API key
            api_secret: Bybit API secret
            testnet: Whether to use testnet
        """
        self.ws_manager = BybitWebSocketManager(api_key, api_secret, testnet)
        
        # Data storage
        self.orderbooks = {}
        self.tickers = {}
        self.trades = {}
        self.klines = {}
        self.positions = {}
        self.orders = {}
        self.wallet = {}
        
        # Trade history (limited)
        self.trade_history = defaultdict(lambda: deque(maxlen=1000))
        
        # Callbacks for UI updates
        self.update_callbacks = []
        
        # Statistics
        self.stats = {
            "messages_received": 0,
            "last_update": None,
            "connected_since": None
        }
        
    async def connect(self):
        """Connect to WebSocket and setup handlers"""
        try:
            await self.ws_manager.connect()
            self.stats["connected_since"] = datetime.now()
            
            # Register internal handlers
            self._register_handlers()
            
            logger.info("WebSocket client connected")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket client: {e}")
            return False
    
    def _register_handlers(self):
        """Register internal data handlers"""
        # Public data handlers
        self.ws_manager.on("orderbook", self._handle_orderbook)
        self.ws_manager.on("trade", self._handle_trade)
        self.ws_manager.on("ticker", self._handle_ticker)
        self.ws_manager.on("kline", self._handle_kline)
        
        # Private data handlers
        self.ws_manager.on("position", self._handle_position)
        self.ws_manager.on("order", self._handle_order)
        self.ws_manager.on("execution", self._handle_execution)
        self.ws_manager.on("wallet", self._handle_wallet)
    
    async def subscribe_market_data(self, symbols: List[str], channels: List[str] = None):
        """
        Subscribe to market data for symbols
        
        Args:
            symbols: List of trading symbols
            channels: List of channels to subscribe (default: all)
        """
        if channels is None:
            channels = ["orderbook", "trade", "ticker", "kline"]
        
        for channel in channels:
            await self.ws_manager.subscribe(channel, symbols)
            logger.info(f"Subscribed to {channel} for {symbols}")
    
    async def subscribe_private_data(self):
        """Subscribe to private account data"""
        private_channels = ["position", "order", "execution", "wallet"]
        
        for channel in private_channels:
            await self.ws_manager.subscribe(channel, private=True)
            logger.info(f"Subscribed to private channel: {channel}")
    
    async def _handle_orderbook(self, data: Dict[str, Any]):
        """Handle orderbook updates"""
        symbol = data["symbol"]
        
        if data["type"] == "snapshot":
            # Full orderbook snapshot
            self.orderbooks[symbol] = {
                "bids": data["data"].get("b", []),
                "asks": data["data"].get("a", []),
                "timestamp": data["timestamp"],
                "update_id": data["data"].get("u", 0)
            }
        else:
            # Delta update
            if symbol in self.orderbooks:
                # Apply delta updates
                self._apply_orderbook_delta(symbol, data["data"])
        
        self.stats["messages_received"] += 1
        self.stats["last_update"] = datetime.now()
        
        # Notify listeners
        await self._notify_update("orderbook", symbol, self.orderbooks[symbol])
    
    async def _handle_trade(self, data: Dict[str, Any]):
        """Handle trade updates"""
        symbol = data["symbol"]
        
        # Store latest trade
        self.trades[symbol] = data
        
        # Add to history
        self.trade_history[symbol].append({
            "price": data["price"],
            "quantity": data["quantity"],
            "side": data["side"],
            "timestamp": data["timestamp"]
        })
        
        self.stats["messages_received"] += 1
        self.stats["last_update"] = datetime.now()
        
        # Notify listeners
        await self._notify_update("trade", symbol, data)
    
    async def _handle_ticker(self, data: Dict[str, Any]):
        """Handle ticker updates"""
        symbol = data["symbol"]
        
        # Update ticker data
        self.tickers[symbol] = data
        
        self.stats["messages_received"] += 1
        self.stats["last_update"] = datetime.now()
        
        # Notify listeners
        await self._notify_update("ticker", symbol, data)
    
    async def _handle_kline(self, data: Dict[str, Any]):
        """Handle kline/candlestick updates"""
        symbol = data["symbol"]
        interval = data["interval"]
        
        # Store kline data
        key = f"{symbol}_{interval}"
        if key not in self.klines:
            self.klines[key] = []
        
        # Update or append kline
        if data["confirm"]:
            # Completed candle
            self.klines[key].append(data)
            # Keep only last 1000 candles
            if len(self.klines[key]) > 1000:
                self.klines[key] = self.klines[key][-1000:]
        else:
            # Update current candle
            if self.klines[key]:
                self.klines[key][-1] = data
            else:
                self.klines[key].append(data)
        
        self.stats["messages_received"] += 1
        self.stats["last_update"] = datetime.now()
        
        # Notify listeners
        await self._notify_update("kline", symbol, data)
    
    async def _handle_position(self, data: Dict[str, Any]):
        """Handle position updates"""
        symbol = data["symbol"]
        
        # Update position data
        self.positions[symbol] = data
        
        self.stats["messages_received"] += 1
        self.stats["last_update"] = datetime.now()
        
        # Notify listeners
        await self._notify_update("position", symbol, data)
    
    async def _handle_order(self, data: Dict[str, Any]):
        """Handle order updates"""
        order_id = data["order_id"]
        
        # Update order data
        self.orders[order_id] = data
        
        self.stats["messages_received"] += 1
        self.stats["last_update"] = datetime.now()
        
        # Notify listeners
        await self._notify_update("order", data["symbol"], data)
    
    async def _handle_execution(self, data: Dict[str, Any]):
        """Handle execution/fill updates"""
        self.stats["messages_received"] += 1
        self.stats["last_update"] = datetime.now()
        
        # Notify listeners
        await self._notify_update("execution", data["symbol"], data)
    
    async def _handle_wallet(self, data: Dict[str, Any]):
        """Handle wallet balance updates"""
        coin = data["coin"]
        
        # Update wallet data
        self.wallet[coin] = data
        
        self.stats["messages_received"] += 1
        self.stats["last_update"] = datetime.now()
        
        # Notify listeners
        await self._notify_update("wallet", coin, data)
    
    def _apply_orderbook_delta(self, symbol: str, delta: Dict[str, Any]):
        """Apply delta updates to orderbook"""
        if symbol not in self.orderbooks:
            return
        
        book = self.orderbooks[symbol]
        
        # Update bids
        for bid in delta.get("b", []):
            price, size = float(bid[0]), float(bid[1])
            if size == 0:
                # Remove price level
                book["bids"] = [b for b in book["bids"] if float(b[0]) != price]
            else:
                # Update or add price level
                updated = False
                for i, existing_bid in enumerate(book["bids"]):
                    if float(existing_bid[0]) == price:
                        book["bids"][i] = bid
                        updated = True
                        break
                if not updated:
                    book["bids"].append(bid)
        
        # Update asks
        for ask in delta.get("a", []):
            price, size = float(ask[0]), float(ask[1])
            if size == 0:
                # Remove price level
                book["asks"] = [a for a in book["asks"] if float(a[0]) != price]
            else:
                # Update or add price level
                updated = False
                for i, existing_ask in enumerate(book["asks"]):
                    if float(existing_ask[0]) == price:
                        book["asks"][i] = ask
                        updated = True
                        break
                if not updated:
                    book["asks"].append(ask)
        
        # Sort orderbook
        book["bids"].sort(key=lambda x: float(x[0]), reverse=True)
        book["asks"].sort(key=lambda x: float(x[0]))
        
        # Limit depth
        book["bids"] = book["bids"][:50]
        book["asks"] = book["asks"][:50]
        
        book["update_id"] = delta.get("u", book["update_id"])
    
    async def _notify_update(self, event_type: str, symbol: str, data: Dict[str, Any]):
        """Notify all registered callbacks about data update"""
        for callback in self.update_callbacks:
            try:
                update = {
                    "type": event_type,
                    "symbol": symbol,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                }
                
                if asyncio.iscoroutinefunction(callback):
                    await callback(update)
                else:
                    callback(update)
                    
            except Exception as e:
                logger.error(f"Error in update callback: {e}")
    
    def on_update(self, callback: Callable):
        """Register callback for data updates"""
        self.update_callbacks.append(callback)
    
    def get_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current orderbook for symbol"""
        return self.orderbooks.get(symbol)
    
    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current ticker for symbol"""
        return self.tickers.get(symbol)
    
    def get_latest_trade(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest trade for symbol"""
        return self.trades.get(symbol)
    
    def get_trade_history(self, symbol: str) -> List[Dict[str, Any]]:
        """Get trade history for symbol"""
        return list(self.trade_history.get(symbol, []))
    
    def get_klines(self, symbol: str, interval: str = "1") -> List[Dict[str, Any]]:
        """Get kline data for symbol"""
        key = f"{symbol}_{interval}"
        return self.klines.get(key, [])
    
    def get_positions(self) -> Dict[str, Any]:
        """Get all current positions"""
        return self.positions.copy()
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get position for specific symbol"""
        return self.positions.get(symbol)
    
    def get_orders(self) -> Dict[str, Any]:
        """Get all current orders"""
        return self.orders.copy()
    
    def get_wallet_balance(self, coin: str = None) -> Dict[str, Any]:
        """Get wallet balance"""
        if coin:
            return self.wallet.get(coin, {})
        return self.wallet.copy()
    
    def get_market_summary(self, symbol: str) -> Dict[str, Any]:
        """Get complete market summary for symbol"""
        ticker = self.get_ticker(symbol)
        orderbook = self.get_orderbook(symbol)
        latest_trade = self.get_latest_trade(symbol)
        
        summary = {
            "symbol": symbol,
            "last_price": ticker.get("last_price") if ticker else None,
            "bid": orderbook["bids"][0][0] if orderbook and orderbook.get("bids") else None,
            "ask": orderbook["asks"][0][0] if orderbook and orderbook.get("asks") else None,
            "spread": None,
            "volume_24h": ticker.get("volume_24h") if ticker else None,
            "price_change_24h": ticker.get("price_24h_percent") if ticker else None,
            "last_trade": latest_trade
        }
        
        # Calculate spread
        if summary["bid"] and summary["ask"]:
            summary["spread"] = float(summary["ask"]) - float(summary["bid"])
            summary["spread_percent"] = (summary["spread"] / float(summary["ask"])) * 100
        
        return summary
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get WebSocket statistics"""
        stats = self.stats.copy()
        stats["is_connected"] = self.ws_manager.is_connected
        stats["is_authenticated"] = self.ws_manager.is_authenticated
        stats["subscriptions"] = len(self.ws_manager.subscriptions)
        return stats
    
    async def disconnect(self):
        """Disconnect WebSocket"""
        await self.ws_manager.disconnect()
        logger.info("WebSocket client disconnected")