"""
Основной модуль торгового бота
"""

import time
import logging
import sys
import signal
from datetime import datetime
import os
from dotenv import load_dotenv
import argparse

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
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Bybit Trading Bot')
    parser.add_argument(
        '--strategy',
        type=str,
        default='adaptive',
        choices=['rsi', 'ema', 'combined', 'grid', 'adaptive', 'halving', 'etf', 'crash', 'dca', 'whale', 'kaufman'],
        help='Trading strategy to use'
    )
    parser.add_argument(
        '--live',
        action='store_true',
        help='Use live trading (default is testnet)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Check interval in seconds (default: 60)'
    )
    
    args = parser.parse_args()
    
    # Проверить наличие API ключей
    load_dotenv()
    if not os.getenv('API_KEY') or not os.getenv('API_SECRET'):
        logger.error("API_KEY and API_SECRET must be set in .env file")
        logger.error("Copy .env.example to .env and add your API credentials")
        sys.exit(1)
    
    # Создать и запустить бота
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
