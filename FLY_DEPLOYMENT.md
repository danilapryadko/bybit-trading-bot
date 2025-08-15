# 🚀 Fly.io Deployment Guide

## Prerequisites

1. Install Fly CLI:
```bash
curl -L https://fly.io/install.sh | sh
```

2. Login to Fly:
```bash
fly auth login
```

## Initial Setup

### 1. Create the app (if not exists):
```bash
fly apps create bybit-trading-bot
```

### 2. Set secrets (sensitive data):
```bash
# Telegram Bot Token (REQUIRED)
fly secrets set TELEGRAM_BOT_TOKEN=8489565613:AAGnJT8IaO8jsNvCp0HdCG5hcZFU4XJAaxY

# Your Telegram User ID (REQUIRED - get from @userinfobot)
fly secrets set TELEGRAM_ALLOWED_USERS=YOUR_USER_ID_HERE

# Bybit API (Optional for demo mode)
fly secrets set BYBIT_API_KEY=your_api_key_here
fly secrets set BYBIT_API_SECRET=your_api_secret_here
```

### 3. Create volumes for persistent storage:
```bash
fly volumes create bot_data --size 1 --region sin
fly volumes create logs --size 1 --region sin
```

## Deploy

### First deployment:
```bash
fly deploy
```

### Subsequent deployments:
```bash
fly deploy --strategy rolling
```

## Monitoring

### Check status:
```bash
fly status
```

### View logs:
```bash
fly logs
```

### SSH into container:
```bash
fly ssh console
```

### Check app URL:
```bash
fly open
```

## Scaling

### Scale to multiple regions:
```bash
fly regions add nrt  # Tokyo
fly regions add hkg  # Hong Kong
```

### Scale instances:
```bash
fly scale count 2  # Run 2 instances
```

### Scale resources:
```bash
fly scale vm shared-cpu-1x  # 1 shared CPU, 256MB RAM
fly scale memory 512  # Increase to 512MB RAM
```

## Health Monitoring

The app exposes several endpoints:

- `/` - Root endpoint with basic info
- `/health` - Health check for Fly.io
- `/status` - Bot status
- `/metrics` - Prometheus metrics
- `/logs` - Recent log entries

## Telegram Bot Commands

Once deployed, your bot will be available at: **@bybit_danila_trading_bot**

Commands:
- `/start` - Initialize bot
- `/status` - Check status
- `/balance` - View balance
- `/positions` - List positions
- `/stop` - Stop trading

## Troubleshooting

### Bot not responding:
```bash
# Check if secrets are set
fly secrets list

# Check logs for errors
fly logs | grep ERROR

# Restart app
fly apps restart
```

### Connection issues:
```bash
# Check app status
fly status

# Scale to different region
fly regions add ams
fly regions remove sin
```

### Update secrets:
```bash
fly secrets set TELEGRAM_ALLOWED_USERS=user1,user2,user3
```

## Environment Variables

Set in fly.toml:
- `BYBIT_TESTNET=true` - Use testnet
- `PAPER_TRADING=true` - Paper trading mode
- `INITIAL_CAPITAL=10000` - Starting capital
- `MAX_POSITIONS=3` - Max open positions
- `RISK_PER_TRADE=1.0` - Risk percentage

## CI/CD Integration

The GitHub Actions workflow automatically deploys on push to main:

1. Tests run on every push
2. Deployment triggers on main branch
3. Fly.io secrets are managed separately

## Cost Estimation

Free tier includes:
- 3 shared-cpu-1x VMs
- 3GB persistent storage
- 160GB outbound transfer

Estimated monthly cost: **$0-5** (within free tier)

## Security Notes

1. Never commit secrets to git
2. Use `fly secrets` for sensitive data
3. Restrict Telegram bot to allowed users
4. Use testnet/paper trading initially
5. Monitor logs for suspicious activity

## Support

- Fly.io Status: https://status.fly.io/
- Fly.io Docs: https://fly.io/docs/
- GitHub Issues: https://github.com/danilapryadko/bbBot/issues