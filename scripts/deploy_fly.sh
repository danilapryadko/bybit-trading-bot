#!/bin/bash

# deploy_fly.sh - Deploy script for Fly.io

set -e

echo "🚀 Deploying Bybit Trading Bot to Fly.io..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo -e "${RED}❌ Fly CLI not found!${NC}"
    echo "Please install it from: https://fly.io/docs/hands-on/install-flyctl/"
    exit 1
fi

# Check if logged in to Fly.io
if ! fly auth whoami &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not logged in to Fly.io${NC}"
    echo "Logging in..."
    fly auth login
fi

# Function to set secrets
set_secrets() {
    echo -e "${YELLOW}📝 Setting secrets...${NC}"
    
    # Check if .env file exists
    if [ ! -f ../.env ]; then
        echo -e "${RED}❌ .env file not found!${NC}"
        echo "Please create .env file with your API keys"
        exit 1
    fi
    
    # Load .env file
    source ../.env
    
    # Set secrets in Fly.io
    echo "Setting API keys..."
    fly secrets set API_KEY=$API_KEY API_SECRET=$API_SECRET --app bybit-trading-bot
    
    echo "Setting trading parameters..."
    fly secrets set \
        SYMBOL=$SYMBOL \
        LEVERAGE=$LEVERAGE \
        POSITION_SIZE=$POSITION_SIZE \
        STOP_LOSS_PERCENT=$STOP_LOSS_PERCENT \
        TAKE_PROFIT_PERCENT=$TAKE_PROFIT_PERCENT \
        --app bybit-trading-bot
    
    echo -e "${GREEN}✅ Secrets set successfully${NC}"
}

# Function to create app
create_app() {
    echo -e "${YELLOW}📱 Creating Fly.io app...${NC}"
    
    if fly apps list | grep -q "bybit-trading-bot"; then
        echo "App already exists, skipping creation..."
    else
        fly apps create bybit-trading-bot --region sin
        echo -e "${GREEN}✅ App created${NC}"
    fi
}

# Function to create database
create_database() {
    echo -e "${YELLOW}💾 Creating PostgreSQL database...${NC}"
    
    if fly postgres list | grep -q "bybit-trading-bot-db"; then
        echo "Database already exists, skipping creation..."
    else
        fly postgres create --name bybit-trading-bot-db --region sin --initial-cluster-size 1 --vm-size shared-cpu-1x --volume-size 1
        
        # Attach database to app
        fly postgres attach bybit-trading-bot-db --app bybit-trading-bot
        
        echo -e "${GREEN}✅ Database created and attached${NC}"
    fi
}

# Function to create Redis
create_redis() {
    echo -e "${YELLOW}🔴 Creating Redis instance...${NC}"
    
    # Fly.io uses Upstash Redis
    fly redis create --name bybit-trading-bot-redis --region sin --plan free
    
    echo -e "${GREEN}✅ Redis created${NC}"
}

# Function to deploy
deploy() {
    echo -e "${YELLOW}🚢 Deploying application...${NC}"
    
    # Deploy with Dockerfile.fly
    fly deploy --dockerfile Dockerfile.fly --strategy rolling
    
    echo -e "${GREEN}✅ Deployment complete${NC}"
}

# Function to check status
check_status() {
    echo -e "${YELLOW}📊 Checking deployment status...${NC}"
    
    fly status --app bybit-trading-bot
    
    echo ""
    echo -e "${GREEN}🎉 Deployment successful!${NC}"
    echo ""
    echo "📌 Your app is available at:"
    echo "   https://bybit-trading-bot.fly.dev"
    echo ""
    echo "📊 Monitoring:"
    echo "   Health: https://bybit-trading-bot.fly.dev/health"
    echo "   Status: https://bybit-trading-bot.fly.dev/status"
    echo "   Metrics: https://bybit-trading-bot.fly.dev/metrics"
    echo ""
    echo "📝 Useful commands:"
    echo "   fly logs                    - View logs"
    echo "   fly ssh console             - SSH into container"
    echo "   fly secrets list            - List secrets"
    echo "   fly scale count 2           - Scale to 2 instances"
    echo "   fly regions add hkg         - Add Hong Kong region"
}

# Main deployment flow
main() {
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   Bybit Trading Bot - Fly.io Deploy   ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    echo ""
    
    # Ask for confirmation
    read -p "Deploy to production? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled"
        exit 0
    fi
    
    # Ask about testnet
    read -p "Use TESTNET? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        export BYBIT_TESTNET=false
        echo -e "${RED}⚠️  WARNING: Using REAL trading!${NC}"
    else
        export BYBIT_TESTNET=true
        echo -e "${GREEN}✅ Using TESTNET${NC}"
    fi
    
    # Deployment steps
    create_app
    create_database
    create_redis
    set_secrets
    deploy
    check_status
}

# Run main function
main
