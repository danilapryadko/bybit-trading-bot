# Bybit Trading Bot - System Documentation

## 🚀 Production URLs
- **Dashboard**: https://bybit-danila-dashboard.fly.dev/
- **GraphQL API**: https://bybit-danila-api.fly.dev/graphql
- **Health Check**: https://bybit-danila-api.fly.dev/health

## 📊 System Architecture

### Microservices
1. **GraphQL API Service** (`services/graphql-api/`)
   - FastAPI + Ariadne GraphQL
   - Connects to Bybit API
   - PostgreSQL database
   - WebSocket support for real-time updates

2. **Frontend Dashboard** (`frontend/`)
   - React + TypeScript
   - Material-UI components
   - Apollo Client for GraphQL
   - Real-time WebSocket updates

### Core Modules

#### 1. Trading System (`bybit_connector.py`)
- Bybit API integration
- Order management
- Position tracking
- Balance monitoring
- Market data streaming

#### 2. Risk Management (`risk_management/`)
- **RiskManager**: Position sizing, risk validation, stop-loss calculation
- **PerformanceAnalytics**: Trading metrics, Sharpe ratio, drawdown analysis
- **AlertSystem**: Real-time alerts for price, risk, and performance

#### 3. Trading Strategies (`strategies/`)
- **Base Strategy**: Abstract class for all strategies
- **RSI Strategy**: RSI-based signals with divergence detection
- **Moving Average Strategy**: MA crossover signals
- **Combined Strategy**: Multi-indicator consensus
- **Strategy Manager**: Orchestrates multiple strategies

#### 4. Database (`database/`)
- PostgreSQL for production
- SQLite for local development
- Trade history
- Performance tracking
- Settings persistence

## 🎯 Features Implemented

### Phase 1: Core Trading ✅
- [x] Bybit API integration (Mainnet)
- [x] Real-time position management
- [x] Order placement and cancellation
- [x] Balance tracking
- [x] WebSocket price streaming

### Phase 2: Trading Strategies ✅
- [x] Strategy architecture
- [x] RSI strategy
- [x] Moving Average strategy
- [x] Combined strategy
- [x] Strategy manager
- [x] Strategy UI dashboard

### Phase 3: Risk Management ✅
- [x] Position size calculator
- [x] Dynamic stop-loss/take-profit
- [x] Risk scoring system
- [x] Performance analytics
- [x] Alert system
- [x] Risk dashboard UI

## 📈 Trading Features

### Position Management
- Real-time P&L tracking
- One-click position closing
- Leverage adjustment
- Margin monitoring

### Order Types
- Market orders
- Limit orders
- Stop-loss orders
- Take-profit orders

### Risk Controls
- Maximum position size limits
- Daily loss limits
- Consecutive loss protection
- Risk/reward ratio validation
- Exposure monitoring

### Performance Metrics
- Win rate
- Sharpe ratio
- Maximum drawdown
- Profit factor
- Expectancy
- Risk-adjusted returns

## 🛠️ Technical Stack

### Backend
- **Python 3.11**
- **FastAPI**: Web framework
- **Ariadne**: GraphQL server
- **Pybit**: Bybit API client
- **SQLAlchemy**: ORM
- **PostgreSQL**: Production database
- **Uvicorn**: ASGI server

### Frontend
- **React 18**
- **TypeScript**
- **Material-UI v5**
- **Apollo Client**: GraphQL client
- **Recharts**: Charting library
- **Redux Toolkit**: State management
- **Vite**: Build tool

### Infrastructure
- **Fly.io**: Hosting platform
- **PostgreSQL**: Managed database
- **Docker**: Containerization
- **GitHub Actions**: CI/CD

## 🔧 Configuration

### Environment Variables
```bash
# API Keys (Required)
BYBIT_API_KEY=your_api_key
BYBIT_API_SECRET=your_api_secret

# Environment
USE_MAINNET=true  # true for mainnet, false for testnet
DATABASE_URL=postgres://...  # Automatically set by Fly.io

# Optional
LOG_LEVEL=INFO
MAX_POSITIONS=3
MAX_DAILY_LOSS=0.05
```

### Risk Settings
Default risk parameters (configurable via UI):
- Max risk per trade: 2%
- Max total risk: 6%
- Max leverage: 10x
- Min risk/reward ratio: 1.5
- Max daily loss: 5%
- Max positions: 3

## 📝 API Endpoints

### GraphQL Queries
```graphql
# Get bot status
query {
  botStatus {
    isRunning
    balance
    positionsCount
  }
}

# Get positions
query {
  positions {
    symbol
    side
    size
    avgPrice
    unrealizedPnl
  }
}

# Get risk metrics
query {
  riskMetrics {
    riskScore
    riskLevel
    exposurePercent
    dailyPnl
  }
}
```

### GraphQL Mutations
```graphql
# Place order
mutation {
  placeOrder(input: {
    symbol: "BTCUSDT"
    side: "Buy"
    orderType: "MARKET"
    quantity: 0.001
  }) {
    success
    orderId
    message
  }
}

# Close position
mutation {
  closePosition(symbol: "BTCUSDT") {
    success
    realizedPnl
  }
}
```

## 🚦 Deployment

### Deploy API
```bash
cd services/graphql-api
fly deploy
```

### Deploy Frontend
```bash
cd frontend
fly deploy
```

### Check Status
```bash
fly status -a bybit-danila-api
fly status -a bybit-danila-dashboard
```

### View Logs
```bash
fly logs -a bybit-danila-api
fly logs -a bybit-danila-dashboard
```

## 🔒 Security

### API Security
- API keys stored as secrets in Fly.io
- HTTPS only for production
- CORS configured for frontend domain
- Rate limiting on API endpoints

### Trading Security
- Position size limits
- Daily loss limits
- Risk validation before trades
- Automatic stop-loss placement

## 📊 Monitoring

### Health Checks
- API: https://bybit-danila-api.fly.dev/health
- Returns balance and connection status

### Metrics to Monitor
- Risk score (keep < 75)
- Daily P&L
- Consecutive losses
- API connectivity
- Position exposure

### Alert Types
- **Critical**: Risk score > 75, API disconnection
- **High**: Large losses, consecutive losses
- **Medium**: Low win rate, poor Sharpe ratio
- **Low**: Information alerts

## 🎮 Usage Guide

### Getting Started
1. Visit https://bybit-danila-dashboard.fly.dev/
2. Dashboard shows account overview
3. Navigate to Trading to place orders
4. Monitor positions in real-time
5. Configure strategies in Strategies page
6. Monitor risk in Risk Management

### Trading Workflow
1. **Check Risk Dashboard** - Ensure risk score is acceptable
2. **Configure Strategy** - Set up trading strategies
3. **Place Order** - Use Trading page or let strategies run
4. **Monitor Position** - Track P&L in Positions
5. **Risk Management** - System automatically manages risk

### Strategy Configuration
1. Go to Strategies page
2. Click "Add Strategy"
3. Select strategy type (RSI, MA, Combined)
4. Configure parameters
5. Activate strategy
6. Monitor signals

## 🐛 Troubleshooting

### Common Issues

**API Connection Failed**
- Check API keys in Fly.io secrets
- Verify mainnet/testnet setting
- Check Bybit API status

**High Risk Score**
- Reduce position size
- Check daily loss
- Wait for cooldown after losses

**Strategy Not Trading**
- Verify strategy is active
- Check risk limits
- Review strategy parameters

## 📈 Future Enhancements

### Phase 4 (Planned)
- [ ] Machine learning predictions
- [ ] Advanced backtesting
- [ ] Portfolio optimization
- [ ] Multi-exchange support

### Phase 5 (Planned)
- [ ] Mobile app
- [ ] Telegram bot integration
- [ ] Advanced charting
- [ ] Social trading features

## 📞 Support

For issues or questions:
1. Check system logs in Fly.io dashboard
2. Review GraphQL API health endpoint
3. Verify risk management settings
4. Check Bybit API status

## 📄 License

Proprietary - All rights reserved

---

**Last Updated**: August 2024
**Version**: 3.0.0
**Status**: Production Ready