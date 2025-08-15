#!/usr/bin/env python3
"""
Automated Report Generator with Charts
Generates trading performance reports with visualizations
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import seaborn as sns
from io import BytesIO
import base64
from pathlib import Path

# Configure matplotlib for better quality
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Report configuration
        self.figure_size = (12, 8)
        self.dpi = 100
        
    def generate_daily_report(self, 
                            trades: List[Dict],
                            positions: List[Dict],
                            metrics: Dict,
                            date: Optional[datetime] = None) -> str:
        """
        Generate daily trading report
        
        Returns: Path to generated report
        """
        if date is None:
            date = datetime.now()
            
        report_date = date.strftime('%Y-%m-%d')
        report_name = f"daily_report_{report_date}.pdf"
        report_path = self.output_dir / report_name
        
        # Create PDF
        with PdfPages(report_path) as pdf:
            # Page 1: Summary
            self._create_summary_page(pdf, metrics, date)
            
            # Page 2: P&L Chart
            self._create_pnl_chart(pdf, trades, date)
            
            # Page 3: Trade Distribution
            self._create_trade_distribution(pdf, trades)
            
            # Page 4: Position Analysis
            self._create_position_analysis(pdf, positions)
            
            # Page 5: Strategy Performance
            self._create_strategy_performance(pdf, trades)
            
            # Page 6: Risk Metrics
            self._create_risk_metrics(pdf, metrics)
            
            # Add metadata
            d = pdf.infodict()
            d['Title'] = f'Trading Report - {report_date}'
            d['Author'] = 'Bybit Trading Bot'
            d['Subject'] = 'Daily Trading Performance Report'
            d['Keywords'] = 'Trading, Cryptocurrency, Performance, Bybit'
            d['CreationDate'] = datetime.now()
            
        logger.info(f"Report generated: {report_path}")
        return str(report_path)
        
    def _create_summary_page(self, pdf: PdfPages, metrics: Dict, date: datetime):
        """Create summary page with key metrics"""
        fig = plt.figure(figsize=self.figure_size)
        fig.suptitle(f"Trading Report - {date.strftime('%Y-%m-%d')}", fontsize=20, fontweight='bold')
        
        # Remove axes
        ax = fig.add_subplot(111)
        ax.axis('off')
        
        # Prepare metrics text
        summary_text = f"""
        PERFORMANCE SUMMARY
        {'='*50}
        
        Total P&L:           ${metrics.get('total_pnl', 0):,.2f}
        Today's P&L:         ${metrics.get('daily_pnl', 0):,.2f}
        Win Rate:            {metrics.get('win_rate', 0):.1f}%
        Total Trades:        {metrics.get('total_trades', 0)}
        Winning Trades:      {metrics.get('winning_trades', 0)}
        Losing Trades:       {metrics.get('losing_trades', 0)}
        
        Average Win:         ${metrics.get('avg_win', 0):,.2f}
        Average Loss:        ${metrics.get('avg_loss', 0):,.2f}
        Profit Factor:       {metrics.get('profit_factor', 0):.2f}
        
        Sharpe Ratio:        {metrics.get('sharpe_ratio', 0):.2f}
        Sortino Ratio:       {metrics.get('sortino_ratio', 0):.2f}
        Max Drawdown:        {metrics.get('max_drawdown', 0):.1f}%
        
        Active Positions:    {metrics.get('active_positions', 0)}
        Total Volume:        ${metrics.get('total_volume', 0):,.0f}
        """
        
        # Add text to figure
        ax.text(0.1, 0.9, summary_text, transform=ax.transAxes,
                fontsize=14, verticalalignment='top', fontfamily='monospace')
        
        # Add status indicators
        status_color = 'green' if metrics.get('daily_pnl', 0) >= 0 else 'red'
        ax.text(0.7, 0.8, '📈' if metrics.get('daily_pnl', 0) >= 0 else '📉',
                transform=ax.transAxes, fontsize=80, color=status_color)
        
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
        
    def _create_pnl_chart(self, pdf: PdfPages, trades: List[Dict], date: datetime):
        """Create P&L chart over time"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.figure_size, height_ratios=[2, 1])
        
        if trades:
            # Convert trades to DataFrame
            df = pd.DataFrame(trades)
            if 'exit_time' in df.columns:
                df['exit_time'] = pd.to_datetime(df['exit_time'])
                df = df.sort_values('exit_time')
                
                # Calculate cumulative P&L
                df['cumulative_pnl'] = df['pnl'].cumsum()
                
                # Plot cumulative P&L
                ax1.plot(df['exit_time'], df['cumulative_pnl'], 
                        linewidth=2, color='blue', label='Cumulative P&L')
                ax1.fill_between(df['exit_time'], 0, df['cumulative_pnl'],
                                where=(df['cumulative_pnl'] >= 0), color='green', alpha=0.3)
                ax1.fill_between(df['exit_time'], 0, df['cumulative_pnl'],
                                where=(df['cumulative_pnl'] < 0), color='red', alpha=0.3)
                
                # Plot individual trade P&L
                colors = ['green' if x >= 0 else 'red' for x in df['pnl']]
                ax2.bar(df['exit_time'], df['pnl'], color=colors, alpha=0.7)
                
                # Format axes
                ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
                plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
                plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        else:
            ax1.text(0.5, 0.5, 'No trades to display', 
                    ha='center', va='center', transform=ax1.transAxes)
            ax2.text(0.5, 0.5, 'No trades to display', 
                    ha='center', va='center', transform=ax2.transAxes)
        
        ax1.set_title('Cumulative P&L Over Time', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Cumulative P&L ($)')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        ax2.set_title('Individual Trade P&L', fontsize=14, fontweight='bold')
        ax2.set_ylabel('P&L ($)')
        ax2.set_xlabel('Time')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
        
    def _create_trade_distribution(self, pdf: PdfPages, trades: List[Dict]):
        """Create trade distribution charts"""
        fig, axes = plt.subplots(2, 2, figsize=self.figure_size)
        
        if trades:
            df = pd.DataFrame(trades)
            
            # P&L Distribution
            if 'pnl' in df.columns:
                ax = axes[0, 0]
                df['pnl'].hist(ax=ax, bins=30, color='skyblue', edgecolor='black')
                ax.axvline(x=0, color='red', linestyle='--', alpha=0.5)
                ax.set_title('P&L Distribution')
                ax.set_xlabel('P&L ($)')
                ax.set_ylabel('Frequency')
            
            # Win/Loss Pie Chart
            ax = axes[0, 1]
            win_loss = df['pnl'].apply(lambda x: 'Win' if x > 0 else 'Loss').value_counts()
            ax.pie(win_loss.values, labels=win_loss.index, autopct='%1.1f%%',
                  colors=['green', 'red'], startangle=90)
            ax.set_title('Win/Loss Distribution')
            
            # Trade Duration Distribution
            if 'entry_time' in df.columns and 'exit_time' in df.columns:
                ax = axes[1, 0]
                df['duration'] = (pd.to_datetime(df['exit_time']) - 
                                pd.to_datetime(df['entry_time'])).dt.total_seconds() / 3600
                df['duration'].hist(ax=ax, bins=20, color='orange', edgecolor='black')
                ax.set_title('Trade Duration Distribution')
                ax.set_xlabel('Duration (hours)')
                ax.set_ylabel('Frequency')
            
            # Symbol Distribution
            ax = axes[1, 1]
            if 'symbol' in df.columns:
                symbol_counts = df['symbol'].value_counts()
                ax.bar(range(len(symbol_counts)), symbol_counts.values)
                ax.set_xticks(range(len(symbol_counts)))
                ax.set_xticklabels(symbol_counts.index, rotation=45)
                ax.set_title('Trades by Symbol')
                ax.set_ylabel('Number of Trades')
        else:
            for ax in axes.flat:
                ax.text(0.5, 0.5, 'No data available', 
                       ha='center', va='center', transform=ax.transAxes)
        
        plt.suptitle('Trade Distribution Analysis', fontsize=16, fontweight='bold')
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
        
    def _create_position_analysis(self, pdf: PdfPages, positions: List[Dict]):
        """Create position analysis charts"""
        fig, axes = plt.subplots(2, 2, figsize=self.figure_size)
        
        if positions:
            df = pd.DataFrame(positions)
            
            # Position Sizes
            ax = axes[0, 0]
            if 'size' in df.columns and 'symbol' in df.columns:
                df.plot(x='symbol', y='size', kind='bar', ax=ax, color='teal')
                ax.set_title('Position Sizes')
                ax.set_ylabel('Size')
                ax.set_xlabel('')
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            # Unrealized P&L
            ax = axes[0, 1]
            if 'unrealized_pnl' in df.columns and 'symbol' in df.columns:
                colors = ['green' if x >= 0 else 'red' for x in df['unrealized_pnl']]
                ax.bar(range(len(df)), df['unrealized_pnl'], color=colors)
                ax.set_xticks(range(len(df)))
                ax.set_xticklabels(df['symbol'], rotation=45)
                ax.set_title('Unrealized P&L by Position')
                ax.set_ylabel('Unrealized P&L ($)')
                ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            
            # Leverage Distribution
            ax = axes[1, 0]
            if 'leverage' in df.columns:
                df['leverage'].value_counts().plot(kind='pie', ax=ax, autopct='%1.1f%%')
                ax.set_title('Leverage Distribution')
                ax.set_ylabel('')
            
            # Risk Exposure
            ax = axes[1, 1]
            if 'margin' in df.columns and 'symbol' in df.columns:
                df.plot(x='symbol', y='margin', kind='barh', ax=ax, color='purple')
                ax.set_title('Margin Usage by Position')
                ax.set_xlabel('Margin ($)')
                ax.set_ylabel('')
        else:
            for ax in axes.flat:
                ax.text(0.5, 0.5, 'No open positions', 
                       ha='center', va='center', transform=ax.transAxes)
        
        plt.suptitle('Position Analysis', fontsize=16, fontweight='bold')
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
        
    def _create_strategy_performance(self, pdf: PdfPages, trades: List[Dict]):
        """Create strategy performance comparison"""
        fig, axes = plt.subplots(2, 2, figsize=self.figure_size)
        
        if trades:
            df = pd.DataFrame(trades)
            
            if 'strategy' in df.columns:
                # Group by strategy
                strategy_stats = df.groupby('strategy').agg({
                    'pnl': ['sum', 'mean', 'count'],
                    'pnl_percent': 'mean'
                }).round(2)
                
                # Total P&L by Strategy
                ax = axes[0, 0]
                strategies = strategy_stats.index
                total_pnl = strategy_stats[('pnl', 'sum')]
                colors = ['green' if x >= 0 else 'red' for x in total_pnl]
                ax.bar(strategies, total_pnl, color=colors)
                ax.set_title('Total P&L by Strategy')
                ax.set_ylabel('Total P&L ($)')
                ax.set_xticklabels(strategies, rotation=45)
                ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
                
                # Average P&L by Strategy
                ax = axes[0, 1]
                avg_pnl = strategy_stats[('pnl', 'mean')]
                colors = ['green' if x >= 0 else 'red' for x in avg_pnl]
                ax.bar(strategies, avg_pnl, color=colors)
                ax.set_title('Average P&L by Strategy')
                ax.set_ylabel('Average P&L ($)')
                ax.set_xticklabels(strategies, rotation=45)
                ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
                
                # Trade Count by Strategy
                ax = axes[1, 0]
                trade_count = strategy_stats[('pnl', 'count')]
                ax.bar(strategies, trade_count, color='blue')
                ax.set_title('Number of Trades by Strategy')
                ax.set_ylabel('Trade Count')
                ax.set_xticklabels(strategies, rotation=45)
                
                # Win Rate by Strategy
                ax = axes[1, 1]
                win_rates = []
                for strategy in strategies:
                    strategy_df = df[df['strategy'] == strategy]
                    wins = (strategy_df['pnl'] > 0).sum()
                    total = len(strategy_df)
                    win_rate = (wins / total * 100) if total > 0 else 0
                    win_rates.append(win_rate)
                
                ax.bar(strategies, win_rates, color='orange')
                ax.set_title('Win Rate by Strategy')
                ax.set_ylabel('Win Rate (%)')
                ax.set_xticklabels(strategies, rotation=45)
                ax.axhline(y=50, color='red', linestyle='--', alpha=0.5)
        else:
            for ax in axes.flat:
                ax.text(0.5, 0.5, 'No strategy data available', 
                       ha='center', va='center', transform=ax.transAxes)
        
        plt.suptitle('Strategy Performance Comparison', fontsize=16, fontweight='bold')
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
        
    def _create_risk_metrics(self, pdf: PdfPages, metrics: Dict):
        """Create risk metrics visualization"""
        fig, axes = plt.subplots(2, 3, figsize=self.figure_size)
        
        # Sharpe Ratio Gauge
        ax = axes[0, 0]
        self._create_gauge_chart(ax, metrics.get('sharpe_ratio', 0), 
                                'Sharpe Ratio', min_val=-2, max_val=3)
        
        # Sortino Ratio Gauge
        ax = axes[0, 1]
        self._create_gauge_chart(ax, metrics.get('sortino_ratio', 0), 
                                'Sortino Ratio', min_val=-2, max_val=3)
        
        # Calmar Ratio Gauge
        ax = axes[0, 2]
        self._create_gauge_chart(ax, metrics.get('calmar_ratio', 0), 
                                'Calmar Ratio', min_val=-1, max_val=2)
        
        # Max Drawdown
        ax = axes[1, 0]
        drawdown = abs(metrics.get('max_drawdown', 0))
        ax.barh(['Max Drawdown'], [drawdown], color='red' if drawdown > 20 else 'orange')
        ax.set_xlim(0, 100)
        ax.set_xlabel('Drawdown (%)')
        ax.set_title('Maximum Drawdown')
        
        # Risk/Reward Ratio
        ax = axes[1, 1]
        risk_reward = metrics.get('risk_reward_ratio', 1)
        color = 'green' if risk_reward > 1.5 else 'orange' if risk_reward > 1 else 'red'
        ax.bar(['Risk/Reward'], [risk_reward], color=color)
        ax.set_ylim(0, 3)
        ax.set_ylabel('Ratio')
        ax.set_title('Risk/Reward Ratio')
        ax.axhline(y=1, color='black', linestyle='--', alpha=0.5)
        
        # Kelly Criterion
        ax = axes[1, 2]
        kelly = metrics.get('kelly_criterion', 0) * 100
        ax.bar(['Kelly %'], [kelly], color='blue')
        ax.set_ylim(0, 30)
        ax.set_ylabel('Optimal Position Size (%)')
        ax.set_title('Kelly Criterion')
        
        plt.suptitle('Risk Metrics Dashboard', fontsize=16, fontweight='bold')
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
        
    def _create_gauge_chart(self, ax, value, title, min_val=-2, max_val=3):
        """Create a gauge chart for metrics"""
        # Create semicircle
        theta = np.linspace(np.pi, 0, 100)
        r = 1
        
        # Color zones
        colors = ['red', 'orange', 'yellow', 'lightgreen', 'green']
        zones = np.linspace(min_val, max_val, len(colors) + 1)
        
        for i, color in enumerate(colors):
            theta_zone = np.linspace(np.pi - np.pi * i/len(colors), 
                                    np.pi - np.pi * (i+1)/len(colors), 20)
            ax.fill_between(theta_zone, 0, r, color=color, alpha=0.3)
        
        # Draw needle
        angle = np.pi - (value - min_val) / (max_val - min_val) * np.pi
        ax.plot([0, r * np.cos(angle)], [0, r * np.sin(angle)], 
               'k-', linewidth=3)
        ax.plot(0, 0, 'ko', markersize=10)
        
        # Labels
        ax.text(0, -0.2, f'{value:.2f}', ha='center', fontsize=14, fontweight='bold')
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-0.3, 1.2)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(title, fontsize=12)
        
    def generate_html_report(self, 
                            trades: List[Dict],
                            positions: List[Dict],
                            metrics: Dict,
                            date: Optional[datetime] = None) -> str:
        """
        Generate HTML report with embedded charts
        
        Returns: HTML string
        """
        if date is None:
            date = datetime.now()
            
        # Generate charts as base64 images
        charts = {}
        
        # P&L Chart
        fig, ax = plt.subplots(figsize=(10, 6))
        if trades:
            df = pd.DataFrame(trades)
            if 'pnl' in df.columns:
                df['cumulative_pnl'] = df['pnl'].cumsum()
                ax.plot(df.index, df['cumulative_pnl'], linewidth=2)
                ax.set_title('Cumulative P&L')
                ax.set_xlabel('Trade #')
                ax.set_ylabel('P&L ($)')
                ax.grid(True, alpha=0.3)
        
        # Save to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        charts['pnl_chart'] = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        # Generate HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Trading Report - {date.strftime('%Y-%m-%d')}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .header {{
                    background-color: #2c3e50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px;
                }}
                .metric-card {{
                    background: white;
                    border-radius: 5px;
                    padding: 15px;
                    margin: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    display: inline-block;
                    min-width: 200px;
                }}
                .metric-value {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #2c3e50;
                }}
                .metric-label {{
                    color: #7f8c8d;
                    font-size: 14px;
                }}
                .chart-container {{
                    background: white;
                    border-radius: 5px;
                    padding: 20px;
                    margin: 20px 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .positive {{ color: #27ae60; }}
                .negative {{ color: #e74c3c; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Trading Performance Report</h1>
                <p>{date.strftime('%A, %B %d, %Y')}</p>
            </div>
            
            <div style="text-align: center; margin: 20px 0;">
                <div class="metric-card">
                    <div class="metric-label">Total P&L</div>
                    <div class="metric-value {'positive' if metrics.get('total_pnl', 0) >= 0 else 'negative'}">
                        ${metrics.get('total_pnl', 0):,.2f}
                    </div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Win Rate</div>
                    <div class="metric-value">{metrics.get('win_rate', 0):.1f}%</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Total Trades</div>
                    <div class="metric-value">{metrics.get('total_trades', 0)}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Sharpe Ratio</div>
                    <div class="metric-value">{metrics.get('sharpe_ratio', 0):.2f}</div>
                </div>
            </div>
            
            <div class="chart-container">
                <h2>Cumulative P&L</h2>
                <img src="data:image/png;base64,{charts['pnl_chart']}" style="width: 100%; max-width: 800px;">
            </div>
            
            <div style="text-align: center; margin-top: 40px; color: #7f8c8d;">
                <p>Generated by Bybit Trading Bot</p>
            </div>
        </body>
        </html>
        """
        
        return html
        
    def send_telegram_report(self, chat_id: str, report_path: str):
        """Send report via Telegram (placeholder for integration)"""
        # This would integrate with the Telegram bot
        logger.info(f"Would send report {report_path} to Telegram chat {chat_id}")
        
    def upload_to_cloud(self, report_path: str) -> str:
        """Upload report to cloud storage (placeholder)"""
        # This would upload to S3, Google Drive, etc.
        logger.info(f"Would upload {report_path} to cloud storage")
        return f"https://example.com/reports/{Path(report_path).name}"


# Example usage
if __name__ == "__main__":
    # Create sample data
    sample_trades = [
        {
            'symbol': 'BTCUSDT',
            'pnl': 150.50,
            'pnl_percent': 1.5,
            'entry_time': datetime.now() - timedelta(hours=5),
            'exit_time': datetime.now() - timedelta(hours=3),
            'strategy': 'RSI',
        },
        {
            'symbol': 'ETHUSDT',
            'pnl': -75.25,
            'pnl_percent': -0.75,
            'entry_time': datetime.now() - timedelta(hours=4),
            'exit_time': datetime.now() - timedelta(hours=2),
            'strategy': 'EMA',
        },
        {
            'symbol': 'BTCUSDT',
            'pnl': 225.00,
            'pnl_percent': 2.25,
            'entry_time': datetime.now() - timedelta(hours=2),
            'exit_time': datetime.now() - timedelta(hours=1),
            'strategy': 'RSI',
        },
    ]
    
    sample_positions = [
        {
            'symbol': 'BTCUSDT',
            'size': 0.01,
            'unrealized_pnl': 50.00,
            'margin': 500.00,
            'leverage': 10,
        },
        {
            'symbol': 'ETHUSDT',
            'size': 0.1,
            'unrealized_pnl': -25.00,
            'margin': 300.00,
            'leverage': 5,
        },
    ]
    
    sample_metrics = {
        'total_pnl': 300.25,
        'daily_pnl': 150.50,
        'win_rate': 66.7,
        'total_trades': 3,
        'winning_trades': 2,
        'losing_trades': 1,
        'avg_win': 187.75,
        'avg_loss': 75.25,
        'profit_factor': 2.5,
        'sharpe_ratio': 1.85,
        'sortino_ratio': 2.10,
        'calmar_ratio': 1.5,
        'max_drawdown': 5.2,
        'risk_reward_ratio': 1.8,
        'kelly_criterion': 0.15,
        'active_positions': 2,
        'total_volume': 50000,
    }
    
    # Generate report
    generator = ReportGenerator()
    report_path = generator.generate_daily_report(
        trades=sample_trades,
        positions=sample_positions,
        metrics=sample_metrics
    )
    
    print(f"Report generated: {report_path}")
    
    # Generate HTML report
    html_report = generator.generate_html_report(
        trades=sample_trades,
        positions=sample_positions,
        metrics=sample_metrics
    )
    
    # Save HTML
    html_path = Path('reports') / f"report_{datetime.now().strftime('%Y%m%d')}.html"
    with open(html_path, 'w') as f:
        f.write(html_report)
    
    print(f"HTML report generated: {html_path}")