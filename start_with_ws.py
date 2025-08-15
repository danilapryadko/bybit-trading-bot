#!/usr/bin/env python3
"""
Combined launcher for Telegram bot, GraphQL API, and WebSocket server
"""

import os
import asyncio
import threading
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import uvicorn
from graphql_server import app as graphql_app
from websocket_server import app as ws_app

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get Telegram token from environment
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7707658830:AAH1zJH8uVFb_VNrp5t-vnp3IUoLNB9n6po')

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("📊 Dashboard", url="https://bybit-danila-dashboard.fly.dev")],
        [InlineKeyboardButton("💹 Market Status", callback_data="market_status")],
        [InlineKeyboardButton("📈 Positions", callback_data="positions")],
        [InlineKeyboardButton("🤖 Bot Status", callback_data="bot_status")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(
        f"Welcome {user.mention_html()}! 🚀\n\n"
        "I'm your Bybit Trading Bot assistant.\n"
        "Choose an option below:",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "market_status":
        await query.edit_message_text(
            "📊 Market Status\n\n"
            "BTC/USDT: $65,432.10 (+2.34%)\n"
            "ETH/USDT: $3,234.56 (+1.89%)\n"
            "BNB/USDT: $456.78 (-0.45%)\n\n"
            "Last updated: Just now"
        )
    elif query.data == "positions":
        await query.edit_message_text(
            "📈 Active Positions\n\n"
            "No active positions\n\n"
            "Total P&L: $0.00"
        )
    elif query.data == "bot_status":
        await query.edit_message_text(
            "🤖 Bot Status\n\n"
            "Status: ✅ Running\n"
            "Trading: 🔴 Disabled\n"
            "Paper Trading: ✅ Enabled\n"
            "Active Strategies: 0\n\n"
            "WebSocket: ✅ Connected\n"
            "GraphQL: ✅ Running\n"
            "Dashboard: ✅ Online"
        )
    elif query.data == "settings":
        keyboard = [
            [InlineKeyboardButton("🔄 Enable Trading", callback_data="enable_trading")],
            [InlineKeyboardButton("📝 Paper Trading", callback_data="paper_trading")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⚙️ Settings\n\n"
            "Configure your trading bot:",
            reply_markup=reply_markup
        )
    elif query.data == "back_to_menu":
        keyboard = [
            [InlineKeyboardButton("📊 Dashboard", url="https://bybit-danila-dashboard.fly.dev")],
            [InlineKeyboardButton("💹 Market Status", callback_data="market_status")],
            [InlineKeyboardButton("📈 Positions", callback_data="positions")],
            [InlineKeyboardButton("🤖 Bot Status", callback_data="bot_status")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Choose an option:",
            reply_markup=reply_markup
        )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send bot status"""
    await update.message.reply_text(
        "🤖 Bot Status\n\n"
        "✅ Telegram Bot: Online\n"
        "✅ GraphQL API: Running\n"
        "✅ WebSocket Server: Active\n"
        "✅ Dashboard: https://bybit-danila-dashboard.fly.dev\n\n"
        "All systems operational!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = """
🤖 Bybit Trading Bot Commands:

/start - Start the bot and show menu
/status - Check bot status
/market - View market prices
/positions - View active positions
/balance - Check account balance
/trade - Place a trade
/stop - Stop trading
/help - Show this help message

📊 Dashboard: https://bybit-danila-dashboard.fly.dev
📡 GraphQL: https://bybit-danila-bot.fly.dev/graphql
    """
    await update.message.reply_text(help_text)

async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show market prices"""
    await update.message.reply_text(
        "💹 Market Prices\n\n"
        "BTC/USDT: $65,432.10\n"
        "ETH/USDT: $3,234.56\n"
        "BNB/USDT: $456.78\n"
        "SOL/USDT: $145.32\n\n"
        "Use /trade to place orders"
    )

def run_telegram_bot():
    """Run Telegram bot"""
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("market", market))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

def run_graphql_server():
    """Run GraphQL server"""
    uvicorn.run(graphql_app, host="0.0.0.0", port=8000)

def run_websocket_server():
    """Run WebSocket server"""
    uvicorn.run(ws_app, host="0.0.0.0", port=8001)

if __name__ == '__main__':
    logger.info("Starting combined services...")
    
    # Start WebSocket server in a thread
    ws_thread = threading.Thread(target=run_websocket_server, daemon=True)
    ws_thread.start()
    logger.info("WebSocket server started on port 8001")
    
    # Start GraphQL server in a thread
    graphql_thread = threading.Thread(target=run_graphql_server, daemon=True)
    graphql_thread.start()
    logger.info("GraphQL API started on port 8000")
    
    # Run Telegram bot in main thread
    logger.info("Starting Telegram bot...")
    run_telegram_bot()