"""
Basic tests for trading bot components
"""

import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators import TechnicalIndicators
from strategies import RSIStrategy, EMAStrategy
import pandas as pd
import numpy as np


class TestIndicators:
    """Тесты для технических индикаторов"""
    
    def test_rsi_calculation(self):
        """Тест расчета RSI"""
        # Создаем тестовые данные
        prices = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
        df = pd.DataFrame({'close': prices})
        
        # Рассчитываем RSI
        indicators = TechnicalIndicators()
        df = indicators.calculate_rsi(df, period=14)
        
        # Проверяем, что RSI рассчитан
        assert 'rsi' in df.columns
        assert not df['rsi'].isna().all()
        
        # RSI должен быть в диапазоне 0-100
        rsi_values = df['rsi'].dropna()
        assert all(0 <= val <= 100 for val in rsi_values)
    
    def test_ema_calculation(self):
        """Тест расчета EMA"""
        # Создаем тестовые данные
        prices = list(range(50, 100))
        df = pd.DataFrame({'close': prices})
        
        # Рассчитываем EMA
        indicators = TechnicalIndicators()
        df = indicators.calculate_ema(df, short_period=9, long_period=21)
        
        # Проверяем, что EMA рассчитаны
        assert 'ema_short' in df.columns
        assert 'ema_long' in df.columns
        
        # Короткая EMA должна быть более реактивной
        last_values = df.tail(10)
        assert last_values['ema_short'].mean() > last_values['ema_long'].mean()
    
    def test_bollinger_bands(self):
        """Тест расчета Bollinger Bands"""
        # Создаем тестовые данные с некоторой волатильностью
        np.random.seed(42)
        prices = 100 + np.random.randn(100) * 5
        df = pd.DataFrame({'close': prices})
        
        # Рассчитываем Bollinger Bands
        indicators = TechnicalIndicators()
        df = indicators.calculate_bollinger_bands(df, period=20, std_dev=2)
        
        # Проверяем наличие полос
        assert 'bb_upper' in df.columns
        assert 'bb_middle' in df.columns
        assert 'bb_lower' in df.columns
        
        # Проверяем логику: upper > middle > lower
        valid_rows = df[['bb_upper', 'bb_middle', 'bb_lower']].dropna()
        assert all(valid_rows['bb_upper'] > valid_rows['bb_middle'])
        assert all(valid_rows['bb_middle'] > valid_rows['bb_lower'])


class TestStrategies:
    """Тесты для торговых стратегий"""
    
    def test_rsi_strategy_signals(self):
        """Тест генерации сигналов RSI стратегии"""
        strategy = RSIStrategy()
        
        # Создаем данные для oversold условия
        oversold_data = pd.DataFrame({
            'close': [100] * 20,
            'rsi': [25] * 20  # RSI < 30
        })
        
        signal = strategy.generate_signal(oversold_data, 'BTCUSDT')
        assert signal['action'] == 'BUY'
        
        # Создаем данные для overbought условия
        overbought_data = pd.DataFrame({
            'close': [100] * 20,
            'rsi': [75] * 20  # RSI > 70
        })
        
        signal = strategy.generate_signal(overbought_data, 'BTCUSDT')
        assert signal['action'] == 'SELL'
    
    def test_ema_strategy_signals(self):
        """Тест генерации сигналов EMA стратегии"""
        strategy = EMAStrategy()
        
        # Создаем данные для бычьего пересечения
        bullish_data = pd.DataFrame({
            'close': list(range(100, 120)),
            'ema_short': list(range(100, 120)),
            'ema_long': list(range(95, 115))
        })
        
        signal = strategy.generate_signal(bullish_data, 'BTCUSDT')
        assert signal['action'] == 'BUY'
        
        # Создаем данные для медвежьего пересечения
        bearish_data = pd.DataFrame({
            'close': list(range(120, 100, -1)),
            'ema_short': list(range(115, 95, -1)),
            'ema_long': list(range(120, 100, -1))
        })
        
        signal = strategy.generate_signal(bearish_data, 'BTCUSDT')
        assert signal['action'] == 'SELL'


class TestRiskManagement:
    """Тесты для риск-менеджмента"""
    
    def test_position_size_calculation(self):
        """Тест расчета размера позиции"""
        from risk_manager import RiskManager
        
        risk_manager = RiskManager(
            max_position_size=0.2,
            max_daily_drawdown=0.05,
            max_total_drawdown=0.15
        )
        
        # Тест с нормальными условиями
        position_size = risk_manager.calculate_position_size(
            balance=1000,
            price=50000,
            stop_loss_percent=2.0
        )
        
        # Размер позиции не должен превышать 20% от баланса
        assert position_size <= 200
        
        # Тест с малым балансом
        small_position = risk_manager.calculate_position_size(
            balance=100,
            price=50000,
            stop_loss_percent=2.0
        )
        
        assert small_position <= 20
    
    def test_risk_limits(self):
        """Тест проверки лимитов риска"""
        from risk_manager import RiskManager
        
        risk_manager = RiskManager(
            max_position_size=0.2,
            max_daily_drawdown=0.05,
            max_total_drawdown=0.15
        )
        
        # Проверка дневной просадки
        risk_manager.update_daily_pnl(-30)  # -3% loss
        assert risk_manager.check_risk_limits(1000) == True
        
        risk_manager.update_daily_pnl(-60)  # -6% total loss
        assert risk_manager.check_risk_limits(1000) == False


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])
