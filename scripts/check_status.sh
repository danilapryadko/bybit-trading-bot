#!/bin/bash
# Check status of all services

echo "📊 Microservices Status Check"
echo "============================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check service
check_service() {
    local service_name=$1
    local app_name=$2
    local health_url=$3
    
    echo -e "${BLUE}$service_name${NC}"
    echo "--------------------"
    
    # Check Fly.io status
    if fly status -a "$app_name" &> /dev/null; then
        echo -e "${GREEN}✅ Fly.io app exists${NC}"
        
        # Get machine status
        status=$(fly status -a "$app_name" 2>/dev/null | grep -E "started|stopped" | head -1)
        if echo "$status" | grep -q "started"; then
            echo -e "${GREEN}✅ Service is running${NC}"
        else
            echo -e "${RED}❌ Service is not running${NC}"
        fi
    else
        echo -e "${RED}❌ Fly.io app doesn't exist${NC}"
        return
    fi
    
    # Check health endpoint if provided
    if [ -n "$health_url" ]; then
        echo -n "🏥 Health check: "
        if curl -s --max-time 5 "$health_url" | grep -q "healthy"; then
            echo -e "${GREEN}HEALTHY${NC}"
        else
            echo -e "${RED}UNHEALTHY or TIMEOUT${NC}"
        fi
    fi
    
    echo ""
}

# Check GraphQL API
check_service "GraphQL API Service" "bybit-danila-api" "https://bybit-danila-api.fly.dev/health"

# Check Telegram Bot
check_service "Telegram Bot Service" "bybit-danila-bot" ""

# Check Dashboard
echo -e "${BLUE}Dashboard${NC}"
echo "--------------------"
if curl -s --max-time 5 "https://bybit-danila-dashboard.fly.dev" > /dev/null; then
    echo -e "${GREEN}✅ Dashboard is accessible${NC}"
else
    echo -e "${RED}❌ Dashboard is not accessible${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}Quick Commands:${NC}"
echo "--------------------"
echo "View API logs:  fly logs -a bybit-danila-api --tail"
echo "View Bot logs:  fly logs -a bybit-danila-bot --tail"
echo "SSH to API:     fly ssh console -a bybit-danila-api"
echo "SSH to Bot:     fly ssh console -a bybit-danila-bot"
echo ""
echo "Deploy API:     ./scripts/deploy_api.sh"
echo "Deploy Bot:     ./scripts/deploy_bot.sh"
echo "Deploy All:     ./scripts/deploy_all.sh"