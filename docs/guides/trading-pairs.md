# 📊 Trading Pairs Configuration Guide

## Overview

The Bybit Trading Bot supports **30 carefully selected trading pairs** optimized for algorithmic trading. These pairs are categorized by type, volatility, and recommended strategies.

## 🎯 30 Trading Pairs Configuration

### Categories

| Category | Count | Purpose | Examples |
|----------|-------|---------|----------|
| **Major** | 5 | High liquidity, stable trading | BTC, ETH, BNB |
| **Layer 1** | 8 | Alternative blockchains | SOL, ADA, AVAX |
| **Layer 2** | 3 | Scaling solutions | MATIC, ARB, OP |
| **DeFi** | 5 | Decentralized finance | LINK, UNI, AAVE |
| **AI** | 3 | AI-related tokens | FET, RENDER, OCEAN |
| **Gaming** | 3 | Metaverse & gaming | SAND, AXS, IMX |
| **Meme** | 3 | High volatility scalping | DOGE, SHIB, PEPE |

## 📋 Complete Pairs List

### Major Cryptocurrencies (5)
1. **BTCUSDT** - Bitcoin (10x leverage, medium volatility)
2. **ETHUSDT** - Ethereum (15x leverage, medium volatility)
3. **BNBUSDT** - Binance Coin (10x leverage, medium volatility)
4. **XRPUSDT** - Ripple (15x leverage, medium volatility)
5. **LTCUSDT** - Litecoin (10x leverage, medium volatility)

### Layer 1 Blockchains (8)
6. **SOLUSDT** - Solana (15x leverage, high volatility)
7. **ADAUSDT** - Cardano (10x leverage, medium volatility)
8. **AVAXUSDT** - Avalanche (15x leverage, high volatility)
9. **DOTUSDT** - Polkadot (10x leverage, medium volatility)
10. **ATOMUSDT** - Cosmos (10x leverage, medium volatility)
11. **NEARUSDT** - NEAR Protocol (15x leverage, high volatility)
12. **APTUSDT** - Aptos (15x leverage, high volatility)
13. **SUIUSDT** - Sui (20x leverage, high volatility)

### Layer 2 Solutions (3)
14. **MATICUSDT** - Polygon (15x leverage, high volatility)
15. **ARBUSDT** - Arbitrum (15x leverage, high volatility)
16. **OPUSDT** - Optimism (15x leverage, high volatility)

### DeFi Tokens (5)
17. **LINKUSDT** - Chainlink (10x leverage, medium volatility)
18. **UNIUSDT** - Uniswap (10x leverage, medium volatility)
19. **AAVEUSDT** - Aave (10x leverage, medium volatility)
20. **LDOUSDT** - Lido DAO (15x leverage, high volatility)
21. **CRVUSDT** - Curve (15x leverage, high volatility)

### AI & Emerging Tech (3)
22. **FETUSDT** - Fetch.ai (20x leverage, extreme volatility)
23. **RENDERUSDT** - Render (15x leverage, high volatility)
24. **OCEANUSDT** - Ocean Protocol (20x leverage, extreme volatility)

### Gaming & Metaverse (3)
25. **SANDUSDT** - The Sandbox (15x leverage, high volatility)
26. **AXSUSDT** - Axie Infinity (15x leverage, high volatility)
27. **IMXUSDT** - Immutable X (15x leverage, high volatility)

### Meme Coins (3)
28. **DOGEUSDT** - Dogecoin (20x leverage, extreme volatility)
29. **SHIBUSDT** - Shiba Inu (20x leverage, extreme volatility)
30. **PEPEUSDT** - Pepe (20x leverage, extreme volatility)

## 🎛️ How to Manage Trading Pairs

### 1. Using Python Code

```python
from trading_pairs_config import get_pairs_manager

manager = get_pairs_manager()

# Get all active pairs
all_pairs = manager.get_all_symbols()

# Get pairs by category
major_pairs = manager.get_pairs_by_category(PairCategory.MAJOR)
defi_pairs = manager.get_pairs_by_category(PairCategory.DEFI)

# Get pairs by volatility
high_vol = manager.get_pairs_by_volatility("high")
extreme_vol = manager.get_pairs_by_volatility("extreme")

# Get recommended pairs for your balance
recommended = manager.get_recommended_pairs_for_balance(500)  # For $500

# Add/remove pairs
manager.add_pair("NEWUSDT", TradingPair(...))
manager.remove_pair("OLDUSDT")

# Enable/disable pairs
manager.toggle_pair("BTCUSDT", active=False)  # Disable
manager.toggle_pair("BTCUSDT", active=True)   # Enable
```

### 2. Using Environment Variables

Add to your `.env` file:

```bash
# Default 10 pairs
TRADING_PAIRS=BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,MATICUSDT,LINKUSDT,ARBUSDT,DOGEUSDT,AVAXUSDT,OPUSDT

# Conservative (3 pairs)
TRADING_PAIRS=BTCUSDT,ETHUSDT,BNBUSDT

# Moderate (6 pairs)
TRADING_PAIRS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,ADAUSDT,LINKUSDT

# Aggressive (all 30 pairs)
TRADING_PAIRS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,ADAUSDT,AVAXUSDT,DOTUSDT,ATOMUSDT,NEARUSDT,APTUSDT,SUIUSDT,MATICUSDT,ARBUSDT,OPUSDT,LINKUSDT,UNIUSDT,AAVEUSDT,LDOUSDT,CRVUSDT,FETUSDT,RENDERUSDT,OCEANUSDT,SANDUSDT,AXSUSDT,IMXUSDT,DOGEUSDT,SHIBUSDT,PEPEUSDT,XRPUSDT,LTCUSDT
```

### 3. Using Telegram Bot

```
/pairs list          - Show all active pairs
/pairs add BTCUSDT   - Add a trading pair
/pairs remove BTCUSDT - Remove a trading pair
/pairs enable BTCUSDT - Enable trading for pair
/pairs disable BTCUSDT - Disable trading for pair
/pairs category major - Show pairs by category
/pairs volatility high - Show pairs by volatility
```

### 4. Using REST API

```bash
# Get all pairs
GET /api/v2/pairs

# Get pairs by category
GET /api/v2/pairs?category=major

# Add pair
POST /api/v2/pairs
{
  "symbol": "NEWUSDT",
  "leverage": 10,
  "max_position": 5000
}

# Remove pair
DELETE /api/v2/pairs/OLDUSDT

# Toggle pair
PUT /api/v2/pairs/BTCUSDT/toggle
{
  "active": true
}
```

## 📈 Optimal Pairs by Strategy

### Scalping (1-5 min)
Best pairs: **DOGEUSDT, SHIBUSDT, PEPEUSDT, FETUSDT, OCEANUSDT**
- Extreme volatility
- High leverage (20x)
- Quick in/out trades

### Day Trading (5-30 min)
Best pairs: **SOLUSDT, MATICUSDT, ARBUSDT, OPUSDT, AVAXUSDT**
- High volatility
- Medium leverage (15x)
- Trend following

### Swing Trading (1h-4h)
Best pairs: **BTCUSDT, ETHUSDT, LINKUSDT, ADAUSDT, DOTUSDT**
- Medium volatility
- Lower leverage (10x)
- Position holding

### Long-term (Daily+)
Best pairs: **BTCUSDT, ETHUSDT, BNBUSDT**
- Lower volatility
- Minimal leverage (5-10x)
- Fundamental based

## 💰 Pairs by Account Size

### Small Account ($100-$1,000)
**5 pairs maximum**, focus on high volatility:
- DOGEUSDT, SHIBUSDT, PEPEUSDT, FETUSDT, SOLUSDT

### Medium Account ($1,000-$10,000)
**10 pairs**, balanced approach:
- BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, MATICUSDT
- LINKUSDT, ARBUSDT, DOGEUSDT, AVAXUSDT, OPUSDT

### Large Account ($10,000+)
**15-30 pairs**, diversified portfolio:
- All major pairs (5)
- Selected Layer 1 (5)
- DeFi tokens (5)
- Some high volatility for alpha

## ⚠️ Risk Management by Pair

### Conservative Pairs (Lower Risk)
- **BTCUSDT**: Max 30% of portfolio
- **ETHUSDT**: Max 25% of portfolio
- **BNBUSDT**: Max 20% of portfolio

### Moderate Risk Pairs
- **SOLUSDT, LINKUSDT, ADAUSDT**: Max 10% each
- **MATICUSDT, DOTUSDT**: Max 10% each

### High Risk Pairs
- **ARBUSDT, OPUSDT, APTUSDT**: Max 5% each
- **Gaming tokens**: Max 5% each

### Extreme Risk (Meme Coins)
- **DOGEUSDT, SHIBUSDT, PEPEUSDT**: Max 2-3% each
- Use only for scalping
- Never hold overnight

## 🔧 Testing Trading Pairs

Run the test script to check pair availability:

```bash
python test_trading_pairs.py
```

This will:
1. Test all 30 pairs on Bybit
2. Check current prices and volumes
3. Calculate spreads
4. Recommend optimal pairs
5. Save configuration

## 📊 Performance Metrics by Pair

Track these metrics for each pair:
- **Win Rate**: Target > 55%
- **Sharpe Ratio**: Target > 1.5
- **Max Drawdown**: Limit < 10%
- **Daily Volume**: Minimum $10M
- **Spread**: Maximum 0.1%

## 🚀 Quick Start

### For Beginners
Start with these 3 pairs:
```python
pairs = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
```

### For Intermediate
Use these 6 pairs:
```python
pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "MATICUSDT", "LINKUSDT"]
```

### For Advanced
Use the default 10 or all 30 pairs:
```python
pairs = manager.get_default_pairs()  # 10 pairs
# or
pairs = manager.get_all_symbols()    # All 30 pairs
```

## 📝 Notes

1. **Liquidity**: All selected pairs have > $10M daily volume
2. **Spreads**: Most pairs have < 0.05% spread
3. **Leverage**: Adjust based on your risk tolerance
4. **Monitoring**: Track performance per pair weekly
5. **Rebalancing**: Review and adjust pairs monthly

## 🔄 Dynamic Pair Selection

The bot can automatically select optimal pairs based on:
- Current market conditions
- Account balance
- Risk profile
- Strategy performance
- Volume and liquidity

Enable auto-selection:
```python
manager.get_optimal_pairs_for_strategy("trend_following")
manager.get_risk_adjusted_pairs("moderate")
```

## 📈 Backtesting with Pairs

Test strategies on different pairs:
```bash
# Test single pair
python backtesting_engine.py --symbol BTCUSDT

# Test multiple pairs
python backtesting_engine.py --symbols BTCUSDT ETHUSDT SOLUSDT

# Test by category
python backtesting_engine.py --category major
```

## 🎯 Conclusion

The 30 configured pairs provide:
- **Diversification** across different sectors
- **Flexibility** for various strategies
- **Risk management** through categorization
- **Scalability** from small to large accounts
- **Adaptability** to market conditions

Start with a few pairs and gradually expand as you gain experience and capital.