#!/usr/bin/env python3
"""
Automatic Report Scheduler
Sends trading reports via email and Telegram on schedule
"""

import os
import logging
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional
import schedule
import json
from dataclasses import dataclass
from enum import Enum

from excel_exporter import get_excel_exporter
from database.service import get_db_service
from performance_analytics import PerformanceAnalytics
from telegram_bot import TelegramBot

logger = logging.getLogger(__name__)

class ReportFrequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"

@dataclass
class ReportConfig:
    """Report configuration"""
    frequency: ReportFrequency
    send_email: bool = True
    send_telegram: bool = True
    send_excel: bool = True
    recipients: List[str] = None
    telegram_chat_ids: List[int] = None
    time_of_day: str = "08:00"  # HH:MM format
    day_of_week: int = 1  # Monday for weekly
    day_of_month: int = 1  # 1st for monthly
    include_charts: bool = True
    include_positions: bool = True
    include_metrics: bool = True

class ReportScheduler:
    """Automatic report scheduler"""
    
    def __init__(
        self,
        config: Optional[ReportConfig] = None,
        smtp_config: Optional[Dict] = None
    ):
        self.config = config or self._load_config()
        self.smtp_config = smtp_config or self._load_smtp_config()
        self.db = get_db_service()
        self.analytics = PerformanceAnalytics()
        self.exporter = get_excel_exporter()
        self.telegram_bot = None
        self._setup_telegram()
        
        # Schedule jobs
        self._schedule_reports()
        
    def _load_config(self) -> ReportConfig:
        """Load report configuration from environment or file"""
        config_file = "report_config.json"
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                data = json.load(f)
                return ReportConfig(
                    frequency=ReportFrequency(data.get('frequency', 'daily')),
                    send_email=data.get('send_email', True),
                    send_telegram=data.get('send_telegram', True),
                    send_excel=data.get('send_excel', True),
                    recipients=data.get('recipients', []),
                    telegram_chat_ids=data.get('telegram_chat_ids', []),
                    time_of_day=data.get('time_of_day', '08:00'),
                    day_of_week=data.get('day_of_week', 1),
                    day_of_month=data.get('day_of_month', 1),
                    include_charts=data.get('include_charts', True),
                    include_positions=data.get('include_positions', True),
                    include_metrics=data.get('include_metrics', True)
                )
        
        # Default configuration
        return ReportConfig(
            frequency=ReportFrequency.DAILY,
            send_email=bool(os.getenv('REPORT_EMAIL_ENABLED', 'true').lower() == 'true'),
            send_telegram=bool(os.getenv('REPORT_TELEGRAM_ENABLED', 'true').lower() == 'true'),
            recipients=os.getenv('REPORT_EMAIL_RECIPIENTS', '').split(','),
            telegram_chat_ids=[int(x) for x in os.getenv('REPORT_TELEGRAM_CHATS', '').split(',') if x],
            time_of_day=os.getenv('REPORT_TIME', '08:00')
        )
    
    def _load_smtp_config(self) -> Dict:
        """Load SMTP configuration"""
        return {
            'host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
            'port': int(os.getenv('SMTP_PORT', '587')),
            'username': os.getenv('SMTP_USERNAME'),
            'password': os.getenv('SMTP_PASSWORD'),
            'from_email': os.getenv('SMTP_FROM_EMAIL', 'bybit-bot@example.com'),
            'use_tls': bool(os.getenv('SMTP_USE_TLS', 'true').lower() == 'true')
        }
    
    def _setup_telegram(self):
        """Setup Telegram bot for report sending"""
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if token and self.config.send_telegram:
            try:
                from telegram import Bot
                self.telegram_bot = Bot(token=token)
                logger.info("Telegram bot configured for report sending")
            except Exception as e:
                logger.warning(f"Failed to setup Telegram bot: {e}")
    
    def _schedule_reports(self):
        """Schedule report generation based on configuration"""
        if self.config.frequency == ReportFrequency.DAILY:
            schedule.every().day.at(self.config.time_of_day).do(self.generate_daily_report)
            logger.info(f"Scheduled daily report at {self.config.time_of_day}")
            
        elif self.config.frequency == ReportFrequency.WEEKLY:
            # Schedule for specific day of week
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            day_name = days[self.config.day_of_week]
            getattr(schedule.every(), day_name).at(self.config.time_of_day).do(self.generate_weekly_report)
            logger.info(f"Scheduled weekly report on {day_name} at {self.config.time_of_day}")
            
        elif self.config.frequency == ReportFrequency.MONTHLY:
            # Check daily and run on specific day of month
            schedule.every().day.at(self.config.time_of_day).do(self._check_monthly_report)
            logger.info(f"Scheduled monthly report on day {self.config.day_of_month} at {self.config.time_of_day}")
    
    def _check_monthly_report(self):
        """Check if today is the day for monthly report"""
        if datetime.now().day == self.config.day_of_month:
            self.generate_monthly_report()
    
    async def generate_daily_report(self):
        """Generate and send daily report"""
        logger.info("Generating daily report...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        
        report = await self._generate_report(
            start_date=start_date,
            end_date=end_date,
            report_type="Daily"
        )
        
        await self._send_report(report, "Daily Trading Report")
    
    async def generate_weekly_report(self):
        """Generate and send weekly report"""
        logger.info("Generating weekly report...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        report = await self._generate_report(
            start_date=start_date,
            end_date=end_date,
            report_type="Weekly"
        )
        
        await self._send_report(report, "Weekly Trading Report")
    
    async def generate_monthly_report(self):
        """Generate and send monthly report"""
        logger.info("Generating monthly report...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        report = await self._generate_report(
            start_date=start_date,
            end_date=end_date,
            report_type="Monthly"
        )
        
        await self._send_report(report, "Monthly Trading Report")
    
    async def _generate_report(
        self,
        start_date: datetime,
        end_date: datetime,
        report_type: str
    ) -> Dict[str, Any]:
        """Generate comprehensive report"""
        
        # Get data
        user_id = 1  # Default user, can be made configurable
        trades = self.db.get_user_trades(user_id, start_date, end_date)
        positions = self.db.get_user_positions(user_id) if self.config.include_positions else []
        
        # Calculate metrics
        metrics = self.analytics.calculate_metrics(trades) if self.config.include_metrics else {}
        
        # Generate Excel report if needed
        excel_file = None
        if self.config.send_excel:
            excel_file = self.exporter.export_trading_report(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                output_path="reports/"
            )
        
        # Prepare report data
        report = {
            'type': report_type,
            'period': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'summary': {
                'total_trades': len(trades),
                'win_rate': metrics.get('win_rate', 0),
                'total_pnl': metrics.get('total_pnl', 0),
                'avg_trade': metrics.get('avg_trade', 0),
                'best_trade': metrics.get('best_trade', 0),
                'worst_trade': metrics.get('worst_trade', 0),
                'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                'max_drawdown': metrics.get('max_drawdown', 0)
            },
            'positions': positions,
            'top_pairs': self._get_top_pairs(trades),
            'excel_file': excel_file,
            'generated_at': datetime.now().isoformat()
        }
        
        return report
    
    def _get_top_pairs(self, trades: List[Dict]) -> List[Dict]:
        """Get top performing trading pairs"""
        pair_pnl = {}
        
        for trade in trades:
            symbol = trade.get('symbol', 'Unknown')
            pnl = trade.get('pnl', 0)
            
            if symbol not in pair_pnl:
                pair_pnl[symbol] = {'total_pnl': 0, 'trades': 0}
            
            pair_pnl[symbol]['total_pnl'] += pnl
            pair_pnl[symbol]['trades'] += 1
        
        # Sort by total P&L
        sorted_pairs = sorted(
            pair_pnl.items(),
            key=lambda x: x[1]['total_pnl'],
            reverse=True
        )
        
        return [
            {
                'symbol': symbol,
                'total_pnl': data['total_pnl'],
                'trades': data['trades'],
                'avg_pnl': data['total_pnl'] / data['trades'] if data['trades'] > 0 else 0
            }
            for symbol, data in sorted_pairs[:5]
        ]
    
    async def _send_report(self, report: Dict, subject: str):
        """Send report via configured channels"""
        
        # Send via email
        if self.config.send_email and self.config.recipients:
            await self._send_email_report(report, subject)
        
        # Send via Telegram
        if self.config.send_telegram and self.telegram_bot and self.config.telegram_chat_ids:
            await self._send_telegram_report(report)
        
        logger.info(f"Report sent successfully: {subject}")
    
    async def _send_email_report(self, report: Dict, subject: str):
        """Send report via email"""
        try:
            # Create HTML content
            html_content = self._generate_html_report(report)
            
            # Create message
            msg = MIMEMultipart('mixed')
            msg['Subject'] = f"[Bybit Bot] {subject}"
            msg['From'] = self.smtp_config['from_email']
            msg['To'] = ', '.join(self.config.recipients)
            
            # Add HTML body
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Attach Excel file if available
            if report.get('excel_file') and os.path.exists(report['excel_file']):
                with open(report['excel_file'], 'rb') as f:
                    excel_part = MIMEApplication(f.read())
                    excel_part.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=os.path.basename(report['excel_file'])
                    )
                    msg.attach(excel_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port']) as server:
                if self.smtp_config['use_tls']:
                    server.starttls()
                
                if self.smtp_config['username'] and self.smtp_config['password']:
                    server.login(self.smtp_config['username'], self.smtp_config['password'])
                
                server.send_message(msg)
                
            logger.info(f"Email report sent to {', '.join(self.config.recipients)}")
            
        except Exception as e:
            logger.error(f"Failed to send email report: {e}")
    
    async def _send_telegram_report(self, report: Dict):
        """Send report via Telegram"""
        try:
            # Format message
            message = self._format_telegram_report(report)
            
            # Send to all configured chat IDs
            for chat_id in self.config.telegram_chat_ids:
                await self.telegram_bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
                
                # Send Excel file if available
                if report.get('excel_file') and os.path.exists(report['excel_file']):
                    with open(report['excel_file'], 'rb') as f:
                        await self.telegram_bot.send_document(
                            chat_id=chat_id,
                            document=f,
                            caption="📊 Detailed Trading Report"
                        )
            
            logger.info(f"Telegram report sent to {len(self.config.telegram_chat_ids)} chats")
            
        except Exception as e:
            logger.error(f"Failed to send Telegram report: {e}")
    
    def _generate_html_report(self, report: Dict) -> str:
        """Generate HTML report content"""
        summary = report['summary']
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h1 {{ color: #2c3e50; }}
                h2 {{ color: #34495e; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #3498db; color: white; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
            </style>
        </head>
        <body>
            <h1>📊 {report['type']} Trading Report</h1>
            <p>Period: {report['period']['start']} to {report['period']['end']}</p>
            
            <h2>Summary</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Total Trades</td><td>{summary['total_trades']}</td></tr>
                <tr><td>Win Rate</td><td>{summary['win_rate']:.2f}%</td></tr>
                <tr><td>Total P&L</td><td class="{'positive' if summary['total_pnl'] >= 0 else 'negative'}">${summary['total_pnl']:,.2f}</td></tr>
                <tr><td>Average Trade</td><td>${summary['avg_trade']:.2f}</td></tr>
                <tr><td>Best Trade</td><td class="positive">${summary['best_trade']:.2f}</td></tr>
                <tr><td>Worst Trade</td><td class="negative">${summary['worst_trade']:.2f}</td></tr>
                <tr><td>Sharpe Ratio</td><td>{summary['sharpe_ratio']:.2f}</td></tr>
                <tr><td>Max Drawdown</td><td>{summary['max_drawdown']:.2f}%</td></tr>
            </table>
            
            <h2>Top Performing Pairs</h2>
            <table>
                <tr><th>Symbol</th><th>Trades</th><th>Total P&L</th><th>Avg P&L</th></tr>
        """
        
        for pair in report['top_pairs']:
            html += f"""
                <tr>
                    <td>{pair['symbol']}</td>
                    <td>{pair['trades']}</td>
                    <td class="{'positive' if pair['total_pnl'] >= 0 else 'negative'}">${pair['total_pnl']:,.2f}</td>
                    <td>${pair['avg_pnl']:.2f}</td>
                </tr>
            """
        
        html += """
            </table>
            
            <p><i>Generated at {report['generated_at']}</i></p>
        </body>
        </html>
        """
        
        return html
    
    def _format_telegram_report(self, report: Dict) -> str:
        """Format report for Telegram"""
        summary = report['summary']
        
        message = f"""
📊 *{report['type']} Trading Report*
━━━━━━━━━━━━━━━━━━━━
📅 Period: {report['period']['start']} to {report['period']['end']}

*Summary*
• Total Trades: {summary['total_trades']}
• Win Rate: {summary['win_rate']:.2f}%
• Total P&L: ${summary['total_pnl']:+,.2f}
• Average Trade: ${summary['avg_trade']:.2f}
• Best Trade: ${summary['best_trade']:+.2f}
• Worst Trade: ${summary['worst_trade']:+.2f}
• Sharpe Ratio: {summary['sharpe_ratio']:.2f}
• Max Drawdown: {summary['max_drawdown']:.2f}%

*Top Performing Pairs*
"""
        
        for i, pair in enumerate(report['top_pairs'], 1):
            emoji = "🟢" if pair['total_pnl'] >= 0 else "🔴"
            message += f"{i}. {emoji} {pair['symbol']}: ${pair['total_pnl']:+,.2f} ({pair['trades']} trades)\n"
        
        return message
    
    def run(self):
        """Run the scheduler"""
        logger.info("Starting report scheduler...")
        
        while True:
            try:
                schedule.run_pending()
                asyncio.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Report scheduler stopped")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                asyncio.sleep(60)

# Singleton instance
_scheduler = None

def get_report_scheduler() -> ReportScheduler:
    """Get singleton report scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = ReportScheduler()
    return _scheduler

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scheduler = get_report_scheduler()
    scheduler.run()