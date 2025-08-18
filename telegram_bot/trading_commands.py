"""
Telegram Bot Trading Commands
Handles all trading-related commands and operations
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import aiohttp
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from .bot_config import bot_settings, Commands, Messages, Keyboards

logger = logging.getLogger(__name__)

class TradingCommands:
    """Trading command handlers"""
    
    def __init__(self, api_client):
        """
        Initialize trading commands
        
        Args:
            api_client: API client for backend communication
        """
        self.api_client = api_client
        self.active_orders = {}
        self.position_monitors = {}
    
    async def handle_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command"""
        try:
            user_id = update.effective_user.id
            
            if not bot_settings.is_authorized(user_id):
                await update.message.reply_text(Messages.NOT_AUTHORIZED)
                return
            
            # Get balance from API
            balance = await self.api_client.get_balance()
            
            message = f"""
💰 *Account Balance*

Available: ${balance['available']:,.2f}
Used Margin: ${balance['used_margin']:,.2f}
Total Equity: ${balance['total_equity']:,.2f}
Unrealized PnL: ${balance['unrealized_pnl']:+,.2f}

Margin Ratio: {balance['margin_ratio']:.2f}%
Free Margin: ${balance['free_margin']:,.2f}
            """
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def handle_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command"""
        try:
            user_id = update.effective_user.id
            
            if not bot_settings.is_authorized(user_id):
                await update.message.reply_text(Messages.NOT_AUTHORIZED)
                return
            
            # Get positions from API
            positions = await self.api_client.get_positions()
            
            if not positions:
                await update.message.reply_text("📊 No open positions")
                return
            
            for position in positions:
                message = Messages.POSITION_TEMPLATE.format(
                    symbol=position['symbol'],
                    side=position['side'],
                    size=position['size'],
                    value=position['value'],
                    entry=position['entry_price'],
                    current=position['current_price'],
                    pnl=position['pnl'],
                    pnl_pct=position['pnl_pct']
                )
                
                keyboard = InlineKeyboardMarkup(
                    Keyboards.position_actions(position['id'])
                )
                
                await update.message.reply_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def handle_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /buy command
        Format: /buy SYMBOL AMOUNT [PRICE]
        """
        try:
            user_id = update.effective_user.id
            
            if not bot_settings.is_authorized(user_id):
                await update.message.reply_text(Messages.NOT_AUTHORIZED)
                return
            
            # Parse command arguments
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "Usage: /buy SYMBOL AMOUNT [PRICE]\n"
                    "Example: /buy BTCUSDT 0.001\n"
                    "Example: /buy ETHUSDT 0.1 3500"
                )
                return
            
            symbol = args[0].upper()
            amount = float(args[1])
            price = float(args[2]) if len(args) > 2 else None
            
            # Validate amount
            if amount <= 0:
                await update.message.reply_text("❌ Amount must be positive")
                return
            
            # Check position size limit
            position_value = amount * (price or await self._get_current_price(symbol))
            if position_value > bot_settings.config.max_position_size:
                await update.message.reply_text(
                    f"❌ Position size exceeds limit of ${bot_settings.config.max_position_size:,.0f}"
                )
                return
            
            # Place order
            order = await self._place_order(
                symbol=symbol,
                side="Buy",
                amount=amount,
                price=price,
                user_id=user_id
            )
            
            if order['success']:
                message = Messages.ORDER_PLACED.format(
                    details=f"Symbol: {symbol}\n"
                           f"Side: Buy\n"
                           f"Amount: {amount}\n"
                           f"Price: ${price or 'Market'}\n"
                           f"Order ID: {order['order_id']}"
                )
                await update.message.reply_text(message, parse_mode='Markdown')
                
                # Set stop loss reminder
                if bot_settings.config.stop_loss_required:
                    await update.message.reply_text(
                        "💡 Don't forget to set a stop loss!\n"
                        f"Use: /stoploss {order['order_id']} PRICE"
                    )
            else:
                message = Messages.ORDER_FAILED.format(error=order['error'])
                await update.message.reply_text(message)
            
        except ValueError:
            await update.message.reply_text("❌ Invalid amount or price format")
        except Exception as e:
            logger.error(f"Error placing buy order: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def handle_sell(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /sell command
        Format: /sell SYMBOL AMOUNT [PRICE]
        """
        try:
            user_id = update.effective_user.id
            
            if not bot_settings.is_authorized(user_id):
                await update.message.reply_text(Messages.NOT_AUTHORIZED)
                return
            
            # Parse command arguments
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "Usage: /sell SYMBOL AMOUNT [PRICE]\n"
                    "Example: /sell BTCUSDT 0.001\n"
                    "Example: /sell ETHUSDT 0.1 3500"
                )
                return
            
            symbol = args[0].upper()
            amount = float(args[1])
            price = float(args[2]) if len(args) > 2 else None
            
            # Validate amount
            if amount <= 0:
                await update.message.reply_text("❌ Amount must be positive")
                return
            
            # Check position size limit
            position_value = amount * (price or await self._get_current_price(symbol))
            if position_value > bot_settings.config.max_position_size:
                await update.message.reply_text(
                    f"❌ Position size exceeds limit of ${bot_settings.config.max_position_size:,.0f}"
                )
                return
            
            # Place order
            order = await self._place_order(
                symbol=symbol,
                side="Sell",
                amount=amount,
                price=price,
                user_id=user_id
            )
            
            if order['success']:
                message = Messages.ORDER_PLACED.format(
                    details=f"Symbol: {symbol}\n"
                           f"Side: Sell\n"
                           f"Amount: {amount}\n"
                           f"Price: ${price or 'Market'}\n"
                           f"Order ID: {order['order_id']}"
                )
                await update.message.reply_text(message, parse_mode='Markdown')
                
                # Set stop loss reminder
                if bot_settings.config.stop_loss_required:
                    await update.message.reply_text(
                        "💡 Don't forget to set a stop loss!\n"
                        f"Use: /stoploss {order['order_id']} PRICE"
                    )
            else:
                message = Messages.ORDER_FAILED.format(error=order['error'])
                await update.message.reply_text(message)
            
        except ValueError:
            await update.message.reply_text("❌ Invalid amount or price format")
        except Exception as e:
            logger.error(f"Error placing sell order: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def handle_close(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /close command
        Format: /close POSITION_ID or /close SYMBOL
        """
        try:
            user_id = update.effective_user.id
            
            if not bot_settings.is_authorized(user_id):
                await update.message.reply_text(Messages.NOT_AUTHORIZED)
                return
            
            if not context.args:
                await update.message.reply_text(
                    "Usage: /close POSITION_ID or /close SYMBOL\n"
                    "Example: /close pos_123456\n"
                    "Example: /close BTCUSDT"
                )
                return
            
            identifier = context.args[0]
            
            # Close position
            result = await self.api_client.close_position(identifier)
            
            if result['success']:
                message = Messages.POSITION_CLOSED.format(
                    pnl=f"${result['pnl']:+,.2f}"
                )
                await update.message.reply_text(message, parse_mode='Markdown')
                
                # Show summary
                await update.message.reply_text(
                    f"📊 *Position Summary*\n"
                    f"Symbol: {result['symbol']}\n"
                    f"Entry: ${result['entry_price']:,.2f}\n"
                    f"Exit: ${result['exit_price']:,.2f}\n"
                    f"Size: {result['size']}\n"
                    f"Duration: {result['duration']}\n"
                    f"P&L: ${result['pnl']:+,.2f} ({result['pnl_pct']:+.2f}%)",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(f"❌ Failed to close position: {result['error']}")
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def handle_close_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /closeall command - closes all open positions"""
        try:
            user_id = update.effective_user.id
            
            if not bot_settings.is_authorized(user_id):
                await update.message.reply_text(Messages.NOT_AUTHORIZED)
                return
            
            # Confirmation keyboard
            keyboard = InlineKeyboardMarkup(
                Keyboards.confirmation("closeall", str(user_id))
            )
            
            await update.message.reply_text(
                "⚠️ *Warning*\n\n"
                "This will close ALL open positions immediately at market price.\n"
                "Are you sure?",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in close all: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def handle_stop_loss(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /stoploss command
        Format: /stoploss POSITION_ID/SYMBOL PRICE [TRAILING%]
        """
        try:
            user_id = update.effective_user.id
            
            if not bot_settings.is_authorized(user_id):
                await update.message.reply_text(Messages.NOT_AUTHORIZED)
                return
            
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "Usage: /stoploss POSITION_ID PRICE [TRAILING%]\n"
                    "Example: /stoploss BTCUSDT 45000\n"
                    "Example: /stoploss ETHUSDT 3200 5"
                )
                return
            
            identifier = args[0]
            stop_price = float(args[1])
            trailing_pct = float(args[2]) if len(args) > 2 else None
            
            # Set stop loss
            result = await self.api_client.set_stop_loss(
                identifier=identifier,
                stop_price=stop_price,
                trailing_pct=trailing_pct
            )
            
            if result['success']:
                message = f"✅ Stop loss set successfully!\n"
                if trailing_pct:
                    message += f"Trailing: {trailing_pct}%"
                await update.message.reply_text(message)
            else:
                await update.message.reply_text(f"❌ Failed to set stop loss: {result['error']}")
            
        except ValueError:
            await update.message.reply_text("❌ Invalid price format")
        except Exception as e:
            logger.error(f"Error setting stop loss: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def handle_take_profit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /takeprofit command
        Format: /takeprofit POSITION_ID/SYMBOL PRICE
        """
        try:
            user_id = update.effective_user.id
            
            if not bot_settings.is_authorized(user_id):
                await update.message.reply_text(Messages.NOT_AUTHORIZED)
                return
            
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "Usage: /takeprofit POSITION_ID PRICE\n"
                    "Example: /takeprofit BTCUSDT 55000"
                )
                return
            
            identifier = args[0]
            tp_price = float(args[1])
            
            # Set take profit
            result = await self.api_client.set_take_profit(
                identifier=identifier,
                tp_price=tp_price
            )
            
            if result['success']:
                await update.message.reply_text("✅ Take profit set successfully!")
            else:
                await update.message.reply_text(f"❌ Failed to set take profit: {result['error']}")
            
        except ValueError:
            await update.message.reply_text("❌ Invalid price format")
        except Exception as e:
            logger.error(f"Error setting take profit: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def _place_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: Optional[float],
        user_id: int
    ) -> Dict[str, Any]:
        """Place an order through the API"""
        try:
            # Check rate limit
            can_trade, wait_time = bot_settings.check_rate_limit(user_id, "trade")
            if not can_trade:
                return {
                    'success': False,
                    'error': f"Rate limited. Wait {wait_time} seconds."
                }
            
            # Prepare order data
            order_data = {
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'order_type': 'limit' if price else 'market',
                'price': price,
                'leverage': bot_settings.config.default_leverage
            }
            
            # Place order via API
            result = await self.api_client.place_order(order_data)
            
            if result['success']:
                # Store active order
                self.active_orders[result['order_id']] = {
                    'user_id': user_id,
                    'symbol': symbol,
                    'side': side,
                    'amount': amount,
                    'price': price,
                    'timestamp': datetime.now()
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        try:
            price_data = await self.api_client.get_price(symbol)
            return price_data['price']
        except:
            return 0.0
    
    async def handle_callback_close_position(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        position_id: str
    ):
        """Handle position close callback"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            if not bot_settings.is_authorized(user_id):
                await query.message.reply_text(Messages.NOT_AUTHORIZED)
                return
            
            # Close position
            result = await self.api_client.close_position(position_id)
            
            if result['success']:
                await query.edit_message_text(
                    f"✅ Position closed!\nP&L: ${result['pnl']:+,.2f}",
                    parse_mode='Markdown'
                )
            else:
                await query.message.reply_text(f"❌ Failed: {result['error']}")
            
        except Exception as e:
            logger.error(f"Error in callback: {e}")
            await query.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def handle_callback_confirm_closeall(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle close all confirmation callback"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            if not bot_settings.is_authorized(user_id):
                await query.message.reply_text(Messages.NOT_AUTHORIZED)
                return
            
            # Close all positions
            result = await self.api_client.close_all_positions()
            
            if result['success']:
                summary = f"""
✅ *All Positions Closed*

Positions Closed: {result['count']}
Total P&L: ${result['total_pnl']:+,.2f}

Details:
"""
                for pos in result['positions']:
                    summary += f"• {pos['symbol']}: ${pos['pnl']:+,.2f}\n"
                
                await query.edit_message_text(summary, parse_mode='Markdown')
            else:
                await query.message.reply_text(f"❌ Failed: {result['error']}")
            
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
            await query.message.reply_text(Messages.SYSTEM_ERROR)