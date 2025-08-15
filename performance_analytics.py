#!/usr/bin/env python3
"""
Performance Analytics Module for Bybit Trading Bot
Tracks and analyzes trading performance metrics
"""
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)

@dataclass
class Trade:
    """Trade record"""
    id: str
    symbol: str
    side: str  # Buy/Sell
    entry_price: float
    exit_price: float
    quantity: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_percent: float
    fees: float
    strategy: str

@dataclass
class PerformanceMetrics:
    """Performance metrics container"""
    # Basic metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # P&L metrics
    total_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Risk metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    
    # Trade statistics
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_win_percent: float = 0.0
    avg_loss_percent: float = 0.0
    
    # Risk-adjusted returns
    risk_adjusted_return: float = 0.0
    return_over_max_dd: float = 0.0
    
    # Time metrics
    avg_trade_duration: float = 0.0
    total_trading_days: int = 0
    avg_trades_per_day: float = 0.0
    
    # Additional
    expectancy: float = 0.0
    kelly_criterion: float = 0.0
    recovery_factor: float = 0.0
    payoff_ratio: float = 0.0

class PerformanceAnalytics:
    """Performance analytics and reporting system"""
    
    def __init__(self, initial_capital: float = 10000.0):
        """Initialize performance analytics"""
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = [initial_capital]
        self.daily_returns: List[float] = []
        self.metrics = PerformanceMetrics()
        
        logger.info(f"Performance Analytics initialized with capital: ${initial_capital}")
    
    def add_trade(self, trade: Trade) -> None:
        """Add a completed trade and update metrics"""
        self.trades.append(trade)
        self.current_capital += trade.pnl
        self.equity_curve.append(self.current_capital)
        
        # Update metrics
        self._update_metrics()
        
        logger.info(f"Trade added: {trade.symbol} PnL: ${trade.pnl:.2f} ({trade.pnl_percent:.2f}%)")
    
    def _update_metrics(self) -> None:
        """Update all performance metrics"""
        if not self.trades:
            return
        
        # Basic counts
        self.metrics.total_trades = len(self.trades)
        self.metrics.winning_trades = sum(1 for t in self.trades if t.pnl > 0)
        self.metrics.losing_trades = sum(1 for t in self.trades if t.pnl < 0)
        self.metrics.win_rate = (self.metrics.winning_trades / self.metrics.total_trades * 100 
                                 if self.metrics.total_trades > 0 else 0)
        
        # P&L calculations
        self.metrics.total_pnl = sum(t.pnl for t in self.trades)
        self.metrics.gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
        self.metrics.gross_loss = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
        self.metrics.profit_factor = (self.metrics.gross_profit / self.metrics.gross_loss 
                                      if self.metrics.gross_loss > 0 else float('inf'))
        
        # Average metrics
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]
        
        if winning_trades:
            self.metrics.avg_win = np.mean([t.pnl for t in winning_trades])
            self.metrics.avg_win_percent = np.mean([t.pnl_percent for t in winning_trades])
            self.metrics.largest_win = max(t.pnl for t in winning_trades)
        
        if losing_trades:
            self.metrics.avg_loss = np.mean([t.pnl for t in losing_trades])
            self.metrics.avg_loss_percent = np.mean([t.pnl_percent for t in losing_trades])
            self.metrics.largest_loss = min(t.pnl for t in losing_trades)
        
        self.metrics.avg_trade = np.mean([t.pnl for t in self.trades])
        
        # Risk metrics
        self._calculate_sharpe_ratio()
        self._calculate_sortino_ratio()
        self._calculate_max_drawdown()
        self._calculate_calmar_ratio()
        
        # Additional metrics
        self._calculate_expectancy()
        self._calculate_kelly_criterion()
        self._calculate_recovery_factor()
        self._calculate_payoff_ratio()
        
        # Time metrics
        self._calculate_time_metrics()
    
    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> None:
        """Calculate Sharpe ratio"""
        if len(self.equity_curve) < 2:
            return
        
        returns = pd.Series(self.equity_curve).pct_change().dropna()
        if len(returns) > 0:
            excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
            if returns.std() > 0:
                self.metrics.sharpe_ratio = np.sqrt(252) * excess_returns.mean() / returns.std()
    
    def _calculate_sortino_ratio(self, risk_free_rate: float = 0.02) -> None:
        """Calculate Sortino ratio (uses downside deviation)"""
        if len(self.equity_curve) < 2:
            return
        
        returns = pd.Series(self.equity_curve).pct_change().dropna()
        if len(returns) > 0:
            excess_returns = returns - risk_free_rate / 252
            downside_returns = returns[returns < 0]
            if len(downside_returns) > 0:
                downside_std = downside_returns.std()
                if downside_std > 0:
                    self.metrics.sortino_ratio = np.sqrt(252) * excess_returns.mean() / downside_std
    
    def _calculate_max_drawdown(self) -> None:
        """Calculate maximum drawdown and duration"""
        if len(self.equity_curve) < 2:
            return
        
        equity = pd.Series(self.equity_curve)
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        
        self.metrics.max_drawdown = abs(drawdown.min()) * 100  # As percentage
        
        # Calculate max drawdown duration
        drawdown_start = None
        max_duration = 0
        current_duration = 0
        
        for i, dd in enumerate(drawdown):
            if dd < 0:
                if drawdown_start is None:
                    drawdown_start = i
                current_duration = i - drawdown_start
            else:
                if current_duration > max_duration:
                    max_duration = current_duration
                drawdown_start = None
                current_duration = 0
        
        self.metrics.max_drawdown_duration = max_duration
    
    def _calculate_calmar_ratio(self) -> None:
        """Calculate Calmar ratio (annual return / max drawdown)"""
        if self.metrics.max_drawdown > 0 and len(self.trades) > 0:
            # Calculate annualized return
            total_days = (self.trades[-1].exit_time - self.trades[0].entry_time).days
            if total_days > 0:
                years = total_days / 365
                annual_return = ((self.current_capital / self.initial_capital) ** (1/years) - 1) * 100
                self.metrics.calmar_ratio = annual_return / self.metrics.max_drawdown
    
    def _calculate_expectancy(self) -> None:
        """Calculate trade expectancy"""
        if self.metrics.total_trades > 0:
            win_prob = self.metrics.win_rate / 100
            loss_prob = 1 - win_prob
            self.metrics.expectancy = (win_prob * self.metrics.avg_win) - (loss_prob * abs(self.metrics.avg_loss))
    
    def _calculate_kelly_criterion(self) -> None:
        """Calculate Kelly Criterion for position sizing"""
        if self.metrics.avg_loss != 0 and self.metrics.win_rate > 0:
            win_prob = self.metrics.win_rate / 100
            win_loss_ratio = abs(self.metrics.avg_win / self.metrics.avg_loss)
            self.metrics.kelly_criterion = (win_prob - (1 - win_prob) / win_loss_ratio) * 100
    
    def _calculate_recovery_factor(self) -> None:
        """Calculate recovery factor (net profit / max drawdown)"""
        if self.metrics.max_drawdown > 0:
            self.metrics.recovery_factor = self.metrics.total_pnl / (self.metrics.max_drawdown * self.initial_capital / 100)
    
    def _calculate_payoff_ratio(self) -> None:
        """Calculate payoff ratio (avg win / avg loss)"""
        if self.metrics.avg_loss != 0:
            self.metrics.payoff_ratio = abs(self.metrics.avg_win / self.metrics.avg_loss)
    
    def _calculate_time_metrics(self) -> None:
        """Calculate time-based metrics"""
        if not self.trades:
            return
        
        # Average trade duration
        durations = [(t.exit_time - t.entry_time).total_seconds() / 3600 
                    for t in self.trades]  # In hours
        self.metrics.avg_trade_duration = np.mean(durations)
        
        # Total trading days
        first_trade = min(t.entry_time for t in self.trades)
        last_trade = max(t.exit_time for t in self.trades)
        self.metrics.total_trading_days = (last_trade - first_trade).days
        
        # Average trades per day
        if self.metrics.total_trading_days > 0:
            self.metrics.avg_trades_per_day = self.metrics.total_trades / self.metrics.total_trading_days
    
    def get_pnl_attribution(self) -> Dict[str, Dict]:
        """Get P&L attribution by strategy, symbol, and time"""
        attribution = {
            'by_strategy': {},
            'by_symbol': {},
            'by_day': {},
            'by_month': {}
        }
        
        # By strategy
        for trade in self.trades:
            if trade.strategy not in attribution['by_strategy']:
                attribution['by_strategy'][trade.strategy] = {
                    'pnl': 0, 'trades': 0, 'win_rate': 0
                }
            attribution['by_strategy'][trade.strategy]['pnl'] += trade.pnl
            attribution['by_strategy'][trade.strategy]['trades'] += 1
        
        # Calculate win rates by strategy
        for strategy in attribution['by_strategy']:
            wins = sum(1 for t in self.trades 
                      if t.strategy == strategy and t.pnl > 0)
            total = attribution['by_strategy'][strategy]['trades']
            attribution['by_strategy'][strategy]['win_rate'] = (wins / total * 100) if total > 0 else 0
        
        # By symbol
        for trade in self.trades:
            if trade.symbol not in attribution['by_symbol']:
                attribution['by_symbol'][trade.symbol] = {
                    'pnl': 0, 'trades': 0, 'win_rate': 0
                }
            attribution['by_symbol'][trade.symbol]['pnl'] += trade.pnl
            attribution['by_symbol'][trade.symbol]['trades'] += 1
        
        # By day
        for trade in self.trades:
            day = trade.exit_time.date().isoformat()
            if day not in attribution['by_day']:
                attribution['by_day'][day] = 0
            attribution['by_day'][day] += trade.pnl
        
        # By month
        for trade in self.trades:
            month = trade.exit_time.strftime('%Y-%m')
            if month not in attribution['by_month']:
                attribution['by_month'][month] = 0
            attribution['by_month'][month] += trade.pnl
        
        return attribution
    
    def get_risk_adjusted_returns(self) -> Dict[str, float]:
        """Calculate various risk-adjusted return metrics"""
        returns = {
            'sharpe_ratio': self.metrics.sharpe_ratio,
            'sortino_ratio': self.metrics.sortino_ratio,
            'calmar_ratio': self.metrics.calmar_ratio,
            'recovery_factor': self.metrics.recovery_factor,
            'profit_factor': self.metrics.profit_factor,
            'return_over_max_dd': 0
        }
        
        # Return over max drawdown
        if self.metrics.max_drawdown > 0:
            total_return = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
            returns['return_over_max_dd'] = total_return / self.metrics.max_drawdown
        
        return returns
    
    def generate_report(self) -> Dict:
        """Generate comprehensive performance report"""
        report = {
            'summary': {
                'initial_capital': self.initial_capital,
                'current_capital': self.current_capital,
                'total_pnl': self.metrics.total_pnl,
                'total_return_pct': ((self.current_capital - self.initial_capital) / self.initial_capital * 100),
                'total_trades': self.metrics.total_trades,
                'win_rate': self.metrics.win_rate
            },
            'metrics': {
                'sharpe_ratio': self.metrics.sharpe_ratio,
                'sortino_ratio': self.metrics.sortino_ratio,
                'calmar_ratio': self.metrics.calmar_ratio,
                'max_drawdown': self.metrics.max_drawdown,
                'profit_factor': self.metrics.profit_factor,
                'expectancy': self.metrics.expectancy,
                'kelly_criterion': self.metrics.kelly_criterion
            },
            'trade_stats': {
                'winning_trades': self.metrics.winning_trades,
                'losing_trades': self.metrics.losing_trades,
                'avg_win': self.metrics.avg_win,
                'avg_loss': self.metrics.avg_loss,
                'largest_win': self.metrics.largest_win,
                'largest_loss': self.metrics.largest_loss,
                'avg_trade_duration_hours': self.metrics.avg_trade_duration
            },
            'attribution': self.get_pnl_attribution(),
            'risk_adjusted': self.get_risk_adjusted_returns()
        }
        
        return report
    
    def export_to_csv(self, filepath: str) -> None:
        """Export trades to CSV file"""
        if not self.trades:
            logger.warning("No trades to export")
            return
        
        df = pd.DataFrame([{
            'id': t.id,
            'symbol': t.symbol,
            'side': t.side,
            'entry_price': t.entry_price,
            'exit_price': t.exit_price,
            'quantity': t.quantity,
            'entry_time': t.entry_time,
            'exit_time': t.exit_time,
            'pnl': t.pnl,
            'pnl_percent': t.pnl_percent,
            'fees': t.fees,
            'strategy': t.strategy
        } for t in self.trades])
        
        df.to_csv(filepath, index=False)
        logger.info(f"Trades exported to {filepath}")
    
    def export_report_json(self, filepath: str) -> None:
        """Export performance report to JSON"""
        report = self.generate_report()
        
        # Convert datetime objects to strings
        def convert_dates(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=convert_dates)
        
        logger.info(f"Report exported to {filepath}")
    
    def calculate_metrics(self, trades: List[Trade]) -> Dict:
        """Calculate metrics for a list of trades (for testing)"""
        if not trades:
            return {}
        
        # Store trades and update metrics
        self.trades = trades
        for trade in trades:
            self.current_capital += trade.pnl
            self.equity_curve.append(self.current_capital)
        
        self._update_metrics()
        
        # Return metrics as dictionary
        return {
            'total_trades': self.metrics.total_trades,
            'winning_trades': self.metrics.winning_trades,
            'losing_trades': self.metrics.losing_trades,
            'win_rate': self.metrics.win_rate,
            'total_pnl': self.metrics.total_pnl,
            'gross_profit': self.metrics.gross_profit,
            'gross_loss': self.metrics.gross_loss,
            'profit_factor': self.metrics.profit_factor,
            'sharpe_ratio': self.metrics.sharpe_ratio,
            'sortino_ratio': self.metrics.sortino_ratio,
            'max_drawdown': self.metrics.max_drawdown,
            'avg_win': self.metrics.avg_win,
            'avg_loss': self.metrics.avg_loss,
            'expectancy': self.metrics.expectancy,
            'kelly_criterion': self.metrics.kelly_criterion
        }
    
    def calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio for given returns series"""
        if len(returns) == 0:
            return 0.0
        
        excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
        if returns.std() > 0:
            return np.sqrt(252) * excess_returns.mean() / returns.std()
        return 0.0
    
    def calculate_max_drawdown(self, equity_curve: pd.Series) -> float:
        """Calculate maximum drawdown for given equity curve"""
        if len(equity_curve) < 2:
            return 0.0
        
        cummax = equity_curve.cummax()
        drawdown = (equity_curve - cummax) / cummax
        return abs(drawdown.min()) * 100  # As percentage
    
    def print_summary(self) -> None:
        """Print performance summary to console"""
        print("\n" + "="*60)
        print("PERFORMANCE SUMMARY")
        print("="*60)
        
        print(f"\nCapital:")
        print(f"  Initial: ${self.initial_capital:,.2f}")
        print(f"  Current: ${self.current_capital:,.2f}")
        print(f"  Total P&L: ${self.metrics.total_pnl:,.2f}")
        print(f"  Return: {((self.current_capital - self.initial_capital) / self.initial_capital * 100):.2f}%")
        
        print(f"\nTrade Statistics:")
        print(f"  Total Trades: {self.metrics.total_trades}")
        print(f"  Win Rate: {self.metrics.win_rate:.2f}%")
        print(f"  Profit Factor: {self.metrics.profit_factor:.2f}")
        print(f"  Expectancy: ${self.metrics.expectancy:.2f}")
        
        print(f"\nRisk Metrics:")
        print(f"  Sharpe Ratio: {self.metrics.sharpe_ratio:.2f}")
        print(f"  Sortino Ratio: {self.metrics.sortino_ratio:.2f}")
        print(f"  Max Drawdown: {self.metrics.max_drawdown:.2f}%")
        print(f"  Calmar Ratio: {self.metrics.calmar_ratio:.2f}")
        
        print(f"\nAverage Metrics:")
        print(f"  Avg Win: ${self.metrics.avg_win:.2f}")
        print(f"  Avg Loss: ${self.metrics.avg_loss:.2f}")
        print(f"  Payoff Ratio: {self.metrics.payoff_ratio:.2f}")
        print(f"  Kelly %: {self.metrics.kelly_criterion:.2f}%")
        
        print("="*60)

# Example usage
if __name__ == "__main__":
    # Create analytics instance
    analytics = PerformanceAnalytics(initial_capital=10000)
    
    # Add sample trades
    from datetime import datetime, timedelta
    import random
    
    for i in range(50):
        # Generate random trade
        entry_price = random.uniform(60000, 70000)
        exit_price = entry_price * (1 + random.uniform(-0.03, 0.05))
        quantity = 0.001
        pnl = (exit_price - entry_price) * quantity
        pnl_percent = ((exit_price - entry_price) / entry_price) * 100
        
        trade = Trade(
            id=f"trade_{i}",
            symbol="BTCUSDT",
            side=random.choice(["Buy", "Sell"]),
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            entry_time=datetime.now() - timedelta(days=30-i),
            exit_time=datetime.now() - timedelta(days=29-i),
            pnl=pnl,
            pnl_percent=pnl_percent,
            fees=abs(pnl) * 0.001,
            strategy=random.choice(["ML_Ensemble", "RSI_Strategy", "EMA_Cross"])
        )
        
        analytics.add_trade(trade)
    
    # Print summary
    analytics.print_summary()
    
    # Generate report
    report = analytics.generate_report()
    print("\nP&L Attribution by Strategy:")
    for strategy, data in report['attribution']['by_strategy'].items():
        print(f"  {strategy}: ${data['pnl']:.2f} ({data['trades']} trades, {data['win_rate']:.1f}% win rate)")
    
    # Export reports
    analytics.export_to_csv("trades_history.csv")
    analytics.export_report_json("performance_report.json")