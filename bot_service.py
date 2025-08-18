#!/usr/bin/env python3
"""
Automated Trading Bot Service для Bybit
Полностью автоматическая торговля с использованием настроенных стратегий
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
from pybit.unified_trading import WebSocket as BybitWebSocket

# Импорт стратегий
from strategies.rsi_strategy import RSIStrategy
from strategies.ma_strategy import MAStrategy
from strategies.grid_trading import GridTradingStrategy

# Импорт компонентов
from risk_management.position_sizer import PositionSizer
from risk_management.stop_loss_manager import StopLossManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_service.log')
    ]
)
logger = logging.getLogger(__name__)


class TradingBotService:
    """Основной сервис автоматической торговли"""
    
    def __init__(self):
        # Конфигурация из окружения
        self.api_key = os.getenv('BYBIT_API_KEY')
        self.api_secret = os.getenv('BYBIT_API_SECRET')
        self.testnet = os.getenv('BYBIT_TESTNET', 'false').lower() == 'true'
        
        # Торговые параметры
        self.symbols = ['BTCUSDT', 'ETHUSDT']  # Торговые пары
        self.max_positions = 3  # Максимум открытых позиций
        self.risk_per_trade = 0.02  # 2% риска на сделку
        self.max_daily_loss = 500  # Максимальный дневной убыток
        
        # Инициализация клиента
        self.client = HTTP(
            testnet=self.testnet,
            api_key=self.api_key,
            api_secret=self.api_secret
        )
        
        # Инициализация стратегий
        self.strategies = {
            'rsi': RSIStrategy(),
            'ma': MAStrategy(),
            'grid': GridTradingStrategy()
        }
        
        # Risk Management
        self.position_sizer = PositionSizer(
            balance=self._get_balance(),
            risk_per_trade=self.risk_per_trade
        )
        self.stop_loss_manager = StopLossManager()
        
        # Состояние
        self.is_running = False
        self.positions = {}
        self.daily_pnl = 0
        self.ws_client = None
        
        logger.info(f"Bot Service initialized - Mode: {'TESTNET' if self.testnet else 'MAINNET'}")
    
    def _get_balance(self) -> float:
        """Получение текущего баланса"""
        try:
            account = self.client.get_wallet_balance(accountType="UNIFIED")
            if account['retCode'] == 0:
                return float(account['result']['list'][0]['totalEquity'])
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
        return 0
    
    def _get_market_data(self, symbol: str) -> Dict:
        """Получение рыночных данных"""
        try:
            # Получаем свечи
            klines = self.client.get_kline(
                category="linear",
                symbol=symbol,
                interval="15",  # 15 минут
                limit=100
            )
            
            # Получаем текущую цену
            ticker = self.client.get_tickers(
                category="linear",
                symbol=symbol
            )
            
            if klines['retCode'] == 0 and ticker['retCode'] == 0:
                return {
                    'klines': klines['result']['list'],
                    'price': float(ticker['result']['list'][0]['lastPrice']),
                    'volume': float(ticker['result']['list'][0]['volume24h'])
                }
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
        return None
    
    def _check_signals(self, symbol: str) -> Optional[Dict]:
        """Проверка торговых сигналов от всех стратегий"""
        market_data = self._get_market_data(symbol)
        if not market_data:
            return None
        
        signals = []
        
        # Проверяем каждую стратегию
        for name, strategy in self.strategies.items():
            try:
                signal = strategy.check_signal(market_data)
                if signal:
                    signals.append({
                        'strategy': name,
                        'signal': signal,
                        'confidence': signal.get('confidence', 0.5)
                    })
            except Exception as e:
                logger.error(f"Error in {name} strategy: {e}")
        
        # Возвращаем сигнал с наибольшей уверенностью
        if signals:
            best_signal = max(signals, key=lambda x: x['confidence'])
            if best_signal['confidence'] > 0.6:  # Минимальный порог уверенности
                return best_signal
        
        return None
    
    def _place_order(self, symbol: str, signal: Dict) -> bool:
        """Размещение ордера на основе сигнала"""
        try:
            # Проверяем лимиты
            if len(self.positions) >= self.max_positions:
                logger.info(f"Max positions reached ({self.max_positions})")
                return False
            
            if self.daily_pnl <= -self.max_daily_loss:
                logger.warning(f"Daily loss limit reached: {self.daily_pnl}")
                return False
            
            # Рассчитываем размер позиции
            price = signal.get('price', self._get_market_data(symbol)['price'])
            position_size = self.position_sizer.calculate_position_size(
                symbol=symbol,
                entry_price=price,
                stop_loss=signal.get('stop_loss', price * 0.98)
            )
            
            # Размещаем ордер
            order = self.client.place_order(
                category="linear",
                symbol=symbol,
                side=signal['signal']['side'],  # Buy или Sell
                orderType="Market",
                qty=str(position_size),
                timeInForce="IOC",
                reduceOnly=False
            )
            
            if order['retCode'] == 0:
                order_id = order['result']['orderId']
                logger.info(f"Order placed: {symbol} {signal['signal']['side']} {position_size}")
                
                # Устанавливаем стоп-лосс
                if signal.get('stop_loss'):
                    self._set_stop_loss(symbol, signal['signal']['side'], signal['stop_loss'])
                
                # Сохраняем позицию
                self.positions[symbol] = {
                    'order_id': order_id,
                    'side': signal['signal']['side'],
                    'size': position_size,
                    'entry_price': price,
                    'strategy': signal['strategy'],
                    'timestamp': datetime.now()
                }
                
                return True
                
        except Exception as e:
            logger.error(f"Error placing order: {e}")
        
        return False
    
    def _set_stop_loss(self, symbol: str, side: str, stop_price: float):
        """Установка стоп-лосса"""
        try:
            # Определяем направление стоп-лосса
            stop_side = "Sell" if side == "Buy" else "Buy"
            
            self.client.place_order(
                category="linear",
                symbol=symbol,
                side=stop_side,
                orderType="Market",
                qty=str(self.positions[symbol]['size']),
                timeInForce="IOC",
                reduceOnly=True,
                stopLoss=str(stop_price)
            )
            
            logger.info(f"Stop loss set for {symbol} at {stop_price}")
            
        except Exception as e:
            logger.error(f"Error setting stop loss: {e}")
    
    def _update_positions(self):
        """Обновление информации о позициях"""
        try:
            positions = self.client.get_positions(
                category="linear",
                settleCoin="USDT"
            )
            
            if positions['retCode'] == 0:
                # Обновляем PnL
                for pos in positions['result']['list']:
                    if float(pos['size']) > 0:
                        pnl = float(pos.get('unrealisedPnl', 0))
                        self.daily_pnl += pnl
                
                # Удаляем закрытые позиции
                open_symbols = [p['symbol'] for p in positions['result']['list'] if float(p['size']) > 0]
                closed = [s for s in self.positions.keys() if s not in open_symbols]
                for symbol in closed:
                    logger.info(f"Position closed: {symbol}")
                    del self.positions[symbol]
                    
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
    
    async def _trading_loop(self):
        """Основной торговый цикл"""
        logger.info("Starting trading loop...")
        
        while self.is_running:
            try:
                # Обновляем позиции
                self._update_positions()
                
                # Проверяем сигналы для каждого символа
                for symbol in self.symbols:
                    if symbol not in self.positions:  # Нет открытой позиции
                        signal = self._check_signals(symbol)
                        if signal:
                            logger.info(f"Signal detected for {symbol}: {signal}")
                            self._place_order(symbol, signal)
                
                # Ждем перед следующей проверкой
                await asyncio.sleep(60)  # Проверка каждую минуту
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(10)
    
    def _setup_websocket(self):
        """Настройка WebSocket для real-time данных"""
        try:
            self.ws_client = BybitWebSocket(
                testnet=self.testnet,
                channel_type="linear"
            )
            
            # Подписка на тикеры
            for symbol in self.symbols:
                self.ws_client.ticker_stream(
                    symbol=symbol,
                    callback=self._handle_ticker_update
                )
            
            logger.info("WebSocket connection established")
            
        except Exception as e:
            logger.error(f"Error setting up WebSocket: {e}")
    
    def _handle_ticker_update(self, message):
        """Обработка обновлений тикера"""
        try:
            data = message.get('data', {})
            symbol = data.get('symbol')
            price = float(data.get('lastPrice', 0))
            
            # Здесь можно добавить логику для быстрой реакции на изменения цены
            logger.debug(f"Ticker update: {symbol} = {price}")
            
        except Exception as e:
            logger.error(f"Error handling ticker update: {e}")
    
    async def start(self):
        """Запуск бота"""
        logger.info("Starting Trading Bot Service...")
        
        # Проверка баланса
        balance = self._get_balance()
        logger.info(f"Account balance: ${balance:.2f}")
        
        if balance < 100:
            logger.error("Insufficient balance for trading")
            return
        
        # Настройка WebSocket
        self._setup_websocket()
        
        # Запуск торгового цикла
        self.is_running = True
        
        try:
            await self._trading_loop()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot stopped due to error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Остановка бота"""
        logger.info("Stopping Trading Bot Service...")
        self.is_running = False
        
        # Закрытие WebSocket
        if self.ws_client:
            self.ws_client.exit()
        
        # Логирование итогов
        logger.info(f"Daily PnL: ${self.daily_pnl:.2f}")
        logger.info(f"Open positions: {len(self.positions)}")
        logger.info("Bot stopped")


async def main():
    """Главная функция"""
    bot = TradingBotService()
    
    # Обработчик сигналов для graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        bot.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Запуск бота
    await bot.start()


if __name__ == "__main__":
    print("="*60)
    print("🤖 BYBIT AUTOMATED TRADING BOT SERVICE")
    print("="*60)
    print(f"Mode: {'TESTNET' if os.getenv('BYBIT_TESTNET', 'false').lower() == 'true' else 'MAINNET'}")
    print(f"Time: {datetime.now()}")
    print("="*60)
    print("\nPress Ctrl+C to stop the bot\n")
    
    asyncio.run(main())