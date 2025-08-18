"""
Performance Analytics Module
Tracks and analyzes trading performance metrics
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from collections import defaultdict

logger = logging.getLogger(__name__)

class PerformanceAnalytics:
    """Advanced performance tracking and analytics"""
    
    def __init__(self):
        self.trades_history = []
        self.daily_stats = defaultdict(dict)
        self.metrics_cache = {}
        
    def add_trade(self, trade: Dict[str, Any]):
        """Add completed trade to history"""
        trade['timestamp'] = trade.get('timestamp', datetime.now())
        self.trades_history.append(trade)
        self._update_daily_stats(trade)
        self._invalidate_cache()
        
    def _update_daily_stats(self, trade: Dict[str, Any]):
        """Update daily statistics"""
        date = trade['timestamp'].date()
        
        if date not in self.daily_stats:
            self.daily_stats[date] = {
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'pnl': 0,
                'volume': 0,
                'fees': 0
            }
        
        stats = self.daily_stats[date]
        stats['trades'] += 1
        stats['pnl'] += trade.get('pnl', 0)
        stats['volume'] += trade.get('volume', 0)
        stats['fees'] += trade.get('fees', 0)
        
        if trade.get('pnl', 0) > 0:
            stats['wins'] += 1
        else:
            stats['losses'] += 1
    
    def _invalidate_cache(self):
        """Clear cached metrics"""
        self.metrics_cache = {}
    
    def calculate_metrics(self, period_days: int = 30) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics
        """
        cache_key = f"metrics_{period_days}"
        if cache_key in self.metrics_cache:
            return self.metrics_cache[cache_key]
        
        # Filter trades for period
        cutoff_date = datetime.now() - timedelta(days=period_days)
        period_trades = [t for t in self.trades_history 
                        if t['timestamp'] >= cutoff_date]
        
        if not period_trades:
            return self._empty_metrics()
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(period_trades)
        
        # Basic metrics
        total_trades = len(period_trades)
        winning_trades = len(df[df['pnl'] > 0])
        losing_trades = len(df[df['pnl'] <= 0])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # PnL metrics
        total_pnl = df['pnl'].sum()
        avg_pnl = df['pnl'].mean()
        best_trade = df['pnl'].max()
        worst_trade = df['pnl'].min()
        
        # Calculate Sharpe Ratio
        if len(df) > 1:
            daily_returns = df.groupby(df['timestamp'].dt.date)['pnl'].sum()
            sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)
        else:
            sharpe_ratio = 0
        
        # Calculate max drawdown
        cumulative_pnl = df['pnl'].cumsum()
        max_drawdown = self._calculate_max_drawdown(cumulative_pnl)
        
        # Calculate profit factor
        total_wins = df[df['pnl'] > 0]['pnl'].sum()
        total_losses = abs(df[df['pnl'] < 0]['pnl'].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Average win/loss
        avg_win = df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = df[df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
        
        # Expectancy
        expectancy = (win_rate/100 * avg_win) + ((1 - win_rate/100) * avg_loss)
        
        # Trading frequency
        trading_days = len(df.groupby(df['timestamp'].dt.date))
        avg_trades_per_day = total_trades / trading_days if trading_days > 0 else 0
        
        metrics = {
            'period_days': period_days,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'total_pnl': round(total_pnl, 2),
            'avg_pnl': round(avg_pnl, 2),
            'best_trade': round(best_trade, 2),
            'worst_trade': round(worst_trade, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2),
            'profit_factor': round(profit_factor, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'expectancy': round(expectancy, 2),
            'avg_trades_per_day': round(avg_trades_per_day, 1),
            'last_updated': datetime.now().isoformat()
        }
        
        self.metrics_cache[cache_key] = metrics
        return metrics
    
    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe Ratio"""
        if len(returns) < 2:
            return 0
        
        excess_returns = returns - (risk_free_rate / 365)  # Daily risk-free rate
        
        if excess_returns.std() == 0:
            return 0
        
        sharpe = (excess_returns.mean() / excess_returns.std()) * np.sqrt(365)
        return sharpe
    
    def _calculate_max_drawdown(self, cumulative_pnl: pd.Series) -> float:
        """Calculate maximum drawdown"""
        if len(cumulative_pnl) < 2:
            return 0
        
        running_max = cumulative_pnl.expanding().max()
        drawdown = cumulative_pnl - running_max
        return abs(drawdown.min())
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure"""
        return {
            'period_days': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'avg_pnl': 0,
            'best_trade': 0,
            'worst_trade': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'profit_factor': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'expectancy': 0,
            'avg_trades_per_day': 0,
            'last_updated': datetime.now().isoformat()
        }
    
    def get_daily_breakdown(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily performance breakdown"""
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        daily_data = []
        for date, stats in sorted(self.daily_stats.items()):
            if date >= cutoff_date:
                win_rate = (stats['wins'] / stats['trades']) * 100 if stats['trades'] > 0 else 0
                daily_data.append({
                    'date': date.isoformat(),
                    'trades': stats['trades'],
                    'wins': stats['wins'],
                    'losses': stats['losses'],
                    'win_rate': round(win_rate, 1),
                    'pnl': round(stats['pnl'], 2),
                    'volume': round(stats['volume'], 2),
                    'fees': round(stats['fees'], 2)
                })
        
        return daily_data
    
    def get_performance_chart_data(self) -> Dict[str, List]:
        """Get data formatted for charting"""
        if not self.trades_history:
            return {'dates': [], 'cumulative_pnl': [], 'daily_pnl': []}
        
        df = pd.DataFrame(self.trades_history)
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        
        # Daily PnL
        daily_pnl = df.groupby('date')['pnl'].sum()
        
        # Cumulative PnL
        cumulative_pnl = daily_pnl.cumsum()
        
        return {
            'dates': [d.isoformat() for d in daily_pnl.index],
            'daily_pnl': daily_pnl.tolist(),
            'cumulative_pnl': cumulative_pnl.tolist()
        }
    
    def get_trade_distribution(self) -> Dict[str, Any]:
        """Analyze trade distribution"""
        if not self.trades_history:
            return {}
        
        df = pd.DataFrame(self.trades_history)
        
        # PnL distribution
        pnl_bins = [-float('inf'), -100, -50, -10, 0, 10, 50, 100, float('inf')]
        pnl_labels = ['< -100', '-100 to -50', '-50 to -10', '-10 to 0', 
                      '0 to 10', '10 to 50', '50 to 100', '> 100']
        
        df['pnl_range'] = pd.cut(df['pnl'], bins=pnl_bins, labels=pnl_labels)
        pnl_distribution = df['pnl_range'].value_counts().to_dict()
        
        # Hour distribution
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        hourly_distribution = df.groupby('hour').size().to_dict()
        
        # Symbol distribution
        symbol_distribution = df['symbol'].value_counts().to_dict() if 'symbol' in df else {}
        
        return {
            'pnl_distribution': pnl_distribution,
            'hourly_distribution': hourly_distribution,
            'symbol_distribution': symbol_distribution
        }
    
    def calculate_risk_adjusted_returns(self, balance: float) -> Dict[str, float]:
        """Calculate risk-adjusted return metrics"""
        if not self.trades_history or balance <= 0:
            return {
                'sortino_ratio': 0,
                'calmar_ratio': 0,
                'return_on_capital': 0
            }
        
        df = pd.DataFrame(self.trades_history)
        
        # Calculate returns as percentage of balance
        df['return'] = df['pnl'] / balance
        
        # Sortino Ratio (only considers downside volatility)
        negative_returns = df[df['return'] < 0]['return']
        downside_std = negative_returns.std() if len(negative_returns) > 0 else 0
        sortino_ratio = (df['return'].mean() / downside_std) * np.sqrt(365) if downside_std > 0 else 0
        
        # Calmar Ratio (return / max drawdown)
        cumulative_returns = df['return'].cumsum()
        max_dd = self._calculate_max_drawdown(cumulative_returns)
        annual_return = df['return'].sum() * (365 / len(df))
        calmar_ratio = annual_return / max_dd if max_dd > 0 else 0
        
        # Return on Capital
        total_return = df['pnl'].sum()
        return_on_capital = (total_return / balance) * 100
        
        return {
            'sortino_ratio': round(sortino_ratio, 2),
            'calmar_ratio': round(calmar_ratio, 2),
            'return_on_capital': round(return_on_capital, 2)
        }