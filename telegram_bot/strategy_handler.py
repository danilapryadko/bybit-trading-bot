"""
Telegram Bot Strategy Handler
Manages trading strategies through Telegram interface
"""

import logging
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from .bot_config import bot_settings, Messages

logger = logging.getLogger(__name__)

class StrategyHandler:
    """Strategy command handlers"""
    
    def __init__(self, api_client):
        """Initialize strategy handler"""
        self.api_client = api_client
        self.active_strategies = {}
    
    async def handle_grid(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /grid command - Grid trading strategy"""
        user_id = update.effective_user.id
        
        if not bot_settings.is_authorized(user_id):
            await update.message.reply_text(Messages.NOT_AUTHORIZED)
            return
        
        if not context.args:
            # Show grid setup menu
            message = """
📊 *Grid Trading Setup*

Usage: /grid SYMBOL LOWER UPPER GRIDS [AMOUNT]

Example:
`/grid BTCUSDT 45000 55000 10 1000`

This creates a grid:
• Symbol: BTCUSDT
• Range: $45,000 - $55,000
• Grid levels: 10
• Investment: $1,000

Features:
✅ Auto-rebalancing
✅ Compound profits
✅ Risk management
✅ 24/7 operation
            """
            await update.message.reply_text(message, parse_mode='Markdown')
            return
        
        try:
            # Parse grid parameters
            symbol = context.args[0].upper()
            lower_price = float(context.args[1])
            upper_price = float(context.args[2])
            grid_count = int(context.args[3])
            investment = float(context.args[4]) if len(context.args) > 4 else 1000
            
            # Validate parameters
            if lower_price >= upper_price:
                await update.message.reply_text("❌ Lower price must be less than upper price")
                return
            
            if grid_count < 2 or grid_count > 100:
                await update.message.reply_text("❌ Grid count must be between 2 and 100")
                return
            
            # Start grid strategy
            result = await self.api_client.start_grid_strategy({
                'symbol': symbol,
                'lower_price': lower_price,
                'upper_price': upper_price,
                'grid_count': grid_count,
                'investment': investment,
                'user_id': user_id
            })
            
            if result['success']:
                strategy_id = result['strategy_id']
                self.active_strategies[strategy_id] = {
                    'type': 'grid',
                    'user_id': user_id,
                    'symbol': symbol
                }
                
                message = f"""
✅ *Grid Strategy Started*

Strategy ID: `{strategy_id}`
Symbol: {symbol}
Range: ${lower_price:,.0f} - ${upper_price:,.0f}
Grids: {grid_count}
Investment: ${investment:,.0f}

Expected daily return: {result['expected_return']:.1f}%
Risk level: {result['risk_level']}

Use /stop {strategy_id} to stop
                """
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ Failed to start grid: {result['error']}")
            
        except (IndexError, ValueError):
            await update.message.reply_text("❌ Invalid parameters. Use /grid for help.")
        except Exception as e:
            logger.error(f"Grid strategy error: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def handle_funding(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /funding command - Funding rate arbitrage"""
        user_id = update.effective_user.id
        
        if not bot_settings.is_authorized(user_id):
            await update.message.reply_text(Messages.NOT_AUTHORIZED)
            return
        
        try:
            # Get funding opportunities
            opportunities = await self.api_client.get_funding_opportunities()
            
            if not opportunities:
                await update.message.reply_text("📊 No funding opportunities currently available")
                return
            
            message = "💰 *Funding Rate Opportunities*\n\n"
            
            for opp in opportunities[:5]:  # Top 5
                apr = opp['funding_rate'] * 3 * 365 * 100  # Annual percentage
                
                message += f"*{opp['symbol']}*\n"
                message += f"Rate: {opp['funding_rate']:.4f}%\n"
                message += f"APR: {apr:.1f}%\n"
                message += f"Direction: {opp['direction']}\n\n"
            
            # Add action buttons
            keyboard = [
                [InlineKeyboardButton("Start Auto-Funding", callback_data="start_funding")],
                [InlineKeyboardButton("View Details", callback_data="funding_details")]
            ]
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Funding strategy error: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def handle_arbitrage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /arbitrage command - Arbitrage opportunities"""
        user_id = update.effective_user.id
        
        if not bot_settings.is_authorized(user_id):
            await update.message.reply_text(Messages.NOT_AUTHORIZED)
            return
        
        try:
            # Get arbitrage opportunities
            opportunities = await self.api_client.get_arbitrage_opportunities()
            
            if not opportunities:
                await update.message.reply_text("🔄 No arbitrage opportunities currently")
                return
            
            message = "🎯 *Arbitrage Opportunities*\n\n"
            
            for opp in opportunities[:3]:  # Top 3
                message += f"*{opp['type']}*\n"
                message += f"Symbol: {opp['symbol']}\n"
                message += f"Spread: {opp['spread_pct']:.2f}%\n"
                message += f"Est. Profit: ${opp['estimated_profit']:.2f}\n"
                message += f"Confidence: {opp['confidence']}%\n\n"
            
            # Add execution button
            if opportunities[0]['confidence'] > 70:
                keyboard = [[
                    InlineKeyboardButton(
                        "Execute Best Opportunity",
                        callback_data=f"execute_arb_{opportunities[0]['id']}"
                    )
                ]]
                
                await update.message.reply_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Arbitrage error: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def handle_dca(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dca command - Dollar Cost Averaging"""
        user_id = update.effective_user.id
        
        if not bot_settings.is_authorized(user_id):
            await update.message.reply_text(Messages.NOT_AUTHORIZED)
            return
        
        if not context.args:
            message = """
💵 *DCA Bot Setup*

Dollar Cost Averaging Strategy

Usage: /dca SYMBOL AMOUNT INTERVAL [DURATION]

Examples:
`/dca BTCUSDT 100 daily 30`
• Buy $100 of BTC daily for 30 days

`/dca ETHUSDT 500 weekly`
• Buy $500 of ETH weekly (ongoing)

Intervals: hourly, daily, weekly, monthly

Benefits:
✅ Reduces timing risk
✅ Automatic execution
✅ Average down volatility
✅ Set and forget
            """
            await update.message.reply_text(message, parse_mode='Markdown')
            return
        
        try:
            # Parse DCA parameters
            symbol = context.args[0].upper()
            amount = float(context.args[1])
            interval = context.args[2].lower()
            duration = int(context.args[3]) if len(context.args) > 3 else None
            
            # Validate interval
            valid_intervals = ['hourly', 'daily', 'weekly', 'monthly']
            if interval not in valid_intervals:
                await update.message.reply_text(
                    f"❌ Invalid interval. Choose from: {', '.join(valid_intervals)}"
                )
                return
            
            # Start DCA strategy
            result = await self.api_client.start_dca_strategy({
                'symbol': symbol,
                'amount': amount,
                'interval': interval,
                'duration': duration,
                'user_id': user_id
            })
            
            if result['success']:
                strategy_id = result['strategy_id']
                self.active_strategies[strategy_id] = {
                    'type': 'dca',
                    'user_id': user_id,
                    'symbol': symbol
                }
                
                duration_text = f"{duration} periods" if duration else "Ongoing"
                
                message = f"""
✅ *DCA Strategy Started*

Strategy ID: `{strategy_id}`
Symbol: {symbol}
Amount: ${amount:,.0f} per {interval}
Duration: {duration_text}

Next purchase: {result['next_execution']}
Total investment: ${result['total_investment']:,.0f}

Use /stop {strategy_id} to stop
                """
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ Failed to start DCA: {result['error']}")
            
        except (IndexError, ValueError):
            await update.message.reply_text("❌ Invalid parameters. Use /dca for help.")
        except Exception as e:
            logger.error(f"DCA strategy error: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)
    
    async def stop_strategy(self, strategy_id: str, user_id: int) -> bool:
        """Stop a running strategy"""
        try:
            if strategy_id not in self.active_strategies:
                return False
            
            strategy = self.active_strategies[strategy_id]
            
            # Check ownership
            if strategy['user_id'] != user_id and not bot_settings.is_admin(user_id):
                return False
            
            # Stop strategy via API
            result = await self.api_client.stop_strategy(strategy_id)
            
            if result['success']:
                del self.active_strategies[strategy_id]
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error stopping strategy: {e}")
            return False
    
    async def get_strategy_status(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get strategy status"""
        try:
            return await self.api_client.get_strategy_status(strategy_id)
        except Exception as e:
            logger.error(f"Error getting strategy status: {e}")
            return None
    
    async def handle_ml_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle ML prediction signals"""
        user_id = update.effective_user.id
        
        if not bot_settings.is_authorized(user_id):
            await update.message.reply_text(Messages.NOT_AUTHORIZED)
            return
        
        try:
            # Get ML signals
            signals = await self.api_client.get_ml_signals()
            
            if not signals:
                await update.message.reply_text("🤖 No ML signals available")
                return
            
            message = "🤖 *Machine Learning Signals*\n\n"
            
            for signal in signals[:5]:
                # Determine emoji based on signal
                if signal['action'] == 'BUY':
                    emoji = "🟢"
                elif signal['action'] == 'SELL':
                    emoji = "🔴"
                else:
                    emoji = "🟡"
                
                message += f"{emoji} *{signal['symbol']}*\n"
                message += f"Action: {signal['action']}\n"
                message += f"Confidence: {signal['confidence']:.1f}%\n"
                message += f"Target: ${signal['target_price']:,.2f}\n"
                message += f"Stop: ${signal['stop_price']:,.2f}\n\n"
            
            # Add auto-trade button for high confidence signals
            high_conf_signals = [s for s in signals if s['confidence'] > 75]
            if high_conf_signals:
                keyboard = [[
                    InlineKeyboardButton(
                        "Auto-Trade High Confidence",
                        callback_data="ml_autotrade"
                    )
                ]]
                
                await update.message.reply_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"ML signals error: {e}")
            await update.message.reply_text(Messages.SYSTEM_ERROR)