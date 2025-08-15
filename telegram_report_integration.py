#!/usr/bin/env python3
"""
Telegram Bot Integration for Automated Reports
Sends daily/weekly trading reports to users
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional
import json
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    JobQueue
)
from telegram.constants import ParseMode

from report_generator import ReportGenerator
from performance_analytics import PerformanceAnalytics

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7707658830:AAH1zJH8uVFb_VNrp5t-vnp3IUoLNB9n6po')
ADMIN_CHAT_ID = 384403397  # Your chat ID

class TelegramReportBot:
    def __init__(self, token: str):
        self.token = token
        self.report_generator = ReportGenerator()
        self.analytics = PerformanceAnalytics()
        self.user_settings = self._load_user_settings()
        
    def _load_user_settings(self) -> Dict:
        """Load user report settings"""
        settings_file = Path('user_report_settings.json')
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                return json.load(f)
        return {}
        
    def _save_user_settings(self):
        """Save user report settings"""
        with open('user_report_settings.json', 'w') as f:
            json.dump(self.user_settings, f, indent=2)
            
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = str(update.effective_user.id)
        
        # Initialize user settings if not exists
        if user_id not in self.user_settings:
            self.user_settings[user_id] = {
                'daily_report': False,
                'weekly_report': False,
                'report_time': '09:00',
                'report_format': 'pdf',
                'notifications': True
            }
            self._save_user_settings()
            
        keyboard = [
            [InlineKeyboardButton("📈 Generate Report Now", callback_data='report_now')],
            [InlineKeyboardButton("⏰ Schedule Reports", callback_data='schedule')],
            [InlineKeyboardButton("📊 View Analytics", callback_data='analytics')],
            [InlineKeyboardButton("⚙️ Settings", callback_data='settings')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "*Trading Report Bot* 🤖\n\n"
            "I can generate and send trading performance reports.\n\n"
            "Choose an option:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /report command - generate immediate report"""
        await update.message.reply_text("📄 Generating report...")
        
        try:
            # Get trading data (mock for now)
            trades, positions, metrics = await self._get_trading_data()
            
            # Generate PDF report
            report_path = self.report_generator.generate_daily_report(
                trades=trades,
                positions=positions,
                metrics=metrics
            )
            
            # Send report file
            with open(report_path, 'rb') as report_file:
                await update.message.reply_document(
                    document=report_file,
                    filename=Path(report_path).name,
                    caption=self._format_report_summary(metrics)
                )
                
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            await update.message.reply_text(
                "❌ Error generating report. Please try again later."
            )
            
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        
        if query.data == 'report_now':
            await query.edit_message_text("📄 Generating report...")
            
            try:
                # Get trading data
                trades, positions, metrics = await self._get_trading_data()
                
                # Generate report
                report_path = self.report_generator.generate_daily_report(
                    trades=trades,
                    positions=positions,
                    metrics=metrics
                )
                
                # Send report
                with open(report_path, 'rb') as report_file:
                    await context.bot.send_document(
                        chat_id=query.message.chat_id,
                        document=report_file,
                        filename=Path(report_path).name,
                        caption=self._format_report_summary(metrics)
                    )
                    
                await query.edit_message_text(
                    "✅ Report generated and sent!",
                    reply_markup=self._get_back_button()
                )
                
            except Exception as e:
                logger.error(f"Error: {e}")
                await query.edit_message_text(
                    "❌ Error generating report.",
                    reply_markup=self._get_back_button()
                )
                
        elif query.data == 'schedule':
            settings = self.user_settings.get(user_id, {})
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        f"{'✅' if settings.get('daily_report') else '⬜'} Daily Report",
                        callback_data='toggle_daily'
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{'✅' if settings.get('weekly_report') else '⬜'} Weekly Report",
                        callback_data='toggle_weekly'
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"⏰ Report Time: {settings.get('report_time', '09:00')}",
                        callback_data='set_time'
                    )
                ],
                [InlineKeyboardButton("🔙 Back", callback_data='back')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "*Report Schedule Settings*\n\n"
                "Configure when you want to receive reports:",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        elif query.data == 'toggle_daily':
            settings = self.user_settings.get(user_id, {})
            settings['daily_report'] = not settings.get('daily_report', False)
            self.user_settings[user_id] = settings
            self._save_user_settings()
            
            # Schedule or remove daily job
            if settings['daily_report']:
                await self._schedule_daily_report(context, user_id)
                await query.answer("✅ Daily reports enabled")
            else:
                await self._remove_daily_report(context, user_id)
                await query.answer("❌ Daily reports disabled")
                
            # Refresh menu
            await self.button_callback(update, context)
            
        elif query.data == 'toggle_weekly':
            settings = self.user_settings.get(user_id, {})
            settings['weekly_report'] = not settings.get('weekly_report', False)
            self.user_settings[user_id] = settings
            self._save_user_settings()
            
            if settings['weekly_report']:
                await query.answer("✅ Weekly reports enabled")
            else:
                await query.answer("❌ Weekly reports disabled")
                
            # Refresh menu
            await self.button_callback(update, context)
            
        elif query.data == 'analytics':
            # Show quick analytics
            trades, positions, metrics = await self._get_trading_data()
            
            analytics_text = f"""
*📊 Trading Analytics*

💰 Total P&L: ${metrics.get('total_pnl', 0):,.2f}
📈 Win Rate: {metrics.get('win_rate', 0):.1f}%
📊 Total Trades: {metrics.get('total_trades', 0)}
🏆 Profit Factor: {metrics.get('profit_factor', 0):.2f}
🔥 Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}
📉 Max Drawdown: {metrics.get('max_drawdown', 0):.1f}%

_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_
            """
            
            await query.edit_message_text(
                analytics_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self._get_back_button()
            )
            
        elif query.data == 'settings':
            settings = self.user_settings.get(user_id, {})
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        f"Format: {settings.get('report_format', 'pdf').upper()}",
                        callback_data='toggle_format'
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{'🔔' if settings.get('notifications') else '🔕'} Notifications",
                        callback_data='toggle_notifications'
                    )
                ],
                [InlineKeyboardButton("🔙 Back", callback_data='back')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "*Report Settings*\n\n"
                "Configure your report preferences:",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        elif query.data == 'toggle_format':
            settings = self.user_settings.get(user_id, {})
            current_format = settings.get('report_format', 'pdf')
            settings['report_format'] = 'html' if current_format == 'pdf' else 'pdf'
            self.user_settings[user_id] = settings
            self._save_user_settings()
            
            await query.answer(f"Format changed to {settings['report_format'].upper()}")
            # Refresh menu
            await self.button_callback(update, context)
            
        elif query.data == 'back':
            # Go back to main menu
            keyboard = [
                [InlineKeyboardButton("📈 Generate Report Now", callback_data='report_now')],
                [InlineKeyboardButton("⏰ Schedule Reports", callback_data='schedule')],
                [InlineKeyboardButton("📊 View Analytics", callback_data='analytics')],
                [InlineKeyboardButton("⚙️ Settings", callback_data='settings')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "*Trading Report Bot* 🤖\n\n"
                "Choose an option:",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
    def _get_back_button(self) -> InlineKeyboardMarkup:
        """Get back button markup"""
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back to Menu", callback_data='back')
        ]])
        
    async def _get_trading_data(self):
        """Get trading data from the bot"""
        # For now, return mock data
        # In production, this would fetch from database or trading bot
        
        trades = [
            {
                'symbol': 'BTCUSDT',
                'pnl': 250.50,
                'pnl_percent': 2.5,
                'entry_time': datetime.now() - timedelta(hours=8),
                'exit_time': datetime.now() - timedelta(hours=6),
                'strategy': 'RSI',
            },
            {
                'symbol': 'ETHUSDT',
                'pnl': -125.25,
                'pnl_percent': -1.25,
                'entry_time': datetime.now() - timedelta(hours=5),
                'exit_time': datetime.now() - timedelta(hours=3),
                'strategy': 'EMA',
            },
            {
                'symbol': 'BTCUSDT',
                'pnl': 175.00,
                'pnl_percent': 1.75,
                'entry_time': datetime.now() - timedelta(hours=2),
                'exit_time': datetime.now() - timedelta(minutes=30),
                'strategy': 'MACD',
            },
        ]
        
        positions = [
            {
                'symbol': 'BTCUSDT',
                'size': 0.02,
                'unrealized_pnl': 85.00,
                'margin': 1000.00,
                'leverage': 10,
            },
        ]
        
        # Calculate metrics
        total_pnl = sum(t['pnl'] for t in trades)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]
        
        metrics = {
            'total_pnl': total_pnl,
            'daily_pnl': total_pnl,
            'win_rate': len(winning_trades) / len(trades) * 100 if trades else 0,
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'avg_win': sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0,
            'avg_loss': sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0,
            'profit_factor': abs(sum(t['pnl'] for t in winning_trades) / sum(t['pnl'] for t in losing_trades)) if losing_trades else 0,
            'sharpe_ratio': 1.75,
            'sortino_ratio': 2.10,
            'calmar_ratio': 1.5,
            'max_drawdown': 3.5,
            'risk_reward_ratio': 2.0,
            'kelly_criterion': 0.18,
            'active_positions': len(positions),
            'total_volume': 75000,
        }
        
        return trades, positions, metrics
        
    def _format_report_summary(self, metrics: Dict) -> str:
        """Format report summary for Telegram"""
        pnl_emoji = '📈' if metrics.get('total_pnl', 0) >= 0 else '📉'
        
        return f"""
{pnl_emoji} *Daily Trading Report*

💰 P&L: ${metrics.get('daily_pnl', 0):,.2f}
🏆 Win Rate: {metrics.get('win_rate', 0):.1f}%
📊 Trades: {metrics.get('total_trades', 0)}
🔥 Sharpe: {metrics.get('sharpe_ratio', 0):.2f}

_Generated at {datetime.now().strftime('%Y-%m-%d %H:%M')}_
        """
        
    async def _schedule_daily_report(self, context: ContextTypes.DEFAULT_TYPE, user_id: str):
        """Schedule daily report for user"""
        settings = self.user_settings.get(user_id, {})
        report_time = settings.get('report_time', '09:00')
        
        # Parse time
        hour, minute = map(int, report_time.split(':'))
        
        # Schedule job
        job_name = f"daily_report_{user_id}"
        
        # Remove existing job if any
        current_jobs = context.job_queue.get_jobs_by_name(job_name)
        for job in current_jobs:
            job.schedule_removal()
            
        # Add new job
        context.job_queue.run_daily(
            self._send_scheduled_report,
            time=time(hour, minute),
            data={'user_id': user_id},
            name=job_name
        )
        
    async def _remove_daily_report(self, context: ContextTypes.DEFAULT_TYPE, user_id: str):
        """Remove scheduled daily report"""
        job_name = f"daily_report_{user_id}"
        current_jobs = context.job_queue.get_jobs_by_name(job_name)
        for job in current_jobs:
            job.schedule_removal()
            
    async def _send_scheduled_report(self, context: ContextTypes.DEFAULT_TYPE):
        """Send scheduled report to user"""
        user_id = context.job.data['user_id']
        
        try:
            # Get trading data
            trades, positions, metrics = await self._get_trading_data()
            
            # Generate report
            report_path = self.report_generator.generate_daily_report(
                trades=trades,
                positions=positions,
                metrics=metrics
            )
            
            # Send report
            with open(report_path, 'rb') as report_file:
                await context.bot.send_document(
                    chat_id=int(user_id),
                    document=report_file,
                    filename=Path(report_path).name,
                    caption=self._format_report_summary(metrics),
                    parse_mode=ParseMode.MARKDOWN
                )
                
            logger.info(f"Scheduled report sent to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending scheduled report: {e}")
            

def main():
    """Run the bot"""
    # Create bot instance
    bot = TelegramReportBot(TOKEN)
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("report", bot.report_command))
    application.add_handler(CallbackQueryHandler(bot.button_callback))
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    

if __name__ == '__main__':
    main()