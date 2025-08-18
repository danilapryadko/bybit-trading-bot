# GraphQL API Documentation 📚

## Base URL
Production: `https://bybit-danila-api.fly.dev/graphql`  
Local: `http://localhost:8000/graphql`

## Authentication
Currently using environment variables for API keys. Future versions will implement JWT authentication.

---

## Queries

### botStatus
Get the current status of the trading bot.

```graphql
query GetBotStatus {
  botStatus {
    isRunning
    mainnet
    balance
    positionsCount
  }
}
```

---

**Last Updated**: December 2024  
**API Version**: 4.0.0
