#!/usr/bin/env python3
"""
Real-time Bybit data connection for Telegram bot and GraphQL
Provides live market data from Bybit WebSocket
"""
import os
import json
import logging
import asyncio
from typing import Dict, Optional, Callable, List
from datetime import datetime
from pybit.unified_trading import WebSocket as BybitWebSocket
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BybitRealTimeData:
    """Real-time data manager for Bybit"""
    
    def __init__(self, testnet: bool = True):
        """Initialize Bybit real-time data connection"""
        self.testnet = testnet
        self.api_key = os.getenv('BYBIT_API_KEY', '')
        self.api_secret = os.getenv('BYBIT_API_SECRET', '')
        
        # Data storage
        self.tickers: Dict[str, dict] = {}
        self.orderbooks: Dict[str, dict] = {}
        self.trades: Dict[str, list] = {}
        self.klines: Dict[str, dict] = {}
        
        # WebSocket connection
        self.ws = None
        self.is_connected = False
        self.subscribed_symbols = set()
        
        # Callbacks
        self.callbacks = {
            'ticker': [],
            'orderbook': [],
            'trade': [],
            'kline': []
        }
        
        logger.info(f"Initialized Bybit real-time data (testnet={testnet})")
    
    def connect(self):
        """Connect to Bybit WebSocket"""
        try:
            # Create WebSocket connection (public data, no auth needed)
            self.ws = BybitWebSocket(
                testnet=self.testnet,
                channel_type="linear"  # Use linear for USDT perpetuals
            )
            
            self.is_connected = True
            logger.info("Connected to Bybit WebSocket")
            
            # Set up default subscriptions
            self.subscribe_default_symbols()
            
        except Exception as e:
            logger.error(f"Failed to connect to Bybit WebSocket: {e}")
            self.is_connected = False
    
    def subscribe_default_symbols(self):
        """Subscribe to default symbols"""
        default_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        for symbol in default_symbols:
            self.subscribe_ticker(symbol)
            self.subscribe_orderbook(symbol)
    
    def subscribe_ticker(self, symbol: str):
        """Subscribe to ticker updates"""
        if not self.ws or not self.is_connected:
            logger.warning("WebSocket not connected")
            return
        
        try:
            self.ws.ticker_stream(
                symbol=symbol,
                callback=lambda data: self._handle_ticker(symbol, data)
            )
            self.subscribed_symbols.add(symbol)
            logger.info(f"Subscribed to ticker for {symbol}")
        except Exception as e:
            logger.error(f"Failed to subscribe to ticker for {symbol}: {e}")
    
    def subscribe_orderbook(self, symbol: str, depth: int = 25):
        """Subscribe to orderbook updates"""
        if not self.ws or not self.is_connected:
            logger.warning("WebSocket not connected")
            return
        
        try:
            self.ws.orderbook_stream(
                depth=depth,
                symbol=symbol,
                callback=lambda data: self._handle_orderbook(symbol, data)
            )
            logger.info(f"Subscribed to orderbook for {symbol}")
        except Exception as e:
            logger.error(f"Failed to subscribe to orderbook for {symbol}: {e}")
    
    def subscribe_trades(self, symbol: str):
        """Subscribe to trade updates"""
        if not self.ws or not self.is_connected:
            logger.warning("WebSocket not connected")
            return
        
        try:
            self.ws.trade_stream(
                symbol=symbol,
                callback=lambda data: self._handle_trade(symbol, data)
            )
            logger.info(f"Subscribed to trades for {symbol}")
        except Exception as e:
            logger.error(f"Failed to subscribe to trades for {symbol}: {e}")
    
    def subscribe_kline(self, symbol: str, interval: str = "1"):
        """Subscribe to kline/candlestick updates"""
        if not self.ws or not self.is_connected:
            logger.warning("WebSocket not connected")
            return
        
        try:
            self.ws.kline_stream(
                interval=interval,
                symbol=symbol,
                callback=lambda data: self._handle_kline(symbol, data)
            )
            logger.info(f"Subscribed to {interval}m klines for {symbol}")
        except Exception as e:
            logger.error(f"Failed to subscribe to klines for {symbol}: {e}")
    
    def _handle_ticker(self, symbol: str, data: dict):
        """Handle ticker update"""
        try:
            if 'data' in data:
                ticker_data = data['data']
                self.tickers[symbol] = {
                    'symbol': symbol,
                    'lastPrice': float(ticker_data.get('lastPrice', 0)),
                    'bidPrice': float(ticker_data.get('bid1Price', 0)),
                    'askPrice': float(ticker_data.get('ask1Price', 0)),
                    'volume24h': float(ticker_data.get('volume24h', 0)),
                    'high24h': float(ticker_data.get('highPrice24h', 0)),
                    'low24h': float(ticker_data.get('lowPrice24h', 0)),
                    'priceChange24h': float(ticker_data.get('price24hPcnt', 0)),
                    'timestamp': datetime.now().isoformat()
                }
                
                # Trigger callbacks
                for callback in self.callbacks['ticker']:
                    callback(symbol, self.tickers[symbol])
                    
        except Exception as e:
            logger.error(f"Error handling ticker data: {e}")
    
    def _handle_orderbook(self, symbol: str, data: dict):
        """Handle orderbook update"""
        try:
            if 'data' in data:
                ob_data = data['data']
                self.orderbooks[symbol] = {
                    'symbol': symbol,
                    'bids': [[float(p), float(q)] for p, q in ob_data.get('b', [])[:10]],
                    'asks': [[float(p), float(q)] for p, q in ob_data.get('a', [])[:10]],
                    'timestamp': datetime.now().isoformat()
                }
                
                # Trigger callbacks
                for callback in self.callbacks['orderbook']:
                    callback(symbol, self.orderbooks[symbol])
                    
        except Exception as e:
            logger.error(f"Error handling orderbook data: {e}")
    
    def _handle_trade(self, symbol: str, data: dict):
        """Handle trade update"""
        try:
            if 'data' in data:
                for trade in data['data']:
                    trade_data = {
                        'symbol': symbol,
                        'price': float(trade.get('p', 0)),
                        'quantity': float(trade.get('v', 0)),
                        'side': trade.get('S', ''),
                        'timestamp': trade.get('T', '')
                    }
                    
                    if symbol not in self.trades:
                        self.trades[symbol] = []
                    
                    self.trades[symbol].append(trade_data)
                    # Keep only last 100 trades
                    self.trades[symbol] = self.trades[symbol][-100:]
                    
                    # Trigger callbacks
                    for callback in self.callbacks['trade']:
                        callback(symbol, trade_data)
                        
        except Exception as e:
            logger.error(f"Error handling trade data: {e}")
    
    def _handle_kline(self, symbol: str, data: dict):
        """Handle kline update"""
        try:
            if 'data' in data:
                for kline in data['data']:
                    kline_data = {
                        'symbol': symbol,
                        'open': float(kline.get('open', 0)),
                        'high': float(kline.get('high', 0)),
                        'low': float(kline.get('low', 0)),
                        'close': float(kline.get('close', 0)),
                        'volume': float(kline.get('volume', 0)),
                        'timestamp': kline.get('start', 0)
                    }
                    
                    self.klines[symbol] = kline_data
                    
                    # Trigger callbacks
                    for callback in self.callbacks['kline']:
                        callback(symbol, kline_data)
                        
        except Exception as e:
            logger.error(f"Error handling kline data: {e}")
    
    def get_ticker(self, symbol: str) -> Optional[dict]:
        """Get current ticker data for symbol"""
        return self.tickers.get(symbol, {
            'symbol': symbol,
            'lastPrice': 0,
            'bidPrice': 0,
            'askPrice': 0,
            'volume24h': 0,
            'high24h': 0,
            'low24h': 0,
            'priceChange24h': 0,
            'timestamp': datetime.now().isoformat()
        })
    
    def get_orderbook(self, symbol: str) -> Optional[dict]:
        """Get current orderbook for symbol"""
        return self.orderbooks.get(symbol, {
            'symbol': symbol,
            'bids': [],
            'asks': [],
            'timestamp': datetime.now().isoformat()
        })
    
    def get_recent_trades(self, symbol: str, limit: int = 10) -> List[dict]:
        """Get recent trades for symbol"""
        if symbol in self.trades:
            return self.trades[symbol][-limit:]
        return []
    
    def add_callback(self, event_type: str, callback: Callable):
        """Add callback for specific event type"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
            logger.info(f"Added callback for {event_type}")
    
    def disconnect(self):
        """Disconnect from WebSocket"""
        if self.ws:
            try:
                # Unsubscribe from all streams
                for symbol in self.subscribed_symbols:
                    self.ws.unsubscribe_v5_public_trade(symbol)
                    self.ws.unsubscribe_v5_public_ticker(symbol)
                
                self.is_connected = False
                logger.info("Disconnected from Bybit WebSocket")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
    
    def get_market_summary(self) -> dict:
        """Get summary of all market data"""
        return {
            'connected': self.is_connected,
            'symbols': list(self.subscribed_symbols),
            'tickers': {
                symbol: {
                    'price': ticker.get('lastPrice', 0),
                    'change24h': ticker.get('priceChange24h', 0)
                }
                for symbol, ticker in self.tickers.items()
            },
            'timestamp': datetime.now().isoformat()
        }

# Global instance
_realtime_data = None

def get_realtime_data() -> BybitRealTimeData:
    """Get or create global real-time data instance"""
    global _realtime_data
    if _realtime_data is None:
        _realtime_data = BybitRealTimeData(
            testnet=os.getenv('BYBIT_TESTNET', 'true').lower() == 'true'
        )
        _realtime_data.connect()
    return _realtime_data

def main():
    """Test real-time data connection"""
    import time
    
    # Create instance
    rt_data = get_realtime_data()
    
    # Add test callbacks
    def on_ticker(symbol, data):
        print(f"📊 {symbol}: ${data['lastPrice']:.2f} ({data['priceChange24h']:+.2%})")
    
    def on_orderbook(symbol, data):
        if data['bids'] and data['asks']:
            spread = data['asks'][0][0] - data['bids'][0][0]
            print(f"📗 {symbol} Spread: ${spread:.2f}")
    
    rt_data.add_callback('ticker', on_ticker)
    rt_data.add_callback('orderbook', on_orderbook)
    
    print("🚀 Connected to Bybit real-time data")
    print("📊 Watching: BTCUSDT, ETHUSDT, SOLUSDT")
    print("Press Ctrl+C to stop\n")
    
    try:
        # Keep running
        while True:
            time.sleep(1)
            
            # Print summary every 10 seconds
            if int(time.time()) % 10 == 0:
                summary = rt_data.get_market_summary()
                print(f"\n📈 Market Summary: {len(summary['symbols'])} symbols tracked")
                
    except KeyboardInterrupt:
        print("\n👋 Stopping...")
        rt_data.disconnect()

if __name__ == "__main__":
    main()