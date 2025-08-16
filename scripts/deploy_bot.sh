#!/bin/bash
# Deploy Telegram Bot Service

set -e

echo "🤖 Deploying Telegram Bot Service"
echo "================================="

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

# Navigate to Telegram Bot directory
cd "$(dirname "$0")/../services/telegram-bot" || exit 1

# Check if app exists
if fly status -a bybit-danila-bot &> /dev/null; then
    echo -e "${GREEN}✅ App 'bybit-danila-bot' exists${NC}"
    echo "This will update the existing bot to microservice architecture"
else
    echo -e "${RED}❌ App 'bybit-danila-bot' doesn't exist${NC}"
    echo "This script updates the existing bot. Please ensure it exists first."
    exit 1
fi

# Confirm update
echo ""
echo -e "${YELLOW}⚠️  WARNING: This will update the existing Telegram bot${NC}"
echo "The bot will be restarted and may be unavailable for a few minutes."
read -p "Continue? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 1
fi

# Deploy the application
echo ""
echo "📦 Deploying Telegram Bot..."
fly deploy -a bybit-danila-bot

# Check deployment status
echo ""
echo "🔍 Checking deployment status..."
fly status -a bybit-danila-bot

# Check logs for errors
echo ""
echo "📝 Recent logs:"
fly logs -a bybit-danila-bot --limit 20

echo ""
echo -e "${GREEN}🎉 Telegram Bot deployment complete!${NC}"
echo "Test the bot by sending /balance command in Telegram"
echo "Monitor logs with: fly logs -a bybit-danila-bot --tail"