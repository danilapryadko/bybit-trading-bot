# API Keys Collection for Future Bot Enhancement
## Saved on: 2025-01-12

### 🔍 Blockchain Data APIs

**Etherscan - 100,000 запросов/день**
- App Name: dsfgsiudfgsdI
- API Key Token: B3GVEXFXPV7MTSY52TFU5VUCSGIJ957ND

**Alchemy - 300M compute units/месяц**
- Name: Anastasia's First App
- App ID: 91g35aj427dj1gna
- API Key: wpRrbbOfGmLrRnRCtgitL
- Network URL: https://worldchain-mainnet.g.alchemy.com/v2/wpRrbbOfGmLrRnRCtgitL

**Moralis - 40,000 запросов/день**
- Name: default
- API Key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6ImQwZWVjODE2LTAyNmUtNDkwZi1iN2IzLTE1MTBkNzVhOWE0ZSIsIm9yZ0lkIjoiNDY0NzM4IiwidXNlcklkIjoiNDc4MTE1IiwidHlwZUlkIjoiMmMzY2U2NzctMzY4Yi00ZjRiLTkzYzItM2VjNjYyY2IyOWY5IiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3NTQ5OTc1MDksImV4cCI6NDkxMDc1NzUwOX0.-juJsp1WyZY-aWv6eOlKGdajdvD6mfSwluB4pht4P-4

**Infura - 100,000 запросов/день**
- API Key: 12386ad664644b55b4f2450ce4e1634f
- API Key Name: My First Key
- API Key Secret: aST8QaoyVircJ9XzFGkSsGx4QHtRI5nL60ffgPdhW7P8O3oZBbwJMA

### 📊 Market Data APIs

**NewsAPI - 100 запросов/день**
- API key: 82ae1129f12142ba9db527b31ea14773

**Alpha Vantage - 500 запросов/день**
- API key: 4L0I2APC0J7P8GGD

**CoinGecko - 10,000 запросов/месяц**
- Label: new
- API Key: CG-ABFj8U5uV4k5RbCr39btNqDM

**CoinMarketCap - 10,000 запросов/месяц**
- API KEY: 0772b206-9c7f-407b-92b2-06f02f4024de

**CryptoCompare - 100,000 запросов/месяц**
- Name: new
- API key: d9bfbbf55b176bd9ed0818e76762515140e0a0421ddc03d074fe0e75f9344c73

### 📈 Technical Analysis APIs

**TAAPI.io - технические индикаторы**
- API key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbHVlIjoiNjg5YjY4MTQ4MDZmZjE2NTFlNGUxYWE3IiwiaWF0IjoxNzU1MDE1MjE5LCJleHAiOjMzMjU5NDc5MjE5fQ.H2JqIAaRz6izNR-Cv8T-GkMgYuEY9j4YP0Pj96cr_FQ

### 📊 Analytics Platforms

**Dune Analytics - SQL запросы**
- API key name: new
- API key token: bsidPJmaNtDHXjcB7JnLpAd67Kog1Dga

**Messari - фундаментальная аналитика**
- API key: +X3e4W3QvWBM2Gn4iX1Y7po0+vBvw8FWEnXSAQqbCSsUezp9

**Santiment - on-chain + социальные данные**
- API key: gtkiih7fkdh7tbg6_ocw2zd7bzzeuxxvh

### 🔗 Node Providers

**GetBlock**
- Endpoint: https://go.getblock.us/a5a60ccb4fb146c7b2d6b00e0e070aa0
- Protocol: Ethereum
- Network: Mainnet
- APIs/Add-ons: json-rpc
- Region: USA, New York

**Chainstack**
- Type: Elastic
- Node Id: ND-823-639-396
- API namespaces: eth, net, web3
- Hosting: Chainstack

**Ankr**
- Endpoint: https://rpc.ankr.com/multichain/3d08ed4429cb1113dbad55621a267776a2b61cdd7cf060e254ca5b49c2259b09

---

## 🚀 Potential Use Cases for Bot Enhancement:

### 1. Market Intelligence Module
- **CoinGecko/CoinMarketCap**: Real-time price feeds, market cap data
- **CryptoCompare**: Historical data, social stats
- **NewsAPI**: Sentiment analysis from news

### 2. On-Chain Analysis Module  
- **Etherscan/Infura/Alchemy**: Track whale wallets, smart money movements
- **Dune Analytics**: Custom queries for on-chain metrics
- **Santiment**: Social trends correlation

### 3. Advanced Technical Analysis
- **TAAPI.io**: Additional indicators not in local library
- **Alpha Vantage**: Traditional market correlation

### 4. Fundamental Analysis
- **Messari**: Project fundamentals, unlock schedules
- **Moralis**: NFT market trends, DeFi metrics

### 5. Cross-Chain Arbitrage Module
- **GetBlock/Chainstack/Ankr**: Multi-chain price monitoring
- **1inch API** (when available): DEX price comparison

---

## ⚠️ Security Notes:
- Store these keys in separate .env files when implementing
- Use different keys for production vs testing
- Implement rate limiting to avoid hitting quotas
- Monitor usage to stay within free tiers
- Rotate keys periodically for security

## 📝 Implementation Priority:
1. **High Priority**: CoinGecko, TAAPI.io (direct trading signals)
2. **Medium Priority**: NewsAPI, Dune (market sentiment)  
3. **Low Priority**: Blockchain nodes (advanced features)
