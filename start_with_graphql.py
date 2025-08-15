#!/usr/bin/env python3
"""
Combined Telegram Bot and GraphQL Server for Fly.io deployment
Runs both services for 24/7 operation
"""
import os
import logging
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_telegram_bot():
    """Run Telegram bot in thread"""
    logger.info("Starting Telegram bot thread...")
    from telegram_bot import TelegramBot
    from bybit_realtime import get_realtime_data
    
    # Get real-time data connection
    rt_data = get_realtime_data()
    
    # Create enhanced trading bot with real data
    class EnhancedTradingBot:
        def __init__(self, realtime_data):
            self.rt_data = realtime_data
            self.is_running = False
            self.paper_trading = True
            self.strategy_name = "ML Ensemble"
            self.start_time = None
            
        def get_balance(self):
            return 10000.0
            
        def get_positions(self):
            return []
            
        def get_ticker(self, symbol):
            # Use real data from Bybit
            ticker = self.rt_data.get_ticker(symbol)
            return {
                'lastPrice': ticker.get('lastPrice', 67500.0),
                'price24hPcnt': ticker.get('priceChange24h', 0.025),
                'volume24h': ticker.get('volume24h', 1000000000)
            }
            
        def close_all_positions(self):
            return []
            
        def stop(self):
            self.is_running = False
            
        def pause(self):
            self.is_running = False
            
        async def start(self):
            self.is_running = True
            logger.info("Enhanced trading bot started with real-time data")
    
    # Create bot with real data
    trading_bot = EnhancedTradingBot(rt_data)
    
    # Get Telegram configuration
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not telegram_token:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return
        
    allowed_users = os.getenv('TELEGRAM_ALLOWED_USERS', '').split(',')
    allowed_users = [int(u.strip()) for u in allowed_users if u.strip()]
    
    # Create and run Telegram bot
    telegram_bot = TelegramBot(
        token=telegram_token,
        allowed_users=allowed_users,
        trading_bot=trading_bot
    )
    
    logger.info("✅ Telegram bot initialized with real-time data!")
    telegram_bot.run()

def run_graphql_server():
    """Run GraphQL server in thread"""
    logger.info("Starting GraphQL server thread...")
    import uvicorn
    from graphql_server import create_app
    from bybit_realtime import get_realtime_data
    
    # Get real-time data connection
    rt_data = get_realtime_data()
    
    # Create enhanced bot with real data for GraphQL
    class EnhancedTradingBot:
        def __init__(self, realtime_data):
            self.rt_data = realtime_data
            self.is_running = False
            self.paper_trading = True
            self.strategy_name = "ML Ensemble"
            self.start_time = None
            
        def get_balance(self):
            return 10000.0
            
        def get_positions(self):
            return []
            
        def get_ticker(self, symbol):
            # Use real data from Bybit
            ticker = self.rt_data.get_ticker(symbol)
            return {
                'lastPrice': ticker.get('lastPrice', 67500.0),
                'price24hPcnt': ticker.get('priceChange24h', 0.025),
                'volume24h': ticker.get('volume24h', 1000000000)
            }
            
        def close_all_positions(self):
            return []
            
        def stop(self):
            self.is_running = False
            
        def pause(self):
            self.is_running = False
            
        async def start(self):
            self.is_running = True
            logger.info("GraphQL bot started with real-time data")
    
    # Create bot with real data
    bot = EnhancedTradingBot(rt_data)
    app = create_app(bot)
    
    # Run server
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )

def main():
    """Main function to run both services"""
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║     Bybit Trading Bot - Full Stack (24/7)           ║
    ║     Telegram Bot + GraphQL API                      ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    logger.info("🚀 Starting combined services for Fly.io...")
    logger.info("📱 Telegram Bot: @bybit_danila_trading_bot")
    logger.info("📊 GraphQL API: http://0.0.0.0:8000/graphql/")
    logger.info("-" * 50)
    
    # Create thread pool
    executor = ThreadPoolExecutor(max_workers=2)
    
    try:
        # Start both services in separate threads
        telegram_future = executor.submit(run_telegram_bot)
        graphql_future = executor.submit(run_graphql_server)
        
        # Keep main thread alive
        while True:
            # Check if threads are still running
            if telegram_future.done():
                logger.error("Telegram bot stopped unexpectedly!")
                telegram_future = executor.submit(run_telegram_bot)
                
            if graphql_future.done():
                logger.error("GraphQL server stopped unexpectedly!")
                graphql_future = executor.submit(run_graphql_server)
                
            # Sleep for monitoring interval
            import time
            time.sleep(10)
            
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down services...")
        executor.shutdown(wait=True)
    except Exception as e:
        logger.error(f"❌ Error in main loop: {e}")
        executor.shutdown(wait=True)

if __name__ == "__main__":
    main()