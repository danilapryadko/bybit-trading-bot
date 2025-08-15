-- init_postgres.sql
-- Инициализация базы данных для торгового бота

-- Создание основных таблиц

-- 1. Стратегии
CREATE TABLE IF NOT EXISTS strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'inactive',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Ордера
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    exchange_order_id VARCHAR(100) UNIQUE,
    strategy_id INTEGER REFERENCES strategies(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    quantity DECIMAL(20,8),
    price DECIMAL(20,8),
    filled_quantity DECIMAL(20,8) DEFAULT 0,
    average_price DECIMAL(20,8),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Сделки
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    exchange_trade_id VARCHAR(100) UNIQUE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(20,8),
    price DECIMAL(20,8),
    fee DECIMAL(20,8),
    fee_currency VARCHAR(10),
    realized_pnl DECIMAL(20,8),
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Позиции
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(20,8),
    entry_price DECIMAL(20,8),
    current_price DECIMAL(20,8),
    unrealized_pnl DECIMAL(20,8),
    realized_pnl DECIMAL(20,8),
    status VARCHAR(20),
    opened_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP WITH TIME ZONE
);

-- 5. Метрики производительности
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id),
    date DATE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    gross_profit DECIMAL(20,8) DEFAULT 0,
    gross_loss DECIMAL(20,8) DEFAULT 0,
    net_profit DECIMAL(20,8) DEFAULT 0,
    sharpe_ratio DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    win_rate DECIMAL(5,4),
    UNIQUE(strategy_id, date)
);

-- 6. Рыночные данные (свечи)
CREATE TABLE IF NOT EXISTS market_data (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    open DECIMAL(20,8),
    high DECIMAL(20,8),
    low DECIMAL(20,8),
    close DECIMAL(20,8),
    volume DECIMAL(20,8),
    trades_count INTEGER,
    PRIMARY KEY (symbol, timeframe, time)
);

-- 7. Баланс аккаунта
CREATE TABLE IF NOT EXISTS account_balance (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    asset VARCHAR(20) NOT NULL,
    free_balance DECIMAL(20,8),
    locked_balance DECIMAL(20,8),
    total_balance DECIMAL(20,8)
);

-- Индексы для производительности
CREATE INDEX idx_orders_strategy_status ON orders(strategy_id, status);
CREATE INDEX idx_orders_symbol_created ON orders(symbol, created_at DESC);
CREATE INDEX idx_trades_executed ON trades(executed_at DESC);
CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_performance_date ON performance_metrics(date DESC);
CREATE INDEX idx_market_data_symbol_time ON market_data(symbol, time DESC);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггеры для обновления updated_at
CREATE TRIGGER update_strategies_updated_at BEFORE UPDATE ON strategies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Вставка начальных данных
INSERT INTO strategies (name, type, parameters, status) VALUES
    ('RSI_Strategy', 'rsi', '{"period": 14, "oversold": 30, "overbought": 70}', 'inactive'),
    ('EMA_Strategy', 'ema', '{"short_period": 9, "long_period": 21}', 'inactive'),
    ('Adaptive_Strategy', 'adaptive', '{}', 'inactive'),
    ('Kaufman_Strategy', 'kaufman', '{"min_er": 0.3, "strong_er": 0.6}', 'inactive')
ON CONFLICT (name) DO NOTHING;
