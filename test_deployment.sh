#!/bin/bash

echo "🔍 Testing Bybit Bot Deployment"
echo "================================"

# Test main bot API
echo ""
echo "1. Testing main bot API (bybit-danila-bot)..."
echo "   URL: https://bybit-danila-bot.fly.dev"

# Test health endpoint
echo "   - Health check:"
curl -s -w "\n   HTTP Status: %{http_code}\n" https://bybit-danila-bot.fly.dev/health

# Test GraphQL endpoint
echo ""
echo "   - GraphQL endpoint:"
curl -s -X POST https://bybit-danila-bot.fly.dev/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ botStatus { isRunning } }"}' \
  -w "\n   HTTP Status: %{http_code}\n"

# Test Dashboard
echo ""
echo "2. Testing Dashboard (bybit-danila-dashboard)..."
echo "   URL: https://bybit-danila-dashboard.fly.dev"
curl -s -o /dev/null -w "   HTTP Status: %{http_code}\n" https://bybit-danila-dashboard.fly.dev

echo ""
echo "================================"
echo "📊 Summary:"
echo ""
echo "If you see HTTP 404 or connection errors, the deployment needs to be updated."
echo ""
echo "To fix WebSocket issues:"
echo "1. Deploy the updated bot:"
echo "   fly deploy -a bybit-danila-bot"
echo ""
echo "2. Check logs:"
echo "   fly logs -a bybit-danila-bot"
echo ""
echo "3. SSH into the container to debug:"
echo "   fly ssh console -a bybit-danila-bot"
echo "   python3 -c 'from bybit_connector import get_bybit_connector; print(get_bybit_connector().get_balance())'"