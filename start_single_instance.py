#!/usr/bin/env python3
"""
Single instance startup script for Fly.io deployment
Ensures only GraphQL API runs (no duplicate Telegram bots)
"""
import os
import logging
import asyncio
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

def main():
    """Main function to run GraphQL API only"""
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║     Bybit Trading Bot - GraphQL API ONLY            ║
    ║     Real-time Data from Bybit                       ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    logger.info("🚀 Starting GraphQL API service for Fly.io...")
    logger.info("📊 GraphQL API: http://0.0.0.0:8000/")
    logger.info("ℹ️  Telegram bot disabled to prevent conflicts")
    logger.info("-" * 50)
    
    # Run migration
    run_migration()
    
    try:
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
                """Get real balance from Bybit account"""
                try:
                    balance = self.connector.get_balance()
                    logger.info(f"Retrieved real balance: {balance} USDT")
                    return balance
                except Exception as e:
                    logger.error(f"Error getting balance: {e}")
                    return 0.0
                
            def get_positions(self):
                """Get real positions from Bybit"""
                try:
                    positions = self.connector.get_positions()
                    logger.info(f"Retrieved {len(positions)} positions")
                    return positions
                except Exception as e:
                    logger.error(f"Error getting positions: {e}")
                    return []
                
            def get_ticker(self, symbol):
                """Get real ticker data from Bybit"""
                try:
                    ticker = self.connector.get_ticker(symbol)
                    return {
                        'lastPrice': ticker.get('price', 0),
                        'price24hPcnt': ticker.get('change24h', 0) / 100,  # Convert percentage
                        'volume24h': ticker.get('volume', 0)
                    }
                except Exception as e:
                    logger.error(f"Error getting ticker for {symbol}: {e}")
                    return {
                        'lastPrice': 0,
                        'price24hPcnt': 0,
                        'volume24h': 0
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
        
        # Log initial balance
        try:
            initial_balance = bot.get_balance()
            logger.info(f"✅ Initial balance from Bybit: {initial_balance} USDT")
        except Exception as e:
            logger.error(f"Could not get initial balance: {e}")
        
        # Run server
        logger.info("Starting Uvicorn server...")
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000,
            log_level="info"
        )
            
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down service...")
    except Exception as e:
        logger.error(f"❌ Error in main loop: {e}", exc_info=True)

if __name__ == "__main__":
    main()