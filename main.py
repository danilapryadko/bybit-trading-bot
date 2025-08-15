"""
Основной модуль торгового бота
Enhanced with full integration of all components
Priority: Reliability and error-free operation
"""

import asyncio
import time
import logging
import sys
import signal
from datetime import datetime
import os
from dotenv import load_dotenv
import argparse

# Import the integrated trading bot
from trading_bot import TradingBot as IntegratedTradingBot, TradingConfig

# Legacy imports for backward compatibility
from bybit_client import BybitClient
from strategies import RSIStrategy, EMAStrategy, CombinedStrategy, GridStrategy
from advanced_strategies import (
    AdaptiveStrategy, HalvingStrategy, ETFMomentumStrategy,
    CrashDetectionStrategy, DCAStrategy, WhaleFollowingStrategy
)
from kaufman_strategy import KaufmanAdaptiveStrategy

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TradingBot:
    """Основной класс торгового бота"""
    
    def __init__(self, strategy_name: str = 'combined', testnet: bool = True):
        load_dotenv()
        
        self.running = False
        self.client = BybitClient(testnet=testnet)
        self.symbol = os.getenv('SYMBOL', 'BTCUSDT')
        
        # Выбор стратегии
        self.strategy = self._create_strategy(strategy_name)
        
        # Интервал между проверками (в секундах)
        self.check_interval = 60  # 1 минута
        
        # Статистика
        self.start_time = None
        self.trades_count = 0
        self.wins = 0
        self.losses = 0
        self.total_pnl = 0.0
        
        logger.info(f"Trading bot initialized with {strategy_name} strategy")
        logger.info(f"Trading symbol: {self.symbol}")
        logger.info(f"Testnet mode: {testnet}")
    
    def _create_strategy(self, strategy_name: str):
        """Создать экземпляр стратегии"""
        strategies = {
            'rsi': RSIStrategy,
            'ema': EMAStrategy,
            'combined': CombinedStrategy,
            'grid': GridStrategy,
            # Новые продвинутые стратегии
            'adaptive': AdaptiveStrategy,
            'halving': HalvingStrategy,
            'etf': ETFMomentumStrategy,
            'crash': CrashDetectionStrategy,
            'dca': DCAStrategy,
            'whale': WhaleFollowingStrategy,
            'kaufman': KaufmanAdaptiveStrategy
        }
        
        if strategy_name not in strategies:
            logger.warning(f"Unknown strategy: {strategy_name}, using adaptive")
            strategy_name = 'adaptive'
        
        return strategies[strategy_name](self.client, self.symbol)
    
    def start(self):
        """Запустить бота"""
        self.running = True
        self.start_time = datetime.now()
        
        logger.info("Trading bot started")
        logger.info("Press Ctrl+C to stop")
        
        # Отобразить начальный баланс
        self._display_balance()
        
        try:
            while self.running:
                self._run_cycle()
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("Received stop signal")
            self.stop()
    
    def stop(self):
        """Остановить бота"""
        self.running = False
        
        logger.info("Stopping trading bot...")
        
        # Закрыть все открытые позиции
        self._close_all_positions()
        
        # Отменить все открытые ордера
        self.client.cancel_all_orders(self.symbol)
        
        # Отобразить финальную статистику
        self._display_statistics()
        
        logger.info("Trading bot stopped")
    
    def _run_cycle(self):
        """Выполнить один цикл торговли"""
        try:
            logger.info("-" * 50)
            logger.info(f"Running trading cycle at {datetime.now()}")
            
            # Выполнить стратегию
            self.strategy.execute()
            
            # Обновить статистику
            self._update_statistics()
            
            # Отобразить текущее состояние
            self._display_status()
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
    
    def _close_all_positions(self):
        """Закрыть все открытые позиции"""
        try:
            positions = self.client.get_positions()
            if positions:
                for position in positions:
                    if float(position['size']) > 0:
                        logger.info(f"Closing position: {position['symbol']}")
                        self.client.close_position(position['symbol'])
        except Exception as e:
            logger.error(f"Error closing positions: {e}")
    
    def _update_statistics(self):
        """Обновить статистику торговли"""
        try:
            # Получить историю ордеров
            orders = self.client.get_order_history(self.symbol, limit=100)
            if not orders:
                return
            
            # Подсчитать статистику
            for order in orders:
                if order['orderStatus'] == 'Filled':
                    self.trades_count += 1
                    
                    # Здесь можно добавить более детальный подсчет PnL
                    # на основе истории сделок
            
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
    
    def _display_balance(self):
        """Отобразить текущий баланс"""
        try:
            balance = self.client.get_account_balance()
            if balance and balance['retCode'] == 0:
                for coin in balance['result']['list'][0]['coin']:
                    if coin['coin'] == 'USDT':
                        logger.info(f"Balance: {coin['walletBalance']} USDT")
                        logger.info(f"Available: {coin['availableToWithdraw']} USDT")
        except Exception as e:
            logger.error(f"Error displaying balance: {e}")
    
    def _display_status(self):
        """Отобразить текущий статус"""
        try:
            # Получить информацию о позиции
            positions = self.client.get_positions(self.symbol)
            
            if positions and len(positions) > 0:
                position = positions[0]
                if float(position['size']) > 0:
                    logger.info(f"Position: {position['side']} {position['size']} @ {position['avgPrice']}")
                    logger.info(f"Unrealized PnL: {position['unrealisedPnl']} USDT")
                else:
                    logger.info("No open position")
            else:
                logger.info("No open position")
            
            # Отобразить текущую цену
            ticker = self.client.get_ticker(self.symbol)
            if ticker:
                logger.info(f"Current price: {ticker['lastPrice']}")
                logger.info(f"24h change: {ticker['price24hPcnt']}%")
            
        except Exception as e:
            logger.error(f"Error displaying status: {e}")
    
    def _display_statistics(self):
        """Отобразить финальную статистику"""
        if self.start_time:
            runtime = datetime.now() - self.start_time
            logger.info("\n" + "=" * 50)
            logger.info("TRADING STATISTICS")
            logger.info("=" * 50)
            logger.info(f"Runtime: {runtime}")
            logger.info(f"Total trades: {self.trades_count}")
            logger.info(f"Wins: {self.wins}")
            logger.info(f"Losses: {self.losses}")
            if self.trades_count > 0:
                win_rate = (self.wins / self.trades_count) * 100
                logger.info(f"Win rate: {win_rate:.2f}%")
            logger.info(f"Total PnL: {self.total_pnl:.2f} USDT")
            logger.info("=" * 50)


def main():
    """Главная функция с поддержкой нового интегрированного бота"""
    parser = argparse.ArgumentParser(description='Bybit Trading Bot - Enhanced Version')
    
    # Mode selection
    parser.add_argument(
        '--mode',
        type=str,
        default='integrated',
        choices=['integrated', 'legacy'],
        help='Bot mode: integrated (new) or legacy (old)'
    )
    
    # Legacy options
    parser.add_argument(
        '--strategy',
        type=str,
        default='adaptive',
        choices=['rsi', 'ema', 'combined', 'grid', 'adaptive', 'halving', 'etf', 'crash', 'dca', 'whale', 'kaufman'],
        help='Trading strategy to use (legacy mode)'
    )
    
    # Common options
    parser.add_argument(
        '--live',
        action='store_true',
        help='Use live trading (default is testnet)'
    )
    parser.add_argument(
        '--paper',
        action='store_true',
        help='Use paper trading mode (integrated mode only)'
    )
    parser.add_argument(
        '--symbols',
        type=str,
        nargs='+',
        default=['BTCUSDT'],
        help='Symbols to trade (integrated mode)'
    )
    parser.add_argument(
        '--balance',
        type=float,
        default=10000.0,
        help='Initial balance for trading'
    )
    parser.add_argument(
        '--risk',
        type=float,
        default=0.02,
        help='Risk per trade (2% default)'
    )
    parser.add_argument(
        '--ml',
        action='store_true',
        help='Enable ML strategies (integrated mode)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Check interval in seconds (legacy mode)'
    )
    
    args = parser.parse_args()
    
    # Проверить наличие API ключей
    load_dotenv()
    if not os.getenv('API_KEY') or not os.getenv('API_SECRET'):
        logger.error("API_KEY and API_SECRET must be set in .env file")
        logger.error("Copy .env.example to .env and add your API credentials")
        sys.exit(1)
    
    if args.mode == 'integrated':
        # Run new integrated bot
        logger.info("=" * 60)
        logger.info("STARTING INTEGRATED TRADING BOT")
        logger.info("Priority: RELIABILITY AND ERROR-FREE OPERATION")
        logger.info("=" * 60)
        
        # Create configuration
        config = TradingConfig(
            symbols=args.symbols,
            testnet=not args.live,
            paper_trading=args.paper or not args.live,  # Default to paper if testnet
            initial_balance=args.balance,
            risk_per_trade=args.risk,
            use_ml_strategies=args.ml,
            max_positions=min(3, len(args.symbols)),  # Max 3 or number of symbols
            use_trailing_stops=True,
            backtest_before_trade=args.ml,  # Backtest if using ML
        )
        
        # Run async bot
        async def run_integrated():
            bot = IntegratedTradingBot(config)
            try:
                await bot.start()
            except KeyboardInterrupt:
                logger.info("Shutting down gracefully...")
                await bot.stop()
        
        # Run the event loop
        try:
            asyncio.run(run_integrated())
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.critical(f"Fatal error: {e}")
            sys.exit(1)
    
    else:
        # Run legacy bot
        logger.info("Running in LEGACY mode")
        bot = TradingBot(
            strategy_name=args.strategy,
            testnet=not args.live
        )
        bot.check_interval = args.interval
        
        # Обработка сигнала остановки
        def signal_handler(sig, frame):
            logger.info("Received interrupt signal")
            bot.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Запустить бота
        bot.start()


if __name__ == "__main__":
    main()
