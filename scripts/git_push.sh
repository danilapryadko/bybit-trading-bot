#!/bin/bash

# git_push.sh - Initialize git and push to GitHub

set -e

echo "🚀 Initializing Git and Pushing to GitHub"
echo "========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Project directory
PROJECT_DIR="/Users/danilapryadkoicloud.com/Documents/bybit-trading-bot/WORK IN THIS FOLDER"
cd "$PROJECT_DIR"

# Check if git is initialized
if [ ! -d .git ]; then
    echo -e "${YELLOW}📦 Initializing Git repository...${NC}"
    git init
    echo -e "${GREEN}✅ Git initialized${NC}"
else
    echo -e "${GREEN}✅ Git already initialized${NC}"
fi

# Configure git user (if not set)
if [ -z "$(git config user.email)" ]; then
    echo -e "${YELLOW}Setting git user configuration...${NC}"
    git config user.email "danilapryadko@icloud.com"
    git config user.name "Danila Pryadko"
fi

# Add remote if not exists
if ! git remote | grep -q origin; then
    echo -e "${YELLOW}📡 Adding remote origin...${NC}"
    git remote add origin https://github.com/danilapryadko/bbBot.git
    echo -e "${GREEN}✅ Remote added${NC}"
else
    echo -e "${GREEN}✅ Remote already configured${NC}"
fi

# Check for uncommitted changes
echo -e "${YELLOW}📋 Checking repository status...${NC}"
git status

# Add all files
echo -e "${YELLOW}📦 Adding files to staging...${NC}"
git add .

# Show what will be committed
echo -e "${BLUE}Files to be committed:${NC}"
git status --short

# Create commit
echo -e "${YELLOW}💾 Creating commit...${NC}"
COMMIT_MSG="Phase 0 Complete: Infrastructure ready with CI/CD

- ✅ Complete project structure
- ✅ Docker environment for local development
- ✅ PostgreSQL database with schema
- ✅ GitHub Actions CI/CD pipeline
- ✅ Fly.io deployment configuration
- ✅ Health monitoring and metrics
- ✅ Automated testing setup
- ✅ Security scanning with Trivy
- ✅ Daily performance reports
- ✅ Telegram notifications support

Ready for deployment and Phase 1 development!"

git commit -m "$COMMIT_MSG" || echo -e "${YELLOW}No changes to commit${NC}"

# Check current branch
CURRENT_BRANCH=$(git branch --show-current)
if [ -z "$CURRENT_BRANCH" ]; then
    echo -e "${YELLOW}📌 No branch detected, creating main branch...${NC}"
    git checkout -b main
    CURRENT_BRANCH="main"
fi

echo -e "${BLUE}Current branch: $CURRENT_BRANCH${NC}"

# Push to GitHub
echo -e "${YELLOW}📤 Pushing to GitHub...${NC}"
echo ""

# Try to push
if git push -u origin $CURRENT_BRANCH; then
    echo -e "${GREEN}✅ Successfully pushed to GitHub!${NC}"
else
    echo -e "${YELLOW}⚠️  Push failed, trying force push for first commit...${NC}"
    read -p "Force push? This will overwrite remote (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push -u origin $CURRENT_BRANCH --force
        echo -e "${GREEN}✅ Force pushed successfully!${NC}"
    else
        echo -e "${RED}❌ Push cancelled${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}🎉 SUCCESS! Code pushed to GitHub${NC}"
echo ""
echo "📊 Repository Info:"
echo "  URL: https://github.com/danilapryadko/bbBot"
echo "  Branch: $CURRENT_BRANCH"
echo ""
echo "🔄 GitHub Actions:"
echo "  CI/CD Pipeline will start automatically"
echo "  View at: https://github.com/danilapryadko/bbBot/actions"
echo ""
echo "📝 Next Steps:"
echo "  1. Set up GitHub Secrets: ./scripts/setup_github_secrets.sh"
echo "  2. Configure Fly.io: fly launch"
echo "  3. Deploy to Fly.io: fly deploy"
echo ""
echo "🚀 Happy Trading!"
