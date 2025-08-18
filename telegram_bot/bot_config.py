"""
Telegram Bot Configuration
Settings and authentication for the trading bot
"""

import os
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum

class UserRole(Enum):
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"

class CommandAccess(Enum):
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    ADMIN_ONLY = "admin_only"

@dataclass
class BotConfig:
    """Telegram bot configuration"""
    # Bot credentials
    bot_token: str
    bot_username: str
    
    # Authentication
    admin_user_ids: List[int]
    allowed_user_ids: List[int]
    require_authentication: bool = True
    
    # Trading settings
    max_position_size: float = 10000  # USD
    default_leverage: int = 10
    allow_market_orders: bool = True
    allow_limit_orders: bool = True
    
    # Risk limits
    daily_loss_limit: float = 1000  # USD
    max_open_positions: int = 10
    stop_loss_required: bool = True
    
    # Monitoring
    alert_chat_id: int = None
    enable_price_alerts: bool = True
    enable_position_alerts: bool = True
    enable_funding_alerts: bool = True
    
    # Features
    enable_trading: bool = True
    enable_monitoring: bool = True
    enable_analytics: bool = True
    enable_backtesting: bool = True
    
    # API endpoints
    api_base_url: str = "https://bybit-danila-api.fly.dev"
    websocket_url: str = "wss://bybit-danila-api.fly.dev/ws"
    
    # Rate limiting
    max_commands_per_minute: int = 30
    max_trades_per_hour: int = 100

class Commands:
    """Bot command definitions"""
    
    # Authentication
    START = "/start"
    AUTH = "/auth"
    LOGOUT = "/logout"
    
    # Account
    BALANCE = "/balance"
    POSITIONS = "/positions"
    ORDERS = "/orders"
    HISTORY = "/history"
    PNL = "/pnl"
    
    # Trading
    BUY = "/buy"
    SELL = "/sell"
    CLOSE = "/close"
    CLOSE_ALL = "/closeall"
    
    # Advanced Orders
    STOP_LOSS = "/stoploss"
    TAKE_PROFIT = "/takeprofit"
    TRAILING = "/trailing"
    
    # Strategies
    GRID = "/grid"
    DCA = "/dca"
    FUNDING = "/funding"
    ARBITRAGE = "/arbitrage"
    
    # Market Data
    PRICE = "/price"
    CHART = "/chart"
    FUNDING_RATE = "/fundingrate"
    VOLUME = "/volume"
    
    # Analytics
    STATS = "/stats"
    PERFORMANCE = "/performance"
    BACKTEST = "/backtest"
    SIGNALS = "/signals"
    
    # Monitoring
    ALERTS = "/alerts"
    SET_ALERT = "/setalert"
    REMOVE_ALERT = "/removealert"
    
    # Settings
    SETTINGS = "/settings"
    SET_LEVERAGE = "/leverage"
    SET_RISK = "/risk"
    
    # Admin
    USERS = "/users"
    ADD_USER = "/adduser"
    REMOVE_USER = "/removeuser"
    SYSTEM = "/system"
    RESTART = "/restart"
    
    # Help
    HELP = "/help"
    COMMANDS = "/commands"
    GUIDE = "/guide"

class Messages:
    """Bot message templates"""
    
    # Welcome
    WELCOME = """
🤖 *Bybit Trading Bot v10.0*

Welcome to your personal trading assistant!

Use /help to see available commands
Use /auth to authenticate
Use /guide for trading guide

_Built with Phase 1-10 features_
    """
    
    # Authentication
    AUTH_SUCCESS = "✅ Authentication successful! You now have access to trading features."
    AUTH_FAILED = "❌ Authentication failed. Please check your credentials."
    NOT_AUTHORIZED = "🔒 You are not authorized to use this command."
    
    # Trading
    ORDER_PLACED = "✅ Order placed successfully!\n{details}"
    ORDER_FAILED = "❌ Failed to place order: {error}"
    POSITION_CLOSED = "✅ Position closed!\nP&L: {pnl}"
    
    # Errors
    INVALID_COMMAND = "❌ Invalid command format. Use /help for syntax."
    RATE_LIMITED = "⚠️ Rate limit exceeded. Please wait {seconds} seconds."
    SYSTEM_ERROR = "🔧 System error occurred. Please try again later."
    
    # Market Data
    PRICE_TEMPLATE = """
💹 *{symbol} Price*
Current: ${price:,.2f}
24h Change: {change:+.2f}%
24h Volume: ${volume:,.0f}
Funding Rate: {funding:.4f}%
    """
    
    # Position Template
    POSITION_TEMPLATE = """
📊 *{symbol} Position*
Side: {side}
Size: {size} ({value:,.2f} USD)
Entry: ${entry:,.2f}
Current: ${current:,.2f}
PnL: {pnl:+.2f} USD ({pnl_pct:+.2f}%)
    """
    
    # Analytics
    STATS_TEMPLATE = """
📈 *Account Statistics*
Total P&L: {total_pnl:+.2f} USD
Win Rate: {win_rate:.1f}%
Trades Today: {trades_today}
Active Positions: {active_positions}
Available Balance: ${balance:,.2f}
    """

class Keyboards:
    """Inline keyboard layouts"""
    
    @staticmethod
    def main_menu() -> List[List[Dict[str, str]]]:
        """Main menu keyboard"""
        return [
            [{"text": "💰 Balance", "callback_data": "balance"},
             {"text": "📊 Positions", "callback_data": "positions"}],
            [{"text": "📈 Buy", "callback_data": "buy"},
             {"text": "📉 Sell", "callback_data": "sell"}],
            [{"text": "🎯 Strategies", "callback_data": "strategies"},
             {"text": "📊 Analytics", "callback_data": "analytics"}],
            [{"text": "⚙️ Settings", "callback_data": "settings"},
             {"text": "❓ Help", "callback_data": "help"}]
        ]
    
    @staticmethod
    def position_actions(position_id: str) -> List[List[Dict[str, str]]]:
        """Position action buttons"""
        return [
            [{"text": "❌ Close", "callback_data": f"close_{position_id}"},
             {"text": "✏️ Modify", "callback_data": f"modify_{position_id}"}],
            [{"text": "🛡 Add SL", "callback_data": f"sl_{position_id}"},
             {"text": "🎯 Add TP", "callback_data": f"tp_{position_id}"}],
            [{"text": "🔄 Refresh", "callback_data": f"refresh_{position_id}"}]
        ]
    
    @staticmethod
    def strategy_selection() -> List[List[Dict[str, str]]]:
        """Strategy selection keyboard"""
        return [
            [{"text": "📊 Grid Trading", "callback_data": "strategy_grid"}],
            [{"text": "💰 Funding Arbitrage", "callback_data": "strategy_funding"}],
            [{"text": "🔄 DCA Bot", "callback_data": "strategy_dca"}],
            [{"text": "🎯 Smart Orders", "callback_data": "strategy_smart"}],
            [{"text": "🤖 ML Predictions", "callback_data": "strategy_ml"}],
            [{"text": "◀️ Back", "callback_data": "main_menu"}]
        ]
    
    @staticmethod
    def confirmation(action: str, data: str) -> List[List[Dict[str, str]]]:
        """Confirmation keyboard"""
        return [
            [{"text": "✅ Confirm", "callback_data": f"confirm_{action}_{data}"},
             {"text": "❌ Cancel", "callback_data": "cancel"}]
        ]

class BotSettings:
    """Runtime bot settings"""
    
    def __init__(self):
        self.config = BotConfig(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            bot_username=os.getenv("TELEGRAM_BOT_USERNAME", "@BybitDanilaBot"),
            admin_user_ids=[int(id) for id in os.getenv("ADMIN_USER_IDS", "").split(",") if id],
            allowed_user_ids=[int(id) for id in os.getenv("ALLOWED_USER_IDS", "").split(",") if id],
            alert_chat_id=int(os.getenv("ALERT_CHAT_ID", "0")) if os.getenv("ALERT_CHAT_ID") else None
        )
        
        # Command access levels
        self.command_access = {
            Commands.START: CommandAccess.PUBLIC,
            Commands.HELP: CommandAccess.PUBLIC,
            Commands.PRICE: CommandAccess.PUBLIC,
            Commands.AUTH: CommandAccess.PUBLIC,
            
            Commands.BALANCE: CommandAccess.AUTHENTICATED,
            Commands.POSITIONS: CommandAccess.AUTHENTICATED,
            Commands.BUY: CommandAccess.AUTHENTICATED,
            Commands.SELL: CommandAccess.AUTHENTICATED,
            Commands.CLOSE: CommandAccess.AUTHENTICATED,
            
            Commands.USERS: CommandAccess.ADMIN_ONLY,
            Commands.ADD_USER: CommandAccess.ADMIN_ONLY,
            Commands.SYSTEM: CommandAccess.ADMIN_ONLY,
            Commands.RESTART: CommandAccess.ADMIN_ONLY,
        }
        
        # Rate limiting
        self.user_command_counts = {}
        self.user_trade_counts = {}
        
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self.config.admin_user_ids
    
    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        if not self.config.require_authentication:
            return True
        return user_id in self.config.allowed_user_ids or self.is_admin(user_id)
    
    def can_execute_command(self, user_id: int, command: str) -> bool:
        """Check if user can execute command"""
        access_level = self.command_access.get(command, CommandAccess.AUTHENTICATED)
        
        if access_level == CommandAccess.PUBLIC:
            return True
        elif access_level == CommandAccess.AUTHENTICATED:
            return self.is_authorized(user_id)
        elif access_level == CommandAccess.ADMIN_ONLY:
            return self.is_admin(user_id)
        
        return False
    
    def check_rate_limit(self, user_id: int, action: str = "command") -> tuple[bool, int]:
        """
        Check if user is rate limited
        
        Returns:
            (is_allowed, seconds_to_wait)
        """
        # Implementation would track timestamps and counts
        # Simplified for now
        return True, 0

# Global settings instance
bot_settings = BotSettings()