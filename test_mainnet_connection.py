#!/usr/bin/env python3
"""
Test Bybit MAINNET connection with provided API keys
"""
import os
import sys
from pybit.unified_trading import HTTP

# Your Bybit API keys (from Fly.io secrets)
API_KEY = "Mx7Ut1KJMaarT5fXQP"
API_SECRET = "o2QmhtAS7Oj1MObuPZIupp3cX5J7xNvQQPom"

def test_mainnet():
    """Test connection to Bybit MAINNET"""
    print("Testing Bybit MAINNET connection...")
    print(f"API Key: {API_KEY[:5]}...")
    
    try:
        # Connect to MAINNET
        session = HTTP(
            testnet=False,  # MAINNET mode
            api_key=API_KEY,
            api_secret=API_SECRET
        )
        
        # Get account info
        result = session.get_wallet_balance(accountType="UNIFIED")
        
        if result["retCode"] == 0:
            print("✅ MAINNET Connection successful!")
            
            # Get balance info
            balance_info = result["result"]["list"][0]
            total_equity = float(balance_info.get("totalEquity", 0))
            available = float(balance_info.get("totalAvailableBalance", 0))
            
            print(f"\n📊 Account Balance:")
            print(f"   Total Equity: ${total_equity:.2f}")
            print(f"   Available: ${available:.2f}")
            
            # Get positions
            positions = session.get_positions(category="linear", settleCoin="USDT")
            if positions["retCode"] == 0:
                position_list = positions["result"]["list"]
                print(f"\n📈 Open Positions: {len(position_list)}")
                for pos in position_list[:3]:  # Show first 3 positions
                    print(f"   - {pos['symbol']}: {pos['side']} {pos['size']}")
            
            return True
        else:
            print(f"❌ API Error: {result.get('retMsg', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

def test_testnet():
    """Test connection to Bybit TESTNET"""
    print("\nTesting Bybit TESTNET connection...")
    
    try:
        # Connect to TESTNET
        session = HTTP(
            testnet=True,  # TESTNET mode
            api_key=API_KEY,
            api_secret=API_SECRET
        )
        
        # Get account info
        result = session.get_wallet_balance(accountType="UNIFIED")
        
        if result["retCode"] == 0:
            print("✅ TESTNET Connection successful!")
            return True
        else:
            print(f"❌ TESTNET Error: {result.get('retMsg', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ TESTNET failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("BYBIT CONNECTION TEST")
    print("=" * 50)
    
    # Test MAINNET
    mainnet_ok = test_mainnet()
    
    # Test TESTNET
    testnet_ok = test_testnet()
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"MAINNET: {'✅ Working' if mainnet_ok else '❌ Failed'}")
    print(f"TESTNET: {'✅ Working' if testnet_ok else '❌ Failed'}")
    
    if mainnet_ok:
        print("\n🎉 Your API keys are valid for MAINNET trading!")
        print("The system should be configured for real trading.")
    elif testnet_ok:
        print("\n⚠️ Your API keys work only for TESTNET.")
        print("These might be testnet-only keys.")
    else:
        print("\n❌ API keys are not working for either network.")
        print("Please check your API keys.")
    
    print("=" * 50)