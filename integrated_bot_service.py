#!/usr/bin/env python3
"""
Integrated Bot Service with Grid Trading and Safe Orders
Production-ready automated trading for Bybit
"""

import os
import sys
import asyncio
import logging
import signal
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
from dataclasses import dataclass, field

from pybit.unified_trading import HTTP
from strategies.safe_order_strategy import SafeOrderStrategy, SafeOrderConfig
from strategies.grid_trading import GridTradingStrategy, GridConfig, GridType, GridDirection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('integrated_bot.log')
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class BotConfig:
    """Main bot configuration"""
    # Trading pairs
    symbols: List[str] = field(default_factory=lambda: ["BTCUSDT"])
    
    # Strategy selection
    active_strategies: List[str] = field(default_factory=lambda: ["grid", "safe_order"])
    
    # Risk management
    max_positions: int = 3
    max_daily_loss: float = 500.0
    risk_per_trade: float = 0.02
    
    # Grid Trading config
    grid_enabled: bool = True
    grid_upper_price: float = 120000
    grid_lower_price: float = 110000
    grid_levels: int = 20
    grid_investment: float = 500.0
    
    # Safe Order config
    safe_order_enabled: bool = True
    safe_order_base_size: float = 50.0
    safe_order_safety_size: float = 100.0
    safe_order_max_orders: int = 5
    safe_order_take_profit: float = 2.0
    
    # System settings
    check_interval: int = 30  # seconds
    health_check_interval: int = 300  # 5 minutes


class IntegratedBotService:
    """Main bot service orchestrating multiple strategies"""
    
    def __init__(self, config: BotConfig = None):
        self.config = config or BotConfig()
        
        # Initialize Bybit client
        self.api_key = os.getenv('BYBIT_API_KEY')
        self.api_secret = os.getenv('BYBIT_API_SECRET')
        self.testnet = os.getenv('BYBIT_TESTNET', 'false').lower() == 'true'
        
        self.client = HTTP(
            testnet=self.testnet,
            api_key=self.api_key,
            api_secret=self.api_secret
        )
        
        # Initialize strategies
        self.strategies = {}
        self._initialize_strategies()
        
        # State tracking
        self.is_running = False
        self.positions = {}
        self.daily_pnl = 0.0
        self.start_time = datetime.now()
        self.last_health_check = datetime.now()
        
        logger.info(f"IntegratedBotService initialized - Mode: {'TESTNET' if self.testnet else 'MAINNET'}")
    
    def _initialize_strategies(self):
        """Initialize configured trading strategies"""
        
        # Initialize Grid Trading
        if self.config.grid_enabled and "grid" in self.config.active_strategies:
            for symbol in self.config.symbols:
                grid_config = GridConfig(
                    symbol=symbol,
                    grid_type=GridType.DYNAMIC,
                    direction=GridDirection.NEUTRAL,
                    upper_price=self.config.grid_upper_price,
                    lower_price=self.config.grid_lower_price,
                    grid_levels=self.config.grid_levels,
                    total_investment=self.config.grid_investment,
                    leverage=1.0,
                    volatility_adjustment=True,
                    auto_compound=True
                )
                
                grid_strategy = GridTradingStrategy(self.client, grid_config)
                self.strategies[f"grid_{symbol}"] = grid_strategy
                logger.info(f"Grid strategy initialized for {symbol}")
        
        # Initialize Safe Order (DCA)
        if self.config.safe_order_enabled and "safe_order" in self.config.active_strategies:
            for symbol in self.config.symbols:
                safe_config = SafeOrderConfig(
                    base_order_size=self.config.safe_order_base_size,
                    safety_order_size=self.config.safe_order_safety_size,
                    max_safety_orders=self.config.safe_order_max_orders,
                    take_profit=self.config.safe_order_take_profit,
                    use_grid=False  # Grid is separate strategy
                )
                
                safe_strategy = SafeOrderStrategy(self.client, symbol, safe_config)
                self.strategies[f"safe_order_{symbol}"] = safe_strategy
                logger.info(f"Safe Order strategy initialized for {symbol}")
    
    def get_account_info(self) -> Dict:
        """Get account balance and status"""
        try:
            account = self.client.get_wallet_balance(accountType="UNIFIED")
            if account['retCode'] == 0:
                return {
                    'balance': float(account['result']['list'][0]['totalEquity']),
                    'available': float(account['result']['list'][0]['availableBalance']),
                    'margin_used': float(account['result']['list'][0]['totalMarginBalance'])
                }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
        return {'balance': 0, 'available': 0, 'margin_used': 0}
    
    def get_market_data(self, symbol: str) -> Dict:
        """Get current market data for symbol"""
        try:
            # Get ticker
            ticker = self.client.get_tickers(
                category="linear",
                symbol=symbol
            )
            
            # Get recent klines for indicators
            klines = self.client.get_kline(
                category="linear",
                symbol=symbol,
                interval="15",
                limit=50
            )
            
            if ticker['retCode'] == 0 and klines['retCode'] == 0:
                prices = [float(k[4]) for k in klines['result']['list']]
                prices.reverse()
                
                # Calculate simple RSI
                rsi = self.calculate_rsi(prices)
                
                return {
                    'symbol': symbol,
                    'price': float(ticker['result']['list'][0]['lastPrice']),
                    'volume': float(ticker['result']['list'][0]['volume24h']),
                    'rsi': rsi,
                    'prices': prices
                }
                
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
        
        return None
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def check_risk_limits(self) -> bool:
        """Check if we're within risk limits"""
        # Check daily loss
        if self.daily_pnl <= -self.config.max_daily_loss:
            logger.warning(f"Daily loss limit reached: ${self.daily_pnl:.2f}")
            return False
        
        # Check open positions
        positions = self.client.get_positions(category="linear", settleCoin="USDT")
        if positions['retCode'] == 0:
            open_positions = [p for p in positions['result']['list'] if float(p.get('size', 0)) > 0]
            if len(open_positions) >= self.config.max_positions:
                logger.info(f"Max positions reached: {len(open_positions)}")
                return False
        
        return True
    
    async def execute_strategies(self):
        """Execute all active strategies"""
        for strategy_name, strategy in self.strategies.items():
            try:
                logger.debug(f"Executing {strategy_name}")
                
                # Get market data for strategy's symbol
                symbol = strategy.symbol if hasattr(strategy, 'symbol') else strategy.config.symbol
                market_data = self.get_market_data(symbol)
                
                if not market_data:
                    continue
                
                # Execute based on strategy type
                if "grid" in strategy_name:
                    await self.execute_grid_strategy(strategy, market_data)
                elif "safe_order" in strategy_name:
                    await self.execute_safe_order_strategy(strategy, market_data)
                
            except Exception as e:
                logger.error(f"Error executing {strategy_name}: {e}")
    
    async def execute_grid_strategy(self, strategy: GridTradingStrategy, market_data: Dict):
        """Execute grid trading strategy"""
        if not strategy.grid_active:
            # Initialize grid if not active
            logger.info("Initializing grid...")
            await strategy.initialize_grid()
            strategy.grid_active = True
        else:
            # Monitor and rebalance grid
            await strategy.monitor_grid()
            
            # Check if rebalance needed
            if datetime.now() - strategy.last_rebalance > strategy.config.rebalance_interval:
                logger.info("Rebalancing grid...")
                await strategy.rebalance_grid(market_data['price'])
    
    async def execute_safe_order_strategy(self, strategy: SafeOrderStrategy, market_data: Dict):
        """Execute safe order (DCA) strategy"""
        # Check existing orders status
        strategy.check_orders_status()
        
        # Check if we should open new position
        should_open, side, confidence = strategy.should_open_position(market_data)
        
        if should_open and confidence > 0.6 and self.check_risk_limits():
            logger.info(f"Opening {side} position for {strategy.symbol} (confidence: {confidence:.2f})")
            strategy.place_base_order(side, market_data['price'])
    
    async def health_check(self):
        """Perform system health check"""
        try:
            # Check API connection
            account = self.get_account_info()
            
            # Log status
            logger.info(f"Health Check - Balance: ${account['balance']:.2f}, "
                       f"Daily PnL: ${self.daily_pnl:.2f}, "
                       f"Uptime: {datetime.now() - self.start_time}")
            
            # Check each strategy
            for name, strategy in self.strategies.items():
                if hasattr(strategy, 'get_statistics'):
                    stats = strategy.get_statistics()
                    logger.info(f"{name} stats: {stats}")
            
            self.last_health_check = datetime.now()
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def trading_loop(self):
        """Main trading loop"""
        logger.info("Starting trading loop...")
        
        while self.is_running:
            try:
                # Check account status
                account = self.get_account_info()
                if account['balance'] < 100:
                    logger.error("Insufficient balance for trading")
                    break
                
                # Execute strategies
                await self.execute_strategies()
                
                # Health check
                if datetime.now() - self.last_health_check > timedelta(seconds=self.config.health_check_interval):
                    await self.health_check()
                
                # Wait before next iteration
                await asyncio.sleep(self.config.check_interval)
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(10)
    
    async def start(self):
        """Start the bot service"""
        logger.info("="*60)
        logger.info("STARTING INTEGRATED BOT SERVICE")
        logger.info(f"Mode: {'TESTNET' if self.testnet else 'MAINNET'}")
        logger.info(f"Symbols: {self.config.symbols}")
        logger.info(f"Active Strategies: {self.config.active_strategies}")
        logger.info("="*60)
        
        # Check initial balance
        account = self.get_account_info()
        logger.info(f"Starting balance: ${account['balance']:.2f}")
        
        if account['balance'] < 100:
            logger.error("Insufficient balance to start trading")
            return
        
        self.is_running = True
        
        try:
            await self.trading_loop()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot stopped due to error: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the bot service"""
        logger.info("Stopping bot service...")
        self.is_running = False
        
        # Log final statistics
        for name, strategy in self.strategies.items():
            if hasattr(strategy, 'get_statistics'):
                stats = strategy.get_statistics()
                logger.info(f"Final {name} stats: {stats}")
        
        logger.info(f"Final daily PnL: ${self.daily_pnl:.2f}")
        logger.info("Bot stopped")


async def main():
    """Main entry point"""
    # Load configuration
    config = BotConfig()
    
    # Override with environment variables if present
    if os.getenv('BOT_SYMBOLS'):
        config.symbols = os.getenv('BOT_SYMBOLS').split(',')
    if os.getenv('BOT_STRATEGIES'):
        config.active_strategies = os.getenv('BOT_STRATEGIES').split(',')
    
    # Create and start bot
    bot = IntegratedBotService(config)
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(bot.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    await bot.start()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🤖 INTEGRATED BYBIT BOT SERVICE")
    print("="*60)
    print("Features:")
    print("  ✅ Grid Trading")
    print("  ✅ Safe Orders (DCA)")
    print("  ✅ Risk Management")
    print("  ✅ Multi-Symbol Support")
    print("="*60)
    print("\nStarting in 5 seconds...")
    print("Press Ctrl+C to stop\n")
    
    import time
    time.sleep(5)
    
    asyncio.run(main())