#!/bin/bash

# Test GraphQL API endpoints

API_URL="https://bybit-danila-api.fly.dev/graphql"

echo "Testing GraphQL API..."
echo ""

# Test 1: Get Balance
echo "1. Testing Balance Query:"
curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{"query":"query { balance { total available currency timestamp } }"}' | jq .

echo ""
echo "2. Testing Positions Query:"
curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{"query":"query { positions { symbol side size avgPrice markPrice unrealizedPnl realizedPnl leverage } }"}' | jq .

echo ""
echo "3. Testing Orders Query:"
curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{"query":"query { orders { orderId symbol side orderType price quantity status createdAt } }"}' | jq .

echo ""
echo "Test complete!"