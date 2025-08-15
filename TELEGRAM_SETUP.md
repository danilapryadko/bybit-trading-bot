# 📱 Telegram Bot Setup Guide

## 🚀 Quick Start

Your Telegram bot is ready at: **[@bybit_danila_trading_bot](https://t.me/bybit_danila_trading_bot)**

## 📋 Setup Steps

### 1. Get Your Telegram User ID
Send a message to [@userinfobot](https://t.me/userinfobot) in Telegram to get your user ID.

### 2. Configure Environment Variables
```bash
# Copy example config
cp .env.example .env

# Edit .env file
nano .env  # or use any text editor
```

Update these values in `.env`:
```env
# Your Telegram bot token (already set)
TELEGRAM_BOT_TOKEN=8489565613:AAGnJT8IaO8jsNvCp0HdCG5hcZFU4XJAaxY

# Your Telegram user ID (get from @userinfobot)
TELEGRAM_ALLOWED_USERS=YOUR_USER_ID_HERE

# Bybit API (optional for demo mode)
BYBIT_API_KEY=your_api_key
BYBIT_API_SECRET=your_api_secret
BYBIT_TESTNET=true

# Trading settings
PAPER_TRADING=true
INITIAL_CAPITAL=10000
RISK_PER_TRADE=1.0
MAX_POSITIONS=3
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Bot
```bash
python run_with_telegram.py
```

### 5. Start Using the Bot
1. Open Telegram
2. Go to [@bybit_danila_trading_bot](https://t.me/bybit_danila_trading_bot)
3. Send `/start` command
4. Use the interactive menu to control your trading bot

## 📱 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot and show main menu |
| `/status` | Check bot status |
| `/balance` | Show account balance |
| `/positions` | List open positions |
| `/stop` | Stop the trading bot |

## 🎮 Interactive Features

The bot provides an interactive keyboard with:

- **📊 Dashboard** - View account overview and P&L
- **💼 Positions** - Manage open positions
- **📈 Market** - Real-time market data
- **🤖 Bot Status** - Start/stop/pause trading
- **⚙️ Settings** - Configure trading parameters
- **❓ Help** - Get help and documentation

## 🔒 Security

- Only authorized users (in `TELEGRAM_ALLOWED_USERS`) can access the bot
- Never share your bot token publicly
- Use testnet mode for testing before going live

## 🎯 Paper Trading Mode

By default, the bot runs in paper trading mode:
- No real money is used
- Perfect for testing strategies
- Switch to live trading by setting `PAPER_TRADING=false` in `.env`

## 📊 Features Available via Telegram

1. **Real-time Monitoring**
   - Account balance and P&L
   - Open positions with live prices
   - Market overview for watchlist

2. **Trading Control**
   - Start/stop/pause bot
   - Close positions remotely
   - Adjust risk parameters

3. **Notifications**
   - Trade executions
   - Position updates
   - Error alerts
   - Signal notifications

## 🛠️ Troubleshooting

### Bot doesn't respond
- Check your user ID is in `TELEGRAM_ALLOWED_USERS`
- Verify bot token is correct
- Check bot is running: `python run_with_telegram.py`

### Can't see positions/balance
- Ensure Bybit API credentials are configured
- Check you're connected to the right network (testnet/mainnet)

### Connection errors
- Verify internet connection
- Check firewall settings
- Ensure Telegram isn't blocked in your region

## 📝 Advanced Configuration

### Multiple Users
Add comma-separated user IDs:
```env
TELEGRAM_ALLOWED_USERS=123456789,987654321
```

### Custom Notifications
Configure in bot settings menu or via `.env`:
```env
NOTIFY_ON_TRADE=true
NOTIFY_ON_ERROR=true
NOTIFY_ON_SIGNAL=true
```

## 🚦 Status Indicators

- 🟢 **Green** - System running normally
- 🟡 **Yellow** - Warning or paper trading mode
- 🔴 **Red** - Error or system stopped
- 📈 **Up Arrow** - Profit/bullish
- 📉 **Down Arrow** - Loss/bearish

## 📞 Support

- GitHub Issues: [Report bugs or request features]
- Telegram: Message the bot with `/help`
- Logs: Check `trading_bot.log` for detailed information

## 🎉 Ready to Trade!

Your bot is configured and ready. Open Telegram and send `/start` to begin!

---

**⚠️ Disclaimer**: Trading cryptocurrencies involves risk. Start with paper trading and small amounts. Never invest more than you can afford to lose.