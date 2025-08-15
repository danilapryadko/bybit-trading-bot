#!/usr/bin/env python3
"""
Integrated Data Service - Combines WebSocket and REST API polling
Falls back to REST API when WebSocket fails
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import aiohttp
from pybit.unified_trading import WebSocket as BybitWebSocket

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntegratedDataService:
    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        self.base_url = "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
        self.callbacks = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws = None
        self.ws_connected = False
        self.use_websocket = True  # Try WebSocket first
        self.running = False
        
        # Polling intervals for REST API (in seconds)
        self.polling_intervals = {
            'ticker': 2,
            'orderbook': 5,
            'trades': 3,
            'kline': 10,
        }
        
    async def start(self):
        """Start the integrated data service"""
        self.running = True
        self.session = aiohttp.ClientSession()
        
        # Try to connect WebSocket first
        await self._connect_websocket()
        
        # Start monitoring and fallback tasks
        tasks = [
            self._monitor_connection(),
            self._rest_api_fallback(),
        ]
        
        await asyncio.gather(*tasks)
        
    async def stop(self):
        """Stop the service"""
        self.running = False
        
        if self.ws:
            try:
                self.ws.exit()
            except:
                pass
                
        if self.session:
            await self.session.close()
            
    def register_callback(self, data_type: str, callback: Callable):
        """Register callback for data updates"""
        if data_type not in self.callbacks:
            self.callbacks[data_type] = []
        self.callbacks[data_type].append(callback)
        logger.info(f"Registered callback for {data_type}")
        
    async def _trigger_callbacks(self, data_type: str, data: Any):
        """Trigger registered callbacks"""
        if data_type in self.callbacks:
            for callback in self.callbacks[data_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Callback error for {data_type}: {e}")
                    
    async def _connect_websocket(self):
        """Connect to Bybit WebSocket"""
        if not self.use_websocket:
            return
            
        try:
            logger.info("Attempting WebSocket connection...")
            
            # Create WebSocket instance
            self.ws = BybitWebSocket(
                testnet=self.testnet,
                channel_type="linear",
            )
            
            # Define handlers
            def handle_ticker(message):
                try:
                    data = message['data']
                    formatted = {
                        'symbol': data['symbol'],
                        'lastPrice': float(data['lastPrice']),
                        'bidPrice': float(data['bid1Price']),
                        'askPrice': float(data['ask1Price']),
                        'volume24h': float(data['volume24h']),
                        'price24hPcnt': float(data['price24hPcnt']) * 100,
                        'timestamp': datetime.now().isoformat(),
                    }
                    asyncio.create_task(self._trigger_callbacks('ticker', formatted))
                except Exception as e:
                    logger.error(f"WebSocket ticker error: {e}")
                    
            def handle_orderbook(message):
                try:
                    data = message['data']
                    formatted = {
                        'symbol': data['s'],
                        'bids': [[float(b[0]), float(b[1])] for b in data.get('b', [])[:10]],
                        'asks': [[float(a[0]), float(a[1])] for a in data.get('a', [])[:10]],
                        'timestamp': data['ts'],
                    }
                    asyncio.create_task(self._trigger_callbacks('orderbook', formatted))
                except Exception as e:
                    logger.error(f"WebSocket orderbook error: {e}")
                    
            def handle_trade(message):
                try:
                    for trade in message['data']:
                        formatted = {
                            'symbol': trade['s'],
                            'price': float(trade['p']),
                            'size': float(trade['v']),
                            'side': trade['S'],
                            'timestamp': trade['T'],
                        }
                        asyncio.create_task(self._trigger_callbacks('trade', formatted))
                except Exception as e:
                    logger.error(f"WebSocket trade error: {e}")
                    
            # Subscribe to streams
            for symbol in self.symbols:
                self.ws.ticker_stream(
                    symbol=symbol,
                    callback=handle_ticker
                )
                
                self.ws.orderbook_stream(
                    depth=25,
                    symbol=symbol,
                    callback=handle_orderbook
                )
                
                self.ws.trade_stream(
                    symbol=symbol,
                    callback=handle_trade
                )
                
            self.ws_connected = True
            logger.info("WebSocket connected successfully")
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self.ws_connected = False
            self.use_websocket = False  # Disable WebSocket and use REST API
            
    async def _monitor_connection(self):
        """Monitor WebSocket connection and reconnect if needed"""
        while self.running:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            if self.use_websocket and not self.ws_connected:
                logger.info("WebSocket disconnected, attempting reconnection...")
                await self._connect_websocket()
                
    async def _rest_api_fallback(self):
        """REST API polling as fallback"""
        while self.running:
            # Only use REST API if WebSocket is not connected
            if not self.ws_connected:
                await asyncio.gather(
                    self._poll_tickers(),
                    self._poll_orderbooks(),
                    self._poll_trades(),
                    asyncio.sleep(1),  # Prevent tight loop
                )
            else:
                await asyncio.sleep(5)  # Check again in 5 seconds
                
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make REST API request"""
        if not self.session:
            return None
            
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.get(url, params=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        return data.get('result', {})
                    else:
                        logger.error(f"API error: {data.get('retMsg')}")
                elif response.status == 403:
                    logger.error(f"Access forbidden (403) - may need VPN or different region")
                else:
                    logger.error(f"HTTP error {response.status}")
        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {endpoint}")
        except Exception as e:
            logger.error(f"Request error: {e}")
            
        return None
        
    async def _poll_tickers(self):
        """Poll ticker data via REST API"""
        for symbol in self.symbols:
            data = await self._make_request(
                "/v5/market/tickers",
                params={'category': 'linear', 'symbol': symbol}
            )
            
            if data and 'list' in data and data['list']:
                ticker = data['list'][0]
                formatted = {
                    'symbol': ticker['symbol'],
                    'lastPrice': float(ticker['lastPrice']),
                    'bidPrice': float(ticker['bid1Price']),
                    'askPrice': float(ticker['ask1Price']),
                    'volume24h': float(ticker['volume24h']),
                    'price24hPcnt': float(ticker['price24hPcnt']) * 100,
                    'highPrice24h': float(ticker['highPrice24h']),
                    'lowPrice24h': float(ticker['lowPrice24h']),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'REST',  # Indicate data source
                }
                
                await self._trigger_callbacks('ticker', formatted)
                logger.debug(f"REST ticker {symbol}: ${formatted['lastPrice']:.2f}")
                
    async def _poll_orderbooks(self):
        """Poll orderbook data via REST API"""
        for symbol in self.symbols:
            data = await self._make_request(
                "/v5/market/orderbook",
                params={'category': 'linear', 'symbol': symbol, 'limit': 25}
            )
            
            if data:
                formatted = {
                    'symbol': symbol,
                    'bids': [[float(b[0]), float(b[1])] for b in data.get('b', [])[:10]],
                    'asks': [[float(a[0]), float(a[1])] for a in data.get('a', [])[:10]],
                    'timestamp': data.get('ts', datetime.now().timestamp() * 1000),
                    'source': 'REST',
                }
                
                await self._trigger_callbacks('orderbook', formatted)
                
    async def _poll_trades(self):
        """Poll recent trades via REST API"""
        for symbol in self.symbols:
            data = await self._make_request(
                "/v5/market/recent-trade",
                params={'category': 'linear', 'symbol': symbol, 'limit': 10}
            )
            
            if data and 'list' in data:
                for trade in data['list'][:5]:
                    formatted = {
                        'symbol': symbol,
                        'price': float(trade['price']),
                        'size': float(trade['size']),
                        'side': trade['side'],
                        'timestamp': int(trade['time']),
                        'source': 'REST',
                    }
                    
                    await self._trigger_callbacks('trade', formatted)
                    
    def get_data_source(self) -> str:
        """Get current data source"""
        if self.ws_connected:
            return "WebSocket"
        else:
            return "REST API"
            
    def get_status(self) -> Dict:
        """Get service status"""
        return {
            'running': self.running,
            'websocket_connected': self.ws_connected,
            'data_source': self.get_data_source(),
            'symbols': self.symbols,
            'timestamp': datetime.now().isoformat(),
        }


async def main():
    """Test the integrated data service"""
    service = IntegratedDataService(testnet=True)
    
    # Register callbacks
    def on_ticker(data):
        source = data.get('source', 'WS')
        print(f"[{source}] Ticker {data['symbol']}: ${data['lastPrice']:.2f}")
        
    def on_orderbook(data):
        if data['bids'] and data['asks']:
            source = data.get('source', 'WS')
            print(f"[{source}] Orderbook {data['symbol']}: Bid ${data['bids'][0][0]:.2f} / Ask ${data['asks'][0][0]:.2f}")
            
    def on_trade(data):
        source = data.get('source', 'WS')
        print(f"[{source}] Trade {data['symbol']}: {data['side']} {data['size']} @ ${data['price']:.2f}")
        
    service.register_callback('ticker', on_ticker)
    service.register_callback('orderbook', on_orderbook)
    service.register_callback('trade', on_trade)
    
    try:
        print("Starting Integrated Data Service...")
        print("Will try WebSocket first, fallback to REST API if needed")
        print("Press Ctrl+C to stop\n")
        
        # Check status periodically
        async def status_checker():
            while True:
                await asyncio.sleep(10)
                status = service.get_status()
                print(f"\n=== Status: {status['data_source']} ===")
                
        # Run service and status checker
        await asyncio.gather(
            service.start(),
            status_checker(),
        )
        
    except KeyboardInterrupt:
        print("\nStopping...")
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())