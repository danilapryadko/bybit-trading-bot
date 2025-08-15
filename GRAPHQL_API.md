# 📊 GraphQL API Documentation

## 🚀 Overview

The Bybit Trading Bot GraphQL API provides a modern, flexible interface for interacting with the trading bot. It supports real-time subscriptions, complex queries, and mutations for bot control.

**Live Endpoint**: `https://bybit-danila-bot.fly.dev/graphql/` (🟢 Running 24/7)  
**Local Endpoint**: `http://localhost:8000/graphql/` (for development)

## 🛠 Quick Start

### Access the API

#### Live on Fly.io (24/7)
```bash
# API is already running at:
https://bybit-danila-bot.fly.dev/graphql/
```

#### Local Development
```bash
# Start GraphQL server locally
python graphql_server.py

# Server will be available at:
# http://localhost:8000/graphql/
```

### Testing with curl

```bash
# Get bot status
curl -X POST http://localhost:8000/graphql/ \
  -H "Content-Type: application/json" \
  -d '{"query":"{ botStatus { isRunning strategy mode } }"}'

# Get balance
curl -X POST http://localhost:8000/graphql/ \
  -H "Content-Type: application/json" \
  -d '{"query":"{ balance { total available unrealizedPnl } }"}'
```

## 📋 Schema Overview

### Queries

| Query | Description | Returns |
|-------|-------------|---------|
| `botStatus` | Get current bot status | BotStatus |
| `balance` | Get account balance | Balance |
| `positions` | List all open positions | [Position] |
| `marketData(symbol)` | Get market data for symbol | MarketData |
| `tradingHistory(limit)` | Get recent trades | [Trade] |
| `performance` | Get performance metrics | Performance |
| `strategies` | List available strategies | [Strategy] |
| `riskMetrics` | Get risk metrics | RiskMetrics |

### Mutations

| Mutation | Description | Returns |
|----------|-------------|---------|
| `startBot(config)` | Start the trading bot | BotStatus |
| `stopBot` | Stop the trading bot | BotStatus |
| `pauseBot` | Pause trading | BotStatus |
| `resumeBot` | Resume trading | BotStatus |
| `updateStrategy(strategy)` | Change strategy | BotStatus |
| `updateRiskProfile(profile)` | Update risk settings | RiskMetrics |
| `placeOrder(order)` | Place a new order | Order |
| `cancelOrder(orderId)` | Cancel an order | Boolean |
| `closePosition(symbol)` | Close specific position | Boolean |
| `closeAllPositions` | Close all positions | Boolean |

### Subscriptions

| Subscription | Description | Returns |
|--------------|-------------|---------|
| `priceUpdate(symbol)` | Real-time price updates | PriceUpdate |
| `positionUpdate` | Position changes | Position |
| `orderUpdate` | Order status updates | Order |
| `botStatusUpdate` | Bot status changes | BotStatus |
| `balanceUpdate` | Balance changes | Balance |

## 📝 Query Examples

### Get Bot Status

```graphql
query GetBotStatus {
  botStatus {
    isRunning
    isPaused
    strategy
    mode
    startTime
    uptime
    errorCount
  }
}
```

### Get Account Balance

```graphql
query GetBalance {
  balance {
    total
    available
    used
    unrealizedPnl
    realizedPnl
    currency
  }
}
```

### Get Positions with Market Data

```graphql
query GetPositionsAndMarket {
  positions {
    symbol
    side
    size
    entryPrice
    unrealizedPnl
    stopLoss
    takeProfit
  }
  marketData(symbol: "BTCUSDT") {
    lastPrice
    bidPrice
    askPrice
    volume24h
    priceChangePercent24h
  }
}
```

### Get Performance Metrics

```graphql
query GetPerformance {
  performance {
    totalTrades
    winningTrades
    losingTrades
    winRate
    totalPnl
    sharpeRatio
    maxDrawdown
    avgWin
    avgLoss
    profitFactor
  }
}
```

### Get Available Strategies

```graphql
query GetStrategies {
  strategies {
    name
    description
    isActive
    parameters
    performance {
      trades
      winRate
      pnl
      sharpeRatio
    }
  }
}
```

## 🔧 Mutation Examples

### Start Bot

```graphql
mutation StartBot {
  startBot(config: {
    strategy: "ML Ensemble"
    symbols: ["BTCUSDT", "ETHUSDT"]
    riskPerTrade: 1.0
    maxPositions: 3
    paperTrading: true
  }) {
    isRunning
    strategy
    mode
  }
}
```

### Place Order

```graphql
mutation PlaceOrder {
  placeOrder(order: {
    symbol: "BTCUSDT"
    side: "Buy"
    type: "Limit"
    quantity: 0.001
    price: 65000
    stopLoss: 63000
    takeProfit: 68000
  }) {
    id
    symbol
    status
    createdAt
  }
}
```

### Update Risk Profile

```graphql
mutation UpdateRisk {
  updateRiskProfile(profile: {
    maxPositions: 5
    maxLeverage: 3.0
    riskPerTrade: 2.0
    dailyLossLimit: 10.0
    useTrailingStop: true
    trailingStopPercent: 2.5
  }) {
    maxPositions
    riskPerTrade
    currentExposure
    valueAtRisk
  }
}
```

### Close All Positions

```graphql
mutation CloseAll {
  closeAllPositions
}
```

## 🔄 Subscription Examples

### Subscribe to Price Updates

```graphql
subscription PriceUpdates {
  priceUpdate(symbol: "BTCUSDT") {
    symbol
    price
    timestamp
  }
}
```

### Subscribe to Position Changes

```graphql
subscription PositionChanges {
  positionUpdate {
    symbol
    side
    size
    unrealizedPnl
    markPrice
  }
}
```

## 🏗 Type Definitions

### BotStatus

```graphql
type BotStatus {
  isRunning: Boolean!
  isPaused: Boolean!
  strategy: String!
  mode: String!
  startTime: String
  uptime: Int
  errorCount: Int
}
```

### Balance

```graphql
type Balance {
  total: Float!
  available: Float!
  used: Float!
  unrealizedPnl: Float!
  realizedPnl: Float!
  currency: String!
}
```

### Position

```graphql
type Position {
  symbol: String!
  side: String!
  size: Float!
  entryPrice: Float!
  markPrice: Float!
  unrealizedPnl: Float!
  realizedPnl: Float!
  leverage: Float!
  stopLoss: Float
  takeProfit: Float
  createdAt: String!
}
```

### MarketData

```graphql
type MarketData {
  symbol: String!
  lastPrice: Float!
  bidPrice: Float!
  askPrice: Float!
  volume24h: Float!
  high24h: Float!
  low24h: Float!
  priceChange24h: Float!
  priceChangePercent24h: Float!
}
```

### Performance

```graphql
type Performance {
  totalTrades: Int!
  winningTrades: Int!
  losingTrades: Int!
  winRate: Float!
  totalPnl: Float!
  sharpeRatio: Float!
  maxDrawdown: Float!
  avgWin: Float!
  avgLoss: Float!
  profitFactor: Float!
}
```

## 🔌 Client Integration

### JavaScript/TypeScript

```javascript
// Using Apollo Client
import { ApolloClient, InMemoryCache, gql } from '@apollo/client';

const client = new ApolloClient({
  uri: 'http://localhost:8000/graphql/',
  cache: new InMemoryCache()
});

// Query example
const GET_BOT_STATUS = gql`
  query GetBotStatus {
    botStatus {
      isRunning
      strategy
      mode
    }
  }
`;

client.query({ query: GET_BOT_STATUS })
  .then(result => console.log(result));

// Subscription example
const PRICE_SUBSCRIPTION = gql`
  subscription OnPriceUpdate($symbol: String!) {
    priceUpdate(symbol: $symbol) {
      price
      timestamp
    }
  }
`;

const subscription = client.subscribe({
  query: PRICE_SUBSCRIPTION,
  variables: { symbol: "BTCUSDT" }
}).subscribe({
  next: (data) => console.log(data),
  error: (err) => console.error(err),
});
```

### Python

```python
import requests

# Query example
query = """
  query {
    botStatus {
      isRunning
      strategy
      mode
    }
    balance {
      total
      available
    }
  }
"""

response = requests.post(
    'http://localhost:8000/graphql/',
    json={'query': query}
)

data = response.json()
print(data)
```

### React Hook Example

```jsx
import { useQuery, useMutation } from '@apollo/client';

function TradingDashboard() {
  // Query bot status
  const { data, loading, error } = useQuery(GET_BOT_STATUS, {
    pollInterval: 1000 // Poll every second
  });

  // Mutation to start bot
  const [startBot] = useMutation(START_BOT);

  const handleStart = () => {
    startBot({
      variables: {
        config: {
          strategy: "ML Ensemble",
          symbols: ["BTCUSDT"],
          paperTrading: true
        }
      }
    });
  };

  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error.message}</p>;

  return (
    <div>
      <h1>Bot Status: {data.botStatus.isRunning ? 'Running' : 'Stopped'}</h1>
      <button onClick={handleStart}>Start Bot</button>
    </div>
  );
}
```

## 🛡 Authentication & Security

Currently, the GraphQL API runs locally without authentication. For production deployment:

1. **Add JWT Authentication**
```python
# In graphql_server.py
from starlette.authentication import requires

@requires("authenticated")
async def resolve_sensitive_query(obj, info):
    # Protected resolver
    pass
```

2. **Rate Limiting**
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

3. **CORS Configuration**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)
```

## 🔧 Development Tools

### GraphQL Playground

Access the interactive playground at `http://localhost:8000/graphql/` when the server is running. Features:
- Schema exploration
- Query autocompletion
- Real-time results
- Query history
- Documentation browser

### Testing Queries

```bash
# Test script
cat > test_graphql.sh << 'EOF'
#!/bin/bash

# Test bot status
echo "Testing bot status..."
curl -X POST http://localhost:8000/graphql/ \
  -H "Content-Type: application/json" \
  -d '{"query":"{ botStatus { isRunning strategy } }"}' \
  | python -m json.tool

# Test balance
echo "Testing balance..."
curl -X POST http://localhost:8000/graphql/ \
  -H "Content-Type: application/json" \
  -d '{"query":"{ balance { total available } }"}' \
  | python -m json.tool
EOF

chmod +x test_graphql.sh
./test_graphql.sh
```

## 📈 Performance Considerations

1. **Query Complexity**: Limit query depth to prevent excessive resource usage
2. **Batching**: Use DataLoader pattern for efficient database queries
3. **Caching**: Implement caching for frequently accessed data
4. **Pagination**: Use cursor-based pagination for large result sets
5. **Subscriptions**: Limit concurrent subscriptions per client

## 🚀 Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY graphql_server.py .
COPY start_telegram_bot.py .
EXPOSE 8000
CMD ["python", "graphql_server.py"]
```

### Fly.io Integration

Add to existing deployment:

```toml
# fly.toml addition
[[services]]
  http_checks = []
  internal_port = 8000
  protocol = "tcp"
  
  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]
  
  [[services.ports]]
    port = 80
    handlers = ["http"]
```

## 📚 Resources

- [GraphQL Documentation](https://graphql.org/)
- [Ariadne Documentation](https://ariadnegraphql.org/)
- [Apollo Client](https://www.apollographql.com/docs/react/)
- [GraphQL Best Practices](https://graphql.org/learn/best-practices/)

---

**Version**: 1.0.0  
**Last Updated**: January 15, 2025  
**Status**: ✅ Active Development