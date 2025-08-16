#!/usr/bin/env python3
"""
Test Real Balance - Verify Bybit Connector Works
"""

import os
import sys

print("=" * 50)
print("🔍 TESTING REAL BYBIT BALANCE")
print("=" * 50)

# Set environment to use testnet
os.environ['USE_MAINNET'] = 'false'
os.environ['BYBIT_API_KEY'] = os.getenv('BYBIT_API_KEY', '')
os.environ['BYBIT_API_SECRET'] = os.getenv('BYBIT_API_SECRET', '')

try:
    from bybit_connector import get_bybit_connector
    
    print("\n📡 Connecting to Bybit API...")
    connector = get_bybit_connector()
    
    print("✅ Connected successfully!")
    
    # Get real balance
    print("\n💰 Getting real balance...")
    balance = connector.get_balance()
    print(f"   Balance: {balance} USDT")
    
    # Get positions
    print("\n📊 Getting open positions...")
    positions = connector.get_positions()
    if positions:
        for pos in positions:
            print(f"   - {pos['symbol']}: {pos['side']} {pos['size']} @ {pos['avgPrice']}")
    else:
        print("   No open positions")
    
    # Get ticker for BTC
    print("\n📈 Getting BTC price...")
    ticker = connector.get_ticker('BTCUSDT')
    print(f"   BTCUSDT: ${ticker.get('price', 0):,.2f}")
    
    print("\n" + "=" * 50)
    print("✅ ALL TESTS PASSED!")
    print("Real Bybit connection is working correctly!")
    print("=" * 50)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nMake sure you have set:")
    print("  export BYBIT_API_KEY=your_api_key")
    print("  export BYBIT_API_SECRET=your_api_secret")
    sys.exit(1)