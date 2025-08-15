#!/bin/bash

echo "╔══════════════════════════════════════════════════════╗"
echo "║     Starting Bybit Trading Bot with Telegram        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo "✅ Created .env file"
fi

echo ""
echo "🚀 Starting bot..."
echo "📱 Telegram: @bybit_danila_trading_bot"
echo "👤 User: @koshkikoshki (Данила Прядко)"
echo "💰 Mode: Paper Trading on Testnet"
echo ""
echo "Press Ctrl+C to stop"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run the bot
python run_with_telegram.py