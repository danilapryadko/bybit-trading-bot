#!/usr/bin/env python3
"""
Main entry point for Bybit Trading Bot with Telegram integration
"""
import os
import sys
import asyncio
import logging
import signal
from typing import Optional
from dotenv import load_dotenv
import threading

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trading_bot import TradingBot
from telegram_bot import TelegramBot
from websocket_manager import WebSocketManager
from risk_manager_v2 import RiskManagerV2

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE', 'trading_bot.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class BotSystem:
    """Main system orchestrator"""
    
    def __init__(self):
        self.trading_bot: Optional[TradingBot] = None
        self.telegram_bot: Optional[TelegramBot] = None
        self.ws_manager: Optional[WebSocketManager] = None
        self.is_running = False
        
    def initialize(self):
        """Initialize all components"""
        logger.info("Initializing Bybit Trading Bot System...")
        
        # Get configuration from environment
        api_key = os.getenv('BYBIT_API_KEY')
        api_secret = os.getenv('BYBIT_API_SECRET')
        testnet = os.getenv('BYBIT_TESTNET', 'true').lower() == 'true'
        
        if not api_key or not api_secret:
            logger.warning("Bybit API credentials not found. Running in demo mode.")
            api_key = "demo"
            api_secret = "demo"
            testnet = True
        
        # Initialize WebSocket manager
        self.ws_manager = WebSocketManager(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret
        )
        
        # Initialize Risk Manager
        risk_manager = RiskManagerV2(
            max_position_size=float(os.getenv('MAX_POSITION_SIZE', '10000')),
            max_portfolio_risk=float(os.getenv('MAX_PORTFOLIO_RISK', '0.1')),
            max_correlation=float(os.getenv('MAX_CORRELATION', '0.7'))
        )
        
        # Initialize Trading Bot
        self.trading_bot = TradingBot(
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet,
            paper_trading=os.getenv('PAPER_TRADING', 'true').lower() == 'true',
            initial_capital=float(os.getenv('INITIAL_CAPITAL', '10000')),
            risk_per_trade=float(os.getenv('RISK_PER_TRADE', '1.0')),
            max_positions=int(os.getenv('MAX_POSITIONS', '3'))
        )
        
        # Initialize Telegram Bot
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if telegram_token:
            allowed_users = os.getenv('TELEGRAM_ALLOWED_USERS', '').split(',')
            allowed_users = [int(u.strip()) for u in allowed_users if u.strip()]
            
            self.telegram_bot = TelegramBot(
                token=telegram_token,
                allowed_users=allowed_users,
                trading_bot=self.trading_bot
            )
            
            # Set up notification callback
            self.trading_bot.notification_callback = self.send_telegram_notification
            
            logger.info(f"Telegram bot initialized: @{os.getenv('TELEGRAM_BOT_USERNAME', 'bybit_trading_bot')}")
        else:
            logger.warning("Telegram bot token not found. Running without Telegram integration.")
            
    async def send_telegram_notification(self, message: str, notification_type: str = "info"):
        """Send notification through Telegram bot"""
        if self.telegram_bot:
            # Send to all authenticated users
            for session in self.telegram_bot.sessions.values():
                if session.is_authenticated:
                    await self.telegram_bot.send_notification(
                        chat_id=session.chat_id,
                        message=message,
                        notification_type=notification_type
                    )
                    
    def run_trading_bot(self):
        """Run trading bot in separate thread"""
        logger.info("Starting trading bot...")
        try:
            asyncio.run(self.trading_bot.run())
        except Exception as e:
            logger.error(f"Trading bot error: {e}")
            
    def run_telegram_bot(self):
        """Run telegram bot in separate thread"""
        if self.telegram_bot:
            logger.info("Starting Telegram bot...")
            try:
                self.telegram_bot.run()
            except Exception as e:
                logger.error(f"Telegram bot error: {e}")
                
    def start(self):
        """Start the complete system"""
        try:
            # Initialize components
            self.initialize()
            self.is_running = True
            
            # Start WebSocket manager
            ws_thread = threading.Thread(target=self.ws_manager.connect, daemon=True)
            ws_thread.start()
            
            # Start trading bot in background thread
            trading_thread = threading.Thread(target=self.run_trading_bot, daemon=True)
            trading_thread.start()
            
            # Run Telegram bot in main thread (blocking)
            if self.telegram_bot:
                logger.info("=" * 50)
                logger.info("🚀 Bybit Trading Bot System Started")
                logger.info(f"📱 Telegram Bot: @{os.getenv('TELEGRAM_BOT_USERNAME', 'bybit_danila_trading_bot')}")
                logger.info(f"💰 Initial Capital: ${os.getenv('INITIAL_CAPITAL', '10000')}")
                logger.info(f"🎯 Mode: {'Paper Trading' if os.getenv('PAPER_TRADING', 'true').lower() == 'true' else 'Live Trading'}")
                logger.info(f"📊 Max Positions: {os.getenv('MAX_POSITIONS', '3')}")
                logger.info(f"⚖️ Risk per Trade: {os.getenv('RISK_PER_TRADE', '1.0')}%")
                logger.info("=" * 50)
                logger.info("\n📱 Open Telegram and send /start to your bot to begin!")
                
                self.run_telegram_bot()
            else:
                logger.info("Running without Telegram bot. Press Ctrl+C to stop.")
                # Keep main thread alive
                while self.is_running:
                    asyncio.run(asyncio.sleep(1))
                    
        except KeyboardInterrupt:
            logger.info("\nShutting down gracefully...")
            self.stop()
        except Exception as e:
            logger.error(f"System error: {e}")
            self.stop()
            
    def stop(self):
        """Stop all components"""
        self.is_running = False
        
        if self.trading_bot:
            self.trading_bot.stop()
            
        if self.ws_manager:
            self.ws_manager.disconnect()
            
        logger.info("System stopped")
        

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    sys.exit(0)
    

def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Print startup banner
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║        Bybit Trading Bot v2.0 with Telegram         ║
    ║                                                      ║
    ║  Features:                                           ║
    ║  • Real-time WebSocket data streaming               ║
    ║  • Advanced ML strategies (LSTM, RF, XGBoost)       ║
    ║  • Risk Management V2 with Kelly Criterion          ║
    ║  • Telegram bot for remote control                  ║
    ║  • Paper trading mode for safe testing              ║
    ║                                                      ║
    ║  Telegram: @bybit_danila_trading_bot                ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    # Check for required environment variables
    if not os.path.exists('.env'):
        logger.warning("No .env file found. Creating from .env.example...")
        if os.path.exists('.env.example'):
            import shutil
            shutil.copy('.env.example', '.env')
            logger.info("Created .env file. Please edit it with your credentials.")
            return
    
    # Create and start system
    system = BotSystem()
    system.start()
    

if __name__ == "__main__":
    main()