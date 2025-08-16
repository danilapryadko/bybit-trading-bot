#!/bin/bash

echo "🚀 Deploying Bybit Trading Bot to Fly.io"
echo "========================================"

# Check if fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo "❌ Fly CLI not found. Please install it first:"
    echo "   curl -L https://fly.io/install.sh | sh"
    exit 1
fi

echo "✅ Fly CLI found"

# Deploy the bot
echo ""
echo "📦 Deploying application..."
fly deploy -a bybit-danila-bot

# Show status
echo ""
echo "📊 Checking deployment status..."
fly status -a bybit-danila-bot

# Show logs
echo ""
echo "📜 Recent logs:"
fly logs -a bybit-danila-bot --limit 20

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🔗 URLs:"
echo "   - GraphQL API: https://bybit-danila-bot.fly.dev/graphql"
echo "   - Dashboard: https://bybit-danila-dashboard.fly.dev"
echo ""
echo "💡 To switch to MAINNET (real money):"
echo "   fly secrets set USE_MAINNET=true -a bybit-danila-bot"
echo ""
echo "📊 To check real balance:"
echo "   fly ssh console -a bybit-danila-bot"
echo "   python3 -c 'from bybit_connector import get_bybit_connector; print(get_bybit_connector().get_balance())'"