# CLAUDE.md - AI Assistant Context

## Project Overview
Professional cryptocurrency trading bot for Bybit exchange with ML models, real-time monitoring, and secure cloud deployment on Fly.io.

## 🆕 Architecture Update (2025-08-15)
**Migration to Microservices Architecture in progress**
- Splitting monolithic application into separate services
- Telegram Bot Service: `bybit-danila-bot`
- GraphQL API Service: `bybit-danila-api` (new)
- Resolves Telegram bot conflicts and improves scalability

## Current Status
- ✅ PostgreSQL database deployed and connected
- ✅ Mainnet API keys configured securely
- ✅ Production/testnet switch implemented (USE_MAINNET env var)
- ✅ Security measures (encryption, rate limiting, audit logging)
- ✅ ML models (Random Forest, XGBoost, Gradient Boosting)
- ✅ Data collection for historical training
- ✅ Telegram bot deployed (@bybit_danila_trading_bot)
- ✅ React dashboard deployed (https://bybit-danila-dashboard.fly.dev)
- ⚠️ GraphQL API migrating to separate service (https://bybit-danila-api.fly.dev/graphql)
- 🔄 Microservices migration in progress

## Important Commands

### Local Testing
```bash
# Run tests
pytest tests/test_comprehensive.py

# Check linting
flake8 .

# Type checking
mypy .
```

### Deployment (Microservices)
```bash
# Deploy GraphQL API Service
cd services/graphql-api
fly deploy -a bybit-danila-api

# Deploy Telegram Bot Service
cd services/telegram-bot
fly deploy -a bybit-danila-bot

# Check status
fly status -a bybit-danila-api
fly status -a bybit-danila-bot

# View logs
fly logs -a bybit-danila-api
fly logs -a bybit-danila-bot

# Switch to mainnet (both services)
fly secrets set USE_MAINNET=true -a bybit-danila-api
fly secrets set USE_MAINNET=true -a bybit-danila-bot
```

### Database Operations
```bash
# Run migration
python database/migrate_to_postgres.py

# Collect historical data
python data_collector.py

# Train ML models
python ml_trainer.py
```

## Key Files
- `config.py` - Configuration management (testnet/mainnet switch)
- `security/security_manager.py` - Security features
- `data_collector.py` - Historical data collection
- `ml_trainer.py` - ML model training
- `database/` - PostgreSQL models and migrations
- `dashboard/` - React frontend
- `services/telegram-bot/` - Telegram bot microservice (NEW)
- `services/graphql-api/` - GraphQL API microservice (NEW)
- `docs/MIGRATION_PLAN.md` - Microservices migration guide
- `docs/ARCHITECTURE.md` - System architecture documentation
- `docs/DEPLOYMENT.md` - Deployment procedures

## Environment Variables
- `USE_MAINNET` - Toggle between testnet (false) and mainnet (true)
- `BYBIT_MAINNET_API_KEY` - Mainnet API key
- `BYBIT_MAINNET_API_SECRET` - Mainnet API secret
- `DATABASE_URL` - PostgreSQL connection string
- `TELEGRAM_BOT_TOKEN` - Telegram bot token

## Known Issues
- ⚠️ Old deployment using monolithic architecture causes Telegram bot conflicts
- ✅ Solution: Microservices architecture (in progress)
- WebSocket blocked by CloudFront in Singapore region (using REST fallback)
- Telegram bot may restart periodically (auto-recovery implemented)

## Next Steps
- 🚀 Complete microservices migration
- Deploy GraphQL API as separate service
- Update dashboard to use new API endpoint
- Add Prometheus/Grafana monitoring
- Increase test coverage to 80%
- Create PWA service worker for offline dashboard
- Implement advanced trading strategies
- Add more ML model types (LSTM, Transformer)

## Backup Information
- Full backup created: `backups/backup_2025-08-15_monolith.tar.gz`
- Secrets backed up: `backups/secrets_backup.md`
- Migration documentation: `docs/MIGRATION_PLAN.md`