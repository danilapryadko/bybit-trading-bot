"""
Bybit Trading Bot
Основной модуль для подключения к Bybit API
"""

from pybit.unified_trading import HTTP
from pybit.unified_trading import WebSocket
import os
from dotenv import load_dotenv
import logging
from typing import Optional, Dict, Any
import time

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BybitClient:
    """Клиент для работы с Bybit API"""
    
    def __init__(self, testnet: bool = True):
        load_dotenv()
        
        self.api_key = os.getenv('API_KEY')
        self.api_secret = os.getenv('API_SECRET')
        self.testnet = testnet
        
        # Инициализация HTTP клиента
        self.session = HTTP(
            testnet=testnet,
            api_key=self.api_key,
            api_secret=self.api_secret
        )
        
        # Инициализация WebSocket клиента (для получения real-time данных)
        self.ws = None
        
        logger.info(f"Bybit client initialized. Testnet: {testnet}")
    
    def get_account_balance(self, account_type: str = "UNIFIED") -> Dict[str, Any]:
        """Получить баланс аккаунта"""
        try:
            response = self.session.get_wallet_balance(
                accountType=account_type
            )
            return response
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return None
    
    def get_kline_data(self, symbol: str, interval: str, limit: int = 200) -> Optional[list]:
        """
        Получить данные свечей
        interval: '1', '3', '5', '15', '30', '60', '120', '240', '360', '720', 'D', 'W', 'M'
        """
        try:
            response = self.session.get_kline(
                category="linear",
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            if response['retCode'] == 0:
                return response['result']['list']
            else:
                logger.error(f"Error getting kline data: {response['retMsg']}")
                return None
        except Exception as e:
            logger.error(f"Error getting kline data: {e}")
            return None
    
    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Получить текущую цену и информацию о тикере"""
        try:
            response = self.session.get_tickers(
                category="linear",
                symbol=symbol
            )
            if response['retCode'] == 0:
                return response['result']['list'][0]
            else:
                logger.error(f"Error getting ticker: {response['retMsg']}")
                return None
        except Exception as e:
            logger.error(f"Error getting ticker: {e}")
            return None
    
    def place_order(self, 
                   symbol: str,
                   side: str,  # 'Buy' or 'Sell'
                   order_type: str,  # 'Market' or 'Limit'
                   qty: str,
                   price: Optional[str] = None,
                   time_in_force: str = "GTC",
                   position_idx: int = 0,  # 0: one-way mode
                   stop_loss: Optional[str] = None,
                   take_profit: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Разместить ордер"""
        try:
            params = {
                "category": "linear",
                "symbol": symbol,
                "side": side,
                "orderType": order_type,
                "qty": qty,
                "timeInForce": time_in_force,
                "positionIdx": position_idx
            }
            
            if price and order_type == "Limit":
                params["price"] = price
            
            if stop_loss:
                params["stopLoss"] = stop_loss
            
            if take_profit:
                params["takeProfit"] = take_profit
            
            response = self.session.place_order(**params)
            
            if response['retCode'] == 0:
                logger.info(f"Order placed successfully: {response['result']}")
                return response['result']
            else:
                logger.error(f"Error placing order: {response['retMsg']}")
                return None
                
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    def get_positions(self, symbol: Optional[str] = None) -> Optional[list]:
        """Получить открытые позиции"""
        try:
            params = {
                "category": "linear",
                "settleCoin": "USDT"
            }
            if symbol:
                params["symbol"] = symbol
            
            response = self.session.get_positions(**params)
            
            if response['retCode'] == 0:
                return response['result']['list']
            else:
                logger.error(f"Error getting positions: {response['retMsg']}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return None
    
    def close_position(self, symbol: str, position_idx: int = 0) -> Optional[Dict[str, Any]]:
        """Закрыть позицию"""
        try:
            # Получить текущую позицию
            positions = self.get_positions(symbol)
            if not positions:
                logger.info("No open positions to close")
                return None
            
            position = positions[0]
            if float(position['size']) == 0:
                logger.info("Position already closed")
                return None
            
            # Определить сторону для закрытия
            close_side = "Sell" if position['side'] == "Buy" else "Buy"
            
            # Разместить рыночный ордер для закрытия
            return self.place_order(
                symbol=symbol,
                side=close_side,
                order_type="Market",
                qty=position['size'],
                position_idx=position_idx
            )
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return None
    
    def set_leverage(self, symbol: str, leverage: str) -> Optional[Dict[str, Any]]:
        """Установить кредитное плечо"""
        try:
            response = self.session.set_leverage(
                category="linear",
                symbol=symbol,
                buyLeverage=leverage,
                sellLeverage=leverage
            )
            
            if response['retCode'] == 0:
                logger.info(f"Leverage set to {leverage}x for {symbol}")
                return response['result']
            else:
                logger.error(f"Error setting leverage: {response['retMsg']}")
                return None
                
        except Exception as e:
            logger.error(f"Error setting leverage: {e}")
            return None
    
    def get_order_history(self, symbol: Optional[str] = None, limit: int = 50) -> Optional[list]:
        """Получить историю ордеров"""
        try:
            params = {
                "category": "linear",
                "limit": limit
            }
            if symbol:
                params["symbol"] = symbol
            
            response = self.session.get_order_history(**params)
            
            if response['retCode'] == 0:
                return response['result']['list']
            else:
                logger.error(f"Error getting order history: {response['retMsg']}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting order history: {e}")
            return None
    
    def cancel_all_orders(self, symbol: Optional[str] = None) -> bool:
        """Отменить все открытые ордера"""
        try:
            params = {
                "category": "linear",
                "settleCoin": "USDT"
            }
            if symbol:
                params["symbol"] = symbol
            
            response = self.session.cancel_all_orders(**params)
            
            if response['retCode'] == 0:
                logger.info("All orders cancelled successfully")
                return True
            else:
                logger.error(f"Error cancelling orders: {response['retMsg']}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")
            return False


if __name__ == "__main__":
    # Тестирование клиента
    client = BybitClient(testnet=True)
    
    # Получить баланс
    balance = client.get_account_balance()
    if balance:
        logger.info(f"Account balance retrieved successfully")
    
    # Получить текущую цену BTCUSDT
    ticker = client.get_ticker("BTCUSDT")
    if ticker:
        logger.info(f"BTCUSDT price: {ticker['lastPrice']}")
    
    # Получить свечи
    klines = client.get_kline_data("BTCUSDT", "15", limit=10)
    if klines:
        logger.info(f"Retrieved {len(klines)} candles")
