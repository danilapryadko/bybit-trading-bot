#!/usr/bin/env python3
"""
Simplified Telegram Bot Runner - Works without database
"""
import os
import sys
import asyncio
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

# Simplified bot without database requirement
class SimpleTradingBot:
    """Simplified trading bot for Telegram"""
    
    def __init__(self):
        self.is_running = False
        self.paper_trading = True
        self.strategy_name = "ML Ensemble"
        self.balance = 10000
        self.positions = []
        self.start_time = None
        
    def get_balance(self):
        return self.balance
        
    def get_positions(self):
        return self.positions
        
    def get_ticker(self, symbol):
        # Mock ticker data
        return {
            'lastPrice': 67500.0,
            'price24hPcnt': 0.025,
            'volume24h': 1000000000
        }
        
    def close_all_positions(self):
        closed = self.positions.copy()
        self.positions = []
        return closed
        
    def stop(self):
        self.is_running = False
        
    def pause(self):
        self.is_running = False
        
    async def start(self):
        self.is_running = True
        self.start_time = asyncio.get_event_loop().time()
        logger.info("Trading bot started (simplified mode)")
        
    async def run(self):
        await self.start()
        while self.is_running:
            await asyncio.sleep(1)


async def main():
    """Main function"""
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
        
    logger.info("=" * 50)
    logger.info("🚀 Starting Bybit Trading Bot (Simplified)")
    logger.info(f"📱 Bot: @bybit_danila_trading_bot")
    logger.info(f"👤 User ID: {allowed_users[0]}")
    logger.info(f"💰 Mode: Paper Trading")
    logger.info("=" * 50)
    
    # Create simplified trading bot
    trading_bot = SimpleTradingBot()
    
    # Create Telegram bot
    telegram_bot = TelegramBot(
        token=telegram_token,
        allowed_users=allowed_users,
        trading_bot=trading_bot
    )
    
    # Set up simple notification
    async def notify(message, type="info"):
        for session in telegram_bot.sessions.values():
            if session.is_authenticated:
                try:
                    await telegram_bot.send_notification(
                        chat_id=session.chat_id,
                        message=message,
                        notification_type=type
                    )
                except:
                    pass
                    
    trading_bot.notification_callback = notify
    
    logger.info("📱 Telegram bot ready!")
    logger.info("Open Telegram and send /start to @bybit_danila_trading_bot")
    
    # Run Telegram bot
    telegram_bot.run()


if __name__ == "__main__":
    try:
        # Don't use asyncio.run since telegram bot creates its own loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("\nBot stopped by user")
    except Exception as e:
        logger.error(f"Error: {e}")