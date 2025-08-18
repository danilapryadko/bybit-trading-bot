"""
WebSocket Manager for Bybit Real-time Data Streaming
Handles connections, subscriptions, and message routing
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
import websockets
import hmac
import hashlib
from collections import defaultdict

logger = logging.getLogger(__name__)

class BybitWebSocketManager:
    """Manages WebSocket connections to Bybit for real-time data"""
    
    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = False):
        """
        Initialize WebSocket Manager
        
        Args:
            api_key: Bybit API key for private endpoints
            api_secret: Bybit API secret for authentication
            testnet: Whether to use testnet
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        # WebSocket URLs
        if testnet:
            self.public_url = "wss://stream-testnet.bybit.com/v5/public/linear"
            self.private_url = "wss://stream-testnet.bybit.com/v5/private"
        else:
            self.public_url = "wss://stream.bybit.com/v5/public/linear"
            self.private_url = "wss://stream.bybit.com/v5/private"
        
        # Connection management
        self.public_ws = None
        self.private_ws = None
        self.is_connected = False
        self.is_authenticated = False
        
        # Subscription management
        self.subscriptions = defaultdict(list)
        self.callbacks = defaultdict(list)
        
        # Heartbeat
        self.last_ping = 0
        self.ping_interval = 20  # seconds
        
        # Reconnection
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        
    def _generate_signature(self) -> tuple:
        """Generate authentication signature for private endpoints"""
        expires = int((time.time() + 5) * 1000)
        signature_payload = f"GET/realtime{expires}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return expires, signature
    
    async def connect(self):
        """Establish WebSocket connections"""
        try:
            # Connect to public WebSocket
            logger.info("Connecting to Bybit public WebSocket...")
            self.public_ws = await websockets.connect(
                self.public_url,
                ping_interval=self.ping_interval,
                ping_timeout=10
            )
            
            # Connect to private WebSocket if credentials provided
            if self.api_key and self.api_secret:
                logger.info("Connecting to Bybit private WebSocket...")
                self.private_ws = await websockets.connect(
                    self.private_url,
                    ping_interval=self.ping_interval,
                    ping_timeout=10
                )
                
                # Authenticate private connection
                await self._authenticate()
            
            self.is_connected = True
            logger.info("WebSocket connections established")
            
            # Start message handlers
            asyncio.create_task(self._handle_public_messages())
            if self.private_ws:
                asyncio.create_task(self._handle_private_messages())
            
            # Start heartbeat
            asyncio.create_task(self._heartbeat())
            
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            await self._reconnect()
    
    async def _authenticate(self):
        """Authenticate private WebSocket connection"""
        try:
            expires, signature = self._generate_signature()
            
            auth_message = {
                "op": "auth",
                "args": [self.api_key, expires, signature]
            }
            
            await self.private_ws.send(json.dumps(auth_message))
            
            # Wait for authentication response
            response = await self.private_ws.recv()
            data = json.loads(response)
            
            if data.get("success"):
                self.is_authenticated = True
                logger.info("Private WebSocket authenticated successfully")
            else:
                logger.error(f"Authentication failed: {data}")
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
    
    async def subscribe(self, channel: str, symbols: List[str] = None, 
                       callback: Callable = None, private: bool = False):
        """
        Subscribe to WebSocket channel
        
        Args:
            channel: Channel name (e.g., 'orderbook', 'trade', 'ticker')
            symbols: List of trading symbols
            callback: Function to call with received data
            private: Whether this is a private channel
        """
        try:
            ws = self.private_ws if private else self.public_ws
            
            if not ws:
                logger.error(f"WebSocket not connected for {'private' if private else 'public'} channel")
                return
            
            # Build subscription message
            if channel in ['orderbook', 'trade', 'ticker', 'kline']:
                # Public channels
                topics = []
                for symbol in symbols or []:
                    if channel == 'kline':
                        topics.append(f"{channel}.1.{symbol}")  # 1 minute kline
                    else:
                        topics.append(f"{channel}.{symbol}")
                
                sub_message = {
                    "op": "subscribe",
                    "args": topics
                }
            else:
                # Private channels
                sub_message = {
                    "op": "subscribe",
                    "args": [channel]
                }
            
            # Send subscription
            await ws.send(json.dumps(sub_message))
            logger.info(f"Subscribed to {channel} for {symbols}")
            
            # Store subscription info
            for topic in sub_message["args"]:
                self.subscriptions[channel].append(topic)
                if callback:
                    self.callbacks[topic].append(callback)
            
        except Exception as e:
            logger.error(f"Subscription error: {e}")
    
    async def unsubscribe(self, channel: str, symbols: List[str] = None, private: bool = False):
        """Unsubscribe from WebSocket channel"""
        try:
            ws = self.private_ws if private else self.public_ws
            
            if not ws:
                return
            
            # Build unsubscription message
            topics = []
            for symbol in symbols or []:
                topics.append(f"{channel}.{symbol}")
            
            unsub_message = {
                "op": "unsubscribe",
                "args": topics
            }
            
            await ws.send(json.dumps(unsub_message))
            logger.info(f"Unsubscribed from {channel} for {symbols}")
            
            # Remove subscription info
            for topic in topics:
                if topic in self.subscriptions[channel]:
                    self.subscriptions[channel].remove(topic)
                if topic in self.callbacks:
                    del self.callbacks[topic]
            
        except Exception as e:
            logger.error(f"Unsubscription error: {e}")
    
    async def _handle_public_messages(self):
        """Handle incoming public WebSocket messages"""
        try:
            async for message in self.public_ws:
                await self._process_message(message, is_private=False)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Public WebSocket connection closed")
            await self._reconnect()
        except Exception as e:
            logger.error(f"Error handling public messages: {e}")
    
    async def _handle_private_messages(self):
        """Handle incoming private WebSocket messages"""
        try:
            async for message in self.private_ws:
                await self._process_message(message, is_private=True)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Private WebSocket connection closed")
            await self._reconnect()
        except Exception as e:
            logger.error(f"Error handling private messages: {e}")
    
    async def _process_message(self, message: str, is_private: bool):
        """Process incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            # Handle different message types
            if "topic" in data:
                topic = data["topic"]
                
                # Process data based on topic
                if "orderbook" in topic:
                    await self._process_orderbook(data)
                elif "trade" in topic:
                    await self._process_trade(data)
                elif "ticker" in topic:
                    await self._process_ticker(data)
                elif "kline" in topic:
                    await self._process_kline(data)
                elif "position" in topic:
                    await self._process_position(data)
                elif "execution" in topic:
                    await self._process_execution(data)
                elif "order" in topic:
                    await self._process_order(data)
                elif "wallet" in topic:
                    await self._process_wallet(data)
                
                # Call registered callbacks
                if topic in self.callbacks:
                    for callback in self.callbacks[topic]:
                        await callback(data)
            
            # Handle system messages
            elif "op" in data:
                if data["op"] == "pong":
                    logger.debug("Received pong")
                elif data["op"] == "subscribe":
                    if data.get("success"):
                        logger.info(f"Subscription successful: {data.get('req_id')}")
                    else:
                        logger.error(f"Subscription failed: {data}")
                elif data["op"] == "auth":
                    if data.get("success"):
                        self.is_authenticated = True
                        logger.info("Authentication successful")
                    else:
                        logger.error(f"Authentication failed: {data}")
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse message: {message}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def _process_orderbook(self, data: Dict[str, Any]):
        """Process orderbook update"""
        topic = data["topic"]
        symbol = topic.split(".")[-1]
        
        orderbook_data = {
            "symbol": symbol,
            "timestamp": data["ts"],
            "type": data["type"],  # snapshot or delta
            "data": data["data"]
        }
        
        # Emit to subscribers
        await self._emit_event("orderbook", orderbook_data)
    
    async def _process_trade(self, data: Dict[str, Any]):
        """Process trade update"""
        topic = data["topic"]
        symbol = topic.split(".")[-1]
        
        for trade in data["data"]:
            trade_data = {
                "symbol": symbol,
                "timestamp": trade["T"],
                "price": float(trade["p"]),
                "quantity": float(trade["v"]),
                "side": trade["S"],
                "trade_id": trade["i"]
            }
            
            # Emit to subscribers
            await self._emit_event("trade", trade_data)
    
    async def _process_ticker(self, data: Dict[str, Any]):
        """Process ticker update"""
        topic = data["topic"]
        symbol = topic.split(".")[-1]
        
        ticker = data["data"]
        ticker_data = {
            "symbol": symbol,
            "timestamp": data["ts"],
            "last_price": float(ticker.get("lastPrice", 0)),
            "bid_price": float(ticker.get("bid1Price", 0)),
            "ask_price": float(ticker.get("ask1Price", 0)),
            "volume_24h": float(ticker.get("volume24h", 0)),
            "turnover_24h": float(ticker.get("turnover24h", 0)),
            "price_24h_percent": float(ticker.get("price24hPcnt", 0))
        }
        
        # Emit to subscribers
        await self._emit_event("ticker", ticker_data)
    
    async def _process_kline(self, data: Dict[str, Any]):
        """Process kline/candlestick update"""
        topic = data["topic"]
        parts = topic.split(".")
        interval = parts[1]
        symbol = parts[2]
        
        for kline in data["data"]:
            kline_data = {
                "symbol": symbol,
                "interval": interval,
                "timestamp": kline["start"],
                "open": float(kline["open"]),
                "high": float(kline["high"]),
                "low": float(kline["low"]),
                "close": float(kline["close"]),
                "volume": float(kline["volume"]),
                "turnover": float(kline["turnover"]),
                "confirm": kline["confirm"]
            }
            
            # Emit to subscribers
            await self._emit_event("kline", kline_data)
    
    async def _process_position(self, data: Dict[str, Any]):
        """Process position update"""
        for position in data["data"]:
            position_data = {
                "symbol": position["symbol"],
                "side": position["side"],
                "size": float(position["size"]),
                "entry_price": float(position.get("avgPrice", 0)),
                "mark_price": float(position.get("markPrice", 0)),
                "unrealized_pnl": float(position.get("unrealisedPnl", 0)),
                "cumulative_pnl": float(position.get("cumRealisedPnl", 0)),
                "position_value": float(position.get("positionValue", 0)),
                "leverage": position.get("leverage", "1"),
                "timestamp": data["creationTime"]
            }
            
            # Emit to subscribers
            await self._emit_event("position", position_data)
    
    async def _process_execution(self, data: Dict[str, Any]):
        """Process execution/fill update"""
        for execution in data["data"]:
            execution_data = {
                "symbol": execution["symbol"],
                "order_id": execution["orderId"],
                "exec_id": execution["execId"],
                "side": execution["side"],
                "price": float(execution["execPrice"]),
                "quantity": float(execution["execQty"]),
                "exec_type": execution["execType"],
                "exec_value": float(execution.get("execValue", 0)),
                "exec_fee": float(execution.get("execFee", 0)),
                "timestamp": execution["execTime"]
            }
            
            # Emit to subscribers
            await self._emit_event("execution", execution_data)
    
    async def _process_order(self, data: Dict[str, Any]):
        """Process order update"""
        for order in data["data"]:
            order_data = {
                "symbol": order["symbol"],
                "order_id": order["orderId"],
                "side": order["side"],
                "order_type": order["orderType"],
                "price": float(order.get("price", 0)),
                "quantity": float(order["qty"]),
                "filled_qty": float(order.get("cumExecQty", 0)),
                "status": order["orderStatus"],
                "time_in_force": order.get("timeInForce"),
                "reduce_only": order.get("reduceOnly", False),
                "timestamp": order["createdTime"]
            }
            
            # Emit to subscribers
            await self._emit_event("order", order_data)
    
    async def _process_wallet(self, data: Dict[str, Any]):
        """Process wallet balance update"""
        for wallet in data["data"]:
            for coin_data in wallet.get("coin", []):
                wallet_data = {
                    "account_type": wallet["accountType"],
                    "coin": coin_data["coin"],
                    "free": float(coin_data.get("free", 0)),
                    "locked": float(coin_data.get("locked", 0)),
                    "total": float(coin_data.get("walletBalance", 0)),
                    "timestamp": data["creationTime"]
                }
                
                # Emit to subscribers
                await self._emit_event("wallet", wallet_data)
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit event to all registered listeners"""
        event_key = f"{event_type}.{data.get('symbol', 'all')}"
        
        # Call specific callbacks
        if event_key in self.callbacks:
            for callback in self.callbacks[event_key]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Error in callback for {event_key}: {e}")
        
        # Call general callbacks for event type
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Error in callback for {event_type}: {e}")
    
    async def _heartbeat(self):
        """Send periodic ping to keep connection alive"""
        while self.is_connected:
            try:
                # Send ping to public WebSocket
                if self.public_ws:
                    ping_message = {"op": "ping"}
                    await self.public_ws.send(json.dumps(ping_message))
                
                # Send ping to private WebSocket
                if self.private_ws:
                    ping_message = {"op": "ping"}
                    await self.private_ws.send(json.dumps(ping_message))
                
                self.last_ping = time.time()
                
                # Wait for next ping interval
                await asyncio.sleep(self.ping_interval)
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break
    
    async def _reconnect(self):
        """Reconnect to WebSocket after disconnection"""
        self.is_connected = False
        self.is_authenticated = False
        
        for attempt in range(self.max_reconnect_attempts):
            try:
                logger.info(f"Reconnection attempt {attempt + 1}/{self.max_reconnect_attempts}")
                await asyncio.sleep(self.reconnect_delay)
                
                await self.connect()
                
                # Resubscribe to all channels
                for channel, topics in self.subscriptions.items():
                    for topic in topics:
                        logger.info(f"Resubscribing to {topic}")
                        # Parse topic and resubscribe
                        # This would need proper implementation based on topic format
                
                break
                
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
                
                if attempt == self.max_reconnect_attempts - 1:
                    logger.error("Max reconnection attempts reached")
                    raise
    
    async def disconnect(self):
        """Disconnect WebSocket connections"""
        self.is_connected = False
        
        try:
            if self.public_ws:
                await self.public_ws.close()
                self.public_ws = None
            
            if self.private_ws:
                await self.private_ws.close()
                self.private_ws = None
            
            logger.info("WebSocket connections closed")
            
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {e}")
    
    def on(self, event: str, callback: Callable):
        """Register event listener"""
        self.callbacks[event].append(callback)
    
    def off(self, event: str, callback: Callable):
        """Remove event listener"""
        if event in self.callbacks and callback in self.callbacks[event]:
            self.callbacks[event].remove(callback)