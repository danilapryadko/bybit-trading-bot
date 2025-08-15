# 📋 ФАЗА 0: ДЕТАЛЬНАЯ ПРОРАБОТКА - ПОДГОТОВКА И ИССЛЕДОВАНИЕ

## 🎯 НЕДЕЛЯ 1: АНАЛИЗ И ПЛАНИРОВАНИЕ

### День 1-2: ОПРЕДЕЛЕНИЕ ТРЕБОВАНИЙ

#### 1. Финансовые параметры

**Торговый капитал:**
```yaml
Начальный капитал:
  - Тестовый: $100 (для проверки системы)
  - Минимальный: $1,000 
  - Оптимальный: $5,000
  - Целевой: $10,000-50,000

Распределение капитала:
  - Активная торговля: 60%
  - Резерв для усреднения: 30%
  - Страховой резерв: 10%
```

**Целевые метрики:**
```yaml
Доходность:
  - Минимальная: 5% в месяц
  - Целевая: 10-15% в месяц
  - При допустимой просадке: 15%

Risk/Reward:
  - Минимальное соотношение: 1:2
  - Целевое: 1:3
  - На сделку риск: 1-2% от депозита
```

#### 2. Выбор торговых пар

**Критерии отбора пар:**
```python
class PairSelectionCriteria:
    MIN_DAILY_VOLUME = 10_000_000  # $10M daily volume
    MIN_LIQUIDITY_SCORE = 0.8      # Based on order book depth
    MAX_SPREAD = 0.001              # 0.1% max spread
    MIN_EXCHANGE_LISTINGS = 5       # Listed on 5+ major exchanges
```

**Рекомендуемые пары для старта:**
```yaml
Tier 1 (Основные):
  - BTC/USDT - максимальная ликвидность
  - ETH/USDT - стабильная волатильность
  - BNB/USDT - предсказуемые паттерны

Tier 2 (Дополнительные):
  - SOL/USDT - высокая волатильность
  - MATIC/USDT - хорошие тренды
  - ARB/USDT - новые возможности
  - LINK/USDT - четкие уровни
  
Tier 3 (Экспериментальные):
  - INJ/USDT, OP/USDT, AVAX/USDT
  - Добавлять после 1 месяца стабильной работы
```

#### 3. Риск-менеджмент

**Лимиты рисков:**
```python
RISK_LIMITS = {
    # Position sizing
    "max_position_size_pct": 0.20,        # 20% от портфеля на позицию
    "max_correlated_exposure": 0.40,      # 40% в коррелированных активах
    
    # Drawdown limits
    "max_daily_drawdown": 0.05,           # 5% дневная просадка
    "max_weekly_drawdown": 0.10,          # 10% недельная
    "max_total_drawdown": 0.15,           # 15% максимальная
    
    # Trade limits
    "max_concurrent_positions": 5,         # Макс позиций одновременно
    "max_trades_per_day": 20,             # Макс сделок в день
    "max_leverage": 3,                     # Макс плечо (начать с 1x)
    
    # Time limits
    "max_position_duration_hours": 72,     # Макс время удержания
    "min_time_between_trades_min": 5,      # Мин время между входами
}
```

#### 4. Временные фреймы

**Стратегия по таймфреймам:**
```yaml
Анализ тренда:
  - 4H, 1D - определение глобального тренда
  - Использование: фильтр направления

Поиск входов:
  - 15M, 1H - основные сигналы
  - Использование: точки входа

Точный вход:
  - 1M, 5M - тайминг входа
  - Использование: минимизация проскальзывания

Данные для хранения:
  - 1M: последние 7 дней (10,080 свечей)
  - 5M: последние 30 дней (8,640 свечей)
  - 15M: последние 90 дней (8,640 свечей)
  - 1H: последние 365 дней (8,760 свечей)
  - 4H: последние 2 года (4,380 свечей)
  - 1D: вся история (∞)
```

---

### День 3-4: ИССЛЕДОВАНИЕ ИНФРАСТРУКТУРЫ

#### 1. Сравнение VPS провайдеров

| Провайдер | Цена/мес | CPU | RAM | SSD | Network | Локация | Плюсы | Минусы |
|-----------|----------|-----|-----|-----|---------|---------|-------|--------|
| **Hetzner CX31** | €5.83 | 2 vCPU | 8GB | 80GB | 20TB | Germany | Цена, надежность | Только EU |
| **DigitalOcean** | $48 | 2 vCPU | 8GB | 160GB | 5TB | Global | Простота, API | Дороже |
| **Contabo VPS M** | €8.99 | 6 vCPU | 16GB | 200GB | 32TB | EU/US | Ресурсы | Поддержка |
| **AWS t3.large** | $62 | 2 vCPU | 8GB | EBS | Pay-per-use | Global | Масштаб | Сложность, цена |
| **Vultr HF** | $48 | 2 vCPU | 8GB | 128GB | 5TB | Global | Производительность | Цена |

**Рекомендация:** 
```yaml
Для старта: Hetzner CX31 (€5.83/мес)
  - Отличное соотношение цена/качество
  - Низкий пинг до Bybit (EU серверы)
  - Легко масштабировать

Для production: Hetzner CX51 (€29/мес)
  - 8 vCPU, 32GB RAM
  - Подходит для 50+ торговых пар
  - NVMe диски для быстрой БД
```

#### 2. Выбор базы данных

**Сравнение Time-Series БД:**

| БД | Запись/сек | Сжатие | SQL | Плюсы | Минусы | Вердикт |
|----|------------|--------|-----|-------|--------|---------|
| **TimescaleDB** | 1.2M | 90% | ✅ | PostgreSQL совместимость, continuous aggregates | Сложнее настройка | ✅ Выбираем |
| **QuestDB** | 2.9M | 80% | ✅ | Максимальная скорость | Менее зрелая | Для HFT |
| **InfluxDB** | 800K | 85% | ❌ | Простота | InfluxQL, не SQL | Не подходит |
| **ClickHouse** | 2M | 95% | ✅ | Аналитика | Сложность | Overkill |

**Решение:**
```sql
-- TimescaleDB для основных данных
-- Структура оптимальная для нашего кейса
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE market_data (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    open DECIMAL(20,8),
    high DECIMAL(20,8),
    low DECIMAL(20,8),
    close DECIMAL(20,8),
    volume DECIMAL(20,8),
    trades_count INT,
    UNIQUE(symbol, timeframe, time)
);

SELECT create_hypertable('market_data', 'time');

-- Автоматическое сжатие через 7 дней
ALTER TABLE market_data SET (
    timescaledb.compress,
    timescaledb.compress_after = '7 days'
);
```

#### 3. Стек мониторинга

**Варианты:**

| Стек | Сложность | Возможности | Стоимость | Решение |
|------|-----------|-------------|-----------|---------|
| **Prometheus + Grafana** | Средняя | Метрики, алерты | Бесплатно | ✅ Основной выбор |
| **ELK Stack** | Высокая | Логи, поиск | Ресурсоемкий | Для логов |
| **Datadog** | Низкая | Все в одном | $15/host | Дорого |
| **New Relic** | Низкая | APM, трейсинг | $100/мес | Избыточно |

**Решение:**
```yaml
Мониторинг стек:
  Метрики: Prometheus + Grafana
  Логи: Loki (легче чем ELK)
  Трейсинг: Jaeger (при необходимости)
  Алерты: AlertManager -> Telegram
  
Преимущества:
  - Полностью self-hosted
  - Бесплатно
  - Гибкая настройка
  - Интеграция с Kubernetes
```

#### 4. Детальное изучение Bybit API v5

**Ключевые эндпоинты:**

```python
BYBIT_ENDPOINTS = {
    # Market Data (Public)
    "klines": "/v5/market/kline",           # Исторические свечи
    "tickers": "/v5/market/tickers",        # Текущие цены
    "orderbook": "/v5/market/orderbook",    # Стакан
    "trades": "/v5/market/recent-trade",    # Последние сделки
    
    # Account (Private)
    "balance": "/v5/account/wallet-balance", # Баланс
    "positions": "/v5/position/list",        # Позиции
    
    # Orders (Private)
    "place_order": "/v5/order/create",      # Создать ордер
    "cancel_order": "/v5/order/cancel",     # Отменить
    "order_history": "/v5/order/history",   # История
    
    # WebSocket Streams
    "ws_public": "wss://stream.bybit.com/v5/public/spot",
    "ws_private": "wss://stream.bybit.com/v5/private"
}

RATE_LIMITS = {
    "order_endpoints": "10 req/sec",
    "non_order_endpoints": "120 req/min",
    "websocket_connections": "20 connections",
    "websocket_subs_per_conn": "60 subscriptions"
}
```

---

### День 5-7: АРХИТЕКТУРНОЕ ПРОЕКТИРОВАНИЕ

#### 1. Микросервисная архитектура

```mermaid
graph TB
    subgraph "Data Layer"
        MD[Market Data Service]
        WS[WebSocket Manager]
    end
    
    subgraph "Core Services"
        SE[Strategy Engine]
        OMS[Order Management]
        RM[Risk Manager]
        PM[Portfolio Manager]
    end
    
    subgraph "Storage"
        TS[(TimescaleDB)]
        RD[(Redis)]
        PG[(PostgreSQL)]
    end
    
    subgraph "Message Bus"
        KF[Kafka]
        RMQ[RabbitMQ]
    end
    
    subgraph "API Layer"
        GW[API Gateway]
        REST[REST API]
        WSS[WebSocket Server]
    end
    
    subgraph "Frontend"
        UI[React Dashboard]
        MB[Mobile App]
    end
    
    WS --> MD
    MD --> KF
    KF --> SE
    SE --> RM
    RM --> OMS
    OMS --> RMQ
    
    MD --> TS
    SE --> RD
    OMS --> PG
    
    GW --> REST
    REST --> PM
    WSS --> UI
```

#### 2. Схема базы данных

```sql
-- Основные таблицы

-- 1. Strategies
CREATE TABLE strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    parameters JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'inactive',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Orders
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exchange_order_id VARCHAR(100) UNIQUE,
    strategy_id UUID REFERENCES strategies(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    quantity DECIMAL(20,8),
    price DECIMAL(20,8),
    filled_quantity DECIMAL(20,8) DEFAULT 0,
    average_price DECIMAL(20,8),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Trades
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id),
    exchange_trade_id VARCHAR(100) UNIQUE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(20,8),
    price DECIMAL(20,8),
    fee DECIMAL(20,8),
    fee_currency VARCHAR(10),
    realized_pnl DECIMAL(20,8),
    executed_at TIMESTAMPTZ
);

-- 4. Positions
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID REFERENCES strategies(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(20,8),
    entry_price DECIMAL(20,8),
    current_price DECIMAL(20,8),
    unrealized_pnl DECIMAL(20,8),
    realized_pnl DECIMAL(20,8),
    status VARCHAR(20),
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    UNIQUE(strategy_id, symbol, status)
);

-- 5. Performance metrics
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID REFERENCES strategies(id),
    date DATE NOT NULL,
    total_trades INT DEFAULT 0,
    winning_trades INT DEFAULT 0,
    losing_trades INT DEFAULT 0,
    gross_profit DECIMAL(20,8) DEFAULT 0,
    gross_loss DECIMAL(20,8) DEFAULT 0,
    net_profit DECIMAL(20,8) DEFAULT 0,
    sharpe_ratio DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    win_rate DECIMAL(5,4),
    UNIQUE(strategy_id, date)
);

-- Индексы для производительности
CREATE INDEX idx_orders_strategy_status ON orders(strategy_id, status);
CREATE INDEX idx_orders_symbol_created ON orders(symbol, created_at DESC);
CREATE INDEX idx_trades_executed ON trades(executed_at DESC);
CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_performance_date ON performance_metrics(date DESC);
```

#### 3. API Endpoints проектирование

```yaml
# REST API Structure
API Version: v1
Base URL: https://api.trading-bot.com/v1

Authentication:
  Type: JWT Bearer Token
  Header: Authorization: Bearer <token>

Endpoints:

# Portfolio
GET    /portfolio                    # Общая информация о портфеле
GET    /portfolio/balance            # Текущий баланс
GET    /portfolio/performance        # Метрики производительности
GET    /portfolio/history           # История изменений

# Positions  
GET    /positions                    # Список активных позиций
GET    /positions/{id}              # Детали позиции
POST   /positions/{id}/close        # Закрыть позицию
GET    /positions/history           # История позиций

# Orders
GET    /orders                       # Список ордеров
GET    /orders/{id}                 # Детали ордера
POST   /orders                      # Создать ордер
PUT    /orders/{id}                 # Изменить ордер
DELETE /orders/{id}                 # Отменить ордер

# Strategies
GET    /strategies                   # Список стратегий
GET    /strategies/{id}             # Детали стратегии
POST   /strategies                  # Создать стратегию
PUT    /strategies/{id}             # Обновить параметры
POST   /strategies/{id}/activate    # Активировать
POST   /strategies/{id}/deactivate  # Деактивировать
GET    /strategies/{id}/performance # Производительность стратегии

# Market Data
GET    /market/symbols               # Доступные символы
GET    /market/klines               # Исторические свечи
GET    /market/ticker               # Текущие цены
GET    /market/orderbook            # Стакан

# Backtesting
POST   /backtest                    # Запустить бэктест
GET    /backtest/{job_id}          # Статус бэктеста
GET    /backtest/{job_id}/results  # Результаты

# System
GET    /system/health               # Health check
GET    /system/metrics             # Prometheus metrics
GET    /system/status              # Статус системы
```

#### 4. Схема потоков данных

```python
# Data Flow Architecture

class DataFlow:
    """
    1. Market Data Flow:
    Exchange -> WebSocket -> Parser -> Normalizer -> Kafka -> 
    -> Strategy Engine -> Signal Generator -> Risk Check -> 
    -> Order Manager -> Exchange
    
    2. Order Execution Flow:
    Signal -> Risk Manager -> Position Sizer -> Order Creator ->
    -> Pre-Trade Checks -> Exchange API -> Order Confirmation ->
    -> Position Tracker -> P&L Calculator -> Performance Metrics
    
    3. Monitoring Flow:
    All Services -> Metrics Collector -> Prometheus -> 
    -> Grafana Dashboards -> AlertManager -> Notifications
    """
    
    FLOW_DIAGRAM = """
    Market Data Pipeline:
    ┌─────────────┐
    │   Bybit     │
    │  WebSocket  │
    └──────┬──────┘
           │ Raw ticks/candles
           ▼
    ┌─────────────┐
    │   Parser    │
    │ Normalizer  │
    └──────┬──────┘
           │ Structured data
           ▼
    ┌─────────────┐
    │    Kafka    │◄──── Backpressure handling
    │   Topics    │
    └──────┬──────┘
           │ Events
           ├────────────┬────────────┬─────────────┐
           ▼            ▼            ▼             ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ Strategy │ │   Risk   │ │   Data   │ │ Monitor  │
    │  Engine  │ │  Manager │ │  Storage │ │  Service │
    └──────────┘ └──────────┘ └──────────┘ └──────────┘
    """
```

---

## 🎯 НЕДЕЛЯ 2: НАСТРОЙКА ОКРУЖЕНИЯ

### День 8-9: НАСТРОЙКА РАЗРАБОТЧЕСКОГО ОКРУЖЕНИЯ

#### 1. Создание структуры проекта

```bash
#!/bin/bash
# setup_project.sh

# Создание основной структуры
mkdir -p bybit-trading-bot-pro
cd bybit-trading-bot-pro

# Создание директорий
mkdir -p {services,libs,tests,docs,configs,scripts,deploy,data}
mkdir -p services/{market_data,order_manager,strategy_engine,risk_manager,api_gateway,backtest}
mkdir -p libs/{indicators,strategies,utils,models,database}
mkdir -p tests/{unit,integration,e2e}
mkdir -p configs/{development,staging,production}
mkdir -p deploy/{docker,kubernetes,terraform}
mkdir -p docs/{api,architecture,strategies}
mkdir -p scripts/{setup,migration,monitoring}
mkdir -p data/{historical,backtest_results,logs}

# Создание основных файлов
touch README.md
touch .env.example
touch .gitignore
touch docker-compose.yml
touch Makefile
touch pyproject.toml
touch setup.py
touch requirements.txt
touch requirements-dev.txt

# Создание .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Project specific
.env
*.log
data/historical/*
data/backtest_results/*
!data/historical/.gitkeep
!data/backtest_results/.gitkeep

# Testing
.coverage
htmlcov/
.pytest_cache/
.tox/

# Docker
*.pid
docker-compose.override.yml

# Secrets
*.pem
*.key
secrets/
EOF

# Создание .env.example
cat > .env.example << 'EOF'
# Environment
ENVIRONMENT=development

# Bybit API
BYBIT_API_KEY=
BYBIT_API_SECRET=
BYBIT_TESTNET=true

# Database
DATABASE_URL=postgresql://trader:password@localhost:5432/trading_bot
TIMESCALE_URL=postgresql://trader:password@localhost:5433/market_data
REDIS_URL=redis://localhost:6379

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# Trading Parameters
INITIAL_CAPITAL=1000
MAX_POSITIONS=5
MAX_POSITION_SIZE=0.2
MAX_DAILY_DRAWDOWN=0.05
MAX_TOTAL_DRAWDOWN=0.15

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
```

#### 2. Poetry настройка

```toml
# pyproject.toml
[tool.poetry]
name = "bybit-trading-bot-pro"
version = "1.0.0"
description = "Professional cryptocurrency trading bot for Bybit"
authors = ["Your Name <your.email@example.com>"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
asyncpg = "^0.29.0"
redis = "^5.0.0"
aiohttp = "^3.9.0"
pandas = "^2.1.0"
numpy = "^1.26.0"
pybit = "^5.6.0"
websockets = "^12.0"
pydantic = "^2.5.0"
sqlalchemy = "^2.0.0"
alembic = "^1.13.0"
asyncio-mqtt = "^0.16.0"
aiokafka = "^0.10.0"
prometheus-client = "^0.19.0"
structlog = "^23.2.0"
python-json-logger = "^2.0.0"
orjson = "^3.9.0"
httpx = "^0.25.0"
typer = "^0.9.0"
rich = "^13.7.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
black = "^23.12.0"
ruff = "^0.1.0"
mypy = "^1.7.0"
ipython = "^8.18.0"
jupyter = "^1.0.0"
pre-commit = "^3.6.0"

[tool.poetry.group.analysis.dependencies]
ta = "^0.11.0"
ta-lib = "^0.4.28"
scipy = "^1.11.0"
scikit-learn = "^1.3.0"
statsmodels = "^0.14.0"
vectorbt = "^0.26.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### День 10-11: НАСТРОЙКА GIT И CI/CD

#### 1. GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: timescale/timescaledb:latest-pg14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
      with:
        version: latest
        virtualenvs-create: true
        virtualenvs-in-project: true
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: .venv
        key: venv-${{ runner.os }}-${{ hashFiles('**/poetry.lock') }}
    
    - name: Install dependencies
      run: poetry install --no-interaction --no-root
    
    - name: Run linting
      run: |
        poetry run ruff check .
        poetry run black --check .
        poetry run mypy .
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379
      run: |
        poetry run pytest --cov=. --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'

  build:
    needs: [test, security]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Login to DockerHub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_TOKEN }}
    
    - name: Build and push
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: ${{ secrets.DOCKER_USERNAME }}/trading-bot:latest
        cache-from: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/trading-bot:buildcache
        cache-to: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/trading-bot:buildcache,mode=max
```

### День 12-14: DOCKER И ЛОКАЛЬНОЕ ОКРУЖЕНИЕ

#### 1. Docker Compose для разработки

```yaml
# docker-compose.yml
version: '3.9'

services:
  # TimescaleDB для market data
  timescaledb:
    image: timescale/timescaledb:latest-pg14
    container_name: trading_timescaledb
    environment:
      POSTGRES_DB: market_data
      POSTGRES_USER: trader
      POSTGRES_PASSWORD: ${DB_PASSWORD:-password}
    ports:
      - "5433:5432"
    volumes:
      - timescale_data:/var/lib/postgresql/data
      - ./scripts/init_timescale.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U trader"]
      interval: 10s
      timeout: 5s
      retries: 5

  # PostgreSQL для application data
  postgres:
    image: postgres:14-alpine
    container_name: trading_postgres
    environment:
      POSTGRES_DB: trading_bot
      POSTGRES_USER: trader
      POSTGRES_PASSWORD: ${DB_PASSWORD:-password}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_postgres.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U trader"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis для caching и pub/sub
  redis:
    image: redis:7-alpine
    container_name: trading_redis
    command: redis-server --appendonly yes
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Kafka для event streaming
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    container_name: trading_zookeeper
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    container_name: trading_kafka
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: 'true'

  # Prometheus для метрик
  prometheus:
    image: prom/prometheus:latest
    container_name: trading_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./configs/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  # Grafana для визуализации
  grafana:
    image: grafana/grafana:latest
    container_name: trading_grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
      GF_INSTALL_PLUGINS: grafana-clock-panel
    volumes:
      - grafana_data:/var/lib/grafana
      - ./configs/grafana/provisioning:/etc/grafana/provisioning
    depends_on:
      - prometheus

  # Loki для логов
  loki:
    image: grafana/loki:latest
    container_name: trading_loki
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml
    volumes:
      - ./configs/loki/loki-config.yml:/etc/loki/local-config.yaml
      - loki_data:/loki

  # Promtail для сбора логов
  promtail:
    image: grafana/promtail:latest
    container_name: trading_promtail
    volumes:
      - ./configs/promtail/promtail-config.yml:/etc/promtail/config.yml
      - /var/log:/var/log
    command: -config.file=/etc/promtail/config.yml

volumes:
  postgres_data:
  timescale_data:
  redis_data:
  prometheus_data:
  grafana_data:
  loki_data:
```

#### 2. Makefile для автоматизации

```makefile
# Makefile

.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: install
install: ## Install dependencies
	poetry install

.PHONY: dev
dev: ## Start development environment
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 10
	poetry run python scripts/check_services.py

.PHONY: stop
stop: ## Stop development environment
	docker-compose down

.PHONY: clean
clean: ## Clean development environment
	docker-compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

.PHONY: test
test: ## Run tests
	poetry run pytest tests/

.PHONY: test-coverage
test-coverage: ## Run tests with coverage
	poetry run pytest --cov=. --cov-report=html tests/

.PHONY: lint
lint: ## Run linters
	poetry run ruff check .
	poetry run black --check .
	poetry run mypy .

.PHONY: format
format: ## Format code
	poetry run black .
	poetry run ruff check --fix .

.PHONY: migrate
migrate: ## Run database migrations
	poetry run alembic upgrade head

.PHONY: migrate-create
migrate-create: ## Create new migration
	@read -p "Enter migration message: " msg; \
	poetry run alembic revision --autogenerate -m "$$msg"

.PHONY: backtest
backtest: ## Run backtest
	poetry run python -m services.backtest.cli

.PHONY: start-market-data
start-market-data: ## Start market data service
	poetry run python -m services.market_data.main

.PHONY: start-strategy-engine
start-strategy-engine: ## Start strategy engine
	poetry run python -m services.strategy_engine.main

.PHONY: start-api
start-api: ## Start API server
	poetry run uvicorn services.api_gateway.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: monitoring
monitoring: ## Open monitoring dashboards
	@echo "Opening monitoring dashboards..."
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3000 (admin/admin)"
	@open http://localhost:3000 || xdg-open http://localhost:3000

.PHONY: logs
logs: ## Show logs
	docker-compose logs -f

.PHONY: shell
shell: ## Open Python shell with project context
	poetry run ipython -i scripts/shell_context.py

.PHONY: build
build: ## Build Docker images
	docker build -t trading-bot:latest .

.PHONY: deploy
deploy: ## Deploy to production
	./scripts/deploy.sh

.PHONY: docs
docs: ## Generate documentation
	poetry run mkdocs build

.PHONY: docs-serve
docs-serve: ## Serve documentation locally
	poetry run mkdocs serve
```

---

## 📋 ЧЕКЛИСТ ЗАВЕРШЕНИЯ ФАЗЫ 0

### ✅ Неделя 1: Анализ и планирование
- [ ] Определены финансовые параметры (капитал, риски, цели)
- [ ] Выбраны торговые пары (3 основные + резервные)
- [ ] Настроены лимиты рисков (drawdown, позиции, leverage)
- [ ] Определены временные фреймы для каждого типа анализа
- [ ] Выбран VPS провайдер (Hetzner CX31 для старта)
- [ ] Выбрана база данных (TimescaleDB)
- [ ] Определен стек мониторинга (Prometheus + Grafana)
- [ ] Изучена документация Bybit API v5
- [ ] Создана архитектурная диаграмма
- [ ] Спроектирована схема БД
- [ ] Определены API endpoints
- [ ] Создана схема потоков данных

### ✅ Неделя 2: Настройка окружения
- [ ] Создана структура проекта
- [ ] Настроен Poetry с зависимостями
- [ ] Инициализирован Git репозиторий
- [ ] Настроен GitHub/GitLab
- [ ] Создан CI/CD pipeline
- [ ] Настроен Docker Compose
- [ ] Создан Makefile
- [ ] Запущены все сервисы локально
- [ ] Проверена работа всех компонентов

---

## 🎯 РЕЗУЛЬТАТЫ ФАЗЫ 0

После завершения Фазы 0 у вас будет:

1. **Четкое понимание**:
   - Сколько инвестировать
   - Какие пары торговать
   - Какие риски допустимы
   - Какая инфраструктура нужна

2. **Готовая инфраструктура**:
   - Настроенное окружение разработки
   - Работающие базы данных
   - Система мониторинга
   - CI/CD pipeline

3. **Документация**:
   - Архитектурные диаграммы
   - Схемы БД
   - API спецификация
   - README с инструкциями

4. **Готовность к разработке**:
   - Все зависимости установлены
   - Тесты настроены
   - Линтеры работают
   - Docker окружение запущено

---

## 🚀 ПЕРЕХОД К ФАЗЕ 1

После успешного завершения Фазы 0, вы готовы к Фазе 1:
- Market Data Service
- Order Management System  
- Risk Manager

Все основы заложены, можно начинать кодирование!
