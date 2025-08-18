#!/usr/bin/env python3
"""
Simplified Automated Trading Bot Service for Bybit
Safe and controlled automated trading
"""

import os
import sys
import asyncio
import logging
import signal
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from pybit.unified_trading import HTTP

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleTradingBot:
    """Упрощенный торговый бот с базовой стратегией"""
    
    def __init__(self):
        # Конфигурация
        self.api_key = os.getenv('BYBIT_API_KEY')
        self.api_secret = os.getenv('BYBIT_API_SECRET')
        self.testnet = os.getenv('BYBIT_TESTNET', 'false').lower() == 'true'
        
        # Торговые параметры (консервативные)
        self.symbols = ['BTCUSDT']  # Начнем с одной пары
        self.position_size = 50  # $50 на позицию
        self.max_positions = 1  # Максимум 1 позиция
        self.stop_loss_percent = 2  # 2% стоп-лосс
        self.take_profit_percent = 3  # 3% тейк-профит
        
        # Параметры стратегии RSI
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.rsi_period = 14
        
        # Инициализация клиента
        self.client = HTTP(
            testnet=self.testnet,
            api_key=self.api_key,
            api_secret=self.api_secret
        )
        
        # Состояние
        self.is_running = False
        self.current_position = None
        self.last_check = datetime.now()
        
        logger.info(f"SimpleTradingBot initialized - Mode: {'TESTNET' if self.testnet else 'MAINNET'}")
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Расчет RSI индикатора"""
        if len(prices) < period + 1:
            return 50  # Нейтральное значение
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Получение рыночных данных"""
        try:
            # Получаем свечи для расчета RSI
            klines = self.client.get_kline(
                category="linear",
                symbol=symbol,
                interval="15",  # 15 минут
                limit=50
            )
            
            if klines['retCode'] == 0:
                # Извлекаем цены закрытия
                prices = [float(k[4]) for k in klines['result']['list']]
                prices.reverse()  # От старых к новым
                
                # Текущая цена
                current_price = prices[-1]
                
                # Расчет RSI
                rsi = self.calculate_rsi(prices, self.rsi_period)
                
                return {
                    'symbol': symbol,
                    'price': current_price,
                    'rsi': rsi,
                    'prices': prices
                }
                
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
        
        return None
    
    def check_entry_signal(self, market_data: Dict) -> Optional[str]:
        """Проверка сигнала на вход в позицию"""
        rsi = market_data['rsi']
        
        # Простая RSI стратегия
        if rsi < self.rsi_oversold:
            logger.info(f"RSI oversold signal: {rsi:.2f}")
            return "Buy"
        elif rsi > self.rsi_overbought:
            logger.info(f"RSI overbought signal: {rsi:.2f}")
            return "Sell"
        
        return None
    
    def place_order(self, symbol: str, side: str, price: float) -> bool:
        """Размещение ордера с защитными ордерами"""
        try:
            # Расчет количества
            qty = self.position_size / price
            qty = round(qty, 3)  # Округление до 3 знаков
            
            # Расчет стоп-лосса и тейк-профита
            if side == "Buy":
                stop_loss = price * (1 - self.stop_loss_percent / 100)
                take_profit = price * (1 + self.take_profit_percent / 100)
            else:
                stop_loss = price * (1 + self.stop_loss_percent / 100)
                take_profit = price * (1 - self.take_profit_percent / 100)
            
            logger.info(f"Placing {side} order: {symbol} qty={qty} price={price:.2f}")
            logger.info(f"Stop Loss: {stop_loss:.2f}, Take Profit: {take_profit:.2f}")
            
            # Размещаем рыночный ордер
            order = self.client.place_order(
                category="linear",
                symbol=symbol,
                side=side,
                orderType="Market",
                qty=str(qty),
                stopLoss=str(stop_loss),
                takeProfit=str(take_profit)
            )
            
            if order['retCode'] == 0:
                logger.info(f"Order placed successfully: {order['result']['orderId']}")
                
                self.current_position = {
                    'symbol': symbol,
                    'side': side,
                    'qty': qty,
                    'entry_price': price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'timestamp': datetime.now()
                }
                
                return True
            else:
                logger.error(f"Order failed: {order}")
                
        except Exception as e:
            logger.error(f"Error placing order: {e}")
        
        return False
    
    def check_positions(self):
        """Проверка текущих позиций"""
        try:
            positions = self.client.get_positions(
                category="linear",
                settleCoin="USDT"
            )
            
            if positions['retCode'] == 0:
                open_positions = [
                    p for p in positions['result']['list'] 
                    if float(p.get('size', 0)) > 0
                ]
                
                if open_positions:
                    pos = open_positions[0]
                    pnl = float(pos.get('unrealisedPnl', 0))
                    logger.info(f"Open position: {pos['symbol']} PnL: ${pnl:.2f}")
                    return True
                else:
                    self.current_position = None
                    return False
                    
        except Exception as e:
            logger.error(f"Error checking positions: {e}")
        
        return False
    
    async def trading_loop(self):
        """Основной торговый цикл"""
        logger.info("Starting trading loop...")
        
        while self.is_running:
            try:
                # Проверяем баланс
                account = self.client.get_wallet_balance(accountType="UNIFIED")
                if account['retCode'] == 0:
                    balance = float(account['result']['list'][0]['totalEquity'])
                    logger.info(f"Account balance: ${balance:.2f}")
                    
                    if balance < 100:
                        logger.error("Insufficient balance for trading")
                        break
                
                # Проверяем существующие позиции
                has_position = self.check_positions()
                
                # Если нет позиции, ищем сигнал
                if not has_position:
                    for symbol in self.symbols:
                        market_data = self.get_market_data(symbol)
                        
                        if market_data:
                            logger.info(f"{symbol}: Price=${market_data['price']:.2f}, RSI={market_data['rsi']:.2f}")
                            
                            signal = self.check_entry_signal(market_data)
                            
                            if signal:
                                logger.info(f"Signal detected: {signal} for {symbol}")
                                
                                # Подтверждение перед размещением ордера
                                logger.info("Waiting 5 seconds before placing order...")
                                await asyncio.sleep(5)
                                
                                # Размещаем ордер
                                success = self.place_order(
                                    symbol,
                                    signal,
                                    market_data['price']
                                )
                                
                                if success:
                                    logger.info("Order placed, waiting for next cycle...")
                                    await asyncio.sleep(60)  # Ждем минуту после сделки
                
                # Ждем перед следующей проверкой
                await asyncio.sleep(30)  # Проверка каждые 30 секунд
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(10)
    
    async def start(self):
        """Запуск бота"""
        logger.info("="*60)
        logger.info("STARTING SIMPLE TRADING BOT")
        logger.info(f"Mode: {'TESTNET' if self.testnet else 'MAINNET'}")
        logger.info(f"Symbol: {self.symbols}")
        logger.info(f"Position size: ${self.position_size}")
        logger.info(f"Stop loss: {self.stop_loss_percent}%")
        logger.info(f"Take profit: {self.take_profit_percent}%")
        logger.info("="*60)
        
        self.is_running = True
        
        try:
            await self.trading_loop()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot stopped due to error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Остановка бота"""
        logger.info("Stopping bot...")
        self.is_running = False
        
        # Проверка открытых позиций
        if self.current_position:
            logger.warning(f"Warning: Open position remains: {self.current_position}")
        
        logger.info("Bot stopped")


async def main():
    """Главная функция"""
    bot = SimpleTradingBot()
    
    # Обработчик сигналов
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        bot.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    await bot.start()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🤖 BYBIT SIMPLE AUTOMATED TRADING BOT")
    print("="*60)
    print("Starting in 5 seconds...")
    print("Press Ctrl+C to stop\n")
    
    import time
    time.sleep(5)
    
    asyncio.run(main())