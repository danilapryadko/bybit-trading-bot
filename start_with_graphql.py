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

# Run database migration on first startup
def run_migration():
    """Run database migration if needed"""
    try:
        if os.getenv('FLY_APP_NAME'):
            logger.info("Checking database migration...")
            from run_migration import main as migrate
            migrate()
    except Exception as e:
        logger.warning(f"Migration check failed (may already be complete): {e}")

# Run migration before starting services
run_migration()

def run_telegram_bot():
    """Run Telegram bot in thread"""
    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        logger.info("Starting Telegram bot thread...")
        from telegram_bot import TelegramBot
        from bybit_connector import get_bybit_connector
        
        # Get real Bybit connector
        connector = get_bybit_connector()
        
        # Create enhanced trading bot with real Bybit connection
        class EnhancedTradingBot:
            def __init__(self, bybit_connector):
                self.connector = bybit_connector
                self.is_running = False
                self.paper_trading = False  # Using real account
                self.strategy_name = "ML Ensemble"
                self.start_time = None
                
            def get_balance(self):
                # Get real balance from Bybit account
                return self.connector.get_balance()
                
            def get_positions(self):
                # Get real positions from Bybit
                return self.connector.get_positions()
                
            def get_ticker(self, symbol):
                # Get real ticker data from Bybit
                ticker = self.connector.get_ticker(symbol)
                return {
                    'lastPrice': ticker.get('price', 0),
                    'price24hPcnt': ticker.get('change24h', 0) / 100,  # Convert percentage
                    'volume24h': ticker.get('volume', 0)
                }
                
            def close_all_positions(self):
                positions = self.connector.get_positions()
                closed = []
                for pos in positions:
                    # Close each position
                    order_id = self.connector.place_order(
                        symbol=pos['symbol'],
                        side='sell' if pos['side'].lower() == 'buy' else 'buy',
                        quantity=pos['size']
                    )
                    if order_id:
                        closed.append(pos['symbol'])
                return closed
                
            def stop(self):
                self.is_running = False
                
            def pause(self):
                self.is_running = False
                
            async def start(self):
                self.is_running = True
                logger.info("Enhanced trading bot started with REAL Bybit connection")
        
        # Create bot with real Bybit connection
        trading_bot = EnhancedTradingBot(connector)
        
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
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}", exc_info=True)
        raise

def run_graphql_server():
    """Run GraphQL server in thread"""
    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        logger.info("Starting GraphQL server thread...")
        import uvicorn
        from graphql_server import create_app
        from bybit_connector import get_bybit_connector
        
        # Get real Bybit connector
        connector = get_bybit_connector()
        
        # Create enhanced bot with real Bybit connection for GraphQL
        class EnhancedTradingBot:
            def __init__(self, bybit_connector):
                self.connector = bybit_connector
                self.is_running = False
                self.paper_trading = False  # Using real account
                self.strategy_name = "ML Ensemble"
                self.start_time = None
                
            def get_balance(self):
                # Get real balance from Bybit account
                return self.connector.get_balance()
                
            def get_positions(self):
                # Get real positions from Bybit
                return self.connector.get_positions()
                
            def get_ticker(self, symbol):
                # Get real ticker data from Bybit
                ticker = self.connector.get_ticker(symbol)
                return {
                    'lastPrice': ticker.get('price', 0),
                    'price24hPcnt': ticker.get('change24h', 0) / 100,  # Convert percentage
                    'volume24h': ticker.get('volume', 0)
                }
                
            def close_all_positions(self):
                positions = self.connector.get_positions()
                closed = []
                for pos in positions:
                    # Close each position
                    order_id = self.connector.place_order(
                        symbol=pos['symbol'],
                        side='sell' if pos['side'].lower() == 'buy' else 'buy',
                        quantity=pos['size']
                    )
                    if order_id:
                        closed.append(pos['symbol'])
                return closed
                
            def stop(self):
                self.is_running = False
                
            def pause(self):
                self.is_running = False
                
            async def start(self):
                self.is_running = True
                logger.info("GraphQL bot started with REAL Bybit connection")
        
        # Create bot with real Bybit connection
        bot = EnhancedTradingBot(connector)
        app = create_app(bot)
        
        # Run server
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Failed to start GraphQL server: {e}", exc_info=True)
        raise

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
    
    # Start GraphQL server in a thread
    import threading
    graphql_thread = threading.Thread(target=run_graphql_server, daemon=True)
    graphql_thread.start()
    
    # Give GraphQL time to start
    import time
    time.sleep(2)
    
    # Run Telegram bot in main thread (needs signal handling)
    try:
        from telegram_bot import TelegramBot
        from bybit_connector import get_bybit_connector
        
        # Get real Bybit connector
        connector = get_bybit_connector()
        
        # Create enhanced trading bot with real Bybit connection
        class EnhancedTradingBot:
            def __init__(self, bybit_connector):
                self.connector = bybit_connector
                self.is_running = False
                self.paper_trading = False  # Using real account
                self.strategy_name = "ML Ensemble"
                self.start_time = None
                
            def get_balance(self):
                # Get real balance from Bybit account
                return self.connector.get_balance()
                
            def get_positions(self):
                # Get real positions from Bybit
                return self.connector.get_positions()
                
            def get_ticker(self, symbol):
                # Get real ticker data from Bybit
                ticker = self.connector.get_ticker(symbol)
                return {
                    'lastPrice': ticker.get('price', 0),
                    'price24hPcnt': ticker.get('change24h', 0) / 100,  # Convert percentage
                    'volume24h': ticker.get('volume', 0)
                }
                
            def close_all_positions(self):
                positions = self.connector.get_positions()
                closed = []
                for pos in positions:
                    # Close each position
                    order_id = self.connector.place_order(
                        symbol=pos['symbol'],
                        side='sell' if pos['side'].lower() == 'buy' else 'buy',
                        quantity=pos['size']
                    )
                    if order_id:
                        closed.append(pos['symbol'])
                return closed
                
            def stop(self):
                self.is_running = False
                
            def pause(self):
                self.is_running = False
                
            async def start(self):
                self.is_running = True
                logger.info("Enhanced trading bot started with REAL Bybit connection")
        
        # Create bot with real Bybit connection
        trading_bot = EnhancedTradingBot(connector)
        
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
            
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down services...")
    except Exception as e:
        logger.error(f"❌ Error in main loop: {e}", exc_info=True)

if __name__ == "__main__":
    main()