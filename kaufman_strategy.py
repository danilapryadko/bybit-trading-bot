"""
Стратегия на основе методологии Перри Кауфмана
Интеграция с существующим торговым ботом
"""

import logging
from typing import Tuple, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime
import os
from dotenv import load_dotenv

from strategies import BaseStrategy
from bybit_client import BybitClient
from indicators import TechnicalIndicators
from kaufman_indicators import (
    KaufmanIndicators, 
    KaufmanPositionSizer, 
    KaufmanStrategy as KaufmanCore
)
from risk_manager import RiskManager

logger = logging.getLogger(__name__)

class KaufmanAdaptiveStrategy(BaseStrategy):
    """
    Адаптивная стратегия на основе методов Перри Кауфмана
    
    Особенности:
    1. KAMA (Kaufman Adaptive Moving Average) вместо обычных MA
    2. Efficiency Ratio для определения качества тренда
    3. Адаптивные размеры позиций и стоп-лоссы
    4. Фильтрация шума для избегания ложных сигналов
    """
    
    def __init__(self, client: BybitClient, symbol: str):
        super().__init__(client, symbol)
        
        # Инициализация компонентов Кауфмана
        self.kaufman_indicators = KaufmanIndicators()
        self.position_sizer = KaufmanPositionSizer()
        self.core_strategy = KaufmanCore()
        self.risk_manager = RiskManager()
        
        load_dotenv()
        
        # Параметры стратегии из .env или дефолтные
        self.min_er_for_entry = float(os.getenv('KAUFMAN_MIN_ER', 0.3))
        self.strong_trend_er = float(os.getenv('KAUFMAN_STRONG_ER', 0.6))
        self.max_noise_level = float(os.getenv('KAUFMAN_MAX_NOISE', 0.7))
        
        # История для анализа эффективности
        self.signal_history = []
        self.er_history = []
        
        logger.info(f"Kaufman Adaptive Strategy initialized for {symbol}")
        logger.info(f"Parameters: Min ER={self.min_er_for_entry}, "
                   f"Strong ER={self.strong_trend_er}, Max Noise={self.max_noise_level}")
    
    def analyze(self) -> Tuple[str, float]:
        """
        Анализ рынка по методологии Кауфмана
        """
        try:
            # Получаем данные для анализа (больше данных для точности)
            klines = self.client.get_kline_data(self.symbol, "60", limit=200)
            if not klines or len(klines) < 100:
                logger.warning("Insufficient data for Kaufman analysis")
                return 'HOLD', 0.0
            
            # Подготавливаем DataFrame
            df = TechnicalIndicators.prepare_dataframe(klines)
            
            # Рассчитываем индикаторы Кауфмана
            prices = df['close']
            
            # KAMA
            kama = self.kaufman_indicators.calculate_kama(prices)
            
            # Efficiency Ratio (основная метрика Кауфмана)
            er = self.kaufman_indicators.calculate_efficiency_ratio(prices.values, 10)
            
            # Сохраняем историю ER для анализа
            self.er_history.append({'timestamp': datetime.now(), 'er': er})
            if len(self.er_history) > 100:
                self.er_history.pop(0)
            
            # Определяем состояние рынка
            market_state = self.kaufman_indicators.calculate_market_state(df)
            
            # Уровень шума
            noise_level = self.kaufman_indicators.calculate_noise_level(prices, 20)
            
            # Логируем состояние рынка
            logger.info(f"Market Analysis - State: {market_state['state']}, "
                       f"ER: {er:.3f}, Noise: {noise_level:.2%}")
            
            # Генерируем сигнал
            signal, confidence = self._generate_kaufman_signal(
                df, kama, er, market_state, noise_level
            )
            
            # Сохраняем историю сигналов
            self.signal_history.append({
                'timestamp': datetime.now(),
                'signal': signal,
                'confidence': confidence,
                'er': er,
                'market_state': market_state['state']
            })
            
            return signal, confidence
            
        except Exception as e:
            logger.error(f"Error in Kaufman analysis: {e}")
            return 'HOLD', 0.0
    
    def _generate_kaufman_signal(self, df: pd.DataFrame, kama: pd.Series, 
                                 er: float, market_state: Dict, 
                                 noise_level: float) -> Tuple[str, float]:
        """
        Генерация сигнала по правилам Кауфмана
        """
        current_price = df['close'].iloc[-1]
        
        # Проверяем базовые условия
        if pd.isna(kama.iloc[-1]):
            return 'HOLD', 0.0
        
        # Фильтр 1: Не торгуем в высоком шуме
        if noise_level > self.max_noise_level:
            logger.info(f"High noise detected ({noise_level:.2%}), skipping trade")
            return 'HOLD', 0.0
        
        # Фильтр 2: Минимальный Efficiency Ratio
        if er < self.min_er_for_entry:
            logger.info(f"Low ER ({er:.3f}), market too choppy")
            return 'HOLD', 0.0
        
        # Адаптивный RSI
        adaptive_rsi = self.kaufman_indicators.calculate_adaptive_rsi(df['close'])
        current_rsi = adaptive_rsi.iloc[-1] if not pd.isna(adaptive_rsi.iloc[-1]) else 50
        
        # Определяем сигнал в зависимости от состояния рынка
        signal = 'HOLD'
        confidence = 0.0
        
        # СИЛЬНЫЙ ТРЕНД - агрессивная торговля
        if market_state['state'] == 'STRONG_TREND':
            if market_state['direction'] == 'UP':
                if current_price > kama.iloc[-1]:
                    # Проверяем, что не перекуплен
                    if current_rsi < 75:
                        signal = 'BUY'
                        confidence = min(0.9, er * 1.2)  # Высокая уверенность
                        logger.info(f"Strong uptrend detected, BUY signal")
            
            elif market_state['direction'] == 'DOWN':
                if current_price < kama.iloc[-1]:
                    # Проверяем, что не перепродан
                    if current_rsi > 25:
                        signal = 'SELL'
                        confidence = min(0.9, er * 1.2)
                        logger.info(f"Strong downtrend detected, SELL signal")
        
        # СЛАБЫЙ ТРЕНД - консервативная торговля
        elif market_state['state'] == 'WEAK_TREND':
            # Ждем отката к KAMA для входа
            price_to_kama = (current_price - kama.iloc[-1]) / kama.iloc[-1]
            
            if market_state['direction'] == 'UP':
                # Покупаем на откате к KAMA в восходящем тренде
                if abs(price_to_kama) < 0.01 and current_price > kama.iloc[-1]:
                    if 40 < current_rsi < 60:
                        signal = 'BUY'
                        confidence = er * 0.7  # Средняя уверенность
                        logger.info(f"Weak uptrend, buying on pullback")
            
            elif market_state['direction'] == 'DOWN':
                # Продаем на откате к KAMA в нисходящем тренде
                if abs(price_to_kama) < 0.01 and current_price < kama.iloc[-1]:
                    if 40 < current_rsi < 60:
                        signal = 'SELL'
                        confidence = er * 0.7
                        logger.info(f"Weak downtrend, selling on pullback")
        
        # ПЕРЕХОДНОЕ СОСТОЯНИЕ - ищем разворот
        elif market_state['state'] == 'TRANSITIONAL':
            # Проверяем пересечение KAMA
            if len(df) >= 2:
                prev_price = df['close'].iloc[-2]
                prev_kama = kama.iloc[-2]
                
                # Бычье пересечение
                if prev_price <= prev_kama and current_price > kama.iloc[-1]:
                    if current_rsi > 45:
                        signal = 'BUY'
                        confidence = er * 0.5  # Низкая уверенность
                        logger.info(f"Potential bullish reversal")
                
                # Медвежье пересечение
                elif prev_price >= prev_kama and current_price < kama.iloc[-1]:
                    if current_rsi < 55:
                        signal = 'SELL'
                        confidence = er * 0.5
                        logger.info(f"Potential bearish reversal")
        
        return signal, confidence
    
    def calculate_position_size(self, price: float) -> float:
        """
        Адаптивный расчет размера позиции по Кауфману
        """
        # Получаем последний ER
        if self.er_history:
            current_er = self.er_history[-1]['er']
        else:
            current_er = 0.5
        
        # Получаем ATR для расчета волатильности
        klines = self.client.get_kline_data(self.symbol, "60", limit=50)
        if klines:
            df = TechnicalIndicators.prepare_dataframe(klines)
            df = TechnicalIndicators.add_all_indicators(df)
            current_atr = df['atr'].iloc[-1] if 'atr' in df else price * 0.02
            avg_atr = df['atr'].mean() if 'atr' in df else price * 0.02
        else:
            current_atr = price * 0.02
            avg_atr = price * 0.02
        
        # Расчет стоп-лосса
        stop_loss_price = price - (current_atr * 2)
        
        # Используем Kaufman Position Sizer
        position_size = self.position_sizer.calculate_position_size(
            account_balance=10000,  # Нужно получить реальный баланс
            entry_price=price,
            stop_loss_price=stop_loss_price,
            efficiency_ratio=current_er,
            volatility=current_atr,
            avg_volatility=avg_atr
        )
        
        # Конвертируем в USDT
        position_value = position_size * price
        
        # Ограничиваем максимальным размером
        max_position = min(self.position_size, position_value)
        
        logger.info(f"Kaufman position sizing: ER={current_er:.3f}, "
                   f"Size={max_position:.2f} USDT")
        
        return max_position
    
    def calculate_stop_loss(self, entry_price: float, side: str) -> float:
        """
        Адаптивный стоп-лосс по Кауфману
        """
        # Получаем последний ER и ATR
        klines = self.client.get_kline_data(self.symbol, "60", limit=50)
        if not klines:
            # Fallback на стандартный стоп
            return super().calculate_stop_loss(entry_price, side)
        
        df = TechnicalIndicators.prepare_dataframe(klines)
        df = TechnicalIndicators.add_all_indicators(df)
        
        current_atr = df['atr'].iloc[-1] if 'atr' in df else entry_price * 0.02
        
        # Получаем ER
        if self.er_history:
            current_er = self.er_history[-1]['er']
        else:
            current_er = 0.5
        
        # Адаптивный стоп: ближе в трендах, дальше в шуме
        if current_er > self.strong_trend_er:
            # Сильный тренд - близкий стоп
            stop_distance = current_atr * 1.5
        elif current_er > self.min_er_for_entry:
            # Слабый тренд - средний стоп
            stop_distance = current_atr * 2.0
        else:
            # Шум - далекий стоп
            stop_distance = current_atr * 3.0
        
        if side == 'Buy':
            stop_loss = entry_price - stop_distance
        else:
            stop_loss = entry_price + stop_distance
        
        logger.info(f"Adaptive stop-loss: ER={current_er:.3f}, "
                   f"Distance={stop_distance:.2f}")
        
        return round(stop_loss, 2)
    
    def calculate_take_profit(self, entry_price: float, side: str) -> float:
        """
        Адаптивный тейк-профит по Кауфману
        """
        # Получаем стоп-лосс для расчета R:R
        stop_loss = self.calculate_stop_loss(entry_price, side)
        stop_distance = abs(entry_price - stop_loss)
        
        # Получаем ER
        if self.er_history:
            current_er = self.er_history[-1]['er']
        else:
            current_er = 0.5
        
        # Адаптивное соотношение риск/прибыль
        if current_er > self.strong_trend_er:
            # Сильный тренд - даем прибыли течь
            reward_ratio = 3.0
        elif current_er > self.min_er_for_entry:
            # Слабый тренд - средний R:R
            reward_ratio = 2.0
        else:
            # Шум - быстрый выход
            reward_ratio = 1.5
        
        if side == 'Buy':
            take_profit = entry_price + (stop_distance * reward_ratio)
        else:
            take_profit = entry_price - (stop_distance * reward_ratio)
        
        logger.info(f"Adaptive take-profit: R:R={reward_ratio:.1f}")
        
        return round(take_profit, 2)
    
    def should_enter_position(self) -> bool:
        """
        Дополнительные фильтры Кауфмана для входа
        """
        # Базовые проверки
        if not super().should_enter_position():
            return False
        
        # Проверяем тренд ER за последние 5 сигналов
        if len(self.er_history) >= 5:
            recent_ers = [h['er'] for h in self.er_history[-5:]]
            avg_recent_er = sum(recent_ers) / len(recent_ers)
            
            # Не входим, если ER падает
            if recent_ers[-1] < avg_recent_er * 0.8:
                logger.info("ER declining, skipping entry")
                return False
        
        # Проверяем консистентность сигналов
        if len(self.signal_history) >= 3:
            recent_signals = [h['signal'] for h in self.signal_history[-3:]]
            
            # Не входим при противоречивых сигналах
            if 'BUY' in recent_signals and 'SELL' in recent_signals:
                logger.info("Contradictory signals, skipping entry")
                return False
        
        return True
    
    def should_exit_position(self) -> bool:
        """
        Адаптивный выход по Кауфману
        """
        if not self.position:
            return False
        
        # Получаем текущие данные
        klines = self.client.get_kline_data(self.symbol, "60", limit=50)
        if not klines:
            return super().should_exit_position()
        
        df = TechnicalIndicators.prepare_dataframe(klines)
        prices = df['close']
        
        # Рассчитываем текущий ER
        current_er = self.kaufman_indicators.calculate_efficiency_ratio(prices.values, 10)
        
        # Рассчитываем KAMA
        kama = self.kaufman_indicators.calculate_kama(prices)
        current_price = prices.iloc[-1]
        
        # Выход при развороте тренда
        if self.position['side'] == 'Buy':
            # Выход из лонга при пересечении KAMA вниз
            if current_price < kama.iloc[-1] and current_er < self.min_er_for_entry:
                logger.info("Exiting long: price below KAMA and low ER")
                return True
        else:
            # Выход из шорта при пересечении KAMA вверх
            if current_price > kama.iloc[-1] and current_er < self.min_er_for_entry:
                logger.info("Exiting short: price above KAMA and low ER")
                return True
        
        # Выход при резком падении ER (тренд заканчивается)
        if self.er_history and len(self.er_history) >= 2:
            prev_er = self.er_history[-2]['er']
            if current_er < prev_er * 0.5:
                logger.info(f"ER dropped sharply ({prev_er:.3f} -> {current_er:.3f}), exiting")
                return True
        
        return super().should_exit_position()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Метрики производительности стратегии Кауфмана
        """
        if not self.signal_history:
            return {}
        
        # Анализ сигналов по состояниям рынка
        signals_by_state = {}
        for signal in self.signal_history:
            state = signal.get('market_state', 'UNKNOWN')
            if state not in signals_by_state:
                signals_by_state[state] = []
            signals_by_state[state].append(signal)
        
        # Средний ER
        avg_er = sum(h['er'] for h in self.er_history) / len(self.er_history) if self.er_history else 0
        
        # Консистентность сигналов
        if len(self.signal_history) >= 2:
            consistent_signals = sum(
                1 for i in range(1, len(self.signal_history))
                if self.signal_history[i]['signal'] == self.signal_history[i-1]['signal']
            )
            consistency_rate = consistent_signals / (len(self.signal_history) - 1)
        else:
            consistency_rate = 0
        
        return {
            'average_er': avg_er,
            'signals_by_market_state': {
                state: len(signals) for state, signals in signals_by_state.items()
            },
            'signal_consistency': consistency_rate,
            'total_signals': len(self.signal_history),
            'current_er': self.er_history[-1]['er'] if self.er_history else 0
        }


if __name__ == "__main__":
    # Тестирование стратегии Кауфмана
    from bybit_client import BybitClient
    
    client = BybitClient(testnet=True)
    strategy = KaufmanAdaptiveStrategy(client, "BTCUSDT")
    
    # Анализ рынка
    signal, confidence = strategy.analyze()
    
    print("\n=== Kaufman Adaptive Strategy ===")
    print(f"Signal: {signal}")
    print(f"Confidence: {confidence:.2%}")
    
    # Метрики производительности
    metrics = strategy.get_performance_metrics()
    if metrics:
        print("\n=== Performance Metrics ===")
        print(f"Average ER: {metrics.get('average_er', 0):.3f}")
        print(f"Current ER: {metrics.get('current_er', 0):.3f}")
        print(f"Signal Consistency: {metrics.get('signal_consistency', 0):.2%}")
        print(f"Signals by Market State: {metrics.get('signals_by_market_state', {})}")
    
    # Расчет адаптивных параметров
    ticker = client.get_ticker("BTCUSDT")
    if ticker:
        price = float(ticker['lastPrice'])
        
        # Размер позиции
        position_size = strategy.calculate_position_size(price)
        print(f"\nAdaptive Position Size: {position_size:.2f} USDT")
        
        # Стоп-лосс и тейк-профит
        stop_loss = strategy.calculate_stop_loss(price, 'Buy')
        take_profit = strategy.calculate_take_profit(price, 'Buy')
        
        print(f"Adaptive Stop-Loss: ${stop_loss:.2f} ({(price - stop_loss)/price*100:.2%})")
        print(f"Adaptive Take-Profit: ${take_profit:.2f} ({(take_profit - price)/price*100:.2%})")
        
        # Risk:Reward
        risk = price - stop_loss
        reward = take_profit - price
        rr_ratio = reward / risk if risk > 0 else 0
        print(f"Risk:Reward Ratio: 1:{rr_ratio:.1f}")
