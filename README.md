# Bybit Trading Bot Dashboard 🚀

Professional cryptocurrency trading bot with real-time dashboard for Bybit exchange.

![Dashboard](https://img.shields.io/badge/Status-Live-success)
![License](https://img.shields.io/badge/License-MIT-blue)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![React](https://img.shields.io/badge/React-18-61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue)

## 🌐 Live Demo

- **Dashboard**: https://bybit-danila-dashboard.fly.dev
- **API**: https://bybit-danila-api.fly.dev/graphql

## ✨ Current Features

### Real-time Market Data
- Live cryptocurrency prices (BTC $118,294 | ETH $4,533 | SOL $192)
- Interactive candlestick charts
- 24h price changes and volume
- Real balance: 499 USDT

### Technical Features
- Auto-reconnection with exponential backoff
- Self-recovery mechanisms
- Microservices architecture
- Real-time updates (prices: 5s, balance: 10s)

## 🛠️ Tech Stack

**Backend**: Python, FastAPI, GraphQL, Bybit API  
**Frontend**: React, TypeScript, Material-UI, Redux  
**Charts**: TradingView Lightweight Charts  
**Deployment**: Fly.io

## 📸 Screenshots

Dashboard showing real-time Bitcoin price at $118,294 with live charts and 499 USDT balance.

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/danilapryadko/bbBot.git
cd bybit-trading-bot

# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
npm run dev
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## ⚠️ Disclaimer

Educational purposes only. Trade at your own risk.

---
**Built with Claude Code** 🤖
