#!/usr/bin/env python3
"""
Bybit REST API Poller - Fallback for WebSocket issues
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BybitRESTPoller:
    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        self.base_url = "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"
        self.session: Optional[aiohttp.ClientSession] = None
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
        self.polling_intervals = {
            'ticker': 2,  # seconds
            'orderbook': 5,
            'trades': 3,
            'kline': 10,
        }
        self.callbacks = {}
        self.running = False
        
    async def start(self):
        """Start polling"""
        self.session = aiohttp.ClientSession()
        self.running = True
        
        # Start polling tasks
        tasks = [
            self._poll_tickers(),
            self._poll_orderbooks(),
            self._poll_trades(),
            self._poll_klines(),
        ]
        
        await asyncio.gather(*tasks)
        
    async def stop(self):
        """Stop polling"""
        self.running = False
        if self.session:
            await self.session.close()
            
    def register_callback(self, data_type: str, callback):
        """Register callback for data updates"""
        if data_type not in self.callbacks:
            self.callbacks[data_type] = []
        self.callbacks[data_type].append(callback)
        
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
                    logger.error(f"Callback error: {e}")
                    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make API request"""
        if not self.session:
            return None
            
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        return data.get('result', {})
                    else:
                        logger.error(f"API error: {data.get('retMsg')}")
                else:
                    logger.error(f"HTTP error {response.status}: {await response.text()}")
        except Exception as e:
            logger.error(f"Request error: {e}")
            
        return None
        
    async def _poll_tickers(self):
        """Poll ticker data"""
        while self.running:
            try:
                for symbol in self.symbols:
                    data = await self._make_request(
                        "/v5/market/tickers",
                        params={'category': 'linear', 'symbol': symbol}
                    )
                    
                    if data and 'list' in data and data['list']:
                        ticker = data['list'][0]
                        formatted_ticker = {
                            'symbol': ticker['symbol'],
                            'lastPrice': float(ticker['lastPrice']),
                            'bidPrice': float(ticker['bid1Price']),
                            'askPrice': float(ticker['ask1Price']),
                            'volume24h': float(ticker['volume24h']),
                            'turnover24h': float(ticker['turnover24h']),
                            'price24hPcnt': float(ticker['price24hPcnt']) * 100,
                            'highPrice24h': float(ticker['highPrice24h']),
                            'lowPrice24h': float(ticker['lowPrice24h']),
                            'timestamp': datetime.now().isoformat(),
                        }
                        
                        await self._trigger_callbacks('ticker', formatted_ticker)
                        logger.info(f"Ticker {symbol}: ${formatted_ticker['lastPrice']:.2f}")
                        
                await asyncio.sleep(self.polling_intervals['ticker'])
                
            except Exception as e:
                logger.error(f"Ticker polling error: {e}")
                await asyncio.sleep(5)
                
    async def _poll_orderbooks(self):
        """Poll orderbook data"""
        while self.running:
            try:
                for symbol in self.symbols:
                    data = await self._make_request(
                        "/v5/market/orderbook",
                        params={'category': 'linear', 'symbol': symbol, 'limit': 25}
                    )
                    
                    if data:
                        orderbook = {
                            'symbol': symbol,
                            'bids': [[float(bid[0]), float(bid[1])] for bid in data.get('b', [])[:10]],
                            'asks': [[float(ask[0]), float(ask[1])] for ask in data.get('a', [])[:10]],
                            'timestamp': data.get('ts', datetime.now().timestamp() * 1000),
                        }
                        
                        await self._trigger_callbacks('orderbook', orderbook)
                        
                await asyncio.sleep(self.polling_intervals['orderbook'])
                
            except Exception as e:
                logger.error(f"Orderbook polling error: {e}")
                await asyncio.sleep(5)
                
    async def _poll_trades(self):
        """Poll recent trades"""
        while self.running:
            try:
                for symbol in self.symbols:
                    data = await self._make_request(
                        "/v5/market/recent-trade",
                        params={'category': 'linear', 'symbol': symbol, 'limit': 20}
                    )
                    
                    if data and 'list' in data:
                        for trade in data['list'][:5]:  # Last 5 trades
                            formatted_trade = {
                                'symbol': symbol,
                                'price': float(trade['price']),
                                'size': float(trade['size']),
                                'side': trade['side'],
                                'timestamp': int(trade['time']),
                            }
                            
                            await self._trigger_callbacks('trade', formatted_trade)
                            
                await asyncio.sleep(self.polling_intervals['trades'])
                
            except Exception as e:
                logger.error(f"Trades polling error: {e}")
                await asyncio.sleep(5)
                
    async def _poll_klines(self):
        """Poll kline/candlestick data"""
        while self.running:
            try:
                for symbol in self.symbols:
                    data = await self._make_request(
                        "/v5/market/kline",
                        params={
                            'category': 'linear',
                            'symbol': symbol,
                            'interval': '1',  # 1 minute
                            'limit': 2,
                        }
                    )
                    
                    if data and 'list' in data and data['list']:
                        kline = data['list'][0]  # Latest candle
                        formatted_kline = {
                            'symbol': symbol,
                            'interval': '1m',
                            'timestamp': int(kline[0]),
                            'open': float(kline[1]),
                            'high': float(kline[2]),
                            'low': float(kline[3]),
                            'close': float(kline[4]),
                            'volume': float(kline[5]),
                            'turnover': float(kline[6]),
                        }
                        
                        await self._trigger_callbacks('kline', formatted_kline)
                        
                await asyncio.sleep(self.polling_intervals['kline'])
                
            except Exception as e:
                logger.error(f"Kline polling error: {e}")
                await asyncio.sleep(5)
                
    async def get_account_info(self, api_key: str, api_secret: str) -> Optional[Dict]:
        """Get account information"""
        # This would require authentication
        # For now, return mock data
        return {
            'totalWalletBalance': 10000.0,
            'totalAvailableBalance': 8000.0,
            'totalMarginBalance': 2000.0,
            'totalInitialMargin': 1000.0,
            'totalMaintenanceMargin': 500.0,
        }
        
    async def get_positions(self, api_key: str, api_secret: str) -> List[Dict]:
        """Get open positions"""
        # This would require authentication
        # For now, return empty list
        return []
        
    async def place_order(self, order_params: Dict, api_key: str, api_secret: str) -> Optional[Dict]:
        """Place an order"""
        # This would require authentication and POST request
        # For now, return mock response
        logger.info(f"Mock order placed: {order_params}")
        return {
            'orderId': f"mock_{datetime.now().timestamp()}",
            'symbol': order_params.get('symbol'),
            'side': order_params.get('side'),
            'orderType': order_params.get('orderType'),
            'qty': order_params.get('qty'),
            'price': order_params.get('price'),
            'status': 'New',
        }


async def main():
    """Test the REST API poller"""
    poller = BybitRESTPoller(testnet=True)
    
    # Register callbacks
    def on_ticker(data):
        print(f"Ticker update: {data['symbol']} = ${data['lastPrice']:.2f}")
        
    def on_orderbook(data):
        if data['bids'] and data['asks']:
            print(f"Orderbook {data['symbol']}: Bid ${data['bids'][0][0]:.2f} / Ask ${data['asks'][0][0]:.2f}")
            
    def on_trade(data):
        print(f"Trade {data['symbol']}: {data['side']} {data['size']} @ ${data['price']:.2f}")
        
    def on_kline(data):
        print(f"Kline {data['symbol']}: O:{data['open']:.2f} H:{data['high']:.2f} L:{data['low']:.2f} C:{data['close']:.2f}")
        
    poller.register_callback('ticker', on_ticker)
    poller.register_callback('orderbook', on_orderbook)
    poller.register_callback('trade', on_trade)
    poller.register_callback('kline', on_kline)
    
    try:
        print("Starting Bybit REST API poller...")
        print("Press Ctrl+C to stop")
        await poller.start()
    except KeyboardInterrupt:
        print("\nStopping...")
        await poller.stop()


if __name__ == "__main__":
    asyncio.run(main())