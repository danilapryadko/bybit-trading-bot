# 🤖 Bybit Trading Bot

[![CI/CD Pipeline](https://github.com/danilapryadko/bbBot/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/danilapryadko/bbBot/actions/workflows/ci-cd.yml)
[![Health Check](https://github.com/danilapryadko/bbBot/actions/workflows/health-check.yml/badge.svg)](https://github.com/danilapryadko/bbBot/actions/workflows/health-check.yml)
[![Deployed on Fly.io](https://img.shields.io/badge/Deployed%20on-Fly.io-purple)](https://bybit-trading-bot.fly.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automated cryptocurrency trading bot for Bybit exchange with advanced strategies, risk management, and cloud deployment.

## ⭐ Key Features

### 🎯 Priority: Reliability & Safety
- **Paper Trading Mode**: Test strategies without real money
- **Comprehensive Error Handling**: Auto-recovery and reconnection
- **Risk Management V2**: Kelly Criterion, VaR, trailing stops
- **Daily Loss Limits**: Automatic trading halt on max loss
- **Multi-layer Safety**: Position limits, correlation checks, drawdown protection

### 🤖 Advanced Trading
- **Real-time WebSocket**: Low-latency market data streaming
- **Smart Order Routing**: Iceberg orders, order splitting
- **ML Strategies**: LSTM, Random Forest, XGBoost ensemble
- **Backtesting Engine**: Historical simulation with Monte Carlo
- **100+ Indicators**: Complete technical analysis toolkit

### 📊 New in v2.0
- ✅ Full integration of all components
- ✅ Async architecture for better performance
- ✅ Machine learning predictions
- ✅ Advanced risk management
- ✅ Paper trading mode
- ✅ Multi-symbol support

## 🚀 Live Status

- 🟢 **Production**: [https://bybit-trading-bot.fly.dev](https://bybit-trading-bot.fly.dev)
- 📊 **Health Check**: [/health](https://bybit-trading-bot.fly.dev/health)
- 📈 **Metrics**: [/metrics](https://bybit-trading-bot.fly.dev/metrics)
- 🔄 **CI/CD**: [GitHub Actions](https://github.com/danilapryadko/bbBot/actions)

## 📋 Project Status

### ✅ Phase 0: Infrastructure (100% COMPLETED)
- ✅ Project structure and organization
- ✅ Docker environment for local development
- ✅ PostgreSQL database with full schema
- ✅ GitHub Actions CI/CD pipeline
- ✅ Fly.io cloud deployment (Singapore region)
- ✅ Health monitoring and metrics
- ✅ Automated testing framework
- ✅ Security scanning with Trivy
- ✅ Daily performance reports
- ✅ All base trading strategies implemented

### ✅ Phase 1: Core Trading Services (100% COMPLETED)
- ✅ WebSocket market data streaming with auto-reconnection
- ✅ Real-time order management system with smart routing
- ✅ Advanced risk management V2 (Kelly Criterion, VaR, trailing stops)
- ✅ Position tracking and P&L calculation
- ✅ Data normalization pipeline
- ✅ Order lifecycle management

### ✅ Phase 2: Strategy & Analytics (60% COMPLETED)
- ✅ Backtesting framework with Monte Carlo simulation
- ✅ Machine learning strategies (LSTM, Random Forest, XGBoost)
- ✅ Feature engineering pipeline (100+ indicators)
- ✅ Strategy optimization with walk-forward analysis
- ⏳ Real-time performance dashboard
- ⏳ Advanced portfolio analytics

### 🔄 Phase 3: User Interface (NEXT PRIORITY)
- ⏳ React frontend dashboard
- ⏳ Telegram bot for notifications
- ⏳ GraphQL API endpoint
- ⏳ Mobile-responsive design
- ⏳ Real-time WebSocket updates

### 📅 Phase 4: Scale & Optimize (PLANNED)
- [ ] Multi-exchange support (Binance, OKX)
- [ ] Kubernetes deployment
- [ ] Multi-region deployment
- [ ] Cross-exchange arbitrage
- [ ] Microservices architecture

### 🔬 Phase 5: Advanced AI (FUTURE)
- [ ] Sentiment analysis (Twitter, Reddit, News)
- [ ] Reinforcement learning bot
- [ ] Options strategies
- [ ] High-frequency trading

## 🛠 Technology Stack

### Core Technologies
- **Language**: Python 3.11
- **Exchange API**: Bybit API v5 with WebSocket
- **Database**: PostgreSQL + Redis
- **Deployment**: Fly.io (Global Edge Network)
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana
- **Container**: Docker
- **Region**: Singapore (Low latency to Bybit)

### New Components (Phase 1-2)
- **WebSocket Manager**: Real-time data streaming
- **Data Normalizer**: Unified data processing
- **Order Manager**: Smart order routing
- **Risk Manager V2**: Advanced risk controls
- **ML Framework**: TensorFlow, XGBoost, scikit-learn
- **Backtesting Engine**: Historical simulation

## 📊 Trading Strategies

### Classic Strategies
- **RSI Strategy**: Oversold/overbought signals
- **EMA Strategy**: Moving average crossovers
- **Grid Strategy**: Automated grid trading
- **Combined Strategy**: Multi-indicator approach

### Advanced Strategies
- **Adaptive Strategy** ⭐: Auto-adjusts to market conditions
- **Kaufman Strategy**: Adaptive moving average with efficiency ratio
- **DCA Strategy**: Dollar-cost averaging for accumulation
- **Whale Following**: Track and follow large traders
- **Crash Detection**: Avoid market crashes like Terra/FTX
- **ETF Momentum**: Trade on ETF inflows

### Machine Learning Strategies (NEW)
- **LSTM Neural Network**: Time series prediction
- **Random Forest**: Feature-based classification
- **XGBoost**: Gradient boosting predictions
- **Ensemble Model**: Combined ML predictions
- **Feature Engineering**: 100+ technical indicators

## 🚀 Quick Start

### Cloud Deployment (Already Running!)

The bot is already deployed at: https://bybit-trading-bot.fly.dev

Monitor it:
```bash
# View logs
fly logs --app bybit-trading-bot

# SSH into container
fly ssh console --app bybit-trading-bot

# Check status
fly status --app bybit-trading-bot
```

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/danilapryadko/bbBot.git
cd bbBot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Run the integrated bot (NEW):
```bash
# Paper trading (safest - no real orders)
python main.py --mode integrated --paper --symbols BTCUSDT

# Testnet trading
python main.py --mode integrated --symbols BTCUSDT ETHUSDT

# With ML strategies
python main.py --mode integrated --paper --ml --symbols BTCUSDT

# Legacy mode (old bot)
python main.py --mode legacy --strategy adaptive
```

5. Using Docker:
```bash
make dev          # Start Docker services
make run-testnet  # Run in testnet
make run          # Run in production
```

## 📈 Performance Metrics

| Metric | Target | Current Status |
|--------|--------|----------------|
| Deployment | ✅ 24/7 | **Active on Fly.io** |
| Uptime | > 99.9% | Monitoring active |
| Latency | < 50ms | ~10ms (Singapore) |
| Health Checks | Every 5 min | ✅ Automated |
| Auto-deploy | On push | ✅ GitHub Actions |

## 🔧 Configuration

Current production configuration:
- **Mode**: TESTNET (safe testing)
- **Symbol**: BTCUSDT
- **Leverage**: 1x (no leverage)
- **Position Size**: $10 (minimum)
- **Stop Loss**: 2%
- **Take Profit**: 3%
- **Strategy**: Adaptive

## 🛡 Security

- ✅ API keys stored as Fly.io secrets
- ✅ Automated security scanning
- ✅ No hardcoded credentials
- ✅ HTTPS only endpoints
- ✅ Rate limiting implemented

## 📊 Monitoring

### Automated Monitoring
- **Health checks**: Every 5 minutes via GitHub Actions
- **Daily reports**: Automated performance reports
- **Alerts**: Telegram notifications (optional)
- **Metrics**: Prometheus format at `/metrics`

### Manual Monitoring
```bash
# Real-time logs
fly logs --app bybit-trading-bot

# Check health
curl https://bybit-trading-bot.fly.dev/health

# View metrics
curl https://bybit-trading-bot.fly.dev/metrics
```

## 🚀 Deployment Pipeline

```mermaid
graph LR
    A[Push to GitHub] --> B[GitHub Actions]
    B --> C[Run Tests]
    C --> D[Security Scan]
    D --> E[Build Docker]
    E --> F[Deploy to Fly.io]
    F --> G[Health Check]
    G --> H[Live on Cloud]
```

## 📝 API Documentation

### Public Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Welcome page |
| `/health` | GET | Health check |
| `/status` | GET | Bot status |
| `/metrics` | GET | Prometheus metrics |

### Health Check Response
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "checks": {
    "bot": true,
    "database": true,
    "api": true
  }
}
```

## 🔄 Development Workflow

1. **Local Development**: Make changes locally
2. **Test**: Run `make test`
3. **Commit**: Push to GitHub
4. **Auto Deploy**: GitHub Actions deploys to Fly.io
5. **Monitor**: Check logs and metrics

## 📚 Documentation

- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Implementation Plan](DETAILED_IMPLEMENTATION_PLAN.md)
- [Phase 0 Details](PHASE_0_DETAILED.md)
- [Market Analysis](MARKET_ANALYSIS_2022_2025.md)
- [Fly.io Deployment](FLY_IO_DEPLOYMENT.md)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open Pull Request

## 📞 Support

- **Repository**: [GitHub](https://github.com/danilapryadko/bbBot)
- **Issues**: [GitHub Issues](https://github.com/danilapryadko/bbBot/issues)
- **Live Bot**: [https://bybit-trading-bot.fly.dev](https://bybit-trading-bot.fly.dev)

## ⚠️ Disclaimer

This bot is for educational purposes. Cryptocurrency trading carries significant risk. Currently running on TESTNET for safety.

## 📄 License

MIT License - see [LICENSE](LICENSE) file

---

**📈 Bot Status**: Live on Fly.io | **🔄 Auto-Deploy**: Enabled | **✅ Phase 0**: Complete
