#!/bin/bash
# Deploy All Microservices

set -e

echo "🚀 Full Microservices Deployment"
echo "================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo -e "${RED}❌ Fly CLI is not installed${NC}"
    echo "Install it with: brew install flyctl"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${BLUE}Phase 1: Deploy GraphQL API Service${NC}"
echo "----------------------------------------"
bash "$SCRIPT_DIR/deploy_api.sh"

echo ""
echo -e "${BLUE}Phase 2: Update Dashboard Configuration${NC}"
echo "----------------------------------------"
echo -e "${YELLOW}Please update your dashboard to use the new API endpoint:${NC}"
echo "Old: https://bybit-danila-bot.fly.dev/graphql"
echo "New: https://bybit-danila-api.fly.dev/graphql"
echo ""
read -p "Press enter when dashboard is updated..."

echo ""
echo -e "${BLUE}Phase 3: Deploy Telegram Bot Service${NC}"
echo "----------------------------------------"
bash "$SCRIPT_DIR/deploy_bot.sh"

echo ""
echo -e "${GREEN}✨ All services deployed successfully!${NC}"
echo ""
echo "Service Status:"
echo "- GraphQL API: https://bybit-danila-api.fly.dev"
echo "- Telegram Bot: @bybit_danila_trading_bot"
echo "- Dashboard: https://bybit-danila-dashboard.fly.dev"
echo ""
echo "Monitor services:"
echo "- API logs: fly logs -a bybit-danila-api --tail"
echo "- Bot logs: fly logs -a bybit-danila-bot --tail"