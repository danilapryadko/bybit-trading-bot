#!/bin/bash

# setup_github_secrets.sh - Configure GitHub Secrets for CI/CD

set -e

echo "🔐 Setting up GitHub Secrets for CI/CD Pipeline"
echo "================================================"
echo ""
echo "This script will help you set up the required secrets for GitHub Actions."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI not found!${NC}"
    echo "Please install it:"
    echo "  macOS: brew install gh"
    echo "  Linux: https://github.com/cli/cli#installation"
    exit 1
fi

# Check if logged in
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not logged in to GitHub${NC}"
    echo "Logging in..."
    gh auth login
fi

echo -e "${GREEN}✅ GitHub CLI ready${NC}"
echo ""

# Function to set secret
set_secret() {
    local name=$1
    local prompt=$2
    local required=$3
    
    echo -e "${YELLOW}$prompt${NC}"
    if [ "$required" = "true" ]; then
        read -s value
        echo ""
        if [ -z "$value" ]; then
            echo -e "${RED}❌ This secret is required!${NC}"
            exit 1
        fi
    else
        read -s value
        echo ""
        if [ -z "$value" ]; then
            echo "Skipping (optional)..."
            return
        fi
    fi
    
    gh secret set "$name" --body "$value"
    echo -e "${GREEN}✅ $name set${NC}"
}

echo "📝 Setting Required Secrets:"
echo "=============================="

# Required secrets
set_secret "FLY_API_TOKEN" "Enter your Fly.io API token (get from: fly auth token):" true

echo ""
echo "📝 Setting Optional Secrets:"
echo "=============================="

# Optional secrets
set_secret "TEST_API_KEY" "Enter Bybit Testnet API Key (optional):" false
set_secret "TEST_API_SECRET" "Enter Bybit Testnet API Secret (optional):" false
set_secret "TELEGRAM_BOT_TOKEN" "Enter Telegram Bot Token for notifications (optional):" false
set_secret "TELEGRAM_CHAT_ID" "Enter Telegram Chat ID (optional):" false

echo ""
echo -e "${GREEN}✅ All secrets configured!${NC}"
echo ""
echo "📊 Current secrets:"
gh secret list

echo ""
echo "🚀 Next steps:"
echo "  1. Commit and push your code"
echo "  2. GitHub Actions will automatically run"
echo "  3. Check Actions tab in GitHub for pipeline status"
echo ""
echo "📝 To add more secrets later:"
echo "  gh secret set SECRET_NAME"
echo ""
echo "🔍 To view secret details:"
echo "  gh secret list"
