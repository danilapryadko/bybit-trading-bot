"""
Модуль управления рисками
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RiskManager:
    """Класс для управления рисками"""
    
    def __init__(self, 
                 max_daily_loss: float = 100.0,
                 max_position_size: float = 1000.0,
                 max_open_positions: int = 3,
                 risk_per_trade: float = 2.0):
        """
        Параметры:
        - max_daily_loss: максимальный дневной убыток в USDT
        - max_position_size: максимальный размер позиции в USDT
        - max_open_positions: максимальное количество открытых позиций
        - risk_per_trade: риск на сделку в процентах от баланса
        """
        self.max_daily_loss = max_daily_loss
        self.max_position_size = max_position_size
        self.max_open_positions = max_open_positions
        self.risk_per_trade = risk_per_trade
        
        # Статистика дня
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.last_reset = datetime.now().date()
        
        # История сделок
        self.trade_history = []
        self.current_positions = []
    
    def reset_daily_stats(self):
        """Сбросить дневную статистику"""
        current_date = datetime.now().date()
        if current_date > self.last_reset:
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.last_reset = current_date
            logger.info("Daily risk statistics reset")
    
    def can_open_position(self, balance: float, position_size: float) -> bool:
        """Проверить, можно ли открыть новую позицию"""
        self.reset_daily_stats()
        
        # Проверить дневной убыток
        if self.daily_pnl <= -self.max_daily_loss:
            logger.warning(f"Daily loss limit reached: {self.daily_pnl:.2f} USDT")
            return False
        
        # Проверить размер позиции
        if position_size > self.max_position_size:
            logger.warning(f"Position size too large: {position_size:.2f} USDT")
            return False
        
        # Проверить количество открытых позиций
        if len(self.current_positions) >= self.max_open_positions:
            logger.warning(f"Maximum open positions reached: {len(self.current_positions)}")
            return False
        
        # Проверить риск на сделку
        max_risk = balance * (self.risk_per_trade / 100)
        if position_size > max_risk:
            logger.warning(f"Position exceeds risk limit: {position_size:.2f} > {max_risk:.2f} USDT")
            return False
        
        return True
    
    def calculate_position_size(self, 
                              balance: float, 
                              entry_price: float, 
                              stop_loss_price: float) -> float:
        """Рассчитать размер позиции на основе риска"""
        # Рассчитать риск в пунктах
        risk_points = abs(entry_price - stop_loss_price)
        
        # Рассчитать максимальный риск в USDT
        max_risk = balance * (self.risk_per_trade / 100)
        
        # Рассчитать размер позиции
        position_size = max_risk / (risk_points / entry_price)
        
        # Ограничить максимальным размером
        position_size = min(position_size, self.max_position_size)
        
        return round(position_size, 2)
    
    def update_position(self, position: Dict[str, Any]):
        """Обновить информацию о позиции"""
        # Найти позицию в списке
        for i, pos in enumerate(self.current_positions):
            if pos['symbol'] == position['symbol']:
                self.current_positions[i] = position
                return
        
        # Если позиция новая, добавить
        self.current_positions.append(position)
    
    def close_position(self, symbol: str, pnl: float):
        """Закрыть позицию и обновить статистику"""
        # Удалить из списка открытых
        self.current_positions = [p for p in self.current_positions if p['symbol'] != symbol]
        
        # Обновить дневную статистику
        self.daily_pnl += pnl
        self.daily_trades += 1
        
        # Добавить в историю
        self.trade_history.append({
            'timestamp': datetime.now(),
            'symbol': symbol,
            'pnl': pnl,
            'daily_pnl': self.daily_pnl
        })
        
        logger.info(f"Position closed: {symbol}, PnL: {pnl:.2f} USDT")
        logger.info(f"Daily PnL: {self.daily_pnl:.2f} USDT")
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Получить метрики риска"""
        total_trades = len(self.trade_history)
        winning_trades = sum(1 for t in self.trade_history if t['pnl'] > 0)
        losing_trades = sum(1 for t in self.trade_history if t['pnl'] < 0)
        
        total_profit = sum(t['pnl'] for t in self.trade_history if t['pnl'] > 0)
        total_loss = sum(t['pnl'] for t in self.trade_history if t['pnl'] < 0)
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        avg_win = (total_profit / winning_trades) if winning_trades > 0 else 0
        avg_loss = (total_loss / losing_trades) if losing_trades > 0 else 0
        
        profit_factor = abs(total_profit / total_loss) if total_loss != 0 else 0
        
        # Максимальная просадка
        max_drawdown = self._calculate_max_drawdown()
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'open_positions': len(self.current_positions)
        }
    
    def _calculate_max_drawdown(self) -> float:
        """Рассчитать максимальную просадку"""
        if not self.trade_history:
            return 0.0
        
        cumulative_pnl = 0.0
        peak = 0.0
        max_drawdown = 0.0
        
        for trade in self.trade_history:
            cumulative_pnl += trade['pnl']
            
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            
            drawdown = peak - cumulative_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown
    
    def should_stop_trading(self) -> bool:
        """Определить, следует ли остановить торговлю"""
        # Остановить при достижении дневного лимита убытков
        if self.daily_pnl <= -self.max_daily_loss:
            logger.error(f"Daily loss limit reached! Stopping trading.")
            return True
        
        # Остановить при большой просадке
        max_drawdown = self._calculate_max_drawdown()
        if max_drawdown > self.max_daily_loss * 2:
            logger.error(f"Maximum drawdown exceeded! Stopping trading.")
            return True
        
        return False
    
    def validate_order(self, order_params: Dict[str, Any]) -> bool:
        """Валидировать параметры ордера"""
        # Проверить обязательные параметры
        required = ['symbol', 'side', 'qty', 'order_type']
        for param in required:
            if param not in order_params:
                logger.error(f"Missing required parameter: {param}")
                return False
        
        # Проверить размер позиции
        if 'price' in order_params:
            position_value = float(order_params['qty']) * float(order_params['price'])
            if position_value > self.max_position_size:
                logger.error(f"Position value exceeds limit: {position_value:.2f} USDT")
                return False
        
        return True


class PositionSizer:
    """Класс для расчета размера позиции"""
    
    @staticmethod
    def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Рассчитать оптимальный размер позиции по критерию Келли
        f = (p * b - q) / b
        где:
        - p = вероятность выигрыша
        - q = вероятность проигрыша (1 - p)
        - b = отношение среднего выигрыша к среднему проигрышу
        """
        if avg_loss == 0:
            return 0.0
        
        p = win_rate
        q = 1 - win_rate
        b = abs(avg_win / avg_loss)
        
        if b == 0:
            return 0.0
        
        kelly = (p * b - q) / b
        
        # Ограничить размер (обычно используют 25% от Келли)
        kelly = max(0, min(kelly * 0.25, 0.1))
        
        return kelly
    
    @staticmethod
    def fixed_fractional(balance: float, risk_percent: float) -> float:
        """Рассчитать размер позиции как фиксированный процент от баланса"""
        return balance * (risk_percent / 100)
    
    @staticmethod
    def volatility_based(balance: float, atr: float, risk_factor: float = 2.0) -> float:
        """Рассчитать размер позиции на основе волатильности (ATR)"""
        # Размер позиции обратно пропорционален волатильности
        base_risk = balance * 0.02  # 2% базовый риск
        volatility_adjustment = 1 / (atr * risk_factor)
        
        return base_risk * volatility_adjustment
    
    @staticmethod
    def martingale(base_size: float, consecutive_losses: int, multiplier: float = 2.0) -> float:
        """
        Мартингейл - удваивать размер после проигрыша
        ВНИМАНИЕ: Очень рискованная стратегия!
        """
        return base_size * (multiplier ** consecutive_losses)
    
    @staticmethod
    def anti_martingale(base_size: float, consecutive_wins: int, multiplier: float = 1.5) -> float:
        """
        Анти-мартингейл - увеличивать размер после выигрыша
        """
        return base_size * (multiplier ** consecutive_wins)


if __name__ == "__main__":
    # Тестирование модуля управления рисками
    risk_manager = RiskManager(
        max_daily_loss=100,
        max_position_size=500,
        max_open_positions=3,
        risk_per_trade=2.0
    )
    
    # Проверить возможность открытия позиции
    can_open = risk_manager.can_open_position(balance=5000, position_size=100)
    print(f"Can open position: {can_open}")
    
    # Рассчитать размер позиции
    position_size = risk_manager.calculate_position_size(
        balance=5000,
        entry_price=50000,
        stop_loss_price=49000
    )
    print(f"Calculated position size: {position_size} USDT")
    
    # Получить метрики риска
    metrics = risk_manager.get_risk_metrics()
    print("Risk metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
