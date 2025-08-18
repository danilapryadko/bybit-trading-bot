# 🔧 Troubleshooting Guide

## Common Issues and Solutions

### 🔴 Critical Issues

#### 1. Dashboard Shows "Disconnected" Status

**Symptoms**:
- Status shows "Reconnecting... (attempt X)"
- Balance shows $0.00
- No price updates

**Solutions**:

1. **Check API URL**:
```javascript
// frontend/.env.production
VITE_API_URL=https://bybit-danila-api.fly.dev  // No /api suffix!
```

2. **Verify API is running**:
```bash
curl https://bybit-danila-api.fly.dev/health
```

3. **Check API logs**:
```bash
fly logs -a bybit-danila-api
```

4. **Restart API service**:
```bash
fly apps restart bybit-danila-api
```

#### 2. Balance Shows 0 or Wrong Amount

**Symptoms**:
- Balance shows 0 USDT
- Balance doesn't match Bybit account

**Solutions**:

1. **Check account type**:
```python
# Money might be in Funding Account, not Unified Account
# Transfer via Bybit website: Assets → Transfer → Funding to Unified
```

2. **Verify API keys**:
```bash
fly secrets list -a bybit-danila-api
# Ensure USE_MAINNET=true for real money
```

3. **Check API permissions**:
- Log into Bybit
- API Management → Check permissions
- Needs: "Account Balance" and "Positions"

#### 3. Orders Not Executing

**Symptoms**:
- Order form submits but nothing happens
- No order in Bybit account

**Current Status**: ⚠️ **Not Implemented**

**Temporary Workaround**:
```javascript
// Orders are not connected to backend yet
// Use Bybit web/app for actual trading
```

**Future Fix** (Phase 1 of Roadmap):
```graphql
mutation PlaceOrder($input: OrderInput!) {
  placeOrder(input: $input) {
    orderId
    status
  }
}
```

### 🟡 Warning Issues

#### 4. "Empty String to Float" Error

**Error Message**:
```
ValueError: could not convert string to float: ''
```

**Solution**:
```python
# In bybit_connector.py
balance_str = coin.get('availableToWithdraw', '0')
if balance_str == '':
    balance_str = coin.get('walletBalance', '0')
balance = float(balance_str or 0)
```

#### 5. CORS Errors in Browser

**Error Message**:
```
Access to fetch at 'api.fly.dev' from origin 'dashboard.fly.dev' has been blocked by CORS
```

**Solution**:
```python
# In services/graphql-api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://bybit-danila-dashboard.fly.dev"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 6. WebSocket Connection Failed

**Error Message**:
```
WebSocket connection to 'wss://...' failed
```

**Solutions**:

1. **Check WebSocket URL**:
```javascript
// Correct URL for Bybit
const ws = new WebSocket('wss://stream.bybit.com/v5/public/linear');
```

2. **Implement reconnection**:
```javascript
let reconnectAttempts = 0;
function connect() {
    ws = new WebSocket(url);
    ws.onerror = () => {
        setTimeout(() => {
            reconnectAttempts++;
            connect();
        }, Math.min(1000 * Math.pow(2, reconnectAttempts), 30000));
    };
}
```

### 🟢 Minor Issues

#### 7. Watchlist Not Persisting

**Symptoms**:
- Added pairs disappear on refresh

**Solution**:
```javascript
// Save to localStorage
localStorage.setItem('tradingWatchlist', JSON.stringify(watchlist));

// Load on mount
useEffect(() => {
    const saved = localStorage.getItem('tradingWatchlist');
    if (saved) {
        const watchlist = JSON.parse(saved);
        // Restore watchlist
    }
}, []);
```

#### 8. Chart Not Loading

**Symptoms**:
- Price chart shows blank
- "Loading..." message persists

**Solutions**:

1. **Check data format**:
```javascript
// Klines need proper timestamp format
const chartData = klines.map(k => ({
    time: k.timestamp, // Must be Unix timestamp in seconds
    open: k.open,
    high: k.high,
    low: k.low,
    close: k.close
}));
```

2. **Verify symbol exists**:
```graphql
query {
  klines(symbol: "BTCUSDT", interval: "15") {
    timestamp
    close
  }
}
```

#### 9. Settings Not Saving

**Current Status**: ⚠️ **Not Implemented**

**Temporary Workaround**:
```javascript
// Store in localStorage for now
localStorage.setItem('settings', JSON.stringify(settings));
```

## 🔍 Debugging Tools

### Browser DevTools

1. **Network Tab**:
```javascript
// Check API calls
Filter: XHR
Look for red (failed) requests
Check response codes and bodies
```

2. **Console**:
```javascript
// Enable verbose logging
localStorage.setItem('debug', 'true');
window.location.reload();
```

3. **Redux DevTools**:
```javascript
// Install browser extension
// View state changes in real-time
```

### API Testing

1. **GraphQL Playground**:
```
https://bybit-danila-api.fly.dev/graphql
```

2. **cURL Tests**:
```bash
# Test balance
curl -X POST https://bybit-danila-api.fly.dev/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ balance { total available } }"}'

# Test ticker
curl -X POST https://bybit-danila-api.fly.dev/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ ticker(symbol: \"BTCUSDT\") { price } }"}'
```

3. **Health Check**:
```bash
curl https://bybit-danila-api.fly.dev/health
```

### Log Analysis

1. **API Logs**:
```bash
fly logs -a bybit-danila-api --tail 100
```

2. **Frontend Logs**:
```bash
fly logs -a bybit-danila-dashboard --tail 100
```

3. **SSH into Container**:
```bash
fly ssh console -a bybit-danila-api
# Check environment
env | grep BYBIT
# Test Python imports
python -c "import bybit_connector; print('OK')"
```

## 🚨 Emergency Procedures

### Service Down

1. **Quick Restart**:
```bash
fly apps restart bybit-danila-api
fly apps restart bybit-danila-dashboard
```

2. **Scale Up**:
```bash
fly scale count 2 -a bybit-danila-api
```

3. **Rollback**:
```bash
fly releases -a bybit-danila-api
fly deploy --image registry.fly.io/bybit-danila-api:v[PREVIOUS]
```

### Data Issues

1. **Database Connection Lost**:
```bash
# Check connection
fly postgres connect -a trading-db

# Restart database
fly postgres restart -a trading-db
```

2. **Corrupted State**:
```javascript
// Clear Redux state
localStorage.clear();
window.location.reload();
```

### API Key Issues

1. **Invalid API Key**:
```bash
# Update secrets
fly secrets set BYBIT_API_KEY=new-key -a bybit-danila-api
fly secrets set BYBIT_API_SECRET=new-secret -a bybit-danila-api
```

2. **Rate Limited**:
```python
# Implement rate limiting
import time
from functools import wraps

def rate_limit(calls=10, period=60):
    def decorator(func):
        last_reset = [time.time()]
        calls_made = [0]
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            if now - last_reset[0] > period:
                calls_made[0] = 0
                last_reset[0] = now
            
            if calls_made[0] >= calls:
                sleep_time = period - (now - last_reset[0])
                time.sleep(sleep_time)
                calls_made[0] = 0
                last_reset[0] = time.time()
            
            calls_made[0] += 1
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

## 📊 Performance Issues

### Slow Loading

1. **Optimize Queries**:
```graphql
# Bad - multiple queries
query {
  balance { total }
}
query {
  ticker(symbol: "BTCUSDT") { price }
}

# Good - batched query
query {
  balance { total }
  ticker(symbol: "BTCUSDT") { price }
}
```

2. **Enable Caching**:
```python
from functools import lru_cache

@lru_cache(maxsize=100, ttl=5)  # 5 second cache
def get_ticker(symbol):
    return bybit_client.get_ticker(symbol)
```

3. **Reduce Update Frequency**:
```javascript
// Adjust polling intervals
const TICKER_INTERVAL = 5000;  // 5 seconds
const BALANCE_INTERVAL = 10000; // 10 seconds
const KLINES_INTERVAL = 30000;  // 30 seconds
```

### High Memory Usage

1. **Check for Memory Leaks**:
```javascript
// Clear intervals on unmount
useEffect(() => {
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval); // Important!
}, []);
```

2. **Limit Data Retention**:
```javascript
// Keep only recent data
const MAX_KLINES = 500;
if (klines.length > MAX_KLINES) {
    klines = klines.slice(-MAX_KLINES);
}
```

## 🔗 Useful Resources

### Documentation
- [Bybit API Docs](https://bybit-exchange.github.io/docs/v5/intro)
- [Fly.io Docs](https://fly.io/docs/)
- [GraphQL Best Practices](https://graphql.org/learn/best-practices/)
- [React Performance](https://react.dev/learn/render-and-commit)

### Support Channels
- GitHub Issues: [Report bugs](https://github.com/your-repo/issues)
- Bybit Support: [API issues](https://www.bybit.com/en-US/help-center)
- Fly.io Support: [Infrastructure](https://fly.io/docs/about/support/)

### Monitoring Tools
- [Fly.io Metrics](https://fly.io/dashboard)
- [GraphQL Playground](https://bybit-danila-api.fly.dev/graphql)
- Browser DevTools (F12)

## 📝 Checklist for New Issues

Before reporting a new issue, check:

- [ ] API is running: `curl https://bybit-danila-api.fly.dev/health`
- [ ] Correct environment variables set
- [ ] Browser console for JavaScript errors
- [ ] Network tab for failed requests
- [ ] API logs for server errors
- [ ] Bybit API status page
- [ ] Clear browser cache and cookies
- [ ] Try incognito/private browsing
- [ ] Test on different network
- [ ] Check GitHub issues for similar problems

## 🆘 Contact Support

If issue persists after trying all solutions:

1. **Collect Information**:
   - Error messages (exact text)
   - Screenshots
   - Browser/OS version
   - Time of occurrence
   - Steps to reproduce

2. **Create GitHub Issue**:
   - Use issue template
   - Include all collected information
   - Tag appropriately (bug, enhancement, etc.)

3. **Emergency Contact**:
   - Telegram: @your_support_bot
   - Email: support@your-domain.com

---

*Last Updated: December 2024*
*Version: 1.0.0*