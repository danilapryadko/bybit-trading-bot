# 🚀 Bybit Trading Bot

[![Status](https://img.shields.io/badge/status-production-green)](https://bybit-danila-dashboard.fly.dev/)
[![Version](https://img.shields.io/badge/version-5.0.0-blue)]()
[![Python](https://img.shields.io/badge/Python-3.11-blue)]()
[![React](https://img.shields.io/badge/React-18-61DAFB)]()
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue)]()

Advanced automated cryptocurrency trading platform with machine learning, portfolio optimization, and comprehensive risk management.

## ✨ Features

- **🤖 Automated Trading** - Multiple strategies with real-time execution
- **📊 Portfolio Optimization** - Multi-asset allocation and rebalancing
- **🧠 Machine Learning** - Price prediction with Random Forest & Gradient Boosting
- **⚡ Real-time Dashboard** - React-based UI with live updates
- **📈 Backtesting** - Historical strategy testing with detailed analytics
- **🛡️ Risk Management** - Dynamic position sizing and risk scoring
- **🔔 Alert System** - Real-time notifications for important events

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/bybit-trading-bot.git
cd bybit-trading-bot

# Setup Python environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Bybit API credentials

# Start backend
python main.py

# In another terminal, start frontend
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173 to access the dashboard.

## 📚 Documentation

All documentation is organized in the [docs/](docs/) directory:

- 📖 [Quick Start Guide](docs/guides/quick-start.md)
- 🏗️ [Architecture Overview](docs/ARCHITECTURE.md)
- 🗺️ [Development Roadmap](docs/ROADMAP.md)
- 🚀 [Deployment Guide](docs/deployment/fly-io.md)
- 📊 [Trading Strategies](docs/guides/trading-strategies.md)

## 🛠️ Tech Stack

### Backend
- Python 3.11 with FastAPI
- GraphQL API with Ariadne
- PostgreSQL database
- Bybit API v5 integration

### Frontend
- React 18 with TypeScript
- Material-UI components
- Redux state management
- Recharts for visualizations

### Infrastructure
- Deployed on Fly.io
- Docker containerization
- GitHub Actions CI/CD

## 📊 Project Structure

```
bybit-trading-bot/
├── api/              # GraphQL API and resolvers
├── strategies/       # Trading strategies
├── risk_management/  # Risk control systems
├── ml_engine/       # Machine learning models
├── portfolio/       # Portfolio optimization
├── backtesting/     # Strategy backtesting
├── frontend/        # React application
├── docs/           # Documentation
└── tests/          # Test suites
```

## 🔧 Configuration

Create a `.env` file with:

```env
# Bybit API
BYBIT_API_KEY=your_api_key
BYBIT_API_SECRET=your_api_secret
BYBIT_TESTNET=false

# Database
DATABASE_URL=postgresql://user:pass@localhost/bybit_bot

# Application
TRADING_ENABLED=true
PAPER_TRADING=false
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/test_strategies.py

# Run with coverage
pytest --cov=. --cov-report=html
```

## 🚢 Deployment

The bot is deployed on Fly.io. For deployment instructions:

```bash
# Deploy to Fly.io
fly deploy

# Check status
fly status

# View logs
fly logs
```

See [deployment documentation](docs/deployment/fly-io.md) for details.

## 📈 Performance

Current system metrics:
- **Backtested Returns**: 15-30% monthly
- **Win Rate**: 65-75%
- **Sharpe Ratio**: 2.0+
- **Max Drawdown**: <10%
- **API Latency**: <50ms

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This bot is for educational purposes. Cryptocurrency trading carries significant risk. Never trade with funds you cannot afford to lose.

## 📞 Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/yourusername/bybit-trading-bot/issues)
- 💬 [Discussions](https://github.com/yourusername/bybit-trading-bot/discussions)

---

**Built with ❤️ for automated trading**