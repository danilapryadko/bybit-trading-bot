# 🤖 Bybit Trading Bot

[![CI/CD Pipeline](https://github.com/danilapryadko/bbBot/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/danilapryadko/bbBot/actions/workflows/ci-cd.yml)
[![Health Check](https://github.com/danilapryadko/bbBot/actions/workflows/health-check.yml/badge.svg)](https://github.com/danilapryadko/bbBot/actions/workflows/health-check.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automated cryptocurrency trading bot for Bybit exchange with advanced strategies and risk management.

## 🚀 Features

- **Multiple Trading Strategies**: RSI, EMA, Adaptive, Kaufman, DCA, and more
- **Risk Management**: Position sizing, stop-loss, take-profit, drawdown limits
- **Real-time Monitoring**: Health checks, metrics, performance tracking
- **Cloud Deployment**: Ready for Fly.io with auto-scaling
- **Database Storage**: PostgreSQL for trades, positions, and metrics
- **CI/CD Pipeline**: Automated testing and deployment via GitHub Actions

## 📊 Strategies

### Classic Strategies
- **RSI Strategy**: Trade on oversold/overbought conditions
- **EMA Strategy**: Moving average crossovers
- **Grid Strategy**: Automated grid trading

### Advanced Strategies (2022-2025 Market Analysis)
- **Adaptive Strategy** ⭐: Adjusts to market conditions (BULL/BEAR/CRASH)
- **Kaufman Strategy**: Adaptive moving average with efficiency ratio
- **DCA Strategy**: Dollar-cost averaging for accumulation
- **Whale Following**: Track large traders

## 🛠 Tech Stack

- **Language**: Python 3.11
- **Exchange API**: Bybit API v5
- **Database**: PostgreSQL + Redis
- **Deployment**: Fly.io / Docker
- **Monitoring**: Prometheus + Grafana
- **CI/CD**: GitHub Actions

## 📦 Installation

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

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Start Docker services:
```bash
make dev
```

5. Initialize database:
```bash
docker exec -i trading_postgres psql -U trader trading_bot < scripts/init_postgres.sql
```

6. Run the bot:
```bash
make run-testnet  # For testnet
make run          # For production (be careful!)
```

## 🚀 Deployment

### Deploy to Fly.io (Recommended)

1. Install Fly CLI:
```bash
curl -L https://fly.io/install.sh | sh
```

2. Deploy:
```bash
fly launch
fly secrets set API_KEY=xxx API_SECRET=yyy
fly deploy
```

### Docker Deployment

```bash
docker build -t bybit-bot .
docker run -d --env-file .env bybit-bot
```

## 📈 Monitoring

- **Health Check**: `https://your-app.fly.dev/health`
- **Status**: `https://your-app.fly.dev/status`
- **Metrics**: `https://your-app.fly.dev/metrics`

## 🧪 Testing

Run tests:
```bash
make test
```

Run with coverage:
```bash
make test-coverage
```

## 🔧 Configuration

Edit `.env` file:

```env
# API Keys
API_KEY=your_api_key
API_SECRET=your_api_secret

# Trading Parameters
BYBIT_TESTNET=true
SYMBOL=BTCUSDT
LEVERAGE=1
POSITION_SIZE=100
STOP_LOSS_PERCENT=2.0
TAKE_PROFIT_PERCENT=3.0

# Strategy Parameters
RSI_PERIOD=14
RSI_OVERSOLD=30
RSI_OVERBOUGHT=70
```

## 📊 Performance

| Metric | Target | Current |
|--------|--------|---------|
| Monthly Return | 10-15% | Testing |
| Max Drawdown | < 15% | Testing |
| Win Rate | > 60% | Testing |
| Sharpe Ratio | > 1.5 | Testing |

## 🛡 Security

- API keys stored as environment variables
- Secrets managed via Fly.io secrets
- No hardcoded credentials
- Regular security scanning via Trivy

## 📝 License

MIT License - see [LICENSE](LICENSE) file

## ⚠️ Disclaimer

This bot is for educational purposes. Cryptocurrency trading carries significant risk. Use at your own risk. Never trade with funds you cannot afford to lose.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📞 Support

- Issues: [GitHub Issues](https://github.com/danilapryadko/bbBot/issues)
- Discussions: [GitHub Discussions](https://github.com/danilapryadko/bbBot/discussions)

## 🙏 Acknowledgments

- Bybit API Documentation
- TA-Lib Technical Analysis Library
- Fly.io Platform

---

**⭐ Star this repository if you find it helpful!**
