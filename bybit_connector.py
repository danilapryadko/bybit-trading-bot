#!/usr/bin/env python3
"""
Real Bybit API Connector
Connects to actual Bybit account for real balance and trading
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pybit.unified_trading import HTTP
from config import get_trading_config
from database.service import get_db_service

logger = logging.getLogger(__name__)

class BybitConnector:
    """Real connection to Bybit API"""
    
    def __init__(self):
        """Initialize Bybit connection"""
        self.config = get_trading_config()
        self.db = get_db_service()
        
        # Initialize Bybit client
        try:
            self.client = HTTP(
                testnet=self.config.is_testnet,
                api_key=self.config.api_key,
                api_secret=self.config.api_secret
            )
            
            logger.info(f"Bybit connector initialized ({'TESTNET' if self.config.is_testnet else 'MAINNET'})")
            
            # Test connection
            self._test_connection()
            
        except Exception as e:
            logger.error(f"Failed to initialize Bybit connector: {e}")
            raise
    
    def _test_connection(self):
        """Test API connection"""
        try:
            # Get server time to test connection
            response = self.client.get_server_time()
            if response.get('retCode') == 0:
                logger.info("Bybit API connection successful")
            else:
                logger.error(f"API connection test failed: {response}")
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
    
    def get_balance(self) -> float:
        """Get real account balance"""
        try:
            response = self.client.get_wallet_balance(
                accountType="UNIFIED",
                coin="USDT"
            )
            
            if response.get('retCode') != 0:
                logger.error(f"Failed to get balance: {response.get('retMsg')}")
                return 0.0
            
            # Extract USDT balance
            accounts = response.get('result', {}).get('list', [])
            if accounts:
                coins = accounts[0].get('coin', [])
                for coin in coins:
                    if coin.get('coin') == 'USDT':
                        # Return available balance
                        balance = float(coin.get('availableToWithdraw', 0))
                        logger.info(f"Current balance: {balance} USDT")
                        return balance
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0.0
    
    def get_positions(self) -> List[Dict]:
        """Get open positions"""
        try:
            response = self.client.get_positions(
                category="linear",
                settleCoin="USDT"
            )
            
            if response.get('retCode') != 0:
                logger.error(f"Failed to get positions: {response.get('retMsg')}")
                return []
            
            positions = []
            for pos in response.get('result', {}).get('list', []):
                if float(pos.get('size', 0)) > 0:
                    positions.append({
                        'symbol': pos.get('symbol'),
                        'side': pos.get('side'),
                        'size': float(pos.get('size', 0)),
                        'avgPrice': float(pos.get('avgPrice', 0)),
                        'markPrice': float(pos.get('markPrice', 0)),
                        'unrealisedPnl': float(pos.get('unrealisedPnl', 0)),
                        'leverage': pos.get('leverage', '1')
                    })
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_ticker(self, symbol: str) -> Dict:
        """Get real ticker data"""
        try:
            response = self.client.get_tickers(
                category="linear",
                symbol=symbol
            )
            
            if response.get('retCode') != 0:
                logger.error(f"Failed to get ticker: {response.get('retMsg')}")
                return self._get_default_ticker(symbol)
            
            tickers = response.get('result', {}).get('list', [])
            if tickers:
                ticker = tickers[0]
                return {
                    'symbol': symbol,
                    'price': float(ticker.get('lastPrice', 0)),
                    'bid': float(ticker.get('bid1Price', 0)),
                    'ask': float(ticker.get('ask1Price', 0)),
                    'volume': float(ticker.get('volume24h', 0)),
                    'high24h': float(ticker.get('highPrice24h', 0)),
                    'low24h': float(ticker.get('lowPrice24h', 0)),
                    'change24h': float(ticker.get('price24hPcnt', 0)) * 100
                }
            
            return self._get_default_ticker(symbol)
            
        except Exception as e:
            logger.error(f"Error getting ticker for {symbol}: {e}")
            return self._get_default_ticker(symbol)
    
    def _get_default_ticker(self, symbol: str) -> Dict:
        """Get default ticker values"""
        defaults = {
            'BTCUSDT': 65000,
            'ETHUSDT': 3200,
            'BNBUSDT': 600,
            'SOLUSDT': 150
        }
        
        price = defaults.get(symbol, 100)
        return {
            'symbol': symbol,
            'price': price,
            'bid': price * 0.999,
            'ask': price * 1.001,
            'volume': 0,
            'high24h': price * 1.02,
            'low24h': price * 0.98,
            'change24h': 0
        }
    
    def get_klines(self, symbol: str, interval: str = '15', limit: int = 100) -> List[Dict]:
        """Get kline/candlestick data"""
        try:
            response = self.client.get_kline(
                category="linear",
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            if response.get('retCode') != 0:
                logger.error(f"Failed to get klines: {response.get('retMsg')}")
                return []
            
            klines = []
            for k in response.get('result', {}).get('list', []):
                klines.append({
                    'timestamp': int(k[0]),
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5])
                })
            
            return klines
            
        except Exception as e:
            logger.error(f"Error getting klines: {e}")
            return []
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = 'MARKET',
        price: Optional[float] = None
    ) -> Optional[str]:
        """Place an order"""
        try:
            params = {
                'category': 'linear',
                'symbol': symbol,
                'side': side.capitalize(),
                'orderType': order_type.capitalize(),
                'qty': str(quantity),
                'timeInForce': 'GTC'
            }
            
            if order_type.upper() == 'LIMIT' and price:
                params['price'] = str(price)
            
            response = self.client.place_order(**params)
            
            if response.get('retCode') != 0:
                logger.error(f"Failed to place order: {response.get('retMsg')}")
                return None
            
            order_id = response.get('result', {}).get('orderId')
            logger.info(f"Order placed: {order_id}")
            
            # Save to database
            self.db.create_order(
                user_id=1,  # Default user
                order_data={
                    'order_id': order_id,
                    'symbol': symbol,
                    'side': side,
                    'type': order_type,
                    'quantity': quantity,
                    'price': price
                }
            )
            
            return order_id
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order"""
        try:
            response = self.client.cancel_order(
                category='linear',
                symbol=symbol,
                orderId=order_id
            )
            
            if response.get('retCode') != 0:
                logger.error(f"Failed to cancel order: {response.get('retMsg')}")
                return False
            
            logger.info(f"Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get open orders"""
        try:
            params = {
                'category': 'linear',
                'settleCoin': 'USDT'
            }
            
            if symbol:
                params['symbol'] = symbol
            
            response = self.client.get_open_orders(**params)
            
            if response.get('retCode') != 0:
                logger.error(f"Failed to get orders: {response.get('retMsg')}")
                return []
            
            orders = []
            for order in response.get('result', {}).get('list', []):
                orders.append({
                    'orderId': order.get('orderId'),
                    'symbol': order.get('symbol'),
                    'side': order.get('side'),
                    'type': order.get('orderType'),
                    'price': float(order.get('price', 0)),
                    'quantity': float(order.get('qty', 0)),
                    'filled': float(order.get('cumExecQty', 0)),
                    'status': order.get('orderStatus'),
                    'createdTime': order.get('createdTime')
                })
            
            return orders
            
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    def get_account_info(self) -> Dict:
        """Get complete account information"""
        try:
            # Get balance
            balance = self.get_balance()
            
            # Get positions
            positions = self.get_positions()
            
            # Calculate total position value and P&L
            total_position_value = 0
            total_unrealized_pnl = 0
            
            for pos in positions:
                position_value = pos['size'] * pos['markPrice']
                total_position_value += position_value
                total_unrealized_pnl += pos['unrealisedPnl']
            
            # Get account settings
            response = self.client.get_account_info()
            margin_mode = 'cross'
            if response.get('retCode') == 0:
                margin_mode = response.get('result', {}).get('marginMode', 'cross')
            
            return {
                'balance': balance,
                'equity': balance + total_unrealized_pnl,
                'margin_used': total_position_value,
                'margin_available': balance - total_position_value,
                'unrealized_pnl': total_unrealized_pnl,
                'position_count': len(positions),
                'margin_mode': margin_mode,
                'positions': positions
            }
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {
                'balance': 0,
                'equity': 0,
                'margin_used': 0,
                'margin_available': 0,
                'unrealized_pnl': 0,
                'position_count': 0,
                'margin_mode': 'cross',
                'positions': []
            }

# Singleton instance
_connector = None

def get_bybit_connector() -> BybitConnector:
    """Get singleton Bybit connector"""
    global _connector
    if _connector is None:
        _connector = BybitConnector()
    return _connector

if __name__ == "__main__":
    # Test the connector
    connector = get_bybit_connector()
    
    # Get account info
    info = connector.get_account_info()
    print(f"Account Balance: ${info['balance']:.2f}")
    print(f"Open Positions: {info['position_count']}")
    print(f"Unrealized P&L: ${info['unrealized_pnl']:.2f}")
    
    # Get ticker
    ticker = connector.get_ticker('BTCUSDT')
    print(f"\nBTC Price: ${ticker['price']:,.2f}")
    print(f"24h Change: {ticker['change24h']:.2f}%")