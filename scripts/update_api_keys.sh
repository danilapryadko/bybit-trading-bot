#!/bin/bash

# Script to update Bybit API keys for mainnet
# ВАЖНО: Замените эти значения на ваши реальные API ключи!

echo "🔑 Updating Bybit API Keys for MAINNET"
echo "========================================="
echo ""
echo "⚠️  ВНИМАНИЕ: Вам нужно получить API ключи с Bybit!"
echo ""
echo "1. Перейдите на: https://www.bybit.com/app/user/api-management"
echo "2. Создайте новый API ключ"
echo "3. Дайте права: Read (обязательно), Spot Trading, Derivatives"
echo "4. Скопируйте API Key и Secret"
echo ""
read -p "Введите ваш Bybit API Key: " API_KEY
read -s -p "Введите ваш Bybit API Secret: " API_SECRET
echo ""

if [ -z "$API_KEY" ] || [ -z "$API_SECRET" ]; then
    echo "❌ API ключи не могут быть пустыми!"
    exit 1
fi

echo ""
echo "📤 Обновляем API сервис..."
fly secrets set \
    BYBIT_MAINNET_API_KEY="$API_KEY" \
    BYBIT_MAINNET_API_SECRET="$API_SECRET" \
    USE_MAINNET=true \
    -a bybit-danila-api

echo ""
echo "📤 Обновляем Telegram Bot..."
fly secrets set \
    BYBIT_MAINNET_API_KEY="$API_KEY" \
    BYBIT_MAINNET_API_SECRET="$API_SECRET" \
    USE_MAINNET=true \
    -a bybit-danila-bot

echo ""
echo "✅ API ключи обновлены!"
echo ""
echo "🔍 Проверяем подключение..."
sleep 5

# Test API connection
echo "Testing API connection..."
curl -s -X POST https://bybit-danila-api.fly.dev/graphql/ \
  -H "Content-Type: application/json" \
  -d '{"query": "{ botStatus { balance isRunning } }"}' | python3 -m json.tool

echo ""
echo "========================================="
echo "Если баланс показывает 0.0, подождите 30 секунд и проверьте снова."
echo "API серверу нужно время для перезапуска с новыми ключами."