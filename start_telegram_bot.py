#!/usr/bin/env python3
"""
Simple Telegram Bot Starter
"""
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Simplified bot for testing
class MockTradingBot:
    def __init__(self):
        self.is_running = False
        self.paper_trading = True
        self.strategy_name = "ML Ensemble"
        self.start_time = None
        
    def get_balance(self):
        return 10000.0
        
    def get_positions(self):
        return []
        
    def get_ticker(self, symbol):
        return {
            'lastPrice': 67500.0,
            'price24hPcnt': 0.025,
            'volume24h': 1000000000
        }
        
    def close_all_positions(self):
        return []
        
    def stop(self):
        self.is_running = False
        
    def pause(self):
        self.is_running = False
        
    async def start(self):
        self.is_running = True
        logger.info("Mock trading bot started")


def main():
    """Main function"""
    # Import here to avoid circular imports
    from telegram_bot import TelegramBot
    
    # Get configuration
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not telegram_token:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env")
        return
        
    allowed_users = os.getenv('TELEGRAM_ALLOWED_USERS', '').split(',')
    allowed_users = [int(u.strip()) for u in allowed_users if u.strip()]
    
    if not allowed_users:
        logger.error("TELEGRAM_ALLOWED_USERS not set in .env")
        return
        
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║      Bybit Trading Bot - Telegram Interface         ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    logger.info(f"📱 Starting Telegram bot: @bybit_danila_trading_bot")
    logger.info(f"👤 Authorized user: {allowed_users[0]}")
    logger.info(f"💰 Mode: Paper Trading (Safe Mode)")
    logger.info("-" * 50)
    
    # Create mock trading bot
    trading_bot = MockTradingBot()
    
    # Create and run Telegram bot
    telegram_bot = TelegramBot(
        token=telegram_token,
        allowed_users=allowed_users,
        trading_bot=trading_bot
    )
    
    logger.info("✅ Bot initialized successfully!")
    logger.info("📱 Open Telegram and send /start to @bybit_danila_trading_bot")
    logger.info("Press Ctrl+C to stop")
    print()
    
    # This will block and run the bot
    telegram_bot.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()