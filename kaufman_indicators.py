"""
Индикаторы и стратегии Перри Кауфмана для криптовалютного трейдинга
Based on "Trading Systems and Methods" by Perry J. Kaufman
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict, Any
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class KaufmanIndicators:
    """Адаптивные индикаторы Перри Кауфмана"""
    
    @staticmethod
    def calculate_efficiency_ratio(prices: np.ndarray, period: int = 10) -> float:
        """
        Расчет Efficiency Ratio (ER) - ключевая метрика Кауфмана
        
        ER = Направленное движение / Общая волатильность
        
        Значения:
        - ER > 0.6: Сильный тренд
        - 0.3 < ER < 0.6: Слабый тренд
        - ER < 0.3: Боковик/шум
        """
        if len(prices) < period + 1:
            return 0.0
        
        # Направленное изменение за период
        direction = abs(prices[-1] - prices[-period-1])
        
        # Сумма абсолютных изменений (волатильность)
        volatility = sum(abs(prices[i] - prices[i-1]) for i in range(-period, 0))
        
        if volatility == 0:
            return 0.0
        
        return direction / volatility
    
    @staticmethod
    def calculate_kama(prices: pd.Series, 
                      er_period: int = 10,
                      fast_ema: int = 2,
                      slow_ema: int = 30) -> pd.Series:
        """
        Kaufman's Adaptive Moving Average (KAMA)
        
        Адаптивная скользящая средняя, которая:
        - Быстро реагирует в трендах
        - Медленно меняется в боковике
        - Фильтрует рыночный шум
        """
        kama = pd.Series(index=prices.index, dtype=float)
        
        # Константы для EMA
        fastest_sc = 2 / (fast_ema + 1)
        slowest_sc = 2 / (slow_ema + 1)
        
        # Начальное значение
        kama.iloc[er_period] = prices.iloc[er_period]
        
        for i in range(er_period + 1, len(prices)):
            # Расчет Efficiency Ratio
            change = abs(prices.iloc[i] - prices.iloc[i - er_period])
            volatility = sum(abs(prices.iloc[j] - prices.iloc[j-1]) 
                           for j in range(i - er_period + 1, i + 1))
            
            er = change / volatility if volatility != 0 else 0
            
            # Smoothing Constant (SC) - адаптивный коэффициент
            sc = (er * (fastest_sc - slowest_sc) + slowest_sc) ** 2
            
            # KAMA calculation
            kama.iloc[i] = kama.iloc[i-1] + sc * (prices.iloc[i] - kama.iloc[i-1])
        
        return kama
    
    @staticmethod
    def calculate_adaptive_rsi(prices: pd.Series, 
                              base_period: int = 14,
                              min_period: int = 7,
                              max_period: int = 28) -> pd.Series:
        """
        Адаптивный RSI по методологии Кауфмана
        Период RSI меняется в зависимости от Efficiency Ratio
        """
        adaptive_rsi = pd.Series(index=prices.index, dtype=float)
        
        for i in range(max_period, len(prices)):
            # Расчет ER для определения периода
            er = KaufmanIndicators.calculate_efficiency_ratio(
                prices.iloc[i-base_period:i+1].values, base_period
            )
            
            # Адаптивный период: меньше в трендах, больше в боковике
            adaptive_period = int(max_period - er * (max_period - min_period))
            
            # Расчет RSI с адаптивным периодом
            delta = prices.iloc[i-adaptive_period:i+1].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=adaptive_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=adaptive_period).mean()
            
            rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] != 0 else 100
            adaptive_rsi.iloc[i] = 100 - (100 / (1 + rs))
        
        return adaptive_rsi
    
    @staticmethod
    def calculate_fractal_efficiency(prices: pd.Series, period: int = 20) -> float:
        """
        Fractal Efficiency - измерение фрактальной размерности движения цены
        По Кауфману для определения характера рынка
        """
        if len(prices) < period:
            return 1.0
        
        # Расчет фрактальной размерности
        n = period
        
        # Максимальное расстояние
        max_diff = prices.iloc[-period:].max() - prices.iloc[-period:].min()
        
        # Длина ломаной линии
        length = sum(abs(prices.iloc[i] - prices.iloc[i-1]) 
                    for i in range(-period + 1, 0))
        
        if max_diff == 0:
            return 1.0
        
        # Fractal dimension
        fractal_dim = 1 + (np.log(length / max_diff) / np.log(2 * n))
        
        # Преобразование в Efficiency (1 = тренд, 2 = случайное блуждание)
        efficiency = 2 - fractal_dim
        
        return max(0, min(1, efficiency))
    
    @staticmethod
    def calculate_noise_level(prices: pd.Series, period: int = 20) -> float:
        """
        Уровень шума по Кауфману
        Используется для фильтрации ложных сигналов
        """
        if len(prices) < period:
            return 1.0
        
        # ER за период
        er = KaufmanIndicators.calculate_efficiency_ratio(
            prices.iloc[-period:].values, period - 1
        )
        
        # Noise = 1 - ER
        return 1 - er
    
    @staticmethod
    def calculate_adaptive_bands(prices: pd.Series, 
                                kama: pd.Series,
                                atr: pd.Series,
                                multiplier: float = 2.0) -> Tuple[pd.Series, pd.Series]:
        """
        Адаптивные полосы Кауфмана
        Ширина полос зависит от Efficiency Ratio
        """
        er_period = 10
        upper_band = pd.Series(index=prices.index, dtype=float)
        lower_band = pd.Series(index=prices.index, dtype=float)
        
        for i in range(er_period, len(prices)):
            if pd.isna(kama.iloc[i]) or pd.isna(atr.iloc[i]):
                continue
            
            # Расчет ER
            er = KaufmanIndicators.calculate_efficiency_ratio(
                prices.iloc[max(0, i-er_period):i+1].values, er_period
            )
            
            # Адаптивный множитель: уже в трендах, шире в боковике
            adaptive_mult = multiplier * (2 - er)  # От multiplier до 2*multiplier
            
            # Полосы
            upper_band.iloc[i] = kama.iloc[i] + adaptive_mult * atr.iloc[i]
            lower_band.iloc[i] = kama.iloc[i] - adaptive_mult * atr.iloc[i]
        
        return upper_band, lower_band
    
    @staticmethod
    def calculate_market_state(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Комплексное определение состояния рынка по Кауфману
        """
        prices = df['close']
        
        # Efficiency Ratio на разных таймфреймах
        er_short = KaufmanIndicators.calculate_efficiency_ratio(prices.values, 10)
        er_medium = KaufmanIndicators.calculate_efficiency_ratio(prices.values, 20)
        er_long = KaufmanIndicators.calculate_efficiency_ratio(prices.values, 50)
        
        # Fractal Efficiency
        fractal_eff = KaufmanIndicators.calculate_fractal_efficiency(prices, 30)
        
        # Noise Level
        noise = KaufmanIndicators.calculate_noise_level(prices, 20)
        
        # Определение состояния
        avg_er = (er_short + er_medium + er_long) / 3
        
        if avg_er > 0.6:
            state = 'STRONG_TREND'
            confidence = avg_er
        elif avg_er > 0.4:
            state = 'WEAK_TREND'
            confidence = avg_er
        elif avg_er > 0.2:
            state = 'TRANSITIONAL'
            confidence = 0.5
        else:
            state = 'RANGING'
            confidence = 1 - avg_er
        
        # Направление тренда
        if state in ['STRONG_TREND', 'WEAK_TREND']:
            kama = KaufmanIndicators.calculate_kama(prices)
            if not pd.isna(kama.iloc[-1]):
                direction = 'UP' if prices.iloc[-1] > kama.iloc[-1] else 'DOWN'
            else:
                direction = 'UNDEFINED'
        else:
            direction = 'SIDEWAYS'
        
        return {
            'state': state,
            'direction': direction,
            'confidence': confidence,
            'efficiency_ratio': avg_er,
            'fractal_efficiency': fractal_eff,
            'noise_level': noise,
            'er_short': er_short,
            'er_medium': er_medium,
            'er_long': er_long
        }


class KaufmanPositionSizer:
    """Управление размером позиции по методологии Кауфмана"""
    
    def __init__(self, 
                 base_risk_percent: float = 2.0,
                 max_risk_percent: float = 5.0,
                 min_risk_percent: float = 0.5):
        """
        Параметры:
        - base_risk_percent: базовый риск на сделку
        - max_risk_percent: максимальный риск в сильном тренде
        - min_risk_percent: минимальный риск в шуме
        """
        self.base_risk = base_risk_percent / 100
        self.max_risk = max_risk_percent / 100
        self.min_risk = min_risk_percent / 100
    
    def calculate_position_size(self,
                               account_balance: float,
                               entry_price: float,
                               stop_loss_price: float,
                               efficiency_ratio: float,
                               volatility: float,
                               avg_volatility: float) -> float:
        """
        Расчет размера позиции по Кауфману
        
        Учитывает:
        1. Efficiency Ratio (качество тренда)
        2. Текущую волатильность относительно средней
        3. Расстояние до стоп-лосса
        """
        # Риск на основе ER
        if efficiency_ratio > 0.6:
            # Сильный тренд - увеличиваем риск
            risk_multiplier = 1.5
        elif efficiency_ratio > 0.3:
            # Слабый тренд - нормальный риск
            risk_multiplier = 1.0
        else:
            # Шум - уменьшаем риск
            risk_multiplier = 0.5
        
        # Корректировка на волатильность
        volatility_ratio = volatility / avg_volatility if avg_volatility > 0 else 1
        volatility_adjustment = 1 / max(0.5, min(2, volatility_ratio))
        
        # Итоговый риск
        adjusted_risk = self.base_risk * risk_multiplier * volatility_adjustment
        adjusted_risk = max(self.min_risk, min(self.max_risk, adjusted_risk))
        
        # Размер позиции
        risk_amount = account_balance * adjusted_risk
        stop_loss_distance = abs(entry_price - stop_loss_price)
        
        if stop_loss_distance == 0:
            return 0
        
        position_size = risk_amount / stop_loss_distance
        
        # Конвертация в количество монет
        coin_amount = position_size / entry_price
        
        return coin_amount
    
    def calculate_dynamic_stops(self,
                               entry_price: float,
                               atr: float,
                               efficiency_ratio: float) -> Tuple[float, float]:
        """
        Динамические стоп-лосс и тейк-профит по Кауфману
        """
        # Стоп-лосс: ближе в трендах, дальше в шуме
        if efficiency_ratio > 0.6:
            stop_distance = atr * 1.5
        elif efficiency_ratio > 0.3:
            stop_distance = atr * 2.0
        else:
            stop_distance = atr * 3.0
        
        # Тейк-профит: соотношение риск/прибыль зависит от ER
        if efficiency_ratio > 0.6:
            reward_ratio = 3.0  # Даем прибыли течь в тренде
        elif efficiency_ratio > 0.3:
            reward_ratio = 2.0
        else:
            reward_ratio = 1.5  # Быстрый выход в шуме
        
        stop_loss = entry_price - stop_distance
        take_profit = entry_price + (stop_distance * reward_ratio)
        
        return stop_loss, take_profit


class KaufmanStrategy:
    """Комплексная стратегия на основе методов Кауфмана"""
    
    def __init__(self):
        self.indicators = KaufmanIndicators()
        self.position_sizer = KaufmanPositionSizer()
        
        # Параметры стратегии
        self.min_er_for_entry = 0.3  # Минимальный ER для входа
        self.strong_trend_er = 0.6   # ER для определения сильного тренда
        self.noise_threshold = 0.7   # Максимальный уровень шума для входа
        
        # История для анализа
        self.trade_history = []
        
    def generate_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Генерация торгового сигнала по методологии Кауфмана
        """
        # Расчет индикаторов
        prices = df['close']
        
        # KAMA
        kama = self.indicators.calculate_kama(prices)
        
        # Efficiency Ratio
        er = self.indicators.calculate_efficiency_ratio(prices.values, 10)
        
        # Adaptive RSI
        adaptive_rsi = self.indicators.calculate_adaptive_rsi(prices)
        
        # Market State
        market_state = self.indicators.calculate_market_state(df)
        
        # Noise Level
        noise = self.indicators.calculate_noise_level(prices, 20)
        
        # ATR для расчета стопов
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(14).mean().iloc[-1]
        
        # Adaptive Bands
        upper_band, lower_band = self.indicators.calculate_adaptive_bands(
            prices, kama, true_range.rolling(14).mean(), 2.0
        )
        
        # Генерация сигнала
        signal = self._determine_signal(
            prices, kama, er, adaptive_rsi, 
            upper_band, lower_band, market_state, noise
        )
        
        # Расчет размера позиции и стопов
        if signal['action'] != 'HOLD':
            # Средняя волатильность за 30 дней
            avg_volatility = true_range.rolling(30).mean().iloc[-1]
            
            # Размер позиции
            stop_loss, take_profit = self.position_sizer.calculate_dynamic_stops(
                prices.iloc[-1], atr, er
            )
            
            position_size = self.position_sizer.calculate_position_size(
                account_balance=10000,  # Нужно передавать реальный баланс
                entry_price=prices.iloc[-1],
                stop_loss_price=stop_loss,
                efficiency_ratio=er,
                volatility=atr,
                avg_volatility=avg_volatility
            )
            
            signal['position_size'] = position_size
            signal['stop_loss'] = stop_loss
            signal['take_profit'] = take_profit
        
        return signal
    
    def _determine_signal(self, prices, kama, er, rsi, upper_band, lower_band, 
                         market_state, noise) -> Dict[str, Any]:
        """
        Определение торгового сигнала
        """
        current_price = prices.iloc[-1]
        
        # Базовые условия
        if pd.isna(kama.iloc[-1]) or pd.isna(rsi.iloc[-1]):
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'Insufficient data'}
        
        # Не торгуем в сильном шуме
        if noise > self.noise_threshold:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'High noise level'}
        
        # Не торгуем при низком ER
        if er < self.min_er_for_entry:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'Low efficiency ratio'}
        
        signal = {'action': 'HOLD', 'confidence': 0, 'reason': ''}
        
        # Сильный тренд
        if market_state['state'] == 'STRONG_TREND':
            if market_state['direction'] == 'UP':
                if current_price > kama.iloc[-1] and rsi.iloc[-1] < 70:
                    signal = {
                        'action': 'BUY',
                        'confidence': er,
                        'reason': 'Strong uptrend confirmed',
                        'market_state': market_state
                    }
            elif market_state['direction'] == 'DOWN':
                if current_price < kama.iloc[-1] and rsi.iloc[-1] > 30:
                    signal = {
                        'action': 'SELL',
                        'confidence': er,
                        'reason': 'Strong downtrend confirmed',
                        'market_state': market_state
                    }
        
        # Слабый тренд - более консервативные условия
        elif market_state['state'] == 'WEAK_TREND':
            # Покупка на отскоке от KAMA в восходящем тренде
            if market_state['direction'] == 'UP':
                if current_price > kama.iloc[-1] and current_price < upper_band.iloc[-1]:
                    if rsi.iloc[-1] > 40 and rsi.iloc[-1] < 60:
                        signal = {
                            'action': 'BUY',
                            'confidence': er * 0.7,
                            'reason': 'Weak uptrend, conservative entry',
                            'market_state': market_state
                        }
            
            # Продажа на отскоке к KAMA в нисходящем тренде
            elif market_state['direction'] == 'DOWN':
                if current_price < kama.iloc[-1] and current_price > lower_band.iloc[-1]:
                    if rsi.iloc[-1] < 60 and rsi.iloc[-1] > 40:
                        signal = {
                            'action': 'SELL',
                            'confidence': er * 0.7,
                            'reason': 'Weak downtrend, conservative entry',
                            'market_state': market_state
                        }
        
        # Переходное состояние - ищем разворот
        elif market_state['state'] == 'TRANSITIONAL':
            # Потенциальный разворот вверх
            if current_price > kama.iloc[-1] and prices.iloc[-2] <= kama.iloc[-2]:
                if rsi.iloc[-1] > 50:
                    signal = {
                        'action': 'BUY',
                        'confidence': er * 0.5,
                        'reason': 'Potential bullish reversal',
                        'market_state': market_state
                    }
            
            # Потенциальный разворот вниз
            elif current_price < kama.iloc[-1] and prices.iloc[-2] >= kama.iloc[-2]:
                if rsi.iloc[-1] < 50:
                    signal = {
                        'action': 'SELL',
                        'confidence': er * 0.5,
                        'reason': 'Potential bearish reversal',
                        'market_state': market_state
                    }
        
        return signal
    
    def backtest_robustness(self, df: pd.DataFrame, 
                           parameter_ranges: Dict[str, Tuple[float, float]]) -> Dict[str, Any]:
        """
        Тестирование робастности по Кауфману
        Проверяет стабильность стратегии при изменении параметров
        """
        results = []
        
        # Тестируем разные комбинации параметров
        for er_min in np.linspace(parameter_ranges['er_min'][0], 
                                 parameter_ranges['er_min'][1], 5):
            for noise_max in np.linspace(parameter_ranges['noise_max'][0],
                                        parameter_ranges['noise_max'][1], 5):
                
                self.min_er_for_entry = er_min
                self.noise_threshold = noise_max
                
                # Простой бэктест
                trades = []
                for i in range(100, len(df), 10):  # Каждые 10 баров
                    signal = self.generate_signal(df.iloc[:i])
                    if signal['action'] != 'HOLD':
                        trades.append(signal)
                
                # Оценка результатов
                win_rate = sum(1 for t in trades if t.get('confidence', 0) > 0.5) / len(trades) if trades else 0
                
                results.append({
                    'er_min': er_min,
                    'noise_max': noise_max,
                    'trades': len(trades),
                    'win_rate': win_rate
                })
        
        # Анализ робастности
        win_rates = [r['win_rate'] for r in results]
        robustness_score = 1 - np.std(win_rates) / np.mean(win_rates) if np.mean(win_rates) > 0 else 0
        
        return {
            'robustness_score': robustness_score,
            'results': results,
            'best_params': max(results, key=lambda x: x['win_rate']),
            'worst_params': min(results, key=lambda x: x['win_rate']),
            'variance': np.var(win_rates)
        }


# Интеграция с существующим ботом
def add_kaufman_to_existing_bot(df: pd.DataFrame) -> pd.DataFrame:
    """
    Добавляет индикаторы Кауфмана в DataFrame
    """
    prices = df['close']
    
    # KAMA
    df['kama'] = KaufmanIndicators.calculate_kama(prices)
    
    # Efficiency Ratio
    er_values = []
    for i in range(10, len(prices)):
        er = KaufmanIndicators.calculate_efficiency_ratio(
            prices.iloc[max(0, i-10):i+1].values, 10
        )
        er_values.append(er)
    
    df['efficiency_ratio'] = pd.Series(er_values, index=df.index[10:])
    
    # Adaptive RSI
    df['adaptive_rsi'] = KaufmanIndicators.calculate_adaptive_rsi(prices)
    
    # Market State
    if len(df) >= 50:
        market_state = KaufmanIndicators.calculate_market_state(df)
        df['market_state'] = market_state['state']
        df['trend_direction'] = market_state['direction']
    
    return df


if __name__ == "__main__":
    # Тестирование индикаторов Кауфмана
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from bybit_client import BybitClient
    from indicators import TechnicalIndicators
    
    # Получаем данные
    client = BybitClient(testnet=True)
    klines = client.get_kline_data("BTCUSDT", "60", limit=200)
    
    if klines:
        df = TechnicalIndicators.prepare_dataframe(klines)
        
        # Добавляем индикаторы Кауфмана
        df = add_kaufman_to_existing_bot(df)
        
        # Анализ рынка
        market_state = KaufmanIndicators.calculate_market_state(df)
        
        print("\n=== Анализ рынка по Кауфману ===")
        print(f"Состояние рынка: {market_state['state']}")
        print(f"Направление: {market_state['direction']}")
        print(f"Уверенность: {market_state['confidence']:.2%}")
        print(f"Efficiency Ratio: {market_state['efficiency_ratio']:.3f}")
        print(f"Уровень шума: {market_state['noise_level']:.2%}")
        print(f"Фрактальная эффективность: {market_state['fractal_efficiency']:.3f}")
        
        # Генерация сигнала
        strategy = KaufmanStrategy()
        signal = strategy.generate_signal(df)
        
        print("\n=== Торговый сигнал ===")
        print(f"Действие: {signal['action']}")
        print(f"Уверенность: {signal.get('confidence', 0):.2%}")
        print(f"Причина: {signal.get('reason', 'N/A')}")
        
        if signal['action'] != 'HOLD':
            print(f"Размер позиции: {signal.get('position_size', 0):.4f} BTC")
            print(f"Stop-Loss: ${signal.get('stop_loss', 0):.2f}")
            print(f"Take-Profit: ${signal.get('take_profit', 0):.2f}")
        
        # Тест робастности
        print("\n=== Тестирование робастности ===")
        parameter_ranges = {
            'er_min': (0.2, 0.4),
            'noise_max': (0.6, 0.8)
        }
        
        robustness = strategy.backtest_robustness(df, parameter_ranges)
        print(f"Робастность стратегии: {robustness['robustness_score']:.2%}")
        print(f"Лучшие параметры: ER>{robustness['best_params']['er_min']:.2f}, "
              f"Noise<{robustness['best_params']['noise_max']:.2f}")
        
        # Последние значения индикаторов
        print("\n=== Текущие значения индикаторов ===")
        print(f"Цена: ${df['close'].iloc[-1]:.2f}")
        print(f"KAMA: ${df['kama'].iloc[-1]:.2f}")
        print(f"Efficiency Ratio: {df['efficiency_ratio'].iloc[-1]:.3f}")
        print(f"Adaptive RSI: {df['adaptive_rsi'].iloc[-1]:.1f}")
