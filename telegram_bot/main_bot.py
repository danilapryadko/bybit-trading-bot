"""
Bybit Trading Bot - Telegram Interface
Main bot handler and orchestrator
"""

import logging
import asyncio
import os
from typing import Optional
from datetime import datetime

from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from .bot_config import bot_settings, Commands, Messages, Keyboards
from .trading_commands import TradingCommands
from .monitoring_alerts import MonitoringAlerts, AlertType, AlertCondition
from .strategy_handler import StrategyHandler
from .api_client import BotAPIClient

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class BybitTradingBot:
    """Main Telegram bot class"""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the trading bot
        
        Args:
            token: Bot token (or from environment)
        """
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("Bot token not provided")
        
        # Initialize components
        self.api_client = BotAPIClient(bot_settings.config.api_base_url)
        self.trading = TradingCommands(self.api_client)
        self.strategies = StrategyHandler(self.api_client)
        
        # Initialize bot and monitoring
        self.bot = Bot(self.token)
        self.monitoring = MonitoringAlerts(self.bot, self.api_client)
        
        # Build application
        self.app = Application.builder().token(self.token).build()
        self._register_handlers()
        
        logger.info("Bybit Trading Bot initialized")
    
    def _register_handlers(self):
        """Register all command and callback handlers"""
        
        # Basic commands
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("auth", self.cmd_auth))
        
        # Account commands
        self.app.add_handler(CommandHandler("balance", self.trading.handle_balance))
        self.app.add_handler(CommandHandler("positions", self.trading.handle_positions))
        self.app.add_handler(CommandHandler("orders", self.cmd_orders))
        self.app.add_handler(CommandHandler("history", self.cmd_history))
        self.app.add_handler(CommandHandler("pnl", self.cmd_pnl))
        
        # Trading commands
        self.app.add_handler(CommandHandler("buy", self.trading.handle_buy))
        self.app.add_handler(CommandHandler("sell", self.trading.handle_sell))
        self.app.add_handler(CommandHandler("close", self.trading.handle_close))
        self.app.add_handler(CommandHandler("closeall", self.trading.handle_close_all))
        
        # Advanced orders
        self.app.add_handler(CommandHandler("stoploss", self.trading.handle_stop_loss))
        self.app.add_handler(CommandHandler("takeprofit", self.trading.handle_take_profit))
        self.app.add_handler(CommandHandler("trailing", self.cmd_trailing))
        
        # Strategy commands
        self.app.add_handler(CommandHandler("grid", self.strategies.handle_grid))
        self.app.add_handler(CommandHandler("funding", self.strategies.handle_funding))
        self.app.add_handler(CommandHandler("arbitrage", self.strategies.handle_arbitrage))
        self.app.add_handler(CommandHandler("dca", self.strategies.handle_dca))
        
        # Market data
        self.app.add_handler(CommandHandler("price", self.cmd_price))
        self.app.add_handler(CommandHandler("chart", self.cmd_chart))
        self.app.add_handler(CommandHandler("fundingrate", self.cmd_funding_rate))
        self.app.add_handler(CommandHandler("volume", self.cmd_volume))
        
        # Analytics
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("performance", self.cmd_performance))
        self.app.add_handler(CommandHandler("signals", self.cmd_signals))
        
        # Alerts
        self.app.add_handler(CommandHandler("alerts", self.cmd_alerts))
        self.app.add_handler(CommandHandler("setalert", self.cmd_set_alert))
        self.app.add_handler(CommandHandler("removealert", self.cmd_remove_alert))
        
        # Settings
        self.app.add_handler(CommandHandler("settings", self.cmd_settings))
        self.app.add_handler(CommandHandler("leverage", self.cmd_leverage))
        
        # Admin commands
        self.app.add_handler(CommandHandler("users", self.cmd_users))
        self.app.add_handler(CommandHandler("system", self.cmd_system))
        
        # Callback query handlers
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Message handler for unknown commands
        self.app.add_handler(MessageHandler(
            filters.COMMAND,
            self.handle_unknown
        ))
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        keyboard = Keyboards.main_menu()
        
        await update.message.reply_text(
            Messages.WELCOME,
            parse_mode='Markdown',
            reply_markup={'inline_keyboard': keyboard}
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📚 *Available Commands*

*Account*
/balance - View account balance
/positions - View open positions
/orders - View open orders
/pnl - View P&L summary

*Trading*
/buy SYMBOL AMOUNT [PRICE] - Buy
/sell SYMBOL AMOUNT [PRICE] - Sell
/close POSITION_ID - Close position
/closeall - Close all positions

*Advanced Orders*
/stoploss POSITION PRICE - Set stop loss
/takeprofit POSITION PRICE - Set take profit
/trailing POSITION PERCENT - Set trailing stop

*Strategies*
/grid - Grid trading strategy
/funding - Funding rate arbitrage
/arbitrage - Arbitrage opportunities
/dca - Dollar cost averaging

*Market Data*
/price SYMBOL - Get current price
/chart SYMBOL - Get price chart
/fundingrate SYMBOL - Funding rate
/volume SYMBOL - Trading volume

*Alerts*
/alerts - View active alerts
/setalert - Create new alert
/removealert ID - Remove alert

*Settings*
/settings - Bot settings
/leverage VALUE - Set leverage

Use /guide for detailed trading guide.
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def cmd_auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /auth command"""
        user_id = update.effective_user.id
        
        if bot_settings.is_authorized(user_id):
            await update.message.reply_text("✅ You are already authenticated!")
            return
        
        # In production, implement proper authentication
        # For now, just check if user is in allowed list
        await update.message.reply_text(
            "🔐 Please contact admin to get access.\n"
            f"Your User ID: `{user_id}`",
            parse_mode='Markdown'
        )
    
    async def cmd_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /orders command"""
        user_id = update.effective_user.id
        
        if not bot_settings.is_authorized(user_id):
            await update.message.reply_text(Messages.NOT_AUTHORIZED)
            return
        
        try:
            orders = await self.api_client.get_open_orders()
            
            if not orders:
                await update.message.reply_text("📋 No open orders")
                return
            
            message = "📋 *Open Orders*\n\n"
            for order in orders:
                message += f"• {order['symbol']} {order['side']} {order['qty']} @ ${order['price']}\n"
                message += f"  Status: {order['status']}\n"
                message += f"  ID: `{order['order_id']}`\n\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def cmd_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /history command"""
        user_id = update.effective_user.id
        
        if not bot_settings.is_authorized(user_id):
            await update.message.reply_text(Messages.NOT_AUTHORIZED)
            return
        
        try:
            # Get trade history (last 10)
            trades = await self.api_client.get_trade_history(limit=10)
            
            if not trades:
                await update.message.reply_text("📜 No trade history")
                return
            
            message = "📜 *Recent Trades*\n\n"
            for trade in trades:
                message += f"• {trade['symbol']} {trade['side']}\n"
                message += f"  Size: {trade['qty']} @ ${trade['price']}\n"
                message += f"  P&L: ${trade['pnl']:+.2f}\n"
                message += f"  Time: {trade['time']}\n\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def cmd_pnl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pnl command"""
        user_id = update.effective_user.id
        
        if not bot_settings.is_authorized(user_id):
            await update.message.reply_text(Messages.NOT_AUTHORIZED)
            return
        
        try:
            pnl_data = await self.api_client.get_pnl_summary()
            
            message = f"""
💰 *P&L Summary*

*Today*
P&L: ${pnl_data['today_pnl']:+,.2f}
Trades: {pnl_data['today_trades']}
Win Rate: {pnl_data['today_win_rate']:.1f}%

*This Week*
P&L: ${pnl_data['week_pnl']:+,.2f}
Trades: {pnl_data['week_trades']}
Win Rate: {pnl_data['week_win_rate']:.1f}%

*This Month*
P&L: ${pnl_data['month_pnl']:+,.2f}
Trades: {pnl_data['month_trades']}
Win Rate: {pnl_data['month_win_rate']:.1f}%

*All Time*
P&L: ${pnl_data['total_pnl']:+,.2f}
Trades: {pnl_data['total_trades']}
Win Rate: {pnl_data['total_win_rate']:.1f}%
            """
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting P&L: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def cmd_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /price command"""
        if not context.args:
            await update.message.reply_text(
                "Usage: /price SYMBOL\n"
                "Example: /price BTCUSDT"
            )
            return
        
        symbol = context.args[0].upper()
        
        try:
            price_data = await self.api_client.get_ticker(symbol)
            
            message = Messages.PRICE_TEMPLATE.format(
                symbol=symbol,
                price=price_data['price'],
                change=price_data['change_24h'],
                volume=price_data['volume_24h'],
                funding=price_data['funding_rate']
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting price: {e}")
            await update.message.reply_text(f"❌ Failed to get price for {symbol}")
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user_id = update.effective_user.id
        
        if not bot_settings.is_authorized(user_id):
            await update.message.reply_text(Messages.NOT_AUTHORIZED)
            return
        
        try:
            stats = await self.api_client.get_account_statistics()
            
            message = Messages.STATS_TEMPLATE.format(
                total_pnl=stats['total_pnl'],
                win_rate=stats['win_rate'],
                trades_today=stats['trades_today'],
                active_positions=stats['active_positions'],
                balance=stats['available_balance']
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def cmd_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts command"""
        user_id = update.effective_user.id
        
        if not bot_settings.is_authorized(user_id):
            await update.message.reply_text(Messages.NOT_AUTHORIZED)
            return
        
        alerts = await self.monitoring.get_user_alerts(user_id)
        
        if not alerts:
            await update.message.reply_text("🔔 No active alerts")
            return
        
        message = "🔔 *Active Alerts*\n\n"
        for alert in alerts:
            message += f"• {alert.type.value} - {alert.symbol}\n"
            message += f"  Condition: {alert.condition.value} {alert.value}\n"
            message += f"  ID: `{alert.id}`\n\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_set_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setalert command"""
        user_id = update.effective_user.id
        
        if not bot_settings.is_authorized(user_id):
            await update.message.reply_text(Messages.NOT_AUTHORIZED)
            return
        
        if len(context.args) < 3:
            await update.message.reply_text(
                "Usage: /setalert TYPE SYMBOL CONDITION VALUE\n"
                "Example: /setalert price BTCUSDT above 50000\n"
                "Example: /setalert funding ETHUSDT above 0.01"
            )
            return
        
        try:
            alert_type = AlertType[context.args[0].upper()]
            symbol = context.args[1].upper()
            condition = AlertCondition[context.args[2].upper()]
            value = float(context.args[3])
            
            alert_id = await self.monitoring.add_alert(
                user_id=user_id,
                alert_type=alert_type,
                symbol=symbol,
                condition=condition,
                value=value
            )
            
            await update.message.reply_text(
                f"✅ Alert created!\nID: `{alert_id}`",
                parse_mode='Markdown'
            )
            
        except (KeyError, ValueError):
            await update.message.reply_text("❌ Invalid alert parameters")
        except Exception as e:
            logger.error(f"Error setting alert: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def cmd_system(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /system command (admin only)"""
        user_id = update.effective_user.id
        
        if not bot_settings.is_admin(user_id):
            await update.message.reply_text(Messages.NOT_AUTHORIZED)
            return
        
        try:
            # Get system metrics
            metrics = self.monitoring.get_metrics()
            api_status = await self.api_client.get_system_status()
            
            message = f"""
🖥 *System Status*

*API*
Status: {'🟢 Online' if api_status['online'] else '🔴 Offline'}
Latency: {metrics['api_latency']:.0f}ms
WebSocket: {'✅' if metrics['websocket_status'] else '❌'}

*Trading*
Positions: {metrics['positions_count']}
Total P&L: ${metrics['total_pnl']:+,.2f}
Margin Usage: {metrics['margin_usage']:.1f}%

*Monitoring*
Active Alerts: {metrics['active_alerts']}
Status: {'🟢 Active' if metrics['monitoring_active'] else '🔴 Inactive'}
Last Update: {metrics['last_update']}

*Bot*
Version: 10.0.0
Uptime: {api_status['uptime']}
Memory: {api_status['memory_usage']:.1f}%
            """
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Main menu callbacks
        if data == "balance":
            await self.trading.handle_balance(update, context)
        elif data == "positions":
            await self.trading.handle_positions(update, context)
        elif data == "strategies":
            keyboard = Keyboards.strategy_selection()
            await query.edit_message_reply_markup(
                reply_markup={'inline_keyboard': keyboard}
            )
        elif data == "main_menu":
            keyboard = Keyboards.main_menu()
            await query.edit_message_reply_markup(
                reply_markup={'inline_keyboard': keyboard}
            )
        
        # Position actions
        elif data.startswith("close_"):
            position_id = data.replace("close_", "")
            await self.trading.handle_callback_close_position(update, context, position_id)
        
        # Confirmations
        elif data.startswith("confirm_closeall"):
            await self.trading.handle_callback_confirm_closeall(update, context)
        elif data == "cancel":
            await query.edit_message_text("❌ Cancelled")
    
    async def handle_unknown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown commands"""
        await update.message.reply_text(
            "❓ Unknown command. Use /help to see available commands."
        )
    
    async def run(self):
        """Run the bot"""
        logger.info("Starting Bybit Trading Bot...")
        
        # Start monitoring
        asyncio.create_task(self.monitoring.start_monitoring())
        
        # Start bot
        await self.app.run_polling()
    
    async def stop(self):
        """Stop the bot"""
        logger.info("Stopping Bybit Trading Bot...")
        await self.monitoring.stop_monitoring()
        await self.app.stop()

# Additional required commands
async def cmd_trailing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /trailing command"""
    await update.message.reply_text("Trailing stop implementation")

async def cmd_chart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /chart command"""
    await update.message.reply_text("Chart generation implementation")

async def cmd_funding_rate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /fundingrate command"""
    await update.message.reply_text("Funding rate implementation")

async def cmd_volume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /volume command"""
    await update.message.reply_text("Volume data implementation")

async def cmd_performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /performance command"""
    await update.message.reply_text("Performance metrics implementation")

async def cmd_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /signals command"""
    await update.message.reply_text("Trading signals implementation")

async def cmd_remove_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removealert command"""
    await update.message.reply_text("Remove alert implementation")

async def cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command"""
    await update.message.reply_text("Settings implementation")

async def cmd_leverage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /leverage command"""
    await update.message.reply_text("Leverage settings implementation")

async def cmd_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /users command"""
    await update.message.reply_text("User management implementation")

if __name__ == "__main__":
    # Run the bot
    bot = BybitTradingBot()
    asyncio.run(bot.run())