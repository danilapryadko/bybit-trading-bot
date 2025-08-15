"""
Продвинутые торговые стратегии на основе анализа 2022-2025
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from abc import ABC, abstractmethod
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

class MarketRegimeDetector:
    """Определение рыночного режима на основе уроков 2022-2025"""
    
    @staticmethod
    def detect_regime(df: pd.DataFrame) -> str:
        """
        Определить текущий рыночный режим
        Возвращает: 'BULL', 'BEAR', 'ACCUMULATION', 'DISTRIBUTION', 'CRASH'
        """
        # Рассчитать индикаторы для определения режима
        sma_20 = df['close'].rolling(20).mean().iloc[-1]
        sma_50 = df['close'].rolling(50).mean().iloc[-1]
        sma_200 = df['close'].rolling(200).mean().iloc[-1] if len(df) >= 200 else sma_50
        
        current_price = df['close'].iloc[-1]
        
        # Волатильность
        returns = df['close'].pct_change()
        volatility = returns.rolling(20).std().iloc[-1]
        
        # RSI
        rsi = TechnicalIndicators.calculate_rsi(df, 14).iloc[-1]
        
        # Объем
        volume_avg = df['volume'].rolling(20).mean().iloc[-1]
        current_volume = df['volume'].iloc[-1]
        volume_spike = current_volume > volume_avg * 2
        
        # Определение режима
        if current_price < sma_200 * 0.7 and volatility > 0.05:
            return 'CRASH'  # Как Terra-Luna или FTX
        elif current_price > sma_20 > sma_50 > sma_200:
            return 'BULL'  # Бычий тренд как в 2023-2024
        elif current_price < sma_20 < sma_50 < sma_200:
            return 'BEAR'  # Медвежий тренд как в 2022
        elif abs(current_price - sma_200) / sma_200 < 0.1 and volatility < 0.02:
            if rsi < 50:
                return 'ACCUMULATION'  # Накопление перед ростом
            else:
                return 'DISTRIBUTION'  # Распределение перед падением
        else:
            return 'ACCUMULATION'  # По умолчанию
    
    @staticmethod
    def get_regime_parameters(regime: str) -> Dict[str, Any]:
        """Получить параметры торговли для каждого режима"""
        params = {
            'BULL': {
                'position_size_multiplier': 1.5,
                'stop_loss': 3.0,
                'take_profit': 10.0,
                'max_positions': 3,
                'strategy': 'trend_following'
            },
            'BEAR': {
                'position_size_multiplier': 0.5,
                'stop_loss': 2.0,
                'take_profit': 5.0,
                'max_positions': 1,
                'strategy': 'mean_reversion'
            },
            'CRASH': {
                'position_size_multiplier': 0,  # Не торгуем
                'stop_loss': 1.0,
                'take_profit': 2.0,
                'max_positions': 0,
                'strategy': 'no_trade'
            },
            'ACCUMULATION': {
                'position_size_multiplier': 1.0,
                'stop_loss': 4.0,
                'take_profit': 8.0,
                'max_positions': 2,
                'strategy': 'dca'
            },
            'DISTRIBUTION': {
                'position_size_multiplier': 0.7,
                'stop_loss': 2.5,
                'take_profit': 5.0,
                'max_positions': 1,
                'strategy': 'scalping'
            }
        }
        return params.get(regime, params['ACCUMULATION'])


class HalvingStrategy(BaseStrategy):
    """Стратегия основанная на циклах халвинга Bitcoin"""
    
    def __init__(self, client: BybitClient, symbol: str):
        super().__init__(client, symbol)
        
        # Даты халвингов
        self.halvings = [
            datetime(2024, 4, 20),  # Примерная дата халвинга 2024
            datetime(2028, 4, 20),  # Следующий халвинг
        ]
        
        self.days_before_halving_to_buy = 180  # Начать покупать за 6 месяцев
        self.days_after_halving_to_hold = 365  # Держать год после халвинга
    
    def get_halving_phase(self) -> str:
        """Определить фазу относительно халвинга"""
        now = datetime.now()
        
        for halving_date in self.halvings:
            days_until = (halving_date - now).days
            days_since = (now - halving_date).days
            
            if 0 <= days_since <= self.days_after_halving_to_hold:
                return 'POST_HALVING_BULL'  # Бычий рынок после халвинга
            elif -self.days_before_halving_to_buy <= days_until <= 0:
                return 'PRE_HALVING_ACCUMULATION'  # Накопление перед халвингом
            elif 0 < days_until <= 60:
                return 'HALVING_HYPE'  # Хайп перед халвингом
        
        return 'NEUTRAL'
    
    def analyze(self) -> Tuple[str, float]:
        phase = self.get_halving_phase()
        
        # Получить данные свечей
        klines = self.client.get_kline_data(self.symbol, "240", limit=100)  # 4H
        if not klines:
            return 'HOLD', 0.0
        
        df = TechnicalIndicators.prepare_dataframe(klines)
        df = TechnicalIndicators.add_all_indicators(df)
        
        # Базовый сигнал
        base_signal, base_confidence = SignalGenerator.combined_signal(df)
        
        # Корректировка на основе фазы халвинга
        if phase == 'PRE_HALVING_ACCUMULATION':
            # Агрессивно покупаем перед халвингом
            if base_signal != 'SELL':
                return 'BUY', min(1.0, base_confidence + 0.3)
        elif phase == 'POST_HALVING_BULL':
            # Держим позиции после халвинга
            if base_signal == 'BUY':
                return 'BUY', min(1.0, base_confidence + 0.2)
            else:
                return 'HOLD', base_confidence
        elif phase == 'HALVING_HYPE':
            # Осторожно в период хайпа
            return base_signal, base_confidence * 0.7
        
        return base_signal, base_confidence
    
    def should_enter_position(self) -> bool:
        phase = self.get_halving_phase()
        if phase in ['PRE_HALVING_ACCUMULATION', 'POST_HALVING_BULL']:
            return True
        return super().should_enter_position()
    
    def should_exit_position(self) -> bool:
        phase = self.get_halving_phase()
        if phase == 'POST_HALVING_BULL':
            # Держим дольше в бычьей фазе
            if self.position:
                pnl_percent = float(self.position['unrealisedPnl']) / float(self.position['positionValue']) * 100
                if pnl_percent < -10:  # Выход только при большом убытке
                    return True
            return False
        return super().should_exit_position()


class ETFMomentumStrategy(BaseStrategy):
    """Стратегия основанная на притоке средств в ETF"""
    
    def __init__(self, client: BybitClient, symbol: str):
        super().__init__(client, symbol)
        self.etf_approval_date = datetime(2024, 1, 10)
        self.momentum_period = 90  # дней после одобрения ETF
    
    def analyze(self) -> Tuple[str, float]:
        """Анализ с учетом эффекта ETF"""
        days_since_etf = (datetime.now() - self.etf_approval_date).days
        
        # Получить данные
        klines = self.client.get_kline_data(self.symbol, "60", limit=200)
        if not klines:
            return 'HOLD', 0.0
        
        df = TechnicalIndicators.prepare_dataframe(klines)
        df = TechnicalIndicators.add_all_indicators(df)
        
        # Базовый сигнал
        base_signal, base_confidence = SignalGenerator.combined_signal(df)
        
        # Усилить сигнал в первые месяцы после ETF
        if 0 < days_since_etf < self.momentum_period:
            momentum_boost = (self.momentum_period - days_since_etf) / self.momentum_period * 0.3
            if base_signal == 'BUY':
                return 'BUY', min(1.0, base_confidence + momentum_boost)
        
        return base_signal, base_confidence
    
    def should_enter_position(self) -> bool:
        # Более агрессивный вход в период после ETF
        days_since_etf = (datetime.now() - self.etf_approval_date).days
        if 0 < days_since_etf < self.momentum_period:
            self.min_confidence = 0.4  # Снизить порог
        return super().should_enter_position()


class CrashDetectionStrategy(BaseStrategy):
    """Стратегия обнаружения и избегания крахов как Terra-Luna/FTX"""
    
    def __init__(self, client: BybitClient, symbol: str):
        super().__init__(client, symbol)
        self.crash_indicators = {
            'volume_spike_threshold': 5.0,  # 5x средний объем
            'price_drop_threshold': -20.0,  # -20% за день
            'volatility_spike': 0.1,  # 10% волатильность
            'correlation_breakdown': 0.3  # Корреляция с BTC < 0.3
        }
    
    def detect_crash_risk(self, df: pd.DataFrame) -> Tuple[bool, float]:
        """
        Обнаружить признаки потенциального краха
        Возвращает: (есть_риск, уровень_риска 0-1)
        """
        risk_score = 0.0
        risk_factors = []
        
        # 1. Аномальный объем (как при падении Terra)
        volume_avg = df['volume'].rolling(20).mean().iloc[-1]
        current_volume = df['volume'].iloc[-1]
        if current_volume > volume_avg * self.crash_indicators['volume_spike_threshold']:
            risk_score += 0.3
            risk_factors.append('volume_spike')
        
        # 2. Резкое падение цены
        daily_return = (df['close'].iloc[-1] - df['close'].iloc[-24]) / df['close'].iloc[-24] * 100
        if daily_return < self.crash_indicators['price_drop_threshold']:
            risk_score += 0.4
            risk_factors.append('price_crash')
        
        # 3. Экстремальная волатильность
        returns = df['close'].pct_change()
        volatility = returns.rolling(24).std().iloc[-1]
        if volatility > self.crash_indicators['volatility_spike']:
            risk_score += 0.2
            risk_factors.append('high_volatility')
        
        # 4. Расхождение с Bitcoin (для альткоинов)
        if self.symbol != 'BTCUSDT':
            # Здесь нужно было бы получить данные BTC и сравнить
            # Упрощенная версия - проверка на изолированное падение
            if daily_return < -10 and volatility > 0.05:
                risk_score += 0.1
                risk_factors.append('isolated_crash')
        
        if risk_factors:
            logger.warning(f"Crash risk detected: {risk_factors}, score: {risk_score}")
        
        return risk_score > 0.5, risk_score
    
    def analyze(self) -> Tuple[str, float]:
        # Получить данные
        klines = self.client.get_kline_data(self.symbol, "60", limit=200)
        if not klines:
            return 'HOLD', 0.0
        
        df = TechnicalIndicators.prepare_dataframe(klines)
        
        # Проверить риск краха
        has_crash_risk, risk_level = self.detect_crash_risk(df)
        
        if has_crash_risk:
            logger.error(f"HIGH CRASH RISK DETECTED! Risk level: {risk_level:.2%}")
            return 'SELL', risk_level  # Экстренный выход
        
        # Если риска нет, используем обычный анализ
        df = TechnicalIndicators.add_all_indicators(df)
        return SignalGenerator.combined_signal(df)
    
    def should_enter_position(self) -> bool:
        # Не входить при признаках краха
        klines = self.client.get_kline_data(self.symbol, "60", limit=100)
        if klines:
            df = TechnicalIndicators.prepare_dataframe(klines)
            has_crash_risk, _ = self.detect_crash_risk(df)
            if has_crash_risk:
                return False
        
        return super().should_enter_position()


class DCAStrategy(BaseStrategy):
    """Dollar Cost Averaging стратегия для накопления в медвежьем рынке"""
    
    def __init__(self, client: BybitClient, symbol: str):
        super().__init__(client, symbol)
        
        self.dca_amount = 100  # USDT на каждую покупку
        self.dca_interval_hours = 24  # Покупать раз в день
        self.last_dca_time = None
        
        # Уровни для покупки (процент падения от ATH)
        self.buy_levels = [-30, -40, -50, -60, -70, -80]
        self.bought_levels = set()
    
    def calculate_drawdown_from_ath(self, df: pd.DataFrame) -> float:
        """Рассчитать просадку от исторического максимума"""
        ath = df['high'].max()
        current = df['close'].iloc[-1]
        return (current - ath) / ath * 100
    
    def analyze(self) -> Tuple[str, float]:
        # Получить данные за длинный период
        klines = self.client.get_kline_data(self.symbol, "D", limit=365)
        if not klines:
            return 'HOLD', 0.0
        
        df = TechnicalIndicators.prepare_dataframe(klines)
        drawdown = self.calculate_drawdown_from_ath(df)
        
        # Проверить, нужно ли покупать на текущем уровне
        for level in self.buy_levels:
            if drawdown <= level and level not in self.bought_levels:
                self.bought_levels.add(level)
                logger.info(f"DCA buy signal at {level}% drawdown")
                return 'BUY', 0.8
        
        # Проверить интервал для регулярной покупки
        if self.last_dca_time:
            hours_since = (datetime.now() - self.last_dca_time).total_seconds() / 3600
            if hours_since >= self.dca_interval_hours and drawdown < -20:
                return 'BUY', 0.6
        
        return 'HOLD', 0.0
    
    def enter_position(self, side: str) -> bool:
        """Входить маленькими порциями"""
        if side == 'Buy':
            # Переопределить размер позиции для DCA
            original_size = self.position_size
            self.position_size = self.dca_amount
            
            result = super().enter_position(side)
            
            self.position_size = original_size
            self.last_dca_time = datetime.now()
            
            return result
        
        return super().enter_position(side)
    
    def should_exit_position(self) -> bool:
        """DCA стратегия держит долго"""
        if self.position:
            pnl_percent = float(self.position['unrealisedPnl']) / float(self.position['positionValue']) * 100
            
            # Выход только при хорошей прибыли или большом убытке
            if pnl_percent > 50 or pnl_percent < -30:
                return True
        
        return False


class WhaleFollowingStrategy(BaseStrategy):
    """Следование за китами - крупными игроками"""
    
    def __init__(self, client: BybitClient, symbol: str):
        super().__init__(client, symbol)
        self.whale_threshold = 1000000  # $1M+ сделки
        
    def detect_whale_activity(self, df: pd.DataFrame) -> str:
        """Обнаружить активность китов"""
        # Анализ объемов
        volume_usd = df['volume'] * df['close']
        avg_volume = volume_usd.rolling(20).mean()
        
        # Последние 5 свечей
        recent_volumes = volume_usd.iloc[-5:]
        recent_avg = avg_volume.iloc[-5:]
        
        # Поиск аномальных объемов
        for i in range(len(recent_volumes)):
            if recent_volumes.iloc[i] > recent_avg.iloc[i] * 3:
                # Большой объем обнаружен
                price_change = df['close'].iloc[-5+i] - df['open'].iloc[-5+i]
                if price_change > 0:
                    logger.info(f"Whale buying detected at index {-5+i}")
                    return 'BUY'
                else:
                    logger.info(f"Whale selling detected at index {-5+i}")
                    return 'SELL'
        
        return 'HOLD'
    
    def analyze(self) -> Tuple[str, float]:
        # Получить данные
        klines = self.client.get_kline_data(self.symbol, "15", limit=100)
        if not klines:
            return 'HOLD', 0.0
        
        df = TechnicalIndicators.prepare_dataframe(klines)
        
        # Обнаружить активность китов
        whale_signal = self.detect_whale_activity(df)
        
        if whale_signal != 'HOLD':
            # Следуем за китами с высокой уверенностью
            return whale_signal, 0.75
        
        # Если китов нет, используем обычный анализ
        df = TechnicalIndicators.add_all_indicators(df)
        return SignalGenerator.combined_signal(df)
    
    def should_enter_position(self) -> bool:
        # Более агрессивный вход при обнаружении китов
        signal, confidence = self.analyze()
        if signal != 'HOLD' and confidence > 0.7:
            return True
        return False


class AdaptiveStrategy(BaseStrategy):
    """Адаптивная стратегия, меняющая подход в зависимости от рынка"""
    
    def __init__(self, client: BybitClient, symbol: str):
        super().__init__(client, symbol)
        
        # Инициализация стратегий
        self.strategies = {
            'halving': HalvingStrategy(client, symbol),
            'etf': ETFMomentumStrategy(client, symbol),
            'crash': CrashDetectionStrategy(client, symbol),
            'dca': DCAStrategy(client, symbol),
            'whale': WhaleFollowingStrategy(client, symbol)
        }
        
        self.risk_manager = RiskManager()
        self.current_regime = 'ACCUMULATION'
    
    def analyze(self) -> Tuple[str, float]:
        """Адаптивный анализ с использованием всех стратегий"""
        # Получить данные
        klines = self.client.get_kline_data(self.symbol, "60", limit=200)
        if not klines:
            return 'HOLD', 0.0
        
        df = TechnicalIndicators.prepare_dataframe(klines)
        
        # Определить рыночный режим
        self.current_regime = MarketRegimeDetector.detect_regime(df)
        regime_params = MarketRegimeDetector.get_regime_parameters(self.current_regime)
        
        logger.info(f"Current market regime: {self.current_regime}")
        
        # Собрать сигналы от всех стратегий
        signals = []
        weights = []
        
        # Проверка краха - приоритет
        crash_signal, crash_confidence = self.strategies['crash'].analyze()
        if crash_signal == 'SELL' and crash_confidence > 0.5:
            logger.warning("CRASH DETECTED - EMERGENCY EXIT")
            return 'SELL', crash_confidence
        
        # В зависимости от режима выбираем стратегии
        if self.current_regime == 'BULL':
            # В бычьем рынке используем momentum стратегии
            etf_signal, etf_conf = self.strategies['etf'].analyze()
            whale_signal, whale_conf = self.strategies['whale'].analyze()
            
            signals.extend([etf_signal, whale_signal])
            weights.extend([0.4, 0.6])
            
        elif self.current_regime == 'BEAR':
            # В медвежьем рынке используем DCA
            dca_signal, dca_conf = self.strategies['dca'].analyze()
            signals.append(dca_signal)
            weights.append(1.0)
            
        elif self.current_regime == 'ACCUMULATION':
            # В накоплении используем халвинг и DCA
            halving_signal, halving_conf = self.strategies['halving'].analyze()
            dca_signal, dca_conf = self.strategies['dca'].analyze()
            
            signals.extend([halving_signal, dca_signal])
            weights.extend([0.6, 0.4])
            
        else:  # DISTRIBUTION или CRASH
            # Осторожная торговля или выход
            return 'HOLD', 0.0
        
        # Агрегировать сигналы
        if not signals:
            return 'HOLD', 0.0
        
        buy_score = sum(w for s, w in zip(signals, weights) if s == 'BUY')
        sell_score = sum(w for s, w in zip(signals, weights) if s == 'SELL')
        total_weight = sum(weights)
        
        if buy_score > sell_score and buy_score / total_weight > 0.5:
            return 'BUY', buy_score / total_weight
        elif sell_score > buy_score and sell_score / total_weight > 0.5:
            return 'SELL', sell_score / total_weight
        else:
            return 'HOLD', 0.0
    
    def should_enter_position(self) -> bool:
        """Адаптивные условия входа"""
        # Не входить в краш
        if self.current_regime == 'CRASH':
            return False
        
        # Проверить риск-менеджмент
        balance = 10000  # Получить реальный баланс
        if not self.risk_manager.can_open_position(balance, self.position_size):
            return False
        
        return super().should_enter_position()
    
    def should_exit_position(self) -> bool:
        """Адаптивные условия выхода"""
        if self.current_regime == 'CRASH':
            return True  # Экстренный выход
        
        # Проверить стоп-лосс от риск-менеджера
        if self.risk_manager.should_stop_trading():
            return True
        
        return super().should_exit_position()
    
    def execute(self):
        """Выполнить с адаптивными параметрами"""
        # Обновить параметры на основе режима
        regime_params = MarketRegimeDetector.get_regime_parameters(self.current_regime)
        
        self.position_size = self.position_size * regime_params['position_size_multiplier']
        self.stop_loss_percent = regime_params['stop_loss']
        self.take_profit_percent = regime_params['take_profit']
        
        super().execute()
        
        # Обновить метрики риска
        if self.position:
            self.risk_manager.update_position(self.position.__dict__)
        
        # Логировать метрики
        metrics = self.risk_manager.get_risk_metrics()
        logger.info(f"Risk metrics: Win rate: {metrics['win_rate']:.1f}%, "
                   f"Daily PnL: {metrics['daily_pnl']:.2f}")


if __name__ == "__main__":
    # Тестирование новых стратегий
    from bybit_client import BybitClient
    
    client = BybitClient(testnet=True)
    
    # Тест адаптивной стратегии
    strategy = AdaptiveStrategy(client, "BTCUSDT")
    
    # Получить анализ
    signal, confidence = strategy.analyze()
    print(f"Adaptive Strategy Signal: {signal} (confidence: {confidence:.2%})")
    print(f"Current Market Regime: {strategy.current_regime}")
    
    # Тест детектора краха
    crash_strategy = CrashDetectionStrategy(client, "BTCUSDT")
    crash_signal, crash_conf = crash_strategy.analyze()
    print(f"\nCrash Detection: {crash_signal} (risk: {crash_conf:.2%})")
    
    # Тест халвинг стратегии
    halving_strategy = HalvingStrategy(client, "BTCUSDT")
    phase = halving_strategy.get_halving_phase()
    print(f"\nHalving Phase: {phase}")
