"""
Database manager for trading bot
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер базы данных для торгового бота"""
    
    def __init__(self):
        """Инициализация подключения к БД"""
        self.db_url = os.getenv('DATABASE_URL', 'postgresql://trader:password@localhost:5432/trading_bot')
        self.pool = None
        self.connect()
    
    def connect(self):
        """Создание пула соединений с БД"""
        try:
            self.pool = SimpleConnectionPool(1, 20, self.db_url)
            logger.info("Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    
    def get_connection(self):
        """Получить соединение из пула"""
        return self.pool.getconn()
    
    def put_connection(self, conn):
        """Вернуть соединение в пул"""
        self.pool.putconn(conn)
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Выполнить SELECT запрос"""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        finally:
            self.put_connection(conn)
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """Выполнить INSERT/UPDATE/DELETE запрос"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            conn.rollback()
            logger.error(f"Database update failed: {e}")
            raise
        finally:
            self.put_connection(conn)
    
    # === Методы для работы с ордерами ===
    
    def save_order(self, order_data: Dict) -> int:
        """Сохранить ордер в БД"""
        query = """
            INSERT INTO orders (
                exchange_order_id, strategy_id, symbol, side, order_type,
                status, quantity, price, filled_quantity, average_price
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, (
                    order_data.get('exchange_order_id'),
                    order_data.get('strategy_id'),
                    order_data.get('symbol'),
                    order_data.get('side'),
                    order_data.get('order_type', 'MARKET'),
                    order_data.get('status'),
                    order_data.get('quantity'),
                    order_data.get('price'),
                    order_data.get('filled_quantity', 0),
                    order_data.get('average_price')
                ))
                conn.commit()
                return cursor.fetchone()[0]
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save order: {e}")
            raise
        finally:
            self.put_connection(conn)
    
    def update_order_status(self, order_id: str, status: str, filled_qty: float = None):
        """Обновить статус ордера"""
        query = """
            UPDATE orders 
            SET status = %s, filled_quantity = COALESCE(%s, filled_quantity)
            WHERE exchange_order_id = %s
        """
        self.execute_update(query, (status, filled_qty, order_id))
    
    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """Получить открытые ордера"""
        if symbol:
            query = "SELECT * FROM orders WHERE status IN ('NEW', 'PARTIALLY_FILLED') AND symbol = %s"
            return self.execute_query(query, (symbol,))
        else:
            query = "SELECT * FROM orders WHERE status IN ('NEW', 'PARTIALLY_FILLED')"
            return self.execute_query(query)
    
    # === Методы для работы с позициями ===
    
    def save_position(self, position_data: Dict) -> int:
        """Сохранить позицию в БД"""
        query = """
            INSERT INTO positions (
                strategy_id, symbol, side, quantity, entry_price,
                current_price, unrealized_pnl, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, (
                    position_data.get('strategy_id'),
                    position_data.get('symbol'),
                    position_data.get('side'),
                    position_data.get('quantity'),
                    position_data.get('entry_price'),
                    position_data.get('current_price'),
                    position_data.get('unrealized_pnl', 0),
                    'OPEN'
                ))
                conn.commit()
                return cursor.fetchone()[0]
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save position: {e}")
            raise
        finally:
            self.put_connection(conn)
    
    def update_position(self, position_id: int, current_price: float, unrealized_pnl: float):
        """Обновить текущую цену и PnL позиции"""
        query = """
            UPDATE positions 
            SET current_price = %s, unrealized_pnl = %s
            WHERE id = %s AND status = 'OPEN'
        """
        self.execute_update(query, (current_price, unrealized_pnl, position_id))
    
    def close_position(self, position_id: int, realized_pnl: float):
        """Закрыть позицию"""
        query = """
            UPDATE positions 
            SET status = 'CLOSED', realized_pnl = %s, closed_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        self.execute_update(query, (realized_pnl, position_id))
    
    def get_open_positions(self, symbol: str = None) -> List[Dict]:
        """Получить открытые позиции"""
        if symbol:
            query = "SELECT * FROM positions WHERE status = 'OPEN' AND symbol = %s"
            return self.execute_query(query, (symbol,))
        else:
            query = "SELECT * FROM positions WHERE status = 'OPEN'"
            return self.execute_query(query)
    
    # === Методы для работы со сделками ===
    
    def save_trade(self, trade_data: Dict) -> int:
        """Сохранить сделку в БД"""
        query = """
            INSERT INTO trades (
                order_id, exchange_trade_id, symbol, side, quantity,
                price, fee, fee_currency, realized_pnl
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, (
                    trade_data.get('order_id'),
                    trade_data.get('exchange_trade_id'),
                    trade_data.get('symbol'),
                    trade_data.get('side'),
                    trade_data.get('quantity'),
                    trade_data.get('price'),
                    trade_data.get('fee', 0),
                    trade_data.get('fee_currency', 'USDT'),
                    trade_data.get('realized_pnl', 0)
                ))
                conn.commit()
                return cursor.fetchone()[0]
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save trade: {e}")
            raise
        finally:
            self.put_connection(conn)
    
    # === Методы для работы с метриками ===
    
    def save_performance_metrics(self, strategy_id: int, metrics: Dict):
        """Сохранить метрики производительности"""
        query = """
            INSERT INTO performance_metrics (
                strategy_id, date, total_trades, winning_trades, losing_trades,
                gross_profit, gross_loss, net_profit, sharpe_ratio, max_drawdown, win_rate
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (strategy_id, date) DO UPDATE SET
                total_trades = EXCLUDED.total_trades,
                winning_trades = EXCLUDED.winning_trades,
                losing_trades = EXCLUDED.losing_trades,
                gross_profit = EXCLUDED.gross_profit,
                gross_loss = EXCLUDED.gross_loss,
                net_profit = EXCLUDED.net_profit,
                sharpe_ratio = EXCLUDED.sharpe_ratio,
                max_drawdown = EXCLUDED.max_drawdown,
                win_rate = EXCLUDED.win_rate
        """
        self.execute_update(query, (
            strategy_id,
            datetime.now().date(),
            metrics.get('total_trades', 0),
            metrics.get('winning_trades', 0),
            metrics.get('losing_trades', 0),
            metrics.get('gross_profit', 0),
            metrics.get('gross_loss', 0),
            metrics.get('net_profit', 0),
            metrics.get('sharpe_ratio'),
            metrics.get('max_drawdown'),
            metrics.get('win_rate')
        ))
    
    def get_performance_metrics(self, strategy_id: int, days: int = 30) -> List[Dict]:
        """Получить метрики производительности за период"""
        query = """
            SELECT * FROM performance_metrics 
            WHERE strategy_id = %s AND date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY date DESC
        """
        return self.execute_query(query, (strategy_id, days))
    
    # === Методы для работы с рыночными данными ===
    
    def save_market_data(self, candles: List[Dict]):
        """Сохранить свечи в БД"""
        query = """
            INSERT INTO market_data (
                time, symbol, timeframe, open, high, low, close, volume, trades_count
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, timeframe, time) DO NOTHING
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                for candle in candles:
                    cursor.execute(query, (
                        candle['time'],
                        candle['symbol'],
                        candle['timeframe'],
                        candle['open'],
                        candle['high'],
                        candle['low'],
                        candle['close'],
                        candle['volume'],
                        candle.get('trades_count', 0)
                    ))
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save market data: {e}")
            raise
        finally:
            self.put_connection(conn)
    
    def get_latest_candles(self, symbol: str, timeframe: str, limit: int = 100) -> List[Dict]:
        """Получить последние свечи"""
        query = """
            SELECT * FROM market_data 
            WHERE symbol = %s AND timeframe = %s
            ORDER BY time DESC
            LIMIT %s
        """
        return self.execute_query(query, (symbol, timeframe, limit))
    
    # === Методы для работы с балансом ===
    
    def save_balance(self, balances: Dict):
        """Сохранить баланс аккаунта"""
        query = """
            INSERT INTO account_balance (
                asset, free_balance, locked_balance, total_balance
            ) VALUES (%s, %s, %s, %s)
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                for asset, balance in balances.items():
                    cursor.execute(query, (
                        asset,
                        balance.get('free', 0),
                        balance.get('locked', 0),
                        balance.get('total', 0)
                    ))
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save balance: {e}")
            raise
        finally:
            self.put_connection(conn)
    
    def get_latest_balance(self, asset: str = 'USDT') -> Dict:
        """Получить последний баланс"""
        query = """
            SELECT * FROM account_balance 
            WHERE asset = %s
            ORDER BY timestamp DESC
            LIMIT 1
        """
        result = self.execute_query(query, (asset,))
        return result[0] if result else None
    
    def close(self):
        """Закрыть все соединения"""
        if self.pool:
            self.pool.closeall()
            logger.info("Database connection pool closed")


# Тестирование при запуске модуля
if __name__ == "__main__":
    db = DatabaseManager()
    
    # Проверка подключения
    try:
        # Получить список стратегий
        strategies = db.execute_query("SELECT * FROM strategies")
        print(f"Found {len(strategies)} strategies")
        for strategy in strategies:
            print(f"  - {strategy['name']}: {strategy['status']}")
        
        # Получить открытые позиции
        positions = db.get_open_positions()
        print(f"\nOpen positions: {len(positions)}")
        
        print("\nDatabase connection successful!")
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        db.close()
