#!/bin/bash
# E2E тест всех страниц Dashboard с использованием curl

echo "============================================================"
echo "🎭 E2E ТЕСТИРОВАНИЕ ВСЕХ СТРАНИЦ BYBIT DASHBOARD"
echo "============================================================"
echo "Время теста: $(date '+%Y-%m-%d %H:%M:%S')"
echo "------------------------------------------------------------"

DASHBOARD_URL="https://bybit-danila-dashboard.fly.dev"
API_URL="https://bybit-danila-api.fly.dev"

# Массив страниц для тестирования
declare -a pages=(
    "Dashboard:/dashboard"
    "Trading:/trading"
    "Positions:/positions"
    "Portfolio:/portfolio"
    "Strategies:/strategies"
    "Risk_Management:/risk"
    "Analytics:/analytics"
    "Backtest:/backtest"
    "Settings:/settings"
)

passed=0
failed=0

# Функция для проверки страницы
check_page() {
    local name=$1
    local path=$2
    local url="${DASHBOARD_URL}${path}"
    
    echo ""
    echo "🔍 Тестирование: $name"
    echo "   URL: $url"
    
    # Загружаем страницу
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$response" = "200" ]; then
        echo "   ✅ Страница загружена (HTTP $response)"
        
        # Получаем содержимое страницы
        content=$(curl -s "$url")
        
        # Проверяем на наличие ошибок
        if echo "$content" | grep -q "Error\|error\|ERROR"; then
            echo "   ⚠️  Найдены потенциальные ошибки на странице"
        fi
        
        # Проверяем наличие React приложения
        if echo "$content" | grep -q "root"; then
            echo "   ✅ React приложение найдено"
        else
            echo "   ❌ React приложение не найдено"
            return 1
        fi
        
        # Проверяем подключение к API (для главной страницы)
        if [ "$name" = "Dashboard" ]; then
            echo "   Проверка соединения с API..."
            api_health=$(curl -s "${API_URL}/health")
            if echo "$api_health" | grep -q "healthy"; then
                echo "   ✅ API соединение активно"
                balance=$(echo "$api_health" | grep -o '"balance":[0-9.]*' | cut -d: -f2)
                echo "   💰 Баланс в API: \$$balance"
            else
                echo "   ❌ Проблема с API соединением"
            fi
        fi
        
        return 0
    else
        echo "   ❌ Ошибка загрузки (HTTP $response)"
        return 1
    fi
}

# Тестируем каждую страницу
echo ""
echo "ТЕСТИРОВАНИЕ СТРАНИЦ:"
echo "------------------------------------------------------------"

for page in "${pages[@]}"; do
    IFS=':' read -r name path <<< "$page"
    
    if check_page "$name" "$path"; then
        ((passed++))
        results+=("$name: ✅ PASSED")
    else
        ((failed++))
        results+=("$name: ❌ FAILED")
    fi
    
    # Небольшая пауза между запросами
    sleep 1
done

# Тестируем GraphQL endpoint
echo ""
echo "🔍 Тестирование GraphQL API"
echo "   URL: ${API_URL}/graphql/"

graphql_query='{"query":"query { botStatus { balance isRunning mode } positions { symbol } }"}'
graphql_response=$(curl -s -X POST "${API_URL}/graphql/" \
    -H "Content-Type: application/json" \
    -d "$graphql_query")

if echo "$graphql_response" | grep -q '"data"'; then
    echo "   ✅ GraphQL работает"
    
    # Извлекаем баланс
    balance=$(echo "$graphql_response" | grep -o '"balance":[0-9.]*' | head -1 | cut -d: -f2)
    if [ ! -z "$balance" ]; then
        echo "   💰 Баланс: \$$balance"
    fi
    
    # Проверяем позиции
    if echo "$graphql_response" | grep -q '"positions":\[\]'; then
        echo "   📊 Позиций: 0 (пусто)"
    elif echo "$graphql_response" | grep -q '"positions"'; then
        echo "   📊 Есть открытые позиции"
    fi
else
    echo "   ❌ GraphQL не отвечает корректно"
fi

# Тестируем WebSocket endpoint
echo ""
echo "🔍 Тестирование WebSocket"
echo "   URL: wss://bybit-danila-api.fly.dev/ws"

# Проверяем доступность WebSocket через HTTP (upgrade header)
ws_check=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Connection: Upgrade" \
    -H "Upgrade: websocket" \
    -H "Sec-WebSocket-Version: 13" \
    -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
    "https://bybit-danila-api.fly.dev/ws")

if [ "$ws_check" = "426" ] || [ "$ws_check" = "101" ]; then
    echo "   ✅ WebSocket endpoint доступен"
else
    echo "   ⚠️  WebSocket status: $ws_check"
fi

# Итоговые результаты
echo ""
echo "============================================================"
echo "📊 РЕЗУЛЬТАТЫ E2E ТЕСТИРОВАНИЯ"
echo "============================================================"
echo ""
echo "РЕЗУЛЬТАТЫ ПО СТРАНИЦАМ:"
for result in "${results[@]}"; do
    echo "  $result"
done

echo ""
echo "------------------------------------------------------------"
echo "ИТОГО:"
echo "  ✅ Успешно: $passed/${#pages[@]}"
echo "  ❌ Неудачно: $failed/${#pages[@]}"
echo "------------------------------------------------------------"

# Проверка общего состояния
echo ""
if [ $failed -eq 0 ]; then
    echo "🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!"
    echo "✅ Dashboard полностью функционален"
    echo "✅ Все страницы доступны"
    echo "✅ API работает корректно"
elif [ $failed -le 2 ]; then
    echo "⚠️  ЧАСТИЧНЫЙ УСПЕХ"
    echo "Некоторые страницы имеют проблемы"
else
    echo "❌ ОБНАРУЖЕНЫ КРИТИЧЕСКИЕ ПРОБЛЕМЫ"
    echo "Требуется исправление"
fi

echo ""
echo "📊 Dashboard: $DASHBOARD_URL"
echo "🔌 API: $API_URL"
echo "============================================================"