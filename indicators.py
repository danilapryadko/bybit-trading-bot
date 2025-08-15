"""
Технические индикаторы для торговой стратегии
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple
import ta
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """Класс для расчета технических индикаторов"""
    
    @staticmethod
    def prepare_dataframe(kline_data: list) -> pd.DataFrame:
        """
        Преобразовать данные свечей в DataFrame
        kline_data: список свечей от Bybit API
        """
        # Bybit возвращает данные в формате:
        # [timestamp, open, high, low, close, volume, turnover]
        df = pd.DataFrame(kline_data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
        ])
        
        # Конвертировать в числовые типы
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Конвертировать timestamp в datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
        
        # Сортировать по времени (от старых к новым)
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df
    
    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Рассчитать RSI (Relative Strength Index)"""
        return ta.momentum.RSIIndicator(close=df['close'], window=period).rsi()
    
    @staticmethod
    def calculate_ema(df: pd.DataFrame, period: int) -> pd.Series:
        """Рассчитать EMA (Exponential Moving Average)"""
        return ta.trend.EMAIndicator(close=df['close'], window=period).ema_indicator()
    
    @staticmethod
    def calculate_sma(df: pd.DataFrame, period: int) -> pd.Series:
        """Рассчитать SMA (Simple Moving Average)"""
        return ta.trend.SMAIndicator(close=df['close'], window=period).sma_indicator()
    
    @staticmethod
    def calculate_macd(df: pd.DataFrame, 
                      fast_period: int = 12, 
                      slow_period: int = 26, 
                      signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Рассчитать MACD
        Возвращает: (macd_line, signal_line, histogram)
        """
        macd = ta.trend.MACD(
            close=df['close'],
            window_slow=slow_period,
            window_fast=fast_period,
            window_sign=signal_period
        )
        return macd.macd(), macd.macd_signal(), macd.macd_diff()
    
    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame, 
                                 period: int = 20, 
                                 std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Рассчитать полосы Боллинджера
        Возвращает: (upper_band, middle_band, lower_band)
        """
        bb = ta.volatility.BollingerBands(
            close=df['close'],
            window=period,
            window_dev=std_dev
        )
        return bb.bollinger_hband(), bb.bollinger_mavg(), bb.bollinger_lband()
    
    @staticmethod
    def calculate_stochastic(df: pd.DataFrame, 
                           k_period: int = 14, 
                           d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """
        Рассчитать стохастический осциллятор
        Возвращает: (%K, %D)
        """
        stoch = ta.momentum.StochasticOscillator(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=k_period,
            smooth_window=d_period
        )
        return stoch.stoch(), stoch.stoch_signal()
    
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Рассчитать ATR (Average True Range)"""
        return ta.volatility.AverageTrueRange(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=period
        ).average_true_range()
    
    @staticmethod
    def calculate_volume_indicators(df: pd.DataFrame) -> dict:
        """Рассчитать индикаторы объема"""
        indicators = {}
        
        # On-Balance Volume
        indicators['obv'] = ta.volume.OnBalanceVolumeIndicator(
            close=df['close'],
            volume=df['volume']
        ).on_balance_volume()
        
        # Volume Weighted Average Price
        indicators['vwap'] = ta.volume.VolumeWeightedAveragePrice(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            volume=df['volume']
        ).volume_weighted_average_price()
        
        return indicators
    
    @staticmethod
    def calculate_support_resistance(df: pd.DataFrame, window: int = 20) -> dict:
        """Рассчитать уровни поддержки и сопротивления"""
        levels = {}
        
        # Простой метод: использовать локальные минимумы и максимумы
        df['support'] = df['low'].rolling(window=window, center=True).min()
        df['resistance'] = df['high'].rolling(window=window, center=True).max()
        
        # Последние значения
        levels['support'] = df['support'].iloc[-1]
        levels['resistance'] = df['resistance'].iloc[-1]
        
        # Pivot Points
        last_candle = df.iloc[-1]
        pivot = (last_candle['high'] + last_candle['low'] + last_candle['close']) / 3
        
        levels['pivot'] = pivot
        levels['r1'] = 2 * pivot - last_candle['low']
        levels['r2'] = pivot + (last_candle['high'] - last_candle['low'])
        levels['s1'] = 2 * pivot - last_candle['high']
        levels['s2'] = pivot - (last_candle['high'] - last_candle['low'])
        
        return levels
    
    @staticmethod
    def add_all_indicators(df: pd.DataFrame, config: dict = None) -> pd.DataFrame:
        """Добавить все индикаторы в DataFrame"""
        if config is None:
            config = {
                'rsi_period': 14,
                'ema_short': 9,
                'ema_long': 21,
                'sma_period': 50,
                'bb_period': 20,
                'bb_std': 2,
                'macd_fast': 12,
                'macd_slow': 26,
                'macd_signal': 9,
                'stoch_k': 14,
                'stoch_d': 3,
                'atr_period': 14
            }
        
        # RSI
        df['rsi'] = TechnicalIndicators.calculate_rsi(df, config['rsi_period'])
        
        # Moving Averages
        df['ema_short'] = TechnicalIndicators.calculate_ema(df, config['ema_short'])
        df['ema_long'] = TechnicalIndicators.calculate_ema(df, config['ema_long'])
        df['sma'] = TechnicalIndicators.calculate_sma(df, config['sma_period'])
        
        # MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = TechnicalIndicators.calculate_macd(
            df, config['macd_fast'], config['macd_slow'], config['macd_signal']
        )
        
        # Bollinger Bands
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = TechnicalIndicators.calculate_bollinger_bands(
            df, config['bb_period'], config['bb_std']
        )
        
        # Stochastic
        df['stoch_k'], df['stoch_d'] = TechnicalIndicators.calculate_stochastic(
            df, config['stoch_k'], config['stoch_d']
        )
        
        # ATR
        df['atr'] = TechnicalIndicators.calculate_atr(df, config['atr_period'])
        
        # Volume indicators
        volume_indicators = TechnicalIndicators.calculate_volume_indicators(df)
        for key, value in volume_indicators.items():
            df[key] = value
        
        return df


class SignalGenerator:
    """Класс для генерации торговых сигналов"""
    
    @staticmethod
    def rsi_signal(df: pd.DataFrame, oversold: float = 30, overbought: float = 70) -> str:
        """
        Генерировать сигнал на основе RSI
        Возвращает: 'BUY', 'SELL', или 'HOLD'
        """
        last_rsi = df['rsi'].iloc[-1]
        prev_rsi = df['rsi'].iloc[-2]
        
        # Покупка при выходе из зоны перепроданности
        if prev_rsi <= oversold and last_rsi > oversold:
            return 'BUY'
        # Продажа при выходе из зоны перекупленности
        elif prev_rsi >= overbought and last_rsi < overbought:
            return 'SELL'
        else:
            return 'HOLD'
    
    @staticmethod
    def ema_crossover_signal(df: pd.DataFrame) -> str:
        """
        Генерировать сигнал на основе пересечения EMA
        Возвращает: 'BUY', 'SELL', или 'HOLD'
        """
        last_short = df['ema_short'].iloc[-1]
        last_long = df['ema_long'].iloc[-1]
        prev_short = df['ema_short'].iloc[-2]
        prev_long = df['ema_long'].iloc[-2]
        
        # Бычье пересечение
        if prev_short <= prev_long and last_short > last_long:
            return 'BUY'
        # Медвежье пересечение
        elif prev_short >= prev_long and last_short < last_long:
            return 'SELL'
        else:
            return 'HOLD'
    
    @staticmethod
    def macd_signal(df: pd.DataFrame) -> str:
        """
        Генерировать сигнал на основе MACD
        Возвращает: 'BUY', 'SELL', или 'HOLD'
        """
        last_macd = df['macd'].iloc[-1]
        last_signal = df['macd_signal'].iloc[-1]
        prev_macd = df['macd'].iloc[-2]
        prev_signal = df['macd_signal'].iloc[-2]
        
        # Бычье пересечение
        if prev_macd <= prev_signal and last_macd > last_signal:
            return 'BUY'
        # Медвежье пересечение
        elif prev_macd >= prev_signal and last_macd < last_signal:
            return 'SELL'
        else:
            return 'HOLD'
    
    @staticmethod
    def bollinger_bands_signal(df: pd.DataFrame) -> str:
        """
        Генерировать сигнал на основе полос Боллинджера
        Возвращает: 'BUY', 'SELL', или 'HOLD'
        """
        last_close = df['close'].iloc[-1]
        last_lower = df['bb_lower'].iloc[-1]
        last_upper = df['bb_upper'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        
        # Отскок от нижней полосы
        if prev_close <= last_lower and last_close > last_lower:
            return 'BUY'
        # Отскок от верхней полосы
        elif prev_close >= last_upper and last_close < last_upper:
            return 'SELL'
        else:
            return 'HOLD'
    
    @staticmethod
    def combined_signal(df: pd.DataFrame, config: dict = None) -> Tuple[str, float]:
        """
        Комбинированный сигнал на основе нескольких индикаторов
        Возвращает: (сигнал, уверенность от 0 до 1)
        """
        if config is None:
            config = {
                'rsi_oversold': 30,
                'rsi_overbought': 70,
                'min_confidence': 0.6
            }
        
        signals = []
        weights = []
        
        # RSI сигнал (вес 0.3)
        rsi_sig = SignalGenerator.rsi_signal(
            df, config['rsi_oversold'], config['rsi_overbought']
        )
        if rsi_sig != 'HOLD':
            signals.append(1 if rsi_sig == 'BUY' else -1)
            weights.append(0.3)
        
        # EMA crossover сигнал (вес 0.25)
        ema_sig = SignalGenerator.ema_crossover_signal(df)
        if ema_sig != 'HOLD':
            signals.append(1 if ema_sig == 'BUY' else -1)
            weights.append(0.25)
        
        # MACD сигнал (вес 0.25)
        macd_sig = SignalGenerator.macd_signal(df)
        if macd_sig != 'HOLD':
            signals.append(1 if macd_sig == 'BUY' else -1)
            weights.append(0.25)
        
        # Bollinger Bands сигнал (вес 0.2)
        bb_sig = SignalGenerator.bollinger_bands_signal(df)
        if bb_sig != 'HOLD':
            signals.append(1 if bb_sig == 'BUY' else -1)
            weights.append(0.2)
        
        if not signals:
            return 'HOLD', 0.0
        
        # Взвешенная сумма сигналов
        weighted_sum = sum(s * w for s, w in zip(signals, weights))
        total_weight = sum(weights)
        
        # Нормализованный результат
        normalized_signal = weighted_sum / total_weight
        confidence = abs(normalized_signal)
        
        if normalized_signal > 0.3:
            return 'BUY', confidence
        elif normalized_signal < -0.3:
            return 'SELL', confidence
        else:
            return 'HOLD', confidence


if __name__ == "__main__":
    # Тестирование индикаторов
    from bybit_client import BybitClient
    
    client = BybitClient(testnet=True)
    klines = client.get_kline_data("BTCUSDT", "15", limit=100)
    
    if klines:
        df = TechnicalIndicators.prepare_dataframe(klines)
        df = TechnicalIndicators.add_all_indicators(df)
        
        print("\nПоследние значения индикаторов:")
        print(f"Close: {df['close'].iloc[-1]}")
        print(f"RSI: {df['rsi'].iloc[-1]:.2f}")
        print(f"EMA Short: {df['ema_short'].iloc[-1]:.2f}")
        print(f"EMA Long: {df['ema_long'].iloc[-1]:.2f}")
        print(f"MACD: {df['macd'].iloc[-1]:.2f}")
        print(f"ATR: {df['atr'].iloc[-1]:.2f}")
        
        # Генерация сигналов
        signal, confidence = SignalGenerator.combined_signal(df)
        print(f"\nТорговый сигнал: {signal} (уверенность: {confidence:.2%})")
