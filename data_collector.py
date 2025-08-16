#!/usr/bin/env python3
"""
Historical Data Collector for Bybit Trading Bot
Collects and stores historical market data for ML model training
"""

import os
import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from pybit.unified_trading import HTTP
import asyncio
import aiohttp
from database.service import get_db_service
from config import get_trading_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HistoricalDataCollector:
    """Collects historical market data from Bybit"""
    
    def __init__(self, symbols: Optional[List[str]] = None):
        """Initialize data collector"""
        self.config = get_trading_config()
        self.db = get_db_service()
        
        # Initialize Bybit client
        self.client = HTTP(
            testnet=self.config.is_testnet,
            api_key=self.config.api_key,
            api_secret=self.config.api_secret
        )
        
        # Default symbols to collect
        self.symbols = symbols or ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
        
        # Timeframes to collect (in minutes)
        self.timeframes = {
            '1': 1,      # 1 minute
            '5': 5,      # 5 minutes
            '15': 15,    # 15 minutes
            '60': 60,    # 1 hour
            '240': 240,  # 4 hours
            'D': 1440    # 1 day
        }
        
        logger.info(f"Data collector initialized for {len(self.symbols)} symbols")
    
    def fetch_klines(
        self,
        symbol: str,
        interval: str,
        start_time: int,
        end_time: Optional[int] = None,
        limit: int = 200
    ) -> pd.DataFrame:
        """Fetch kline/candlestick data from Bybit"""
        try:
            # Bybit API call
            response = self.client.get_kline(
                category="linear",
                symbol=symbol,
                interval=interval,
                start=start_time,
                end=end_time,
                limit=limit
            )
            
            if response['retCode'] != 0:
                logger.error(f"API error: {response['retMsg']}")
                return pd.DataFrame()
            
            # Parse response
            klines = response['result']['list']
            
            if not klines:
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
            ])
            
            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
                df[col] = df[col].astype(float)
            
            # Sort by timestamp
            df = df.sort_values('timestamp')
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return pd.DataFrame()
    
    def collect_historical_data(
        self,
        symbol: str,
        interval: str,
        days_back: int = 30
    ) -> pd.DataFrame:
        """Collect historical data for specified period"""
        logger.info(f"Collecting {days_back} days of {interval} data for {symbol}")
        
        all_data = []
        end_time = int(time.time() * 1000)
        start_time = end_time - (days_back * 24 * 60 * 60 * 1000)
        
        current_end = end_time
        
        while current_end > start_time:
            # Fetch batch
            df = self.fetch_klines(
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=current_end,
                limit=200
            )
            
            if df.empty:
                break
            
            all_data.append(df)
            
            # Update end time for next batch
            current_end = int(df['timestamp'].min().timestamp() * 1000) - 1
            
            # Rate limiting
            time.sleep(0.1)
        
        if not all_data:
            return pd.DataFrame()
        
        # Combine all data
        full_df = pd.concat(all_data, ignore_index=True)
        full_df = full_df.drop_duplicates(subset=['timestamp'])
        full_df = full_df.sort_values('timestamp')
        
        logger.info(f"Collected {len(full_df)} candles for {symbol}")
        
        return full_df
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to the dataframe"""
        if df.empty:
            return df
        
        # Simple Moving Averages
        df['sma_7'] = df['close'].rolling(window=7).mean()
        df['sma_25'] = df['close'].rolling(window=25).mean()
        df['sma_99'] = df['close'].rolling(window=99).mean()
        
        # Exponential Moving Averages
        df['ema_7'] = df['close'].ewm(span=7, adjust=False).mean()
        df['ema_25'] = df['close'].ewm(span=25, adjust=False).mean()
        
        # RSI
        df['rsi'] = self.calculate_rsi(df['close'])
        
        # MACD
        df['macd'], df['macd_signal'], df['macd_diff'] = self.calculate_macd(df['close'])
        
        # Bollinger Bands
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = self.calculate_bollinger_bands(df['close'])
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Price changes
        df['price_change'] = df['close'].pct_change()
        df['price_change_5'] = df['close'].pct_change(periods=5)
        df['price_change_10'] = df['close'].pct_change(periods=10)
        
        # Volatility
        df['volatility'] = df['price_change'].rolling(window=20).std()
        
        # Support and Resistance levels
        df['resistance'] = df['high'].rolling(window=20).max()
        df['support'] = df['low'].rolling(window=20).min()
        
        return df
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_macd(
        self,
        prices: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD indicator"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        macd_diff = macd - macd_signal
        
        return macd, macd_signal, macd_diff
    
    def calculate_bollinger_bands(
        self,
        prices: pd.Series,
        period: int = 20,
        std_dev: int = 2
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    def save_to_database(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """Save collected data to database"""
        if df.empty:
            logger.warning(f"No data to save for {symbol}")
            return
        
        try:
            # Prepare data for database
            records = []
            for _, row in df.iterrows():
                records.append({
                    'symbol': symbol,
                    'timestamp': row['timestamp'],
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row['volume'],
                    'timeframe': timeframe
                })
            
            # Batch insert
            saved = self.db.save_market_data(records)
            logger.info(f"Saved {saved} records for {symbol} to database")
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
    
    def save_to_csv(self, df: pd.DataFrame, symbol: str, interval: str):
        """Save collected data to CSV file"""
        if df.empty:
            return
        
        # Create data directory if not exists
        os.makedirs('historical_data', exist_ok=True)
        
        # Save to CSV
        filename = f"historical_data/{symbol}_{interval}_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(filename, index=False)
        logger.info(f"Saved data to {filename}")
    
    def collect_all_symbols(self, days_back: int = 30):
        """Collect data for all configured symbols"""
        logger.info(f"Starting data collection for {len(self.symbols)} symbols")
        
        for symbol in self.symbols:
            for interval_key, interval_name in [('15', '15m'), ('60', '1h'), ('D', '1d')]:
                try:
                    # Collect raw data
                    df = self.collect_historical_data(symbol, interval_key, days_back)
                    
                    if not df.empty:
                        # Add indicators
                        df = self.add_technical_indicators(df)
                        
                        # Save to database
                        self.save_to_database(df, symbol, interval_name)
                        
                        # Save to CSV
                        self.save_to_csv(df, symbol, interval_name)
                    
                    # Rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error collecting {symbol} {interval_name}: {e}")
        
        logger.info("Data collection completed")
    
    def get_training_data(
        self,
        symbol: str,
        interval: str = '15m',
        lookback_days: int = 90
    ) -> pd.DataFrame:
        """Get processed data ready for ML training"""
        # Fetch from database
        market_data = self.db.get_latest_market_data(
            symbol=symbol,
            timeframe=interval,
            limit=lookback_days * 96  # 96 15-min candles per day
        )
        
        if not market_data:
            logger.warning(f"No data found for {symbol}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame([{
            'timestamp': d.timestamp,
            'open': d.open,
            'high': d.high,
            'low': d.low,
            'close': d.close,
            'volume': d.volume
        } for d in market_data])
        
        # Add indicators
        df = self.add_technical_indicators(df)
        
        # Add target variable (next candle direction)
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        
        # Remove NaN values
        df = df.dropna()
        
        return df
    
    async def collect_realtime_data(self):
        """Collect real-time data using WebSocket (when available)"""
        # This would connect to Bybit WebSocket for real-time data
        # Currently blocked by CloudFront, so using REST polling instead
        pass

def main():
    """Main function to run data collection"""
    collector = HistoricalDataCollector()
    
    # Collect historical data for all symbols
    collector.collect_all_symbols(days_back=90)
    
    # Get training data example
    training_data = collector.get_training_data('BTCUSDT', '15m')
    if not training_data.empty:
        logger.info(f"Training data shape: {training_data.shape}")
        logger.info(f"Features: {list(training_data.columns)}")

if __name__ == "__main__":
    main()