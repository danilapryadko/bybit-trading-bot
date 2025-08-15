"""
WebSocket Manager for Bybit Trading Bot
Handles real-time market data streaming and connection management
"""

import asyncio
import json
import logging
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime
import websocket
import threading
from collections import deque
import time
from pybit.unified_trading import WebSocket as BybitWebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time market data"""
    
    def __init__(self, testnet: bool = True, api_key: str = None, api_secret: str = None):
        self.testnet = testnet
        self.api_key = api_key
        self.api_secret = api_secret
        self.ws_public = None
        self.ws_private = None
        self.subscriptions = {}
        self.callbacks = {}
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5
        self.message_queue = deque(maxlen=10000)
        self.last_ping = time.time()
        self.connection_lock = threading.Lock()
        
        # Data storage for real-time updates
        self.orderbook_data = {}
        self.ticker_data = {}
        self.trade_data = {}
        self.kline_data = {}
        
        logger.info(f"WebSocket Manager initialized. Testnet: {testnet}")
    
    def connect(self):
        """Establish WebSocket connections"""
        try:
            with self.connection_lock:
                # Public WebSocket for market data
                self.ws_public = BybitWebSocket(
                    testnet=self.testnet,
                    channel_type="spot"  # or "linear", "inverse", "option"
                )
                
                # Private WebSocket for account updates (if credentials provided)
                if self.api_key and self.api_secret:
                    self.ws_private = BybitWebSocket(
                        testnet=self.testnet,
                        channel_type="private",
                        api_key=self.api_key,
                        api_secret=self.api_secret
                    )
                
                self.is_connected = True
                self.reconnect_attempts = 0
                logger.info("WebSocket connections established successfully")
                
                # Start heartbeat thread
                self._start_heartbeat()
                
        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            self._handle_reconnect()
    
    def _start_heartbeat(self):
        """Start heartbeat thread to maintain connection"""
        def heartbeat():
            while self.is_connected:
                try:
                    current_time = time.time()
                    if current_time - self.last_ping > 20:  # Send ping every 20 seconds
                        if self.ws_public:
                            self.ws_public.ping()
                        if self.ws_private:
                            self.ws_private.ping()
                        self.last_ping = current_time
                    time.sleep(10)
                except Exception as e:
                    logger.error(f"Heartbeat error: {e}")
        
        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
    
    def _handle_reconnect(self):
        """Handle reconnection logic"""
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"Attempting to reconnect... (Attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
            time.sleep(self.reconnect_delay * self.reconnect_attempts)
            self.connect()
        else:
            logger.error("Max reconnection attempts reached. WebSocket connection failed.")
            self.is_connected = False
    
    def subscribe_orderbook(self, symbol: str, depth: int = 50, callback: Optional[Callable] = None):
        """Subscribe to orderbook updates"""
        try:
            if not self.ws_public:
                self.connect()
            
            def handle_orderbook(message):
                """Process orderbook updates"""
                try:
                    data = message.get("data", {})
                    symbol = data.get("s")
                    
                    # Store orderbook data
                    self.orderbook_data[symbol] = {
                        "bids": data.get("b", []),
                        "asks": data.get("a", []),
                        "timestamp": data.get("t"),
                        "update_id": data.get("u")
                    }
                    
                    # Execute callback if provided
                    if callback:
                        callback(self.orderbook_data[symbol])
                    
                    # Add to message queue
                    self.message_queue.append({
                        "type": "orderbook",
                        "symbol": symbol,
                        "data": self.orderbook_data[symbol],
                        "timestamp": datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing orderbook message: {e}")
            
            # Subscribe to orderbook stream
            self.ws_public.orderbook_stream(
                depth=depth,
                symbol=symbol,
                callback=handle_orderbook
            )
            
            self.subscriptions[f"orderbook_{symbol}"] = {
                "type": "orderbook",
                "symbol": symbol,
                "depth": depth,
                "callback": callback
            }
            
            logger.info(f"Subscribed to orderbook for {symbol} with depth {depth}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to orderbook: {e}")
    
    def subscribe_ticker(self, symbol: str, callback: Optional[Callable] = None):
        """Subscribe to ticker updates"""
        try:
            if not self.ws_public:
                self.connect()
            
            def handle_ticker(message):
                """Process ticker updates"""
                try:
                    data = message.get("data", {})
                    symbol = data.get("symbol")
                    
                    # Store ticker data
                    self.ticker_data[symbol] = {
                        "last_price": float(data.get("lastPrice", 0)),
                        "bid_price": float(data.get("bidPrice", 0)),
                        "ask_price": float(data.get("askPrice", 0)),
                        "volume_24h": float(data.get("volume24h", 0)),
                        "turnover_24h": float(data.get("turnover24h", 0)),
                        "price_24h_pcnt": float(data.get("price24hPcnt", 0)),
                        "high_24h": float(data.get("highPrice24h", 0)),
                        "low_24h": float(data.get("lowPrice24h", 0)),
                        "timestamp": data.get("t")
                    }
                    
                    # Execute callback if provided
                    if callback:
                        callback(self.ticker_data[symbol])
                    
                    # Add to message queue
                    self.message_queue.append({
                        "type": "ticker",
                        "symbol": symbol,
                        "data": self.ticker_data[symbol],
                        "timestamp": datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing ticker message: {e}")
            
            # Subscribe to ticker stream
            self.ws_public.ticker_stream(
                symbol=symbol,
                callback=handle_ticker
            )
            
            self.subscriptions[f"ticker_{symbol}"] = {
                "type": "ticker",
                "symbol": symbol,
                "callback": callback
            }
            
            logger.info(f"Subscribed to ticker for {symbol}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to ticker: {e}")
    
    def subscribe_trades(self, symbol: str, callback: Optional[Callable] = None):
        """Subscribe to trade updates"""
        try:
            if not self.ws_public:
                self.connect()
            
            def handle_trade(message):
                """Process trade updates"""
                try:
                    data = message.get("data", [])
                    
                    for trade in data:
                        trade_info = {
                            "symbol": trade.get("s"),
                            "price": float(trade.get("p", 0)),
                            "quantity": float(trade.get("v", 0)),
                            "timestamp": trade.get("t"),
                            "is_buyer_maker": trade.get("m", False),
                            "trade_id": trade.get("i")
                        }
                        
                        # Store latest trades (keep last 100)
                        if symbol not in self.trade_data:
                            self.trade_data[symbol] = deque(maxlen=100)
                        self.trade_data[symbol].append(trade_info)
                        
                        # Execute callback if provided
                        if callback:
                            callback(trade_info)
                        
                        # Add to message queue
                        self.message_queue.append({
                            "type": "trade",
                            "symbol": symbol,
                            "data": trade_info,
                            "timestamp": datetime.now().isoformat()
                        })
                    
                except Exception as e:
                    logger.error(f"Error processing trade message: {e}")
            
            # Subscribe to trade stream
            self.ws_public.trade_stream(
                symbol=symbol,
                callback=handle_trade
            )
            
            self.subscriptions[f"trades_{symbol}"] = {
                "type": "trades",
                "symbol": symbol,
                "callback": callback
            }
            
            logger.info(f"Subscribed to trades for {symbol}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to trades: {e}")
    
    def subscribe_kline(self, symbol: str, interval: str = "1m", callback: Optional[Callable] = None):
        """Subscribe to kline/candlestick updates"""
        try:
            if not self.ws_public:
                self.connect()
            
            def handle_kline(message):
                """Process kline updates"""
                try:
                    data = message.get("data", [])
                    
                    for kline in data:
                        kline_info = {
                            "symbol": kline.get("symbol"),
                            "interval": kline.get("interval"),
                            "open_time": kline.get("start"),
                            "open": float(kline.get("open", 0)),
                            "high": float(kline.get("high", 0)),
                            "low": float(kline.get("low", 0)),
                            "close": float(kline.get("close", 0)),
                            "volume": float(kline.get("volume", 0)),
                            "turnover": float(kline.get("turnover", 0)),
                            "confirm": kline.get("confirm", False)
                        }
                        
                        # Store kline data
                        key = f"{symbol}_{interval}"
                        if key not in self.kline_data:
                            self.kline_data[key] = deque(maxlen=500)
                        self.kline_data[key].append(kline_info)
                        
                        # Execute callback if provided
                        if callback:
                            callback(kline_info)
                        
                        # Add to message queue
                        self.message_queue.append({
                            "type": "kline",
                            "symbol": symbol,
                            "interval": interval,
                            "data": kline_info,
                            "timestamp": datetime.now().isoformat()
                        })
                    
                except Exception as e:
                    logger.error(f"Error processing kline message: {e}")
            
            # Subscribe to kline stream
            self.ws_public.kline_stream(
                interval=interval,
                symbol=symbol,
                callback=handle_kline
            )
            
            self.subscriptions[f"kline_{symbol}_{interval}"] = {
                "type": "kline",
                "symbol": symbol,
                "interval": interval,
                "callback": callback
            }
            
            logger.info(f"Subscribed to kline for {symbol} with interval {interval}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to kline: {e}")
    
    def subscribe_positions(self, callback: Optional[Callable] = None):
        """Subscribe to position updates (private)"""
        if not self.ws_private:
            logger.error("Private WebSocket not initialized. API credentials required.")
            return
        
        try:
            def handle_position(message):
                """Process position updates"""
                try:
                    data = message.get("data", [])
                    
                    for position in data:
                        position_info = {
                            "symbol": position.get("symbol"),
                            "side": position.get("side"),
                            "size": float(position.get("size", 0)),
                            "entry_price": float(position.get("entryPrice", 0)),
                            "mark_price": float(position.get("markPrice", 0)),
                            "unrealized_pnl": float(position.get("unrealisedPnl", 0)),
                            "realized_pnl": float(position.get("realisedPnl", 0)),
                            "margin": float(position.get("positionIM", 0)),
                            "leverage": float(position.get("leverage", 1)),
                            "timestamp": position.get("updatedTime")
                        }
                        
                        # Execute callback if provided
                        if callback:
                            callback(position_info)
                        
                        logger.info(f"Position update: {position_info}")
                    
                except Exception as e:
                    logger.error(f"Error processing position message: {e}")
            
            # Subscribe to position stream
            self.ws_private.position_stream(callback=handle_position)
            
            self.subscriptions["positions"] = {
                "type": "positions",
                "callback": callback
            }
            
            logger.info("Subscribed to position updates")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to positions: {e}")
    
    def subscribe_orders(self, callback: Optional[Callable] = None):
        """Subscribe to order updates (private)"""
        if not self.ws_private:
            logger.error("Private WebSocket not initialized. API credentials required.")
            return
        
        try:
            def handle_order(message):
                """Process order updates"""
                try:
                    data = message.get("data", [])
                    
                    for order in data:
                        order_info = {
                            "order_id": order.get("orderId"),
                            "symbol": order.get("symbol"),
                            "side": order.get("side"),
                            "order_type": order.get("orderType"),
                            "price": float(order.get("price", 0)),
                            "quantity": float(order.get("qty", 0)),
                            "filled_quantity": float(order.get("cumExecQty", 0)),
                            "status": order.get("orderStatus"),
                            "time_in_force": order.get("timeInForce"),
                            "reduce_only": order.get("reduceOnly", False),
                            "created_time": order.get("createdTime"),
                            "updated_time": order.get("updatedTime")
                        }
                        
                        # Execute callback if provided
                        if callback:
                            callback(order_info)
                        
                        logger.info(f"Order update: {order_info}")
                    
                except Exception as e:
                    logger.error(f"Error processing order message: {e}")
            
            # Subscribe to order stream
            self.ws_private.order_stream(callback=handle_order)
            
            self.subscriptions["orders"] = {
                "type": "orders",
                "callback": callback
            }
            
            logger.info("Subscribed to order updates")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to orders: {e}")
    
    def get_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current orderbook data"""
        return self.orderbook_data.get(symbol)
    
    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current ticker data"""
        return self.ticker_data.get(symbol)
    
    def get_recent_trades(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trades"""
        if symbol in self.trade_data:
            trades = list(self.trade_data[symbol])
            return trades[-limit:] if len(trades) > limit else trades
        return []
    
    def get_klines(self, symbol: str, interval: str = "1m", limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent klines"""
        key = f"{symbol}_{interval}"
        if key in self.kline_data:
            klines = list(self.kline_data[key])
            return klines[-limit:] if len(klines) > limit else klines
        return []
    
    def get_message_queue(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent messages from queue"""
        messages = list(self.message_queue)
        return messages[-limit:] if len(messages) > limit else messages
    
    def unsubscribe(self, subscription_key: str):
        """Unsubscribe from a data stream"""
        if subscription_key in self.subscriptions:
            del self.subscriptions[subscription_key]
            logger.info(f"Unsubscribed from {subscription_key}")
    
    def disconnect(self):
        """Disconnect WebSocket connections"""
        try:
            self.is_connected = False
            
            if self.ws_public:
                self.ws_public.exit()
                self.ws_public = None
            
            if self.ws_private:
                self.ws_private.exit()
                self.ws_private = None
            
            self.subscriptions.clear()
            self.callbacks.clear()
            
            logger.info("WebSocket connections closed")
            
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {e}")
    
    def __del__(self):
        """Cleanup on destruction"""
        self.disconnect()