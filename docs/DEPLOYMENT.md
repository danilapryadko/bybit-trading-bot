# 🚀 Deployment Guide for Microservices

## Prerequisites
- Fly.io CLI installed (`brew install flyctl`)
- Fly.io account with verified payment method
- Access to Bybit API keys
- PostgreSQL database URL

## Service Deployment Order
1. GraphQL API Service (new)
2. Telegram Bot Service (update existing)
3. Dashboard (update configuration)

## 1. Deploy GraphQL API Service

### Step 1: Navigate to service directory
```bash
cd services/graphql-api
```

### Step 2: Create new Fly.io application
```bash
fly apps create bybit-danila-api
```

### Step 3: Create symlinks for shared code
```bash
# From graphql-api directory
ln -s ../../bybit_connector.py .
ln -s ../../config.py .
ln -s ../../database ./database
```

### Step 4: Set secrets
```bash
# Bybit API credentials
fly secrets set BYBIT_API_KEY="your-testnet-key" -a bybit-danila-api
fly secrets set BYBIT_API_SECRET="your-testnet-secret" -a bybit-danila-api
fly secrets set BYBIT_MAINNET_API_KEY="your-mainnet-key" -a bybit-danila-api
fly secrets set BYBIT_MAINNET_API_SECRET="your-mainnet-secret" -a bybit-danila-api

# Database
fly secrets set DATABASE_URL="postgresql://..." -a bybit-danila-api

# Environment
fly secrets set USE_MAINNET="false" -a bybit-danila-api
```

### Step 5: Deploy
```bash
fly deploy -a bybit-danila-api
```

### Step 6: Verify deployment
```bash
# Check status
fly status -a bybit-danila-api

# Check logs
fly logs -a bybit-danila-api

# Test health endpoint
curl https://bybit-danila-api.fly.dev/health
```

## 2. Update Telegram Bot Service

### Step 1: Navigate to service directory
```bash
cd services/telegram-bot
```

### Step 2: Create symlinks for shared code
```bash
# From telegram-bot directory
ln -s ../../telegram_bot.py .
ln -s ../../trading_bot.py .
ln -s ../../bybit_connector.py .
ln -s ../../config.py .
ln -s ../../strategies.py .
ln -s ../../database ./database
ln -s ../../security ./security
```

### Step 3: Deploy update
```bash
fly deploy -a bybit-danila-bot
```

### Step 4: Verify deployment
```bash
# Check status
fly status -a bybit-danila-bot

# Check logs
fly logs -a bybit-danila-bot

# Test bot commands
# Send /balance to your Telegram bot
```

## 3. Update Dashboard Configuration

### Step 1: Update API endpoint
Edit `dashboard/src/config.js` or environment file:
```javascript
// Old configuration
const API_URL = 'https://bybit-danila-bot.fly.dev/graphql';

// New configuration
const API_URL = 'https://bybit-danila-api.fly.dev/graphql';
```

### Step 2: Rebuild and deploy dashboard
```bash
cd dashboard
npm run build
fly deploy -a bybit-danila-dashboard
```

## Monitoring and Troubleshooting

### Check Service Health
```bash
# GraphQL API
curl https://bybit-danila-api.fly.dev/health

# Response should be:
{
  "status": "healthy",
  "service": "graphql-api",
  "balance": 10000.0,
  "mainnet": false,
  "version": "2.0.0"
}
```

### View Logs
```bash
# GraphQL API logs
fly logs -a bybit-danila-api --tail

# Telegram Bot logs
fly logs -a bybit-danila-bot --tail
```

### SSH into Services
```bash
# GraphQL API
fly ssh console -a bybit-danila-api

# Telegram Bot
fly ssh console -a bybit-danila-bot
```

### Scale Services
```bash
# Scale GraphQL API horizontally
fly scale count 2 -a bybit-danila-api

# Scale Telegram Bot vertically
fly scale memory 512 -a bybit-danila-bot
```

## Rollback Procedures

### Rollback GraphQL API
```bash
# List releases
fly releases -a bybit-danila-api

# Rollback to previous version
fly deploy --image registry.fly.io/bybit-danila-api@sha256:<previous-sha>
```

### Rollback Telegram Bot
```bash
# List releases
fly releases -a bybit-danila-bot

# Rollback to previous version
fly deploy --image registry.fly.io/bybit-danila-bot@sha256:<previous-sha>
```

## Environment Variables Reference

### GraphQL API Service
| Variable | Description | Example |
|----------|-------------|---------|
| BYBIT_API_KEY | Testnet API key | xxx-xxx-xxx |
| BYBIT_API_SECRET | Testnet API secret | yyy-yyy-yyy |
| BYBIT_MAINNET_API_KEY | Mainnet API key | aaa-aaa-aaa |
| BYBIT_MAINNET_API_SECRET | Mainnet API secret | bbb-bbb-bbb |
| DATABASE_URL | PostgreSQL connection | postgresql://user:pass@host/db |
| USE_MAINNET | Use mainnet (true/false) | false |

### Telegram Bot Service
| Variable | Description | Example |
|----------|-------------|---------|
| TELEGRAM_BOT_TOKEN | Bot token from BotFather | 123456:ABC-DEF |
| TELEGRAM_ALLOWED_USERS | Comma-separated user IDs | 12345,67890 |
| BYBIT_API_KEY | Testnet API key | xxx-xxx-xxx |
| BYBIT_API_SECRET | Testnet API secret | yyy-yyy-yyy |
| DATABASE_URL | PostgreSQL connection | postgresql://user:pass@host/db |
| USE_MAINNET | Use mainnet (true/false) | false |

## Common Issues and Solutions

### Issue: GraphQL API not responding
**Solution:**
1. Check logs: `fly logs -a bybit-danila-api`
2. Verify port 8000 is exposed in Dockerfile
3. Check health endpoint
4. Verify DATABASE_URL is correct

### Issue: Telegram bot conflicts
**Solution:**
1. Ensure only one instance is running
2. Check `fly scale count 1 -a bybit-danila-bot`
3. Clear webhook: Use BotFather to reset webhook

### Issue: Database connection errors
**Solution:**
1. Verify DATABASE_URL in secrets
2. Check PostgreSQL is accessible
3. Run migrations manually if needed

### Issue: CORS errors in dashboard
**Solution:**
1. Check CORS configuration in GraphQL API
2. Verify allowed origins include dashboard URL
3. Clear browser cache

## Performance Tuning

### GraphQL API
```toml
# fly.toml adjustments
[services.concurrency]
  hard_limit = 200  # Increase for high traffic
  soft_limit = 150
  type = "connections"

[[vm]]
  cpu_kind = "shared"
  cpus = 2  # Increase for better performance
  memory_mb = 1024
```

### Telegram Bot
```toml
# fly.toml adjustments
[[vm]]
  cpu_kind = "shared"
  cpus = 1  # Usually sufficient
  memory_mb = 512  # Increase if using heavy ML models
```

## Security Checklist

- [ ] All secrets are set via `fly secrets set`
- [ ] No hardcoded credentials in code
- [ ] HTTPS enforced on all endpoints
- [ ] Rate limiting configured
- [ ] User authentication enabled
- [ ] Database connections use SSL
- [ ] Regular security updates applied

## Backup and Recovery

### Backup Database
```bash
# Manual backup
fly postgres backup create -a bybit-postgres

# List backups
fly postgres backup list -a bybit-postgres
```

### Restore Database
```bash
# Restore from backup
fly postgres backup restore <backup-id> -a bybit-postgres
```

## Maintenance Mode

### Enable Maintenance Mode
```bash
# Set maintenance flag
fly secrets set MAINTENANCE_MODE=true -a bybit-danila-api
fly secrets set MAINTENANCE_MODE=true -a bybit-danila-bot
```

### Disable Maintenance Mode
```bash
# Remove maintenance flag
fly secrets unset MAINTENANCE_MODE -a bybit-danila-api
fly secrets unset MAINTENANCE_MODE -a bybit-danila-bot
```