"""
Стратегии торговли
"""

import logging
from typing import Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from bybit_client import BybitClient
from indicators import TechnicalIndicators, SignalGenerator

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """Базовый класс для торговых стратегий"""
    
    def __init__(self, client: BybitClient, symbol: str):
        self.client = client
        self.symbol = symbol
        self.position = None
        self.last_signal = 'HOLD'
        
        load_dotenv()
        
        # Параметры из .env
        self.leverage = int(os.getenv('LEVERAGE', 10))
        self.position_size = float(os.getenv('POSITION_SIZE', 100))  # в USDT
        self.stop_loss_percent = float(os.getenv('STOP_LOSS_PERCENT', 2.0))
        self.take_profit_percent = float(os.getenv('TAKE_PROFIT_PERCENT', 3.0))
        
    @abstractmethod
    def analyze(self) -> Tuple[str, float]:
        """
        Анализировать рынок и генерировать сигнал
        Возвращает: (сигнал, уверенность)
        """
        pass
    
    @abstractmethod
    def should_enter_position(self) -> bool:
        """Определить, следует ли входить в позицию"""
        pass
    
    @abstractmethod
    def should_exit_position(self) -> bool:
        """Определить, следует ли выходить из позиции"""
        pass
    
    def calculate_position_size(self, price: float) -> float:
        """Рассчитать размер позиции"""
        # Размер позиции в количестве монет
        qty = self.position_size / price
        return round(qty, 3)
    
    def calculate_stop_loss(self, entry_price: float, side: str) -> float:
        """Рассчитать стоп-лосс"""
        if side == 'Buy':
            return round(entry_price * (1 - self.stop_loss_percent / 100), 2)
        else:
            return round(entry_price * (1 + self.stop_loss_percent / 100), 2)
    
    def calculate_take_profit(self, entry_price: float, side: str) -> float:
        """Рассчитать тейк-профит"""
        if side == 'Buy':
            return round(entry_price * (1 + self.take_profit_percent / 100), 2)
        else:
            return round(entry_price * (1 - self.take_profit_percent / 100), 2)
    
    def enter_position(self, side: str) -> bool:
        """Войти в позицию"""
        try:
            # Получить текущую цену
            ticker = self.client.get_ticker(self.symbol)
            if not ticker:
                logger.error("Failed to get ticker")
                return False
            
            current_price = float(ticker['lastPrice'])
            
            # Рассчитать параметры позиции
            qty = self.calculate_position_size(current_price)
            stop_loss = self.calculate_stop_loss(current_price, side)
            take_profit = self.calculate_take_profit(current_price, side)
            
            # Установить кредитное плечо
            self.client.set_leverage(self.symbol, str(self.leverage))
            
            # Разместить ордер
            order = self.client.place_order(
                symbol=self.symbol,
                side=side,
                order_type="Market",
                qty=str(qty),
                stop_loss=str(stop_loss),
                take_profit=str(take_profit)
            )
            
            if order:
                logger.info(f"Entered {side} position: {qty} @ {current_price}")
                logger.info(f"Stop Loss: {stop_loss}, Take Profit: {take_profit}")
                return True
            else:
                logger.error("Failed to enter position")
                return False
                
        except Exception as e:
            logger.error(f"Error entering position: {e}")
            return False
    
    def exit_position(self) -> bool:
        """Выйти из позиции"""
        try:
            result = self.client.close_position(self.symbol)
            if result:
                logger.info("Position closed successfully")
                return True
            else:
                logger.error("Failed to close position")
                return False
                
        except Exception as e:
            logger.error(f"Error exiting position: {e}")
            return False
    
    def update_position(self):
        """Обновить информацию о позиции"""
        positions = self.client.get_positions(self.symbol)
        if positions and len(positions) > 0:
            self.position = positions[0]
            if float(self.position['size']) == 0:
                self.position = None
        else:
            self.position = None
    
    def execute(self):
        """Выполнить стратегию"""
        try:
            # Обновить информацию о позиции
            self.update_position()
            
            # Анализировать рынок
            signal, confidence = self.analyze()
            
            logger.info(f"Signal: {signal}, Confidence: {confidence:.2%}")
            
            # Если есть открытая позиция
            if self.position:
                if self.should_exit_position():
                    self.exit_position()
            
            # Если нет открытой позиции
            else:
                if signal == 'BUY' and self.should_enter_position():
                    self.enter_position('Buy')
                elif signal == 'SELL' and self.should_enter_position():
                    self.enter_position('Sell')
            
            self.last_signal = signal
            
        except Exception as e:
            logger.error(f"Error executing strategy: {e}")


class RSIStrategy(BaseStrategy):
    """Стратегия на основе RSI"""
    
    def __init__(self, client: BybitClient, symbol: str):
        super().__init__(client, symbol)
        
        load_dotenv()
        
        # Параметры RSI
        self.rsi_period = int(os.getenv('RSI_PERIOD', 14))
        self.rsi_oversold = float(os.getenv('RSI_OVERSOLD', 30))
        self.rsi_overbought = float(os.getenv('RSI_OVERBOUGHT', 70))
        
        self.min_confidence = 0.6
    
    def analyze(self) -> Tuple[str, float]:
        """Анализировать рынок на основе RSI"""
        # Получить данные свечей
        klines = self.client.get_kline_data(self.symbol, "15", limit=100)
        if not klines:
            return 'HOLD', 0.0
        
        # Подготовить DataFrame и рассчитать индикаторы
        df = TechnicalIndicators.prepare_dataframe(klines)
        df['rsi'] = TechnicalIndicators.calculate_rsi(df, self.rsi_period)
        
        # Генерировать сигнал
        signal = SignalGenerator.rsi_signal(df, self.rsi_oversold, self.rsi_overbought)
        
        # Рассчитать уверенность на основе расстояния от порогов
        last_rsi = df['rsi'].iloc[-1]
        if signal == 'BUY':
            confidence = (self.rsi_oversold - last_rsi + 10) / 20
        elif signal == 'SELL':
            confidence = (last_rsi - self.rsi_overbought + 10) / 20
        else:
            confidence = 0.0
        
        confidence = max(0, min(1, confidence))  # Ограничить от 0 до 1
        
        return signal, confidence
    
    def should_enter_position(self) -> bool:
        """Проверить условия для входа в позицию"""
        # Не входить, если уже есть позиция
        if self.position:
            return False
        
        # Проверить достаточный баланс
        balance = self.client.get_account_balance()
        if not balance:
            return False
        
        # Здесь можно добавить дополнительные проверки
        return True
    
    def should_exit_position(self) -> bool:
        """Проверить условия для выхода из позиции"""
        if not self.position:
            return False
        
        # Выйти при противоположном сигнале
        if self.position['side'] == 'Buy' and self.last_signal == 'SELL':
            return True
        elif self.position['side'] == 'Sell' and self.last_signal == 'BUY':
            return True
        
        return False


class EMAStrategy(BaseStrategy):
    """Стратегия на основе пересечения EMA"""
    
    def __init__(self, client: BybitClient, symbol: str):
        super().__init__(client, symbol)
        
        load_dotenv()
        
        # Параметры EMA
        self.ema_short = int(os.getenv('EMA_SHORT', 9))
        self.ema_long = int(os.getenv('EMA_LONG', 21))
        
        self.min_confidence = 0.5
    
    def analyze(self) -> Tuple[str, float]:
        """Анализировать рынок на основе EMA"""
        # Получить данные свечей
        klines = self.client.get_kline_data(self.symbol, "15", limit=100)
        if not klines:
            return 'HOLD', 0.0
        
        # Подготовить DataFrame и рассчитать индикаторы
        df = TechnicalIndicators.prepare_dataframe(klines)
        df['ema_short'] = TechnicalIndicators.calculate_ema(df, self.ema_short)
        df['ema_long'] = TechnicalIndicators.calculate_ema(df, self.ema_long)
        
        # Генерировать сигнал
        signal = SignalGenerator.ema_crossover_signal(df)
        
        # Рассчитать уверенность на основе расстояния между EMA
        last_short = df['ema_short'].iloc[-1]
        last_long = df['ema_long'].iloc[-1]
        
        # Нормализовать разницу
        diff_percent = abs((last_short - last_long) / last_long) * 100
        confidence = min(1.0, diff_percent / 2)  # Максимум при 2% разнице
        
        return signal, confidence
    
    def should_enter_position(self) -> bool:
        """Проверить условия для входа в позицию"""
        if self.position:
            return False
        
        balance = self.client.get_account_balance()
        if not balance:
            return False
        
        return True
    
    def should_exit_position(self) -> bool:
        """Проверить условия для выхода из позиции"""
        if not self.position:
            return False
        
        if self.position['side'] == 'Buy' and self.last_signal == 'SELL':
            return True
        elif self.position['side'] == 'Sell' and self.last_signal == 'BUY':
            return True
        
        return False


class CombinedStrategy(BaseStrategy):
    """Комбинированная стратегия с несколькими индикаторами"""
    
    def __init__(self, client: BybitClient, symbol: str):
        super().__init__(client, symbol)
        
        load_dotenv()
        
        # Загрузить параметры для всех индикаторов
        self.config = {
            'rsi_period': int(os.getenv('RSI_PERIOD', 14)),
            'rsi_oversold': float(os.getenv('RSI_OVERSOLD', 30)),
            'rsi_overbought': float(os.getenv('RSI_OVERBOUGHT', 70)),
            'ema_short': int(os.getenv('EMA_SHORT', 9)),
            'ema_long': int(os.getenv('EMA_LONG', 21)),
            'min_confidence': 0.6
        }
        
        self.min_confidence = 0.6
    
    def analyze(self) -> Tuple[str, float]:
        """Анализировать рынок с использованием нескольких индикаторов"""
        # Получить данные свечей
        klines = self.client.get_kline_data(self.symbol, "15", limit=200)
        if not klines:
            return 'HOLD', 0.0
        
        # Подготовить DataFrame и добавить все индикаторы
        df = TechnicalIndicators.prepare_dataframe(klines)
        df = TechnicalIndicators.add_all_indicators(df, self.config)
        
        # Генерировать комбинированный сигнал
        signal, confidence = SignalGenerator.combined_signal(df, self.config)
        
        return signal, confidence
    
    def should_enter_position(self) -> bool:
        """Проверить условия для входа в позицию"""
        if self.position:
            return False
        
        # Проверить баланс
        balance = self.client.get_account_balance()
        if not balance:
            return False
        
        # Входить только при высокой уверенности
        _, confidence = self.analyze()
        if confidence < self.min_confidence:
            return False
        
        return True
    
    def should_exit_position(self) -> bool:
        """Проверить условия для выхода из позиции"""
        if not self.position:
            return False
        
        # Проверить PnL
        pnl_percent = float(self.position['unrealisedPnl']) / float(self.position['positionValue']) * 100
        
        # Выйти при достижении целевого профита или лосса
        if pnl_percent >= self.take_profit_percent or pnl_percent <= -self.stop_loss_percent:
            return True
        
        # Выйти при сильном противоположном сигнале
        signal, confidence = self.analyze()
        if confidence > 0.7:
            if self.position['side'] == 'Buy' and signal == 'SELL':
                return True
            elif self.position['side'] == 'Sell' and signal == 'BUY':
                return True
        
        return False


class GridStrategy(BaseStrategy):
    """Сеточная стратегия"""
    
    def __init__(self, client: BybitClient, symbol: str):
        super().__init__(client, symbol)
        
        # Параметры сетки
        self.grid_levels = 10  # Количество уровней сетки
        self.grid_spacing = 0.5  # Расстояние между уровнями в процентах
        self.order_amount = 10  # Размер каждого ордера в USDT
        
        self.grid_orders = []
        self.last_price = 0
    
    def setup_grid(self, center_price: float):
        """Установить сетку ордеров"""
        try:
            # Отменить все существующие ордера
            self.client.cancel_all_orders(self.symbol)
            
            # Создать сетку ордеров
            for i in range(self.grid_levels):
                # Ордера на покупку ниже текущей цены
                buy_price = center_price * (1 - (i + 1) * self.grid_spacing / 100)
                buy_qty = self.order_amount / buy_price
                
                buy_order = self.client.place_order(
                    symbol=self.symbol,
                    side="Buy",
                    order_type="Limit",
                    qty=str(round(buy_qty, 3)),
                    price=str(round(buy_price, 2))
                )
                
                if buy_order:
                    self.grid_orders.append(buy_order)
                
                # Ордера на продажу выше текущей цены
                sell_price = center_price * (1 + (i + 1) * self.grid_spacing / 100)
                sell_qty = self.order_amount / sell_price
                
                sell_order = self.client.place_order(
                    symbol=self.symbol,
                    side="Sell",
                    order_type="Limit",
                    qty=str(round(sell_qty, 3)),
                    price=str(round(sell_price, 2))
                )
                
                if sell_order:
                    self.grid_orders.append(sell_order)
            
            logger.info(f"Grid setup completed with {len(self.grid_orders)} orders")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up grid: {e}")
            return False
    
    def analyze(self) -> Tuple[str, float]:
        """Анализ не требуется для сеточной стратегии"""
        return 'HOLD', 0.0
    
    def should_enter_position(self) -> bool:
        """Сетка управляет позициями автоматически"""
        return False
    
    def should_exit_position(self) -> bool:
        """Сетка управляет позициями автоматически"""
        return False
    
    def execute(self):
        """Выполнить сеточную стратегию"""
        try:
            # Получить текущую цену
            ticker = self.client.get_ticker(self.symbol)
            if not ticker:
                return
            
            current_price = float(ticker['lastPrice'])
            
            # Инициализировать сетку при первом запуске
            if not self.grid_orders:
                self.setup_grid(current_price)
                self.last_price = current_price
                return
            
            # Перестроить сетку при значительном изменении цены
            price_change = abs(current_price - self.last_price) / self.last_price * 100
            if price_change > self.grid_spacing * self.grid_levels:
                logger.info("Price moved significantly, rebuilding grid")
                self.setup_grid(current_price)
                self.last_price = current_price
            
        except Exception as e:
            logger.error(f"Error executing grid strategy: {e}")


if __name__ == "__main__":
    # Тестирование стратегий
    client = BybitClient(testnet=True)
    
    # Выбрать стратегию
    # strategy = RSIStrategy(client, "BTCUSDT")
    # strategy = EMAStrategy(client, "BTCUSDT")
    strategy = CombinedStrategy(client, "BTCUSDT")
    
    # Выполнить один цикл стратегии
    strategy.execute()
