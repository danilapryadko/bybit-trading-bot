# 🚀 Migration Plan: Monolith to Microservices

## Overview
This document outlines the migration from a monolithic architecture to a microservices architecture for the Bybit Trading Bot.

## Current Architecture (Monolith)
- Single application running both Telegram bot and GraphQL API
- Conflicts between services (Telegram bot getUpdates conflicts)
- Difficult to scale individual components
- Single point of failure

## Target Architecture (Microservices)
```
┌─────────────────────────────────────────────────────────┐
│                     User Interfaces                      │
├────────────────┬────────────────┬───────────────────────┤
│  Telegram App  │   Dashboard    │   External APIs       │
└────────┬───────┴────────┬───────┴───────────┬───────────┘
         │                │                   │
         ▼                ▼                   ▼
┌────────────────┐ ┌──────────────┐ ┌──────────────────┐
│ Telegram Bot   │ │ GraphQL API  │ │   Future APIs    │
│   Service      │ │   Service    │ │                  │
└────────┬───────┘ └──────┬───────┘ └────────┬─────────┘
         │                │                   │
         └────────────────┼───────────────────┘
                          ▼
                 ┌────────────────┐
                 │   PostgreSQL   │
                 │    Database    │
                 └────────────────┘
```

## Migration Steps

### Phase 1: Backup (✅ Completed)
- Created full backup of monolithic application
- Saved secrets configuration
- Archive location: `backups/backup_2025-08-15_monolith.tar.gz`

### Phase 2: Create Service Structure (✅ Completed)
```
services/
├── telegram-bot/
│   ├── main.py
│   ├── Dockerfile
│   ├── fly.toml
│   └── requirements.txt
├── graphql-api/
│   ├── main.py
│   ├── Dockerfile
│   ├── fly.toml
│   └── requirements.txt
└── shared/
    └── (symlinks to shared code)
```

### Phase 3: Deploy GraphQL API Service
1. Create new Fly.io application:
   ```bash
   cd services/graphql-api
   fly apps create bybit-danila-api
   ```

2. Set secrets for API service:
   ```bash
   fly secrets set BYBIT_API_KEY="..." -a bybit-danila-api
   fly secrets set BYBIT_API_SECRET="..." -a bybit-danila-api
   fly secrets set BYBIT_MAINNET_API_KEY="..." -a bybit-danila-api
   fly secrets set BYBIT_MAINNET_API_SECRET="..." -a bybit-danila-api
   fly secrets set DATABASE_URL="..." -a bybit-danila-api
   fly secrets set USE_MAINNET="false" -a bybit-danila-api
   ```

3. Deploy the API service:
   ```bash
   fly deploy -a bybit-danila-api
   ```

### Phase 4: Update Telegram Bot Service
1. Update existing application:
   ```bash
   cd services/telegram-bot
   fly deploy -a bybit-danila-bot
   ```

### Phase 5: Update Dashboard Configuration
Update the dashboard to point to the new API endpoint:
- Old: `https://bybit-danila-bot.fly.dev/graphql`
- New: `https://bybit-danila-api.fly.dev/graphql`

## Benefits of Microservices Architecture

### 1. Isolation and Independence
- Services can be developed, deployed, and scaled independently
- No more Telegram bot conflicts
- Failure in one service doesn't affect others

### 2. Scalability
- GraphQL API can scale based on dashboard traffic
- Telegram bot scales based on user interactions
- Resource optimization per service

### 3. Maintainability
- Clear separation of concerns
- Easier debugging with isolated logs
- Simpler testing of individual components

### 4. Technology Flexibility
- Can use different tech stacks for different services
- Easy to add new services (webhooks, REST API, etc.)

## Rollback Plan
If issues arise during migration:
1. Restore from backup: `backups/backup_2025-08-15_monolith.tar.gz`
2. Deploy original monolithic application
3. Revert dashboard configuration

## Monitoring and Health Checks
Each service has its own health endpoint:
- Telegram Bot: Internal health check (no HTTP endpoint needed)
- GraphQL API: `https://bybit-danila-api.fly.dev/health`

## Environment Variables

### Telegram Bot Service
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_USERS`
- `BYBIT_API_KEY`
- `BYBIT_API_SECRET`
- `DATABASE_URL`
- `USE_MAINNET`

### GraphQL API Service
- `BYBIT_API_KEY`
- `BYBIT_API_SECRET`
- `BYBIT_MAINNET_API_KEY`
- `BYBIT_MAINNET_API_SECRET`
- `DATABASE_URL`
- `USE_MAINNET`

## Testing Plan
1. Deploy GraphQL API service first
2. Test API endpoints independently
3. Deploy updated Telegram bot
4. Test bot commands
5. Update dashboard configuration
6. Run full E2E tests

## Timeline
- Day 1: Create structure and documentation ✅
- Day 2: Deploy GraphQL API service
- Day 3: Update Telegram bot service
- Day 4: Testing and monitoring
- Day 5: Full migration complete

## Success Criteria
- ✅ Both services running independently
- ✅ No Telegram bot conflicts
- ✅ Dashboard displaying real data
- ✅ All health checks passing
- ✅ E2E tests passing with >90% success rate