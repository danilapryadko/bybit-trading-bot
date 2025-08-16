#!/bin/bash
# Deploy GraphQL API Service

set -e

echo "🚀 Deploying GraphQL API Service"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo -e "${RED}❌ Fly CLI is not installed${NC}"
    echo "Install it with: brew install flyctl"
    exit 1
fi

# Navigate to GraphQL API directory
cd "$(dirname "$0")/../services/graphql-api" || exit 1

# Check if app exists
if fly status -a bybit-danila-api &> /dev/null; then
    echo -e "${GREEN}✅ App 'bybit-danila-api' exists${NC}"
else
    echo -e "${YELLOW}⚠️  App 'bybit-danila-api' doesn't exist${NC}"
    echo "Creating new app..."
    fly apps create bybit-danila-api --org personal
    
    echo ""
    echo "Setting secrets..."
    echo -e "${YELLOW}Please set the following secrets:${NC}"
    echo "fly secrets set BYBIT_API_KEY='your-key' -a bybit-danila-api"
    echo "fly secrets set BYBIT_API_SECRET='your-secret' -a bybit-danila-api"
    echo "fly secrets set BYBIT_MAINNET_API_KEY='your-mainnet-key' -a bybit-danila-api"
    echo "fly secrets set BYBIT_MAINNET_API_SECRET='your-mainnet-secret' -a bybit-danila-api"
    echo "fly secrets set DATABASE_URL='your-database-url' -a bybit-danila-api"
    echo "fly secrets set USE_MAINNET='false' -a bybit-danila-api"
    echo ""
    read -p "Press enter when secrets are set..."
fi

# Deploy the application
echo ""
echo "📦 Deploying GraphQL API..."
fly deploy -a bybit-danila-api

# Check deployment status
echo ""
echo "🔍 Checking deployment status..."
fly status -a bybit-danila-api

# Test health endpoint
echo ""
echo "🏥 Testing health endpoint..."
if curl -s https://bybit-danila-api.fly.dev/health | grep -q "healthy"; then
    echo -e "${GREEN}✅ Health check passed!${NC}"
    curl -s https://bybit-danila-api.fly.dev/health | python3 -m json.tool
else
    echo -e "${RED}❌ Health check failed${NC}"
    echo "Check logs with: fly logs -a bybit-danila-api"
fi

echo ""
echo -e "${GREEN}🎉 GraphQL API deployment complete!${NC}"
echo "GraphQL endpoint: https://bybit-danila-api.fly.dev/graphql"
echo "Health endpoint: https://bybit-danila-api.fly.dev/health"