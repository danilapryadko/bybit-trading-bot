"""
Telegram Bot for Bybit Trading Bot
Provides notifications and remote control capabilities
"""
import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telegram.constants import ParseMode

# from trading_bot import TradingBot  # Not needed, we'll use the bot passed in
# from risk_manager_v2 import RiskManagerV2
# from backtesting_engine import BacktestingEngine

logger = logging.getLogger(__name__)


@dataclass
class UserSession:
    """User session management"""
    user_id: int
    chat_id: int
    is_authenticated: bool = False
    last_activity: datetime = None
    trading_bot: Optional[Any] = None
    

class TelegramBot:
    """Telegram bot for trading notifications and control"""
    
    def __init__(
        self,
        token: str,
        allowed_users: List[int] = None,
        trading_bot: Optional[Any] = None
    ):
        self.token = token
        self.allowed_users = allowed_users or []
        self.trading_bot = trading_bot
        self.sessions: Dict[int, UserSession] = {}
        self.app = None
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Check if user is allowed
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text(
                "⛔ Unauthorized access. This bot is private."
            )
            return
            
        # Create or update session
        self.sessions[user_id] = UserSession(
            user_id=user_id,
            chat_id=chat_id,
            is_authenticated=True,
            last_activity=datetime.now(),
            trading_bot=self.trading_bot
        )
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Dashboard", callback_data="dashboard"),
                InlineKeyboardButton("💼 Positions", callback_data="positions")
            ],
            [
                InlineKeyboardButton("📈 Market", callback_data="market"),
                InlineKeyboardButton("🤖 Bot Status", callback_data="status")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                InlineKeyboardButton("❓ Help", callback_data="help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_message = (
            "🚀 *Welcome to Bybit Trading Bot*\n\n"
            "I'm your personal trading assistant. "
            "Select an option below to get started:"
        )
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show trading dashboard"""
        query = update.callback_query
        await query.answer()
        
        if not self.trading_bot:
            await query.edit_message_text("❌ Trading bot not initialized")
            return
            
        # Get account info
        balance = self.trading_bot.get_balance()
        positions = self.trading_bot.get_positions()
        pnl = sum(p.get('unrealizedPnl', 0) for p in positions)
        
        dashboard_text = (
            "📊 *Trading Dashboard*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 *Balance:* ${balance:,.2f}\n"
            f"📈 *Open Positions:* {len(positions)}\n"
            f"💵 *Unrealized P&L:* ${pnl:+,.2f}\n"
            f"🤖 *Bot Status:* {'🟢 Active' if self.trading_bot.is_running else '🔴 Stopped'}\n"
            f"📝 *Strategy:* {self.trading_bot.strategy_name}\n"
            f"⏰ *Updated:* {datetime.now().strftime('%H:%M:%S')}"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="dashboard"),
                InlineKeyboardButton("◀️ Back", callback_data="menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            dashboard_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show open positions"""
        query = update.callback_query
        await query.answer()
        
        if not self.trading_bot:
            await query.edit_message_text("❌ Trading bot not initialized")
            return
            
        positions = self.trading_bot.get_positions()
        
        if not positions:
            positions_text = "📭 *No open positions*"
        else:
            positions_text = "💼 *Open Positions*\n━━━━━━━━━━━━━━━━━━━━\n\n"
            
            for pos in positions[:5]:  # Show max 5 positions
                symbol = pos['symbol']
                side = pos['side']
                size = pos['size']
                entry_price = pos['avgPrice']
                mark_price = pos['markPrice']
                pnl = pos['unrealizedPnl']
                pnl_percent = (pnl / (size * entry_price)) * 100 if entry_price > 0 else 0
                
                emoji = "🟢" if side == "Buy" else "🔴"
                pnl_emoji = "📈" if pnl >= 0 else "📉"
                
                positions_text += (
                    f"{emoji} *{symbol}*\n"
                    f"├ Side: {side}\n"
                    f"├ Size: {size}\n"
                    f"├ Entry: ${entry_price:.4f}\n"
                    f"├ Mark: ${mark_price:.4f}\n"
                    f"└ P&L: {pnl_emoji} ${pnl:+,.2f} ({pnl_percent:+.2f}%)\n\n"
                )
                
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="positions"),
                InlineKeyboardButton("❌ Close All", callback_data="close_all")
            ],
            [InlineKeyboardButton("◀️ Back", callback_data="menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            positions_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show market overview"""
        query = update.callback_query
        await query.answer()
        
        if not self.trading_bot:
            await query.edit_message_text("❌ Trading bot not initialized")
            return
            
        # Get market data for watchlist
        watchlist = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        market_text = "📈 *Market Overview*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for symbol in watchlist:
            ticker = self.trading_bot.get_ticker(symbol)
            if ticker:
                price = ticker['lastPrice']
                change_24h = ticker['price24hPcnt'] * 100
                volume = ticker['volume24h']
                
                trend = "🟢" if change_24h >= 0 else "🔴"
                market_text += (
                    f"{trend} *{symbol}*\n"
                    f"├ Price: ${price:,.2f}\n"
                    f"├ 24h: {change_24h:+.2f}%\n"
                    f"└ Volume: ${volume/1e6:.1f}M\n\n"
                )
                
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="market"),
                InlineKeyboardButton("◀️ Back", callback_data="menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            market_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot status"""
        query = update.callback_query
        await query.answer()
        
        if not self.trading_bot:
            status_text = "❌ *Bot Status: Not Initialized*"
            keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="menu")]]
        else:
            is_running = self.trading_bot.is_running
            status_emoji = "🟢" if is_running else "🔴"
            
            status_text = (
                f"{status_emoji} *Bot Status*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🤖 *Status:* {'Running' if is_running else 'Stopped'}\n"
                f"📝 *Strategy:* {self.trading_bot.strategy_name}\n"
                f"🎯 *Mode:* {'Paper' if self.trading_bot.paper_trading else 'Live'}\n"
                f"⚖️ *Risk per trade:* {self.trading_bot.risk_per_trade}%\n"
                f"📊 *Max positions:* {self.trading_bot.max_positions}\n"
                f"⏰ *Uptime:* {self._get_uptime()}\n"
            )
            
            if is_running:
                keyboard = [
                    [
                        InlineKeyboardButton("⏸️ Pause", callback_data="pause_bot"),
                        InlineKeyboardButton("🛑 Stop", callback_data="stop_bot")
                    ],
                    [InlineKeyboardButton("◀️ Back", callback_data="menu")]
                ]
            else:
                keyboard = [
                    [InlineKeyboardButton("▶️ Start", callback_data="start_bot")],
                    [InlineKeyboardButton("◀️ Back", callback_data="menu")]
                ]
                
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            status_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show settings menu"""
        query = update.callback_query
        await query.answer()
        
        settings_text = (
            "⚙️ *Settings*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Select a setting to modify:"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Strategy", callback_data="set_strategy"),
                InlineKeyboardButton("⚖️ Risk", callback_data="set_risk")
            ],
            [
                InlineKeyboardButton("🎯 Leverage", callback_data="set_leverage"),
                InlineKeyboardButton("📈 Positions", callback_data="set_positions")
            ],
            [
                InlineKeyboardButton("🔔 Alerts", callback_data="set_alerts"),
                InlineKeyboardButton("📝 Watchlist", callback_data="set_watchlist")
            ],
            [InlineKeyboardButton("◀️ Back", callback_data="menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            settings_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help information"""
        query = update.callback_query
        await query.answer()
        
        help_text = (
            "❓ *Help & Commands*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "*Available Commands:*\n"
            "/start - Start the bot\n"
            "/status - Check bot status\n"
            "/balance - Show account balance\n"
            "/positions - List open positions\n"
            "/open [symbol] [side] [amount] - Open position\n"
            "/close [symbol] - Close position\n"
            "/report [daily|weekly|monthly] - Get trading report\n"
            "/stop - Stop the bot\n\n"
            "*Keyboard Shortcuts:*\n"
            "Use the inline buttons to navigate\n"
            "and control the bot easily.\n\n"
            "*Support:*\n"
            "GitHub: github.com/bybit-bot\n"
            "Version: 2.0.0"
        )
        
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard buttons"""
        query = update.callback_query
        
        handlers = {
            "menu": self.show_menu,
            "dashboard": self.dashboard,
            "positions": self.positions,
            "market": self.market,
            "status": self.status,
            "settings": self.settings,
            "help": self.help,
            "start_bot": self.start_bot,
            "stop_bot": self.stop_bot,
            "pause_bot": self.pause_bot,
            "close_all": self.close_all_positions,
        }
        
        handler = handlers.get(query.data)
        if handler:
            await handler(update, context)
        else:
            await query.answer("Function not implemented yet")
            
    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main menu"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Dashboard", callback_data="dashboard"),
                InlineKeyboardButton("💼 Positions", callback_data="positions")
            ],
            [
                InlineKeyboardButton("📈 Market", callback_data="market"),
                InlineKeyboardButton("🤖 Bot Status", callback_data="status")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                InlineKeyboardButton("❓ Help", callback_data="help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📱 *Main Menu*\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def start_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start trading bot"""
        query = update.callback_query
        await query.answer()
        
        if self.trading_bot and not self.trading_bot.is_running:
            # Start bot in background
            asyncio.create_task(self.trading_bot.start())
            await query.edit_message_text(
                "✅ Trading bot started successfully!",
                parse_mode=ParseMode.MARKDOWN
            )
            await asyncio.sleep(2)
            await self.status(update, context)
        else:
            await query.edit_message_text("❌ Bot already running or not initialized")
            
    async def stop_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop trading bot"""
        query = update.callback_query
        await query.answer()
        
        if self.trading_bot and self.trading_bot.is_running:
            self.trading_bot.stop()
            await query.edit_message_text(
                "🛑 Trading bot stopped successfully!",
                parse_mode=ParseMode.MARKDOWN
            )
            await asyncio.sleep(2)
            await self.status(update, context)
        else:
            await query.edit_message_text("❌ Bot not running")
            
    async def pause_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pause trading bot"""
        query = update.callback_query
        await query.answer()
        
        if self.trading_bot and self.trading_bot.is_running:
            self.trading_bot.pause()
            await query.edit_message_text(
                "⏸️ Trading bot paused. Use /start to resume.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text("❌ Bot not running")
            
    async def close_all_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Close all open positions"""
        query = update.callback_query
        await query.answer("Closing all positions...")
        
        if self.trading_bot:
            results = self.trading_bot.close_all_positions()
            await query.edit_message_text(
                f"✅ Closed {len(results)} positions",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text("❌ Bot not initialized")
            
    async def open_position_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /open command - Open a new position"""
        user_id = update.effective_user.id
        
        # Check authorization
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text("⛔ Unauthorized access")
            return
            
        # Parse arguments: /open BTCUSDT long 0.001
        args = context.args
        if len(args) < 3:
            await update.message.reply_text(
                "❌ Invalid format\n"
                "Usage: `/open [symbol] [side] [amount]`\n"
                "Example: `/open BTCUSDT long 0.001`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        symbol = args[0].upper()
        side = args[1].lower()
        try:
            amount = float(args[2])
        except ValueError:
            await update.message.reply_text("❌ Invalid amount")
            return
            
        if side not in ['long', 'buy', 'short', 'sell']:
            await update.message.reply_text("❌ Side must be 'long' or 'short'")
            return
            
        # Convert to standard side format
        side = 'Buy' if side in ['long', 'buy'] else 'Sell'
        
        if not self.trading_bot:
            await update.message.reply_text("❌ Trading bot not initialized")
            return
            
        try:
            # Place order through trading bot
            order = self.trading_bot.place_order(
                symbol=symbol,
                side=side,
                qty=amount,
                order_type='Market'
            )
            
            await update.message.reply_text(
                f"✅ *Position Opened*\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"Symbol: {symbol}\n"
                f"Side: {side}\n"
                f"Amount: {amount}\n"
                f"Order ID: {order.get('orderId', 'N/A')}\n"
                f"Status: {order.get('orderStatus', 'N/A')}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to open position: {str(e)}")
            
    async def close_position_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /close command - Close a position"""
        user_id = update.effective_user.id
        
        # Check authorization
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text("⛔ Unauthorized access")
            return
            
        # Parse arguments: /close BTCUSDT
        args = context.args
        if len(args) < 1:
            await update.message.reply_text(
                "❌ Invalid format\n"
                "Usage: `/close [symbol]`\n"
                "Example: `/close BTCUSDT`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        symbol = args[0].upper()
        
        if not self.trading_bot:
            await update.message.reply_text("❌ Trading bot not initialized")
            return
            
        try:
            # Get position for symbol
            positions = self.trading_bot.get_positions()
            position = next((p for p in positions if p['symbol'] == symbol), None)
            
            if not position:
                await update.message.reply_text(f"❌ No open position for {symbol}")
                return
                
            # Close the position
            result = self.trading_bot.close_position(symbol)
            
            await update.message.reply_text(
                f"✅ *Position Closed*\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"Symbol: {symbol}\n"
                f"Side: {position['side']}\n"
                f"Size: {position['size']}\n"
                f"P&L: ${position.get('unrealizedPnl', 0):+,.2f}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to close position: {str(e)}")
            
    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /report command - Generate trading report"""
        user_id = update.effective_user.id
        
        # Check authorization
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text("⛔ Unauthorized access")
            return
            
        # Parse arguments: /report daily|weekly|monthly
        args = context.args
        period = args[0].lower() if args else 'daily'
        
        if period not in ['daily', 'weekly', 'monthly']:
            await update.message.reply_text(
                "❌ Invalid period\n"
                "Usage: `/report [daily|weekly|monthly]`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        if not self.trading_bot:
            await update.message.reply_text("❌ Trading bot not initialized")
            return
            
        try:
            # Calculate date range
            from datetime import datetime, timedelta
            end_date = datetime.now()
            
            if period == 'daily':
                start_date = end_date - timedelta(days=1)
            elif period == 'weekly':
                start_date = end_date - timedelta(days=7)
            else:  # monthly
                start_date = end_date - timedelta(days=30)
                
            # Get trades for period
            trades = self.trading_bot.get_trades(start_date, end_date)
            positions = self.trading_bot.get_positions()
            balance = self.trading_bot.get_balance()
            
            # Calculate statistics
            total_trades = len(trades)
            winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
            losing_trades = sum(1 for t in trades if t.get('pnl', 0) <= 0)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            total_pnl = sum(t.get('pnl', 0) for t in trades)
            avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
            best_trade = max(trades, key=lambda t: t.get('pnl', 0)) if trades else None
            worst_trade = min(trades, key=lambda t: t.get('pnl', 0)) if trades else None
            
            # Format report
            report_text = (
                f"📊 *{period.capitalize()} Trading Report*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n\n"
                f"*Account Summary*\n"
                f"💰 Balance: ${balance:,.2f}\n"
                f"📈 Open Positions: {len(positions)}\n\n"
                f"*Trading Statistics*\n"
                f"📊 Total Trades: {total_trades}\n"
                f"✅ Winning: {winning_trades}\n"
                f"❌ Losing: {losing_trades}\n"
                f"📈 Win Rate: {win_rate:.1f}%\n\n"
                f"*P&L Summary*\n"
                f"💵 Total P&L: ${total_pnl:+,.2f}\n"
                f"📊 Average P&L: ${avg_pnl:+,.2f}\n"
            )
            
            if best_trade:
                report_text += f"🎯 Best Trade: ${best_trade.get('pnl', 0):+,.2f}\n"
            if worst_trade:
                report_text += f"📉 Worst Trade: ${worst_trade.get('pnl', 0):+,.2f}\n"
                
            # Add top pairs if available
            if trades:
                from collections import Counter
                pair_pnl = {}
                for trade in trades:
                    symbol = trade.get('symbol', 'Unknown')
                    if symbol not in pair_pnl:
                        pair_pnl[symbol] = 0
                    pair_pnl[symbol] += trade.get('pnl', 0)
                    
                top_pairs = sorted(pair_pnl.items(), key=lambda x: x[1], reverse=True)[:3]
                if top_pairs:
                    report_text += "\n*Top Performing Pairs*\n"
                    for symbol, pnl in top_pairs:
                        report_text += f"• {symbol}: ${pnl:+,.2f}\n"
                        
            await update.message.reply_text(report_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to generate report: {str(e)}")
            
    async def send_notification(
        self,
        chat_id: int,
        message: str,
        notification_type: str = "info"
    ):
        """Send notification to user"""
        emoji_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "trade": "💹",
            "position": "💼",
            "signal": "📡"
        }
        
        emoji = emoji_map.get(notification_type, "📢")
        formatted_message = f"{emoji} {message}"
        
        try:
            await self.app.bot.send_message(
                chat_id=chat_id,
                text=formatted_message,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            
    def _get_uptime(self) -> str:
        """Get bot uptime"""
        if not self.trading_bot or not hasattr(self.trading_bot, 'start_time'):
            return "N/A"
            
        uptime = datetime.now() - self.trading_bot.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
            
    def run(self):
        """Run the telegram bot"""
        # Create application
        self.app = Application.builder().token(self.token).build()
        
        # Add command handlers
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("open", self.open_position_command))
        self.app.add_handler(CommandHandler("close", self.close_position_command))
        self.app.add_handler(CommandHandler("report", self.report_command))
        self.app.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Add error handler
        self.app.add_error_handler(self.error_handler)
        
        # Start polling
        logger.info("Starting Telegram bot...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        # Send error message to user
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again later."
            )
            

def main():
    """Main entry point"""
    # Load configuration
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return
        
    # Get allowed users from environment
    allowed_users = os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",")
    allowed_users = [int(u.strip()) for u in allowed_users if u.strip()]
    
    # Initialize trading bot (optional - can be passed from main app)
    trading_bot = None  # Will be initialized by main application
    
    # Create and run telegram bot
    bot = TelegramBot(
        token=token,
        allowed_users=allowed_users,
        trading_bot=trading_bot
    )
    
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Telegram bot stopped by user")
    except Exception as e:
        logger.error(f"Telegram bot error: {e}")
        

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()