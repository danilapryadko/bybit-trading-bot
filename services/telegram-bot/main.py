#!/usr/bin/env python3
"""
Telegram Bot Microservice
Handles all Telegram bot interactions for Bybit Trading Bot
"""
import os
import sys
import logging
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# Add parent directories to path for imports
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global status for health check
bot_status = {"running": False, "last_update": None}

class HealthHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for health checks"""
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "status": "healthy" if bot_status["running"] else "starting",
                "service": "telegram-bot",
                "running": bot_status["running"],
                "last_update": bot_status["last_update"]
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default HTTP server logs
        pass

def start_health_server():
    """Start health check HTTP server in background"""
    server = HTTPServer(('0.0.0.0', 8080), HealthHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    logger.info("Health check server started on port 8080")

def main():
    """Main entry point for Telegram Bot service"""
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║     Bybit Trading Bot - Telegram Service            ║
    ║     Microservice Architecture v2.0                  ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    logger.info("🤖 Starting Telegram Bot Microservice...")
    logger.info("📡 Connecting to Bybit...")
    logger.info("-" * 50)
    
    # Start health check server
    start_health_server()
    
    # Run database migration if needed
    try:
        if os.getenv('FLY_APP_NAME'):
            logger.info("Checking database migration...")
            from database.migrate_to_postgres import main as migrate
            migrate()
    except Exception as e:
        logger.warning(f"Migration check: {e}")
    
    try:
        # Import dependencies
        from telegram_bot import TelegramBot
        from bybit_connector import get_bybit_connector
        
        # Use simplified TradingBot for microservice
        logger.info("Using simplified TradingBot (REST API only)")
        from trading_bot_simple import TradingBot
        
        # Initialize Bybit connector
        logger.info("Initializing Bybit connector...")
        connector = get_bybit_connector()
        
        # Initialize trading bot with real Bybit connection
        logger.info("Initializing trading bot...")
        trading_bot = TradingBot(
            api_key=os.getenv('BYBIT_API_KEY'),
            api_secret=os.getenv('BYBIT_API_SECRET'),
            testnet=not os.getenv('USE_MAINNET', 'false').lower() == 'true'
        )
        
        # Test connection
        try:
            balance = trading_bot.get_balance()
            logger.info(f"✅ Connected to Bybit. Balance: {balance} USDT")
            bot_status["running"] = True
            bot_status["last_update"] = str(os.popen('date').read().strip())
        except Exception as e:
            logger.error(f"Failed to connect to Bybit: {e}")
            
        # Initialize and start Telegram bot
        logger.info("Starting Telegram bot...")
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        allowed_users = os.getenv('TELEGRAM_ALLOWED_USERS', '').split(',')
        allowed_users = [int(u.strip()) for u in allowed_users if u.strip()]
        
        telegram_bot = TelegramBot(
            token=telegram_token,
            allowed_users=allowed_users,
            trading_bot=trading_bot
        )
        
        # Start the bot
        telegram_bot.run()
        
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down Telegram Bot service...")
    except Exception as e:
        logger.error(f"❌ Error in Telegram Bot service: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()