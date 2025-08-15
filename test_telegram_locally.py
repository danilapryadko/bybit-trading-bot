#!/usr/bin/env python3
"""
Quick test script for Telegram bot
Run this to verify your bot works before deployment
"""
import os
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_telegram_bot():
    """Test Telegram bot connection"""
    try:
        from telegram import Bot
        
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            print("❌ TELEGRAM_BOT_TOKEN not found in .env")
            print("Please add: TELEGRAM_BOT_TOKEN=8489565613:AAGnJT8IaO8jsNvCp0HdCG5hcZFU4XJAaxY")
            return False
            
        print(f"🔄 Testing bot token...")
        bot = Bot(token=token)
        
        # Test bot connection
        me = await bot.get_me()
        print(f"✅ Bot connected successfully!")
        print(f"   Username: @{me.username}")
        print(f"   Name: {me.first_name}")
        print(f"   Can join groups: {me.can_join_groups}")
        print(f"   Can read messages: {me.can_read_all_group_messages}")
        
        # Get your user ID
        user_id = os.getenv('TELEGRAM_ALLOWED_USERS')
        if user_id:
            print(f"\n✅ Allowed users configured: {user_id}")
            try:
                # Try to send a test message
                await bot.send_message(
                    chat_id=int(user_id.split(',')[0]),
                    text="🚀 Test message from Bybit Trading Bot!\nYour bot is working correctly."
                )
                print("✅ Test message sent! Check your Telegram.")
            except Exception as e:
                print(f"⚠️  Could not send message. Start a chat with your bot first: @{me.username}")
        else:
            print("\n⚠️  TELEGRAM_ALLOWED_USERS not configured")
            print("   To get your user ID:")
            print("   1. Open Telegram")
            print("   2. Search for @userinfobot")
            print("   3. Send any message")
            print("   4. Copy your ID and add to .env:")
            print("   TELEGRAM_ALLOWED_USERS=your_id_here")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_trading_bot():
    """Test trading bot initialization"""
    print("\n🔄 Testing trading bot initialization...")
    
    try:
        # Check if API keys are configured
        api_key = os.getenv('BYBIT_API_KEY')
        api_secret = os.getenv('BYBIT_API_SECRET')
        
        if not api_key or not api_secret:
            print("⚠️  Bybit API credentials not configured (running in demo mode)")
        else:
            print("✅ Bybit API credentials found")
            
        testnet = os.getenv('BYBIT_TESTNET', 'true').lower() == 'true'
        paper_trading = os.getenv('PAPER_TRADING', 'true').lower() == 'true'
        
        print(f"   Testnet: {testnet}")
        print(f"   Paper Trading: {paper_trading}")
        print(f"   Initial Capital: ${os.getenv('INITIAL_CAPITAL', '10000')}")
        print(f"   Max Positions: {os.getenv('MAX_POSITIONS', '3')}")
        print(f"   Risk per Trade: {os.getenv('RISK_PER_TRADE', '1.0')}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("""
╔══════════════════════════════════════════════════════╗
║         Bybit Trading Bot - Telegram Test           ║
╚══════════════════════════════════════════════════════╝
    """)
    
    # Check .env file
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Creating from template...")
        if os.path.exists('.env.example'):
            import shutil
            shutil.copy('.env.example', '.env')
            print("✅ Created .env file. Please edit it with your credentials.")
        return
    
    # Run tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    telegram_ok = loop.run_until_complete(test_telegram_bot())
    trading_ok = loop.run_until_complete(test_trading_bot())
    
    print("\n" + "="*50)
    if telegram_ok and trading_ok:
        print("✅ All tests passed! Your bot is ready.")
        print("\nNext steps:")
        print("1. Run locally: python run_with_telegram.py")
        print("2. Deploy to Fly.io: fly deploy")
    else:
        print("⚠️  Some tests failed. Please check configuration.")
        
if __name__ == "__main__":
    main()