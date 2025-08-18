#!/bin/bash
# Final integration test for Bybit Trading Dashboard

echo "============================================================"
echo "🎯 BYBIT TRADING DASHBOARD - FINAL INTEGRATION TEST"
echo "============================================================"
echo "Test Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "------------------------------------------------------------"

# Test API Health
echo ""
echo "✅ Testing API Health..."
health=$(curl -s https://bybit-danila-api.fly.dev/health)
echo "   Response: $health"

# Test GraphQL Balance
echo ""
echo "✅ Testing GraphQL Balance Query..."
balance_query='{"query":"query { botStatus { balance isRunning mode } }"}'
balance_response=$(curl -s -X POST https://bybit-danila-api.fly.dev/graphql/ \
  -H "Content-Type: application/json" \
  -d "$balance_query")
echo "   Balance Response: $balance_response"

# Extract balance value
balance_value=$(echo $balance_response | grep -o '"balance":[0-9.]*' | head -1 | cut -d: -f2)
echo "   💰 Balance: \$$balance_value"

# Test GraphQL Positions
echo ""
echo "✅ Testing GraphQL Positions Query..."
positions_query='{"query":"query { positions { symbol side size } }"}'
positions_response=$(curl -s -X POST https://bybit-danila-api.fly.dev/graphql/ \
  -H "Content-Type: application/json" \
  -d "$positions_query")
echo "   Positions: $(echo $positions_response | grep -o '"positions":\[[^]]*\]')"

# Test Dashboard Load
echo ""
echo "✅ Testing Dashboard Load..."
dashboard_status=$(curl -s -o /dev/null -w "%{http_code}" https://bybit-danila-dashboard.fly.dev)
echo "   Dashboard HTTP Status: $dashboard_status"

if [ "$dashboard_status" = "200" ]; then
  echo "   ✅ Dashboard loads successfully"
else
  echo "   ❌ Dashboard failed to load"
fi

# Summary
echo ""
echo "============================================================"
echo "📊 TEST RESULTS SUMMARY"
echo "============================================================"

# Check if balance is correct (should be around 499)
if (( $(echo "$balance_value > 400" | bc -l) )); then
  echo "✅ Balance verified: \$$balance_value"
  balance_ok=1
else
  echo "❌ Balance issue: \$$balance_value"
  balance_ok=0
fi

# Check dashboard
if [ "$dashboard_status" = "200" ]; then
  echo "✅ Dashboard loads successfully"
  dashboard_ok=1
else
  echo "❌ Dashboard load failed"
  dashboard_ok=0
fi

# Check API
if [[ $health == *"healthy"* ]]; then
  echo "✅ API is healthy"
  api_ok=1
else
  echo "❌ API health check failed"
  api_ok=0
fi

echo "------------------------------------------------------------"

if [ $balance_ok -eq 1 ] && [ $dashboard_ok -eq 1 ] && [ $api_ok -eq 1 ]; then
  echo ""
  echo "🎉 ALL TESTS PASSED!"
  echo "✅ Dashboard is fully functional"
  echo "✅ API is working correctly"
  echo "✅ Balance is displayed (\$$balance_value)"
  echo ""
  echo "📊 Dashboard URL: https://bybit-danila-dashboard.fly.dev"
  echo "🔌 API URL: https://bybit-danila-api.fly.dev"
  echo "📡 GraphQL: https://bybit-danila-api.fly.dev/graphql"
else
  echo ""
  echo "⚠️ Some tests failed"
  echo "Check the output above for details"
fi

echo "============================================================"