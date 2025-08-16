#!/usr/bin/env python3
"""
Telegram Bot Only - для отдельного запуска без конфликтов
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

def main():
    """Main function to run Telegram bot only"""
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║     Bybit Trading Bot - Telegram Bot Only           ║
    ║     Real-time Data from Bybit                       ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    logger.info("🚀 Starting Telegram Bot service...")
    logger.info("📱 Bot: @bybit_danila_trading_bot")
    logger.info("-" * 50)
    
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
                logger.info("Trading bot started with REAL Bybit connection")
        
        # Create bot with real Bybit connection
        trading_bot = EnhancedTradingBot(connector)
        
        # Get Telegram configuration
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not telegram_token:
            logger.error("TELEGRAM_BOT_TOKEN not set")
            return
            
        allowed_users = os.getenv('TELEGRAM_ALLOWED_USERS', '').split(',')
        allowed_users = [int(u.strip()) for u in allowed_users if u.strip()]
        
        # Log initial balance
        try:
            initial_balance = trading_bot.get_balance()
            logger.info(f"✅ Initial balance from Bybit: {initial_balance} USDT")
        except Exception as e:
            logger.error(f"Could not get initial balance: {e}")
        
        # Create and run Telegram bot
        telegram_bot = TelegramBot(
            token=telegram_token,
            allowed_users=allowed_users,
            trading_bot=trading_bot
        )
        
        logger.info("✅ Telegram bot initialized with real-time data!")
        logger.info("📢 Available commands:")
        logger.info("  /start - Start the bot")
        logger.info("  /balance - Check account balance")
        logger.info("  /positions - View open positions")
        logger.info("  /open - Open a new position")
        logger.info("  /close - Close a position")
        logger.info("  /report - Get trading report")
        logger.info("  /help - Show all commands")
        
        telegram_bot.run()
            
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down Telegram bot...")
    except Exception as e:
        logger.error(f"❌ Error in main loop: {e}", exc_info=True)

if __name__ == "__main__":
    main()