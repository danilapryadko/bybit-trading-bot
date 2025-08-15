"""
Backtesting Framework for Bybit Trading Bot
Historical data testing and strategy optimization
"""

import logging
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
import pandas as pd
import numpy as np
from collections import deque
import json
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import pickle
import os

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Backtesting configuration"""
    start_date: datetime
    end_date: datetime
    initial_balance: float = 10000.0
    symbols: List[str] = field(default_factory=lambda: ["BTCUSDT"])
    timeframe: str = "1h"  # 1m, 5m, 15m, 30m, 1h, 4h, 1d
    commission: float = 0.0006  # 0.06% maker fee
    slippage: float = 0.0001  # 0.01% slippage
    use_limit_orders: bool = True
    use_market_orders: bool = False
    enable_shorting: bool = True
    max_positions: int = 5
    data_source: str = "bybit"  # bybit, csv, database
    optimization_enabled: bool = False
    optimization_metric: str = "sharpe_ratio"  # sharpe_ratio, total_return, win_rate
    walk_forward_analysis: bool = False
    monte_carlo_runs: int = 0  # 0 = disabled


@dataclass
class BacktestTrade:
    """Trade record for backtesting"""
    symbol: str
    side: str  # buy/sell
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: float = 0.0
    quantity: float = 0.0
    commission: float = 0.0
    pnl: float = 0.0
    pnl_percentage: float = 0.0
    trade_duration: Optional[timedelta] = None
    exit_reason: str = ""  # stop_loss, take_profit, signal, manual
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestResult:
    """Backtesting results"""
    config: BacktestConfig
    trades: List[BacktestTrade]
    equity_curve: pd.Series
    metrics: Dict[str, Any]
    optimization_results: Optional[Dict[str, Any]] = None
    monte_carlo_results: Optional[Dict[str, Any]] = None


class BacktestingEngine:
    """Engine for backtesting trading strategies"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.data_cache = {}  # symbol -> DataFrame
        self.current_balance = config.initial_balance
        self.positions = {}  # symbol -> BacktestTrade
        self.completed_trades = []
        self.equity_curve = []
        self.current_time = config.start_date
        
        # Performance tracking
        self.metrics = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_return": 0.0,
            "total_return_pct": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "calmar_ratio": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "largest_win": 0.0,
            "largest_loss": 0.0,
            "average_trade_duration": timedelta(0),
            "max_consecutive_wins": 0,
            "max_consecutive_losses": 0,
            "recovery_factor": 0.0,
            "expectancy": 0.0,
            "sqn": 0.0  # System Quality Number
        }
        
        logger.info(f"Backtesting Engine initialized: {config.start_date} to {config.end_date}")
    
    async def load_historical_data(self, symbol: str) -> pd.DataFrame:
        """Load historical data for a symbol"""
        try:
            if symbol in self.data_cache:
                return self.data_cache[symbol]
            
            if self.config.data_source == "bybit":
                data = await self._fetch_bybit_data(symbol)
            elif self.config.data_source == "csv":
                data = self._load_csv_data(symbol)
            elif self.config.data_source == "database":
                data = self._load_database_data(symbol)
            else:
                raise ValueError(f"Unknown data source: {self.config.data_source}")
            
            # Validate and clean data
            data = self._validate_data(data)
            
            # Cache the data
            self.data_cache[symbol] = data
            
            logger.info(f"Loaded {len(data)} candles for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Error loading historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    async def _fetch_bybit_data(self, symbol: str) -> pd.DataFrame:
        """Fetch historical data from Bybit API"""
        try:
            all_data = []
            interval_map = {
                "1m": 1, "5m": 5, "15m": 15, "30m": 30,
                "1h": 60, "4h": 240, "1d": 1440
            }
            interval = interval_map.get(self.config.timeframe, 60)
            
            current_time = self.config.end_date
            
            async with aiohttp.ClientSession() as session:
                while current_time > self.config.start_date:
                    # Bybit API endpoint
                    url = "https://api.bybit.com/v5/market/kline"
                    params = {
                        "category": "spot",
                        "symbol": symbol,
                        "interval": str(interval),
                        "end": int(current_time.timestamp() * 1000),
                        "limit": 200
                    }
                    
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data["retCode"] == 0:
                                klines = data["result"]["list"]
                                if not klines:
                                    break
                                
                                for kline in klines:
                                    all_data.append({
                                        "timestamp": datetime.fromtimestamp(int(kline[0]) / 1000, tz=timezone.utc),
                                        "open": float(kline[1]),
                                        "high": float(kline[2]),
                                        "low": float(kline[3]),
                                        "close": float(kline[4]),
                                        "volume": float(kline[5]),
                                        "turnover": float(kline[6])
                                    })
                                
                                # Update current_time for next iteration
                                current_time = datetime.fromtimestamp(int(klines[-1][0]) / 1000, tz=timezone.utc)
                            else:
                                logger.error(f"API error: {data['retMsg']}")
                                break
                        else:
                            logger.error(f"HTTP error: {response.status}")
                            break
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
            
            # Convert to DataFrame
            df = pd.DataFrame(all_data)
            if not df.empty:
                df = df.sort_values("timestamp")
                df = df.set_index("timestamp")
                
                # Add technical indicators
                df = self._add_technical_indicators(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching Bybit data: {e}")
            return pd.DataFrame()
    
    def _load_csv_data(self, symbol: str) -> pd.DataFrame:
        """Load data from CSV file"""
        try:
            filename = f"data/{symbol}_{self.config.timeframe}.csv"
            df = pd.read_csv(filename, parse_dates=["timestamp"], index_col="timestamp")
            
            # Filter by date range
            df = df[(df.index >= self.config.start_date) & (df.index <= self.config.end_date)]
            
            # Add technical indicators
            df = self._add_technical_indicators(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading CSV data: {e}")
            return pd.DataFrame()
    
    def _load_database_data(self, symbol: str) -> pd.DataFrame:
        """Load data from database"""
        # Implement database loading logic here
        logger.warning("Database data loading not implemented")
        return pd.DataFrame()
    
    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and clean historical data"""
        if df.empty:
            return df
        
        # Remove duplicates
        df = df[~df.index.duplicated(keep='first')]
        
        # Forward fill missing values
        df = df.fillna(method='ffill')
        
        # Remove rows with zero volume
        df = df[df['volume'] > 0]
        
        # Check for data gaps
        expected_freq = pd.Timedelta(self.config.timeframe.replace('m', 'min').replace('h', 'hour').replace('d', 'day'))
        time_diff = df.index.to_series().diff()
        gaps = time_diff[time_diff > expected_freq * 2]
        
        if not gaps.empty:
            logger.warning(f"Found {len(gaps)} data gaps")
        
        return df
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to the data"""
        try:
            # Simple Moving Averages
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['sma_200'] = df['close'].rolling(window=200).mean()
            
            # Exponential Moving Averages
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            
            # ATR (Average True Range)
            high_low = df['high'] - df['low']
            high_close = (df['high'] - df['close'].shift()).abs()
            low_close = (df['low'] - df['close'].shift()).abs()
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['atr'] = true_range.rolling(window=14).mean()
            
            # Volume indicators
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # Price change
            df['returns'] = df['close'].pct_change()
            df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
            
            return df
            
        except Exception as e:
            logger.error(f"Error adding technical indicators: {e}")
            return df
    
    async def run_backtest(self, strategy: Callable) -> BacktestResult:
        """Run backtest with a given strategy"""
        try:
            logger.info("Starting backtest...")
            
            # Load data for all symbols
            for symbol in self.config.symbols:
                await self.load_historical_data(symbol)
            
            # Check if data is loaded
            if not self.data_cache:
                logger.error("No data loaded for backtesting")
                return self._create_empty_result()
            
            # Get the common date range across all symbols
            date_range = self._get_common_date_range()
            
            # Initialize equity curve
            self.equity_curve = [self.current_balance]
            
            # Main backtest loop
            for timestamp in date_range:
                self.current_time = timestamp
                
                # Get current data for all symbols
                current_data = {}
                for symbol in self.config.symbols:
                    if symbol in self.data_cache:
                        df = self.data_cache[symbol]
                        if timestamp in df.index:
                            current_data[symbol] = df.loc[timestamp]
                
                if not current_data:
                    continue
                
                # Update open positions
                self._update_positions(current_data)
                
                # Generate signals from strategy
                signals = strategy(current_data, self.positions, self.current_balance)
                
                # Execute trades based on signals
                self._execute_signals(signals, current_data)
                
                # Record equity
                equity = self._calculate_equity(current_data)
                self.equity_curve.append(equity)
            
            # Close any remaining positions
            self._close_all_positions(current_data)
            
            # Calculate metrics
            self._calculate_metrics()
            
            # Run optimization if enabled
            optimization_results = None
            if self.config.optimization_enabled:
                optimization_results = await self._run_optimization(strategy)
            
            # Run Monte Carlo simulation if enabled
            monte_carlo_results = None
            if self.config.monte_carlo_runs > 0:
                monte_carlo_results = self._run_monte_carlo()
            
            # Create result
            result = BacktestResult(
                config=self.config,
                trades=self.completed_trades,
                equity_curve=pd.Series(self.equity_curve, index=date_range[:len(self.equity_curve)]),
                metrics=self.metrics,
                optimization_results=optimization_results,
                monte_carlo_results=monte_carlo_results
            )
            
            logger.info(f"Backtest completed: {self.metrics['total_trades']} trades, "
                       f"{self.metrics['total_return_pct']:.2f}% return")
            
            return result
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return self._create_empty_result()
    
    def _get_common_date_range(self) -> pd.DatetimeIndex:
        """Get common date range across all symbols"""
        if not self.data_cache:
            return pd.DatetimeIndex([])
        
        # Find intersection of all date ranges
        date_ranges = [df.index for df in self.data_cache.values()]
        common_dates = date_ranges[0]
        
        for dates in date_ranges[1:]:
            common_dates = common_dates.intersection(dates)
        
        return common_dates.sort_values()
    
    def _update_positions(self, current_data: Dict[str, pd.Series]):
        """Update open positions with current prices"""
        for symbol, position in list(self.positions.items()):
            if symbol in current_data:
                current_price = current_data[symbol]['close']
                
                # Check stop loss
                if position.metadata.get('stop_loss'):
                    if position.side == 'buy' and current_price <= position.metadata['stop_loss']:
                        self._close_position(symbol, current_price, 'stop_loss')
                    elif position.side == 'sell' and current_price >= position.metadata['stop_loss']:
                        self._close_position(symbol, current_price, 'stop_loss')
                
                # Check take profit
                if position.metadata.get('take_profit'):
                    if position.side == 'buy' and current_price >= position.metadata['take_profit']:
                        self._close_position(symbol, current_price, 'take_profit')
                    elif position.side == 'sell' and current_price <= position.metadata['take_profit']:
                        self._close_position(symbol, current_price, 'take_profit')
    
    def _execute_signals(self, signals: Dict[str, Any], current_data: Dict[str, pd.Series]):
        """Execute trading signals"""
        for symbol, signal in signals.items():
            if symbol not in current_data:
                continue
            
            current_price = current_data[symbol]['close']
            
            if signal['action'] == 'buy' and symbol not in self.positions:
                self._open_position(symbol, 'buy', current_price, signal.get('size', 0.1))
            elif signal['action'] == 'sell' and symbol not in self.positions and self.config.enable_shorting:
                self._open_position(symbol, 'sell', current_price, signal.get('size', 0.1))
            elif signal['action'] == 'close' and symbol in self.positions:
                self._close_position(symbol, current_price, 'signal')
    
    def _open_position(self, symbol: str, side: str, price: float, size: float):
        """Open a new position"""
        if len(self.positions) >= self.config.max_positions:
            return
        
        # Calculate position size
        position_value = self.current_balance * size
        quantity = position_value / price
        
        # Apply commission
        commission = position_value * self.config.commission
        self.current_balance -= commission
        
        # Apply slippage
        if side == 'buy':
            entry_price = price * (1 + self.config.slippage)
        else:
            entry_price = price * (1 - self.config.slippage)
        
        # Create trade record
        trade = BacktestTrade(
            symbol=symbol,
            side=side,
            entry_time=self.current_time,
            entry_price=entry_price,
            quantity=quantity,
            commission=commission
        )
        
        self.positions[symbol] = trade
        self.metrics['total_trades'] += 1
        
        logger.debug(f"Opened {side} position: {symbol} @ {entry_price:.2f}")
    
    def _close_position(self, symbol: str, price: float, reason: str):
        """Close an existing position"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        # Apply slippage
        if position.side == 'buy':
            exit_price = price * (1 - self.config.slippage)
        else:
            exit_price = price * (1 + self.config.slippage)
        
        # Calculate P&L
        if position.side == 'buy':
            pnl = (exit_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - exit_price) * position.quantity
        
        # Apply commission
        commission = exit_price * position.quantity * self.config.commission
        pnl -= commission
        
        # Update position
        position.exit_time = self.current_time
        position.exit_price = exit_price
        position.pnl = pnl
        position.pnl_percentage = (pnl / (position.entry_price * position.quantity)) * 100
        position.trade_duration = position.exit_time - position.entry_time
        position.exit_reason = reason
        position.commission += commission
        
        # Update balance
        self.current_balance += position.entry_price * position.quantity + pnl
        
        # Update metrics
        if pnl > 0:
            self.metrics['winning_trades'] += 1
        else:
            self.metrics['losing_trades'] += 1
        
        # Move to completed trades
        self.completed_trades.append(position)
        del self.positions[symbol]
        
        logger.debug(f"Closed {position.side} position: {symbol} @ {exit_price:.2f}, PnL: {pnl:.2f}")
    
    def _close_all_positions(self, current_data: Dict[str, pd.Series]):
        """Close all remaining positions"""
        for symbol in list(self.positions.keys()):
            if symbol in current_data:
                price = current_data[symbol]['close']
            else:
                # Use last known price
                price = self.positions[symbol].entry_price
            
            self._close_position(symbol, price, 'end_of_backtest')
    
    def _calculate_equity(self, current_data: Dict[str, pd.Series]) -> float:
        """Calculate current equity including open positions"""
        equity = self.current_balance
        
        for symbol, position in self.positions.items():
            if symbol in current_data:
                current_price = current_data[symbol]['close']
                
                if position.side == 'buy':
                    unrealized_pnl = (current_price - position.entry_price) * position.quantity
                else:
                    unrealized_pnl = (position.entry_price - current_price) * position.quantity
                
                equity += position.entry_price * position.quantity + unrealized_pnl
        
        return equity
    
    def _calculate_metrics(self):
        """Calculate performance metrics"""
        if not self.completed_trades:
            return
        
        # Basic metrics
        self.metrics['total_return'] = self.current_balance - self.config.initial_balance
        self.metrics['total_return_pct'] = (self.metrics['total_return'] / self.config.initial_balance) * 100
        
        # Win rate
        if self.metrics['total_trades'] > 0:
            self.metrics['win_rate'] = self.metrics['winning_trades'] / self.metrics['total_trades']
        
        # Average win/loss
        wins = [t.pnl for t in self.completed_trades if t.pnl > 0]
        losses = [t.pnl for t in self.completed_trades if t.pnl <= 0]
        
        if wins:
            self.metrics['average_win'] = np.mean(wins)
            self.metrics['largest_win'] = max(wins)
        
        if losses:
            self.metrics['average_loss'] = np.mean(losses)
            self.metrics['largest_loss'] = min(losses)
        
        # Profit factor
        if losses:
            total_wins = sum(wins) if wins else 0
            total_losses = abs(sum(losses))
            self.metrics['profit_factor'] = total_wins / total_losses if total_losses > 0 else 0
        
        # Drawdown
        equity_curve = pd.Series(self.equity_curve)
        rolling_max = equity_curve.expanding().max()
        drawdown = (equity_curve - rolling_max) / rolling_max
        self.metrics['max_drawdown'] = drawdown.min()
        
        # Sharpe ratio (annualized)
        returns = equity_curve.pct_change().dropna()
        if len(returns) > 1:
            periods_per_year = self._get_periods_per_year()
            self.metrics['sharpe_ratio'] = (returns.mean() * periods_per_year) / (returns.std() * np.sqrt(periods_per_year))
        
        # Sortino ratio
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_std = downside_returns.std()
            if downside_std > 0:
                periods_per_year = self._get_periods_per_year()
                self.metrics['sortino_ratio'] = (returns.mean() * periods_per_year) / (downside_std * np.sqrt(periods_per_year))
        
        # Calmar ratio
        if self.metrics['max_drawdown'] != 0:
            annual_return = self.metrics['total_return_pct'] * (365 / (self.config.end_date - self.config.start_date).days)
            self.metrics['calmar_ratio'] = annual_return / abs(self.metrics['max_drawdown'])
        
        # Average trade duration
        durations = [t.trade_duration for t in self.completed_trades if t.trade_duration]
        if durations:
            self.metrics['average_trade_duration'] = sum(durations, timedelta()) / len(durations)
        
        # Consecutive wins/losses
        self._calculate_consecutive_trades()
        
        # Expectancy
        if self.metrics['total_trades'] > 0:
            self.metrics['expectancy'] = (
                self.metrics['win_rate'] * self.metrics.get('average_win', 0) +
                (1 - self.metrics['win_rate']) * self.metrics.get('average_loss', 0)
            )
        
        # System Quality Number (SQN)
        if self.completed_trades:
            trade_returns = [t.pnl for t in self.completed_trades]
            if len(trade_returns) > 1:
                avg_return = np.mean(trade_returns)
                std_return = np.std(trade_returns)
                if std_return > 0:
                    self.metrics['sqn'] = (avg_return / std_return) * np.sqrt(len(trade_returns))
    
    def _get_periods_per_year(self) -> int:
        """Get number of periods per year based on timeframe"""
        timeframe_map = {
            "1m": 525600, "5m": 105120, "15m": 35040, "30m": 17520,
            "1h": 8760, "4h": 2190, "1d": 365
        }
        return timeframe_map.get(self.config.timeframe, 365)
    
    def _calculate_consecutive_trades(self):
        """Calculate maximum consecutive wins/losses"""
        consecutive_wins = 0
        consecutive_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in self.completed_trades:
            if trade.pnl > 0:
                current_wins += 1
                current_losses = 0
                consecutive_wins = max(consecutive_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                consecutive_losses = max(consecutive_losses, current_losses)
        
        self.metrics['max_consecutive_wins'] = consecutive_wins
        self.metrics['max_consecutive_losses'] = consecutive_losses
    
    async def _run_optimization(self, strategy: Callable) -> Dict[str, Any]:
        """Run strategy optimization"""
        logger.info("Running strategy optimization...")
        
        # Define parameter ranges for optimization
        param_ranges = {
            'risk_per_trade': [0.01, 0.02, 0.03],
            'stop_loss_multiplier': [1.5, 2.0, 2.5],
            'take_profit_ratio': [1.5, 2.0, 2.5, 3.0]
        }
        
        best_result = None
        best_metric = -float('inf')
        all_results = []
        
        # Grid search optimization
        for risk in param_ranges['risk_per_trade']:
            for sl_mult in param_ranges['stop_loss_multiplier']:
                for tp_ratio in param_ranges['take_profit_ratio']:
                    # Update strategy parameters
                    params = {
                        'risk_per_trade': risk,
                        'stop_loss_multiplier': sl_mult,
                        'take_profit_ratio': tp_ratio
                    }
                    
                    # Run backtest with these parameters
                    self._reset_state()
                    modified_strategy = lambda data, pos, bal: strategy(data, pos, bal, **params)
                    result = await self.run_backtest(modified_strategy)
                    
                    # Track results
                    optimization_metric = result.metrics.get(self.config.optimization_metric, 0)
                    all_results.append({
                        'parameters': params,
                        'metric': optimization_metric,
                        'metrics': result.metrics
                    })
                    
                    # Update best result
                    if optimization_metric > best_metric:
                        best_metric = optimization_metric
                        best_result = {
                            'parameters': params,
                            'metric': optimization_metric,
                            'result': result
                        }
        
        logger.info(f"Optimization complete. Best {self.config.optimization_metric}: {best_metric:.4f}")
        
        return {
            'best': best_result,
            'all_results': all_results
        }
    
    def _run_monte_carlo(self) -> Dict[str, Any]:
        """Run Monte Carlo simulation"""
        logger.info(f"Running {self.config.monte_carlo_runs} Monte Carlo simulations...")
        
        if not self.completed_trades:
            return {}
        
        # Extract trade returns
        trade_returns = [t.pnl_percentage / 100 for t in self.completed_trades]
        
        results = []
        for _ in range(self.config.monte_carlo_runs):
            # Randomly sample trades with replacement
            simulated_returns = np.random.choice(trade_returns, size=len(trade_returns), replace=True)
            
            # Calculate equity curve
            equity = self.config.initial_balance
            equity_curve = [equity]
            
            for ret in simulated_returns:
                equity *= (1 + ret)
                equity_curve.append(equity)
            
            # Calculate metrics for this simulation
            final_return = (equity - self.config.initial_balance) / self.config.initial_balance
            max_dd = self._calculate_max_drawdown(equity_curve)
            
            results.append({
                'final_return': final_return,
                'max_drawdown': max_dd,
                'final_equity': equity
            })
        
        # Calculate statistics
        returns = [r['final_return'] for r in results]
        drawdowns = [r['max_drawdown'] for r in results]
        
        return {
            'mean_return': np.mean(returns),
            'std_return': np.std(returns),
            'min_return': np.min(returns),
            'max_return': np.max(returns),
            'percentiles': {
                '5%': np.percentile(returns, 5),
                '25%': np.percentile(returns, 25),
                '50%': np.percentile(returns, 50),
                '75%': np.percentile(returns, 75),
                '95%': np.percentile(returns, 95)
            },
            'mean_max_drawdown': np.mean(drawdowns),
            'worst_drawdown': np.min(drawdowns),
            'probability_profit': sum(1 for r in returns if r > 0) / len(returns)
        }
    
    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """Calculate maximum drawdown from equity curve"""
        peak = equity_curve[0]
        max_dd = 0
        
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (value - peak) / peak
            if dd < max_dd:
                max_dd = dd
        
        return max_dd
    
    def _reset_state(self):
        """Reset engine state for new backtest"""
        self.current_balance = self.config.initial_balance
        self.positions = {}
        self.completed_trades = []
        self.equity_curve = []
        self.current_time = self.config.start_date
        self.metrics = {key: 0 for key in self.metrics}
    
    def _create_empty_result(self) -> BacktestResult:
        """Create empty result for failed backtest"""
        return BacktestResult(
            config=self.config,
            trades=[],
            equity_curve=pd.Series([self.config.initial_balance]),
            metrics=self.metrics
        )
    
    def save_results(self, result: BacktestResult, filename: str):
        """Save backtest results to file"""
        try:
            # Create results directory if it doesn't exist
            os.makedirs("results", exist_ok=True)
            
            # Save as pickle
            with open(f"results/{filename}.pkl", "wb") as f:
                pickle.dump(result, f)
            
            # Save metrics as JSON
            metrics_json = {
                k: str(v) if isinstance(v, timedelta) else v
                for k, v in result.metrics.items()
            }
            with open(f"results/{filename}_metrics.json", "w") as f:
                json.dump(metrics_json, f, indent=2)
            
            # Save trades as CSV
            if result.trades:
                trades_df = pd.DataFrame([asdict(t) for t in result.trades])
                trades_df.to_csv(f"results/{filename}_trades.csv", index=False)
            
            # Save equity curve
            result.equity_curve.to_csv(f"results/{filename}_equity.csv")
            
            logger.info(f"Results saved to results/{filename}")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")