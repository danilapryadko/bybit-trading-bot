# Microservices Directory

This directory contains the microservices implementation of the Bybit Trading Bot.

## Services

### 📱 telegram-bot/
Telegram Bot service that handles user interactions via Telegram.
- Processes user commands
- Sends trading notifications
- Manages trading operations

### 📊 graphql-api/
GraphQL API service that provides data access for the dashboard and external integrations.
- Real-time balance and position data
- Trading history
- Market data

### 🔗 shared/
Shared code and utilities used by multiple services.
- Database models
- Bybit connector
- Common configurations

## Quick Start

### Deploy GraphQL API
```bash
cd graphql-api
fly apps create bybit-danila-api
fly deploy -a bybit-danila-api
```

### Deploy Telegram Bot
```bash
cd telegram-bot
fly deploy -a bybit-danila-bot
```

## Architecture Benefits

1. **Service Isolation** - Each service runs independently
2. **Scalability** - Services can scale based on their specific needs
3. **Maintainability** - Clear separation of concerns
4. **Reliability** - Failure in one service doesn't affect others
5. **Development Speed** - Teams can work on services independently

## Documentation

- [Migration Plan](../docs/MIGRATION_PLAN.md)
- [Architecture Overview](../docs/ARCHITECTURE.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)