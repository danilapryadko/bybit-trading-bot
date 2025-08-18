"""
Backtesting Engine
Comprehensive backtesting framework for strategy evaluation
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)

@dataclass
class Trade:
    """Represents a single trade"""
    entry_time: datetime
    exit_time: Optional[datetime] = None
    symbol: str = "BTCUSDT"
    side: str = "Long"
    entry_price: float = 0
    exit_price: Optional[float] = None
    quantity: float = 0
    leverage: int = 1
    pnl: float = 0
    pnl_percent: float = 0
    fees: float = 0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BacktestResult:
    """Backtest results container"""
    # Performance metrics
    total_return: float = 0
    total_pnl: float = 0
    win_rate: float = 0
    profit_factor: float = 0
    sharpe_ratio: float = 0
    sortino_ratio: float = 0
    max_drawdown: float = 0
    max_drawdown_duration: int = 0
    calmar_ratio: float = 0
    
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0
    avg_loss: float = 0
    best_trade: float = 0
    worst_trade: float = 0
    avg_trade_duration: float = 0
    
    # Risk metrics
    risk_reward_ratio: float = 0
    expectancy: float = 0
    kelly_criterion: float = 0
    var_95: float = 0  # Value at Risk
    cvar_95: float = 0  # Conditional VaR
    
    # Additional data
    equity_curve: List[float] = field(default_factory=list)
    trades: List[Trade] = field(default_factory=list)
    daily_returns: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class BacktestEngine:
    """Advanced backtesting engine with realistic simulation"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Backtesting parameters
        self.initial_capital = self.config.get('initial_capital', 10000)
        self.commission = self.config.get('commission', 0.0006)  # 0.06%
        self.slippage = self.config.get('slippage', 0.0001)  # 0.01%
        self.max_positions = self.config.get('max_positions', 3)
        self.position_size = self.config.get('position_size', 0.1)  # 10% per trade
        self.use_leverage = self.config.get('use_leverage', False)
        self.max_leverage = self.config.get('max_leverage', 10)
        
        # Risk management
        self.use_stop_loss = self.config.get('use_stop_loss', True)
        self.stop_loss_pct = self.config.get('stop_loss_pct', 0.02)  # 2%
        self.use_take_profit = self.config.get('use_take_profit', True)
        self.take_profit_pct = self.config.get('take_profit_pct', 0.04)  # 4%
        self.use_trailing_stop = self.config.get('use_trailing_stop', False)
        self.trailing_stop_pct = self.config.get('trailing_stop_pct', 0.015)
        
        # State
        self.reset()
        
    def reset(self):
        """Reset backtesting state"""
        self.capital = self.initial_capital
        self.positions = []
        self.trades = []
        self.equity_curve = [self.initial_capital]
        self.peak_equity = self.initial_capital
        self.drawdown_start = None
        self.current_drawdown = 0
        self.max_drawdown = 0
        self.max_drawdown_duration = 0
        
    def run(self, 
            data: pd.DataFrame, 
            strategy,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None) -> BacktestResult:
        """
        Run backtest on historical data
        
        Args:
            data: DataFrame with OHLCV data
            strategy: Strategy object with generate_signals method
            start_date: Start date for backtest
            end_date: End date for backtest
            
        Returns:
            BacktestResult object
        """
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        
        # Reset state
        self.reset()
        
        # Filter data by date range
        if start_date:
            data = data[data.index >= start_date]
        if end_date:
            data = data[data.index <= end_date]
        
        # Generate signals
        signals = strategy.generate_signals(data)
        
        # Simulate trading
        for i in range(len(data)):
            current_bar = data.iloc[i]
            current_time = data.index[i]
            
            # Update open positions
            self._update_positions(current_bar)
            
            # Check for exit signals
            self._check_exits(current_bar, current_time)
            
            # Check for entry signals
            if i < len(signals):
                signal = signals.iloc[i]
                if signal != 0 and len(self.positions) < self.max_positions:
                    self._enter_position(current_bar, current_time, signal)
            
            # Update equity
            self._update_equity(current_bar)
        
        # Close all remaining positions
        if len(data) > 0:
            self._close_all_positions(data.iloc[-1], data.index[-1])
        
        # Calculate results
        return self._calculate_results()
    
    def _enter_position(self, bar: pd.Series, timestamp: datetime, signal: float):
        """Enter a new position"""
        # Calculate position size
        position_value = self.capital * self.position_size
        
        # Apply leverage
        leverage = min(abs(signal) * self.max_leverage, self.max_leverage) if self.use_leverage else 1
        
        # Calculate entry price with slippage
        entry_price = bar['close'] * (1 + self.slippage if signal > 0 else 1 - self.slippage)
        
        # Calculate quantity
        quantity = position_value * leverage / entry_price
        
        # Calculate fees
        fees = position_value * self.commission
        
        # Calculate stop loss and take profit
        if signal > 0:  # Long
            stop_loss = entry_price * (1 - self.stop_loss_pct) if self.use_stop_loss else None
            take_profit = entry_price * (1 + self.take_profit_pct) if self.use_take_profit else None
            side = "Long"
        else:  # Short
            stop_loss = entry_price * (1 + self.stop_loss_pct) if self.use_stop_loss else None
            take_profit = entry_price * (1 - self.take_profit_pct) if self.use_take_profit else None
            side = "Short"
        
        # Create trade
        trade = Trade(
            entry_time=timestamp,
            symbol=bar.get('symbol', 'BTCUSDT'),
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            leverage=leverage,
            fees=fees,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata={'signal_strength': abs(signal)}
        )
        
        # Add to positions
        self.positions.append(trade)
        
        # Deduct fees from capital
        self.capital -= fees
        
        logger.debug(f"Entered {side} position at {entry_price:.2f}, quantity: {quantity:.4f}")
    
    def _update_positions(self, bar: pd.Series):
        """Update position P&L and trailing stops"""
        for position in self.positions:
            current_price = bar['close']
            
            if position.side == "Long":
                position.pnl = (current_price - position.entry_price) * position.quantity
                position.pnl_percent = (current_price - position.entry_price) / position.entry_price
                
                # Update trailing stop
                if self.use_trailing_stop and position.pnl > 0:
                    new_stop = current_price * (1 - self.trailing_stop_pct)
                    if position.stop_loss is None or new_stop > position.stop_loss:
                        position.stop_loss = new_stop
                        
            else:  # Short
                position.pnl = (position.entry_price - current_price) * position.quantity
                position.pnl_percent = (position.entry_price - current_price) / position.entry_price
                
                # Update trailing stop
                if self.use_trailing_stop and position.pnl > 0:
                    new_stop = current_price * (1 + self.trailing_stop_pct)
                    if position.stop_loss is None or new_stop < position.stop_loss:
                        position.stop_loss = new_stop
    
    def _check_exits(self, bar: pd.Series, timestamp: datetime):
        """Check for position exits"""
        positions_to_close = []
        
        for position in self.positions:
            should_exit = False
            exit_reason = None
            
            # Check stop loss
            if position.stop_loss:
                if position.side == "Long" and bar['low'] <= position.stop_loss:
                    should_exit = True
                    exit_reason = "Stop Loss"
                    position.exit_price = position.stop_loss
                elif position.side == "Short" and bar['high'] >= position.stop_loss:
                    should_exit = True
                    exit_reason = "Stop Loss"
                    position.exit_price = position.stop_loss
            
            # Check take profit
            if not should_exit and position.take_profit:
                if position.side == "Long" and bar['high'] >= position.take_profit:
                    should_exit = True
                    exit_reason = "Take Profit"
                    position.exit_price = position.take_profit
                elif position.side == "Short" and bar['low'] <= position.take_profit:
                    should_exit = True
                    exit_reason = "Take Profit"
                    position.exit_price = position.take_profit
            
            if should_exit:
                self._close_position(position, timestamp, exit_reason)
                positions_to_close.append(position)
        
        # Remove closed positions
        for position in positions_to_close:
            self.positions.remove(position)
    
    def _close_position(self, position: Trade, timestamp: datetime, reason: str):
        """Close a position"""
        if position.exit_price is None:
            position.exit_price = position.entry_price  # Should not happen
        
        position.exit_time = timestamp
        position.exit_reason = reason
        
        # Calculate final P&L with fees
        exit_fees = position.quantity * position.exit_price * self.commission
        position.fees += exit_fees
        
        if position.side == "Long":
            position.pnl = (position.exit_price - position.entry_price) * position.quantity - position.fees
        else:
            position.pnl = (position.entry_price - position.exit_price) * position.quantity - position.fees
        
        position.pnl_percent = position.pnl / (position.entry_price * position.quantity)
        
        # Update capital
        self.capital += position.pnl + (position.entry_price * position.quantity)
        
        # Add to trades history
        self.trades.append(position)
        
        logger.debug(f"Closed {position.side} position: PnL={position.pnl:.2f} ({reason})")
    
    def _close_all_positions(self, bar: pd.Series, timestamp: datetime):
        """Close all open positions"""
        for position in self.positions[:]:
            position.exit_price = bar['close']
            self._close_position(position, timestamp, "End of Backtest")
            self.positions.remove(position)
    
    def _update_equity(self, bar: pd.Series):
        """Update equity curve"""
        # Calculate current equity
        equity = self.capital
        for position in self.positions:
            current_price = bar['close']
            if position.side == "Long":
                unrealized_pnl = (current_price - position.entry_price) * position.quantity
            else:
                unrealized_pnl = (position.entry_price - current_price) * position.quantity
            equity += unrealized_pnl + (position.entry_price * position.quantity)
        
        self.equity_curve.append(equity)
        
        # Update drawdown
        if equity > self.peak_equity:
            self.peak_equity = equity
            self.drawdown_start = None
            self.current_drawdown = 0
        else:
            drawdown = (self.peak_equity - equity) / self.peak_equity
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
            
            if self.drawdown_start is None:
                self.drawdown_start = len(self.equity_curve)
            
            drawdown_duration = len(self.equity_curve) - self.drawdown_start
            if drawdown_duration > self.max_drawdown_duration:
                self.max_drawdown_duration = drawdown_duration
    
    def _calculate_results(self) -> BacktestResult:
        """Calculate backtest results"""
        result = BacktestResult()
        
        if not self.trades:
            return result
        
        # Basic metrics
        result.total_trades = len(self.trades)
        result.winning_trades = len([t for t in self.trades if t.pnl > 0])
        result.losing_trades = len([t for t in self.trades if t.pnl <= 0])
        result.win_rate = result.winning_trades / result.total_trades if result.total_trades > 0 else 0
        
        # P&L metrics
        pnls = [t.pnl for t in self.trades]
        result.total_pnl = sum(pnls)
        result.total_return = (self.equity_curve[-1] - self.initial_capital) / self.initial_capital
        
        winning_pnls = [t.pnl for t in self.trades if t.pnl > 0]
        losing_pnls = [t.pnl for t in self.trades if t.pnl <= 0]
        
        result.avg_win = np.mean(winning_pnls) if winning_pnls else 0
        result.avg_loss = np.mean(losing_pnls) if losing_pnls else 0
        result.best_trade = max(pnls) if pnls else 0
        result.worst_trade = min(pnls) if pnls else 0
        
        # Profit factor
        gross_profit = sum(winning_pnls) if winning_pnls else 0
        gross_loss = abs(sum(losing_pnls)) if losing_pnls else 1
        result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Risk metrics
        result.max_drawdown = self.max_drawdown
        result.max_drawdown_duration = self.max_drawdown_duration
        
        # Calculate daily returns
        equity_series = pd.Series(self.equity_curve)
        daily_returns = equity_series.pct_change().dropna()
        result.daily_returns = daily_returns.tolist()
        
        # Sharpe ratio (annualized)
        if len(daily_returns) > 1:
            mean_return = daily_returns.mean()
            std_return = daily_returns.std()
            result.sharpe_ratio = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        
        # Sortino ratio
        negative_returns = daily_returns[daily_returns < 0]
        if len(negative_returns) > 0:
            downside_std = negative_returns.std()
            result.sortino_ratio = (mean_return / downside_std) * np.sqrt(252) if downside_std > 0 else 0
        
        # Calmar ratio
        annual_return = result.total_return * (252 / len(self.equity_curve))
        result.calmar_ratio = annual_return / result.max_drawdown if result.max_drawdown > 0 else 0
        
        # Expectancy
        result.expectancy = (result.win_rate * result.avg_win) - ((1 - result.win_rate) * abs(result.avg_loss))
        
        # Risk/Reward ratio
        result.risk_reward_ratio = abs(result.avg_win / result.avg_loss) if result.avg_loss != 0 else 0
        
        # Kelly Criterion
        if result.avg_loss != 0:
            result.kelly_criterion = (result.win_rate * result.risk_reward_ratio - (1 - result.win_rate)) / result.risk_reward_ratio
        
        # VaR and CVaR
        if len(daily_returns) > 0:
            result.var_95 = np.percentile(daily_returns, 5)
            result.cvar_95 = daily_returns[daily_returns <= result.var_95].mean()
        
        # Trade duration
        durations = [(t.exit_time - t.entry_time).total_seconds() / 3600 
                    for t in self.trades if t.exit_time]
        result.avg_trade_duration = np.mean(durations) if durations else 0
        
        # Store additional data
        result.equity_curve = self.equity_curve
        result.trades = self.trades
        
        return result
    
    def optimize_parameters(self, 
                           data: pd.DataFrame,
                           strategy_class,
                           param_grid: Dict[str, List[Any]],
                           metric: str = 'sharpe_ratio') -> Dict[str, Any]:
        """
        Optimize strategy parameters using grid search
        
        Args:
            data: Historical data
            strategy_class: Strategy class to optimize
            param_grid: Dictionary of parameters to test
            metric: Metric to optimize for
            
        Returns:
            Best parameters and results
        """
        from itertools import product
        
        # Generate parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        param_combinations = list(product(*param_values))
        
        best_result = None
        best_params = None
        best_metric_value = -float('inf')
        
        results = []
        
        for params in param_combinations:
            # Create parameter dictionary
            param_dict = dict(zip(param_names, params))
            
            # Create strategy with parameters
            strategy = strategy_class(**param_dict)
            
            # Run backtest
            result = self.run(data, strategy)
            
            # Get metric value
            metric_value = getattr(result, metric, 0)
            
            # Store result
            results.append({
                'params': param_dict,
                'result': result,
                metric: metric_value
            })
            
            # Check if best
            if metric_value > best_metric_value:
                best_metric_value = metric_value
                best_params = param_dict
                best_result = result
        
        logger.info(f"Optimization complete. Best {metric}: {best_metric_value:.4f}")
        logger.info(f"Best parameters: {best_params}")
        
        return {
            'best_params': best_params,
            'best_result': best_result,
            'all_results': results
        }
    
    def generate_report(self, result: BacktestResult) -> str:
        """Generate detailed backtest report"""
        report = []
        report.append("="*60)
        report.append("BACKTEST REPORT")
        report.append("="*60)
        
        report.append("\n📊 PERFORMANCE METRICS")
        report.append("-"*40)
        report.append(f"Total Return: {result.total_return*100:.2f}%")
        report.append(f"Total P&L: ${result.total_pnl:.2f}")
        report.append(f"Win Rate: {result.win_rate*100:.1f}%")
        report.append(f"Profit Factor: {result.profit_factor:.2f}")
        report.append(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        report.append(f"Sortino Ratio: {result.sortino_ratio:.2f}")
        report.append(f"Max Drawdown: {result.max_drawdown*100:.1f}%")
        report.append(f"Calmar Ratio: {result.calmar_ratio:.2f}")
        
        report.append("\n📈 TRADE STATISTICS")
        report.append("-"*40)
        report.append(f"Total Trades: {result.total_trades}")
        report.append(f"Winning Trades: {result.winning_trades}")
        report.append(f"Losing Trades: {result.losing_trades}")
        report.append(f"Average Win: ${result.avg_win:.2f}")
        report.append(f"Average Loss: ${result.avg_loss:.2f}")
        report.append(f"Best Trade: ${result.best_trade:.2f}")
        report.append(f"Worst Trade: ${result.worst_trade:.2f}")
        report.append(f"Avg Trade Duration: {result.avg_trade_duration:.1f} hours")
        
        report.append("\n⚠️ RISK METRICS")
        report.append("-"*40)
        report.append(f"Risk/Reward Ratio: {result.risk_reward_ratio:.2f}")
        report.append(f"Expectancy: ${result.expectancy:.2f}")
        report.append(f"Kelly Criterion: {result.kelly_criterion:.2%}")
        report.append(f"VaR (95%): {result.var_95*100:.2f}%")
        report.append(f"CVaR (95%): {result.cvar_95*100:.2f}%")
        
        report.append("\n"+"="*60)
        
        return "\n".join(report)