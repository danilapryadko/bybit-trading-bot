# 🚀 Quick Start Guide

## ✅ Your Bot is Ready!

**Telegram Bot**: [@bybit_danila_trading_bot](https://t.me/bybit_danila_trading_bot)  
**User**: @koshkikoshki (Данила Прядко, ID: 384403397)  
**Status**: Configured and tested successfully!

## 📱 Start Trading Bot

### Option 1: One-click start (Recommended)
```bash
./start_bot.sh
```

### Option 2: Manual start
```bash
source venv/bin/activate
python run_with_telegram.py
```

## 💬 Telegram Commands

Open [@bybit_danila_trading_bot](https://t.me/bybit_danila_trading_bot) and use:

- `/start` - Initialize bot and show menu
- `/status` - Check bot status
- `/balance` - View account balance
- `/positions` - List open positions
- `/stop` - Stop the bot

## 🎮 Interactive Menu

After `/start`, you'll see buttons for:
- 📊 **Dashboard** - Account overview
- 💼 **Positions** - Manage trades
- 📈 **Market** - Live prices
- 🤖 **Bot Status** - Control bot
- ⚙️ **Settings** - Configure parameters
- ❓ **Help** - Get assistance

## 🔧 Configuration

Current settings (`.env`):
- **Mode**: Paper Trading (safe mode)
- **Network**: Testnet
- **Capital**: $10,000
- **Risk**: 1% per trade
- **Max Positions**: 3

## 🌐 Deploy to Cloud (Fly.io)

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Deploy
fly deploy

# Set your secrets
fly secrets set TELEGRAM_ALLOWED_USERS=384403397
```

## 📊 React Dashboard

Start frontend locally:
```bash
cd frontend
npm install
npm run dev
```

Open: http://localhost:5173

## 🧪 Test Connection

```bash
python test_telegram_locally.py
```

## 📈 Trading Strategies

Available strategies:
- **ML Ensemble** - Combined LSTM, Random Forest, XGBoost
- **LSTM Neural Network** - Deep learning predictions
- **Random Forest** - Ensemble tree-based model
- **XGBoost** - Gradient boosting
- **Momentum** - Trend following
- **Mean Reversion** - Counter-trend

## ⚠️ Safety Features

- ✅ Paper trading mode by default
- ✅ Testnet for safe testing
- ✅ Risk management (max 1% per trade)
- ✅ Position limits (max 3 positions)
- ✅ Stop-loss and take-profit
- ✅ Telegram authentication

## 🆘 Troubleshooting

### Bot not responding?
1. Check bot is running: `ps aux | grep telegram`
2. Check logs: `tail -f trading_bot.log`
3. Restart: `./start_bot.sh`

### Connection issues?
1. Check internet connection
2. Verify Telegram not blocked
3. Check API credentials in `.env`

## 📝 Next Steps

1. **Test strategies** in paper trading mode
2. **Monitor performance** via Telegram
3. **Adjust parameters** through bot settings
4. **Switch to live** when confident (update `.env`)

## 🎉 Ready to Trade!

Your bot is configured and ready. Start with `./start_bot.sh` and control everything through Telegram!

---

**Remember**: Always start with paper trading to test your strategies safely.