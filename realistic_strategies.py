"""
Реалистичная имплементация стратегий с использованием только доступных данных
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from bybit_client import BybitClient
from indicators import TechnicalIndicators, SignalGenerator
from risk_manager import RiskManager
from strategies import BaseStrategy

logger = logging.getLogger(__name__)

class RealisticMarketAnalyzer:
    """Анализатор рынка на основе реально доступных данных"""
    
    @staticmethod
    def get_market_structure(client: BybitClient, symbol: str) -> Dict[str, Any]:
        """Получить структуру рынка используя только доступные данные"""
        try:
            # Получаем данные разных таймфреймов
            m15_klines = client.get_kline_data(symbol, "15", limit=100)
            h1_klines = client.get_kline_data(symbol, "60", limit=100)
            h4_klines = client.get_kline_data(symbol, "240", limit=50)
            
            if not all([m15_klines, h1_klines, h4_klines]):
                return None
            
            # Преобразуем в DataFrame
            m15_df = TechnicalIndicators.prepare_dataframe(m15_klines)
            h1_df = TechnicalIndicators.prepare_dataframe(h1_klines)
            h4_df = TechnicalIndicators.prepare_dataframe(h4_klines)
            
            # Рассчитываем тренды на разных таймфреймах
            m15_trend = RealisticMarketAnalyzer._calculate_trend(m15_df)
            h1_trend = RealisticMarketAnalyzer._calculate_trend(h1_df)
            h4_trend = RealisticMarketAnalyzer._calculate_trend(h4_df)
            
            # Волатильность
            volatility = h1_df['close'].pct_change().std()
            
            # Объемный анализ
            volume_trend = RealisticMarketAnalyzer._analyze_volume(h1_df)
            
            # Получаем текущий тикер для дополнительной информации
            ticker = client.get_ticker(symbol)
            
            return {
                'trends': {
                    'm15': m15_trend,
                    'h1': h1_trend,
                    'h4': h4_trend
                },
                'volatility': volatility,
                'volume_trend': volume_trend,
                'price_change_24h': float(ticker['price24hPcnt']) if ticker else 0,
                'current_price': float(ticker['lastPrice']) if ticker else 0,
                'bid_ask_spread': float(ticker['ask1Price']) - float(ticker['bid1Price']) if ticker else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting market structure: {e}")
            return None
    
    @staticmethod
    def _calculate_trend(df: pd.DataFrame) -> str:
        """Определить тренд на основе EMA и структуры цены"""
        if len(df) < 50:
            return 'UNDEFINED'
        
        # Рассчитываем EMA
        ema_9 = df['close'].ewm(span=9).mean()
        ema_21 = df['close'].ewm(span=21).mean()
        ema_50 = df['close'].ewm(span=50).mean()
        
        current_price = df['close'].iloc[-1]
        
        # Определяем тренд
        if current_price > ema_9.iloc[-1] > ema_21.iloc[-1] > ema_50.iloc[-1]:
            # Проверяем, что цена делает более высокие максимумы
            recent_highs = df['high'].iloc[-20:].rolling(5).max()
            if recent_highs.iloc[-1] > recent_highs.iloc[-10]:
                return 'STRONG_UP'
            return 'UP'
        elif current_price < ema_9.iloc[-1] < ema_21.iloc[-1] < ema_50.iloc[-1]:
            # Проверяем, что цена делает более низкие минимумы
            recent_lows = df['low'].iloc[-20:].rolling(5).min()
            if recent_lows.iloc[-1] < recent_lows.iloc[-10]:
                return 'STRONG_DOWN'
            return 'DOWN'
        else:
            return 'RANGING'
    
    @staticmethod
    def _analyze_volume(df: pd.DataFrame) -> str:
        """Анализ объемов"""
        recent_volume = df['volume'].iloc[-10:].mean()
        historical_volume = df['volume'].iloc[-50:-10].mean()
        
        if recent_volume > historical_volume * 1.5:
            return 'INCREASING'
        elif recent_volume < historical_volume * 0.7:
            return 'DECREASING'
        else:
            return 'NORMAL'
    
    @staticmethod
    def detect_support_resistance(df: pd.DataFrame) -> Dict[str, float]:
        """Определить уровни поддержки и сопротивления"""
        # Используем локальные минимумы и максимумы
        window = 20
        
        highs = df['high'].rolling(window=window, center=True).max()
        lows = df['low'].rolling(window=window, center=True).min()
        
        # Последние значимые уровни
        resistance = highs.dropna().iloc[-1]
        support = lows.dropna().iloc[-1]
        
        # Pivot points
        last_candle = df.iloc[-1]
        pivot = (last_candle['high'] + last_candle['low'] + last_candle['close']) / 3
        
        return {
            'support': support,
            'resistance': resistance,
            'pivot': pivot,
            'r1': 2 * pivot - last_candle['low'],
            's1': 2 * pivot - last_candle['high']
        }


class RealisticAdaptiveStrategy(BaseStrategy):
    """Реалистичная адаптивная стратегия"""
    
    def __init__(self, client: BybitClient, symbol: str):
        super().__init__(client, symbol)
        self.analyzer = RealisticMarketAnalyzer()
        self.market_structure = None
        self.risk_manager = RiskManager()
        
        # Параметры стратегии
        self.min_trend_alignment = 2  # Минимум 2 таймфрейма должны совпадать
        self.volatility_threshold = 0.03  # 3% волатильность считается высокой
        self.volume_confirmation = True  # Требовать подтверждения объемом
        
    def update_market_data(self):
        """Обновить данные о рынке"""
        self.market_structure = self.analyzer.get_market_structure(self.client, self.symbol)
        
        if not self.market_structure:
            logger.error("Failed to get market structure")
            return False
        
        logger.info(f"Market structure updated: {self.market_structure}")
        return True
    
    def analyze(self) -> Tuple[str, float]:
        """Анализировать рынок и генерировать сигнал"""
        if not self.update_market_data():
            return 'HOLD', 0.0
        
        # Получаем детальные данные для анализа
        klines = self.client.get_kline_data(self.symbol, "60", limit=100)
        if not klines:
            return 'HOLD', 0.0
        
        df = TechnicalIndicators.prepare_dataframe(klines)
        df = TechnicalIndicators.add_all_indicators(df)
        
        # Определяем режим рынка
        market_regime = self._determine_market_regime()
        
        # Генерируем сигнал в зависимости от режима
        if market_regime == 'TRENDING':
            return self._trend_following_signal(df)
        elif market_regime == 'RANGING':
            return self._range_trading_signal(df)
        elif market_regime == 'HIGH_VOLATILITY':
            return self._volatility_signal(df)
        else:
            return 'HOLD', 0.0
    
    def _determine_market_regime(self) -> str:
        """Определить текущий рыночный режим"""
        trends = self.market_structure['trends']
        volatility = self.market_structure['volatility']
        
        # Подсчитываем согласованность трендов
        trend_values = list(trends.values())
        up_count = sum(1 for t in trend_values if 'UP' in t)
        down_count = sum(1 for t in trend_values if 'DOWN' in t)
        
        # Высокая волатильность
        if volatility > self.volatility_threshold:
            return 'HIGH_VOLATILITY'
        
        # Трендовый рынок
        if up_count >= self.min_trend_alignment or down_count >= self.min_trend_alignment:
            return 'TRENDING'
        
        # Боковой рынок
        return 'RANGING'
    
    def _trend_following_signal(self, df: pd.DataFrame) -> Tuple[str, float]:
        """Сигнал для трендового рынка"""
        trends = self.market_structure['trends']
        
        # Определяем направление тренда
        up_count = sum(1 for t in trends.values() if 'UP' in t)
        down_count = sum(1 for t in trends.values() if 'DOWN' in t)
        
        # Получаем технические сигналы
        rsi = df['rsi'].iloc[-1]
        macd_hist = df['macd_hist'].iloc[-1]
        
        confidence = 0.0
        signal = 'HOLD'
        
        if up_count >= self.min_trend_alignment:
            # Восходящий тренд
            if rsi < 70 and macd_hist > 0:
                signal = 'BUY'
                confidence = min(1.0, up_count / 3 * 0.7)
                
                # Добавляем уверенность за подтверждение объемом
                if self.market_structure['volume_trend'] == 'INCREASING':
                    confidence = min(1.0, confidence + 0.2)
                    
        elif down_count >= self.min_trend_alignment:
            # Нисходящий тренд
            if rsi > 30 and macd_hist < 0:
                signal = 'SELL'
                confidence = min(1.0, down_count / 3 * 0.7)
                
                if self.market_structure['volume_trend'] == 'INCREASING':
                    confidence = min(1.0, confidence + 0.2)
        
        return signal, confidence
    
    def _range_trading_signal(self, df: pd.DataFrame) -> Tuple[str, float]:
        """Сигнал для бокового рынка"""
        # Получаем уровни поддержки/сопротивления
        levels = self.analyzer.detect_support_resistance(df)
        current_price = df['close'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        
        # Расстояние до уровней
        dist_to_support = (current_price - levels['support']) / current_price
        dist_to_resistance = (levels['resistance'] - current_price) / current_price
        
        signal = 'HOLD'
        confidence = 0.0
        
        # Покупка около поддержки
        if dist_to_support < 0.02 and rsi < 40:  # В пределах 2% от поддержки
            signal = 'BUY'
            confidence = 0.6
            if rsi < 30:
                confidence = 0.8
        
        # Продажа около сопротивления
        elif dist_to_resistance < 0.02 and rsi > 60:  # В пределах 2% от сопротивления
            signal = 'SELL'
            confidence = 0.6
            if rsi > 70:
                confidence = 0.8
        
        return signal, confidence
    
    def _volatility_signal(self, df: pd.DataFrame) -> Tuple[str, float]:
        """Сигнал для высокой волатильности (осторожный режим)"""
        # В период высокой волатильности используем более консервативный подход
        rsi = df['rsi'].iloc[-1]
        bb_position = (df['close'].iloc[-1] - df['bb_lower'].iloc[-1]) / (df['bb_upper'].iloc[-1] - df['bb_lower'].iloc[-1])
        
        signal = 'HOLD'
        confidence = 0.0
        
        # Только экстремальные условия
        if rsi < 20 and bb_position < 0.1:  # Сильная перепроданность
            signal = 'BUY'
            confidence = 0.5
        elif rsi > 80 and bb_position > 0.9:  # Сильная перекупленность
            signal = 'SELL'
            confidence = 0.5
        
        return signal, confidence
    
    def should_enter_position(self) -> bool:
        """Определить, следует ли входить в позицию"""
        # Проверяем риск-менеджмент
        balance = 10000  # Здесь нужно получить реальный баланс
        if not self.risk_manager.can_open_position(balance, self.position_size):
            return False
        
        # Не входим при экстремальной волатильности
        if self.market_structure and self.market_structure['volatility'] > 0.05:
            logger.warning("Volatility too high, skipping entry")
            return False
        
        # Проверяем 24h изменение цены (не входим после больших движений)
        if self.market_structure and abs(self.market_structure['price_change_24h']) > 0.15:
            logger.warning("Price moved too much in 24h, skipping entry")
            return False
        
        return super().should_enter_position()


class RealisticDCAStrategy(BaseStrategy):
    """Реалистичная DCA стратегия"""
    
    def __init__(self, client: BybitClient, symbol: str):
        super().__init__(client, symbol)
        
        # Параметры DCA
        self.dca_amount = 100  # USDT на каждую покупку
        self.min_price_drop = 0.05  # Минимальное падение 5% между покупками
        self.max_buys_per_day = 3
        self.last_buy_price = None
        self.daily_buys = 0
        self.last_reset = datetime.now().date()
        
    def reset_daily_counter(self):
        """Сбросить дневной счетчик"""
        current_date = datetime.now().date()
        if current_date > self.last_reset:
            self.daily_buys = 0
            self.last_reset = current_date
    
    def analyze(self) -> Tuple[str, float]:
        """Анализ для DCA"""
        self.reset_daily_counter()
        
        # Получаем текущую цену
        ticker = self.client.get_ticker(self.symbol)
        if not ticker:
            return 'HOLD', 0.0
        
        current_price = float(ticker['lastPrice'])
        
        # Первая покупка или проверка условий для следующей
        if self.last_buy_price is None:
            # Первая покупка - проверяем общие условия рынка
            klines = self.client.get_kline_data(self.symbol, "D", limit=30)
            if klines:
                df = TechnicalIndicators.prepare_dataframe(klines)
                month_high = df['high'].max()
                
                # Покупаем если цена упала на 10% от месячного максимума
                if current_price < month_high * 0.9:
                    self.last_buy_price = current_price
                    return 'BUY', 0.7
        else:
            # Последующие покупки
            price_drop = (self.last_buy_price - current_price) / self.last_buy_price
            
            if price_drop >= self.min_price_drop and self.daily_buys < self.max_buys_per_day:
                self.last_buy_price = current_price
                self.daily_buys += 1
                return 'BUY', 0.6
        
        return 'HOLD', 0.0
    
    def enter_position(self, side: str) -> bool:
        """Входить маленькими порциями"""
        if side == 'Buy':
            # Сохраняем оригинальный размер
            original_size = self.position_size
            # Используем фиксированный размер для DCA
            self.position_size = self.dca_amount
            
            result = super().enter_position(side)
            
            # Восстанавливаем оригинальный размер
            self.position_size = original_size
            
            return result
        
        return super().enter_position(side)


class RealisticGridStrategy(BaseStrategy):
    """Реалистичная сеточная стратегия"""
    
    def __init__(self, client: BybitClient, symbol: str):
        super().__init__(client, symbol)
        
        # Параметры сетки
        self.grid_levels = 10
        self.grid_spacing_percent = 1.0  # 1% между уровнями
        self.order_amount = 50  # USDT на каждый ордер
        self.grid_orders = []
        self.last_update_price = 0
        self.update_threshold = 0.05  # Обновить сетку при движении 5%
        
    def setup_grid(self, center_price: float) -> bool:
        """Установить сетку ордеров"""
        try:
            # Отменяем старые ордера
            self.client.cancel_all_orders(self.symbol)
            self.grid_orders = []
            
            # Создаем новую сетку
            for i in range(1, self.grid_levels + 1):
                # Ордера на покупку ниже текущей цены
                buy_price = center_price * (1 - i * self.grid_spacing_percent / 100)
                buy_qty = self.order_amount / buy_price
                
                buy_order = self.client.place_order(
                    symbol=self.symbol,
                    side="Buy",
                    order_type="Limit",
                    qty=str(round(buy_qty, 3)),
                    price=str(round(buy_price, 2)),
                    time_in_force="GTC"
                )
                
                if buy_order:
                    self.grid_orders.append(buy_order)
                
                # Ордера на продажу выше текущей цены
                sell_price = center_price * (1 + i * self.grid_spacing_percent / 100)
                sell_qty = self.order_amount / sell_price
                
                sell_order = self.client.place_order(
                    symbol=self.symbol,
                    side="Sell",
                    order_type="Limit",
                    qty=str(round(sell_qty, 3)),
                    price=str(round(sell_price, 2)),
                    time_in_force="GTC"
                )
                
                if sell_order:
                    self.grid_orders.append(sell_order)
            
            self.last_update_price = center_price
            logger.info(f"Grid setup completed with {len(self.grid_orders)} orders")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up grid: {e}")
            return False
    
    def analyze(self) -> Tuple[str, float]:
        """Сетка не требует анализа для сигналов"""
        return 'HOLD', 0.0
    
    def execute(self):
        """Выполнить сеточную стратегию"""
        try:
            # Получаем текущую цену
            ticker = self.client.get_ticker(self.symbol)
            if not ticker:
                return
            
            current_price = float(ticker['lastPrice'])
            
            # Инициализируем сетку при первом запуске
            if not self.grid_orders:
                self.setup_grid(current_price)
                return
            
            # Проверяем, нужно ли перестроить сетку
            if self.last_update_price > 0:
                price_change = abs(current_price - self.last_update_price) / self.last_update_price
                
                if price_change > self.update_threshold:
                    logger.info(f"Price moved {price_change:.2%}, rebuilding grid")
                    self.setup_grid(current_price)
            
        except Exception as e:
            logger.error(f"Error executing grid strategy: {e}")


if __name__ == "__main__":
    # Тестирование реалистичных стратегий
    from bybit_client import BybitClient
    
    client = BybitClient(testnet=True)
    
    # Тест реалистичной адаптивной стратегии
    print("\n=== Testing Realistic Adaptive Strategy ===")
    adaptive = RealisticAdaptiveStrategy(client, "BTCUSDT")
    signal, confidence = adaptive.analyze()
    print(f"Signal: {signal}, Confidence: {confidence:.2%}")
    
    if adaptive.market_structure:
        print(f"Market trends: {adaptive.market_structure['trends']}")
        print(f"Volatility: {adaptive.market_structure['volatility']:.4f}")
        print(f"Volume trend: {adaptive.market_structure['volume_trend']}")
    
    # Тест DCA стратегии
    print("\n=== Testing Realistic DCA Strategy ===")
    dca = RealisticDCAStrategy(client, "BTCUSDT")
    signal, confidence = dca.analyze()
    print(f"DCA Signal: {signal}, Confidence: {confidence:.2%}")
    
    # Тест Grid стратегии
    print("\n=== Testing Realistic Grid Strategy ===")
    grid = RealisticGridStrategy(client, "BTCUSDT")
    print(f"Grid initialized with {grid.grid_levels} levels")
    print(f"Grid spacing: {grid.grid_spacing_percent}%")
