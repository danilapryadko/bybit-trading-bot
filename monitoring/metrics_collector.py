#!/usr/bin/env python3
"""
Prometheus Metrics Collector for Bybit Trading Bot
Exports metrics for monitoring with Prometheus and Grafana
"""

import os
import time
import logging
from typing import Dict, Any
from datetime import datetime, timezone
from prometheus_client import (
    Counter, Gauge, Histogram, Summary,
    start_http_server, generate_latest,
    CollectorRegistry, CONTENT_TYPE_LATEST
)
from flask import Flask, Response
import psutil

logger = logging.getLogger(__name__)

# Create metrics registry
registry = CollectorRegistry()

# Trading Metrics
trades_total = Counter(
    'trading_bot_trades_total',
    'Total number of trades executed',
    ['symbol', 'side', 'status'],
    registry=registry
)

trades_profit_total = Gauge(
    'trading_bot_profit_total',
    'Total profit/loss in USD',
    registry=registry
)

open_positions = Gauge(
    'trading_bot_open_positions',
    'Number of open positions',
    ['symbol'],
    registry=registry
)

account_balance = Gauge(
    'trading_bot_account_balance',
    'Current account balance in USD',
    registry=registry
)

win_rate = Gauge(
    'trading_bot_win_rate',
    'Percentage of winning trades',
    registry=registry
)

# Performance Metrics
trade_execution_time = Histogram(
    'trading_bot_trade_execution_seconds',
    'Time taken to execute trades',
    ['symbol'],
    registry=registry
)

api_request_duration = Summary(
    'trading_bot_api_request_duration_seconds',
    'API request duration',
    ['endpoint', 'method'],
    registry=registry
)

api_errors_total = Counter(
    'trading_bot_api_errors_total',
    'Total number of API errors',
    ['endpoint', 'error_type'],
    registry=registry
)

# ML Model Metrics
model_predictions = Counter(
    'trading_bot_ml_predictions_total',
    'Total ML model predictions',
    ['model', 'prediction'],
    registry=registry
)

model_accuracy = Gauge(
    'trading_bot_ml_accuracy',
    'ML model accuracy score',
    ['model'],
    registry=registry
)

model_training_time = Gauge(
    'trading_bot_ml_training_seconds',
    'Time taken to train ML models',
    ['model'],
    registry=registry
)

# System Metrics
cpu_usage = Gauge(
    'trading_bot_cpu_usage_percent',
    'CPU usage percentage',
    registry=registry
)

memory_usage = Gauge(
    'trading_bot_memory_usage_bytes',
    'Memory usage in bytes',
    registry=registry
)

disk_usage = Gauge(
    'trading_bot_disk_usage_percent',
    'Disk usage percentage',
    registry=registry
)

websocket_connections = Gauge(
    'trading_bot_websocket_connections',
    'Number of active WebSocket connections',
    registry=registry
)

database_connections = Gauge(
    'trading_bot_database_connections',
    'Number of active database connections',
    registry=registry
)

# Risk Metrics
position_size = Gauge(
    'trading_bot_position_size_usd',
    'Current position size in USD',
    ['symbol'],
    registry=registry
)

leverage_used = Gauge(
    'trading_bot_leverage',
    'Current leverage being used',
    ['symbol'],
    registry=registry
)

risk_score = Gauge(
    'trading_bot_risk_score',
    'Current risk score (0-100)',
    registry=registry
)

max_drawdown = Gauge(
    'trading_bot_max_drawdown_percent',
    'Maximum drawdown percentage',
    registry=registry
)

# Alert Metrics
alerts_sent = Counter(
    'trading_bot_alerts_sent_total',
    'Total alerts sent',
    ['type', 'severity'],
    registry=registry
)

telegram_messages = Counter(
    'trading_bot_telegram_messages_total',
    'Total Telegram messages sent',
    ['type'],
    registry=registry
)

class MetricsCollector:
    """Collects and exports metrics for Prometheus"""
    
    def __init__(self, port: int = 9090):
        """Initialize metrics collector"""
        self.port = port
        self.app = Flask(__name__)
        self.setup_routes()
        
        # Start system metrics collection
        self.collect_system_metrics()
        
        logger.info(f"Metrics collector initialized on port {port}")
    
    def setup_routes(self):
        """Setup Flask routes for metrics"""
        @self.app.route('/metrics')
        def metrics():
            """Prometheus metrics endpoint"""
            return Response(
                generate_latest(registry),
                mimetype=CONTENT_TYPE_LATEST
            )
        
        @self.app.route('/health')
        def health():
            """Health check endpoint"""
            return {'status': 'healthy', 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    def collect_system_metrics(self):
        """Collect system resource metrics"""
        try:
            # CPU usage
            cpu_usage.set(psutil.cpu_percent(interval=1))
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage.set(memory.used)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage.set(disk.percent)
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def update_trading_metrics(self, metrics: Dict[str, Any]):
        """Update trading-related metrics"""
        try:
            # Update counters and gauges
            if 'total_trades' in metrics:
                for trade in metrics.get('trades', []):
                    trades_total.labels(
                        symbol=trade['symbol'],
                        side=trade['side'],
                        status=trade['status']
                    ).inc()
            
            if 'profit' in metrics:
                trades_profit_total.set(metrics['profit'])
            
            if 'balance' in metrics:
                account_balance.set(metrics['balance'])
            
            if 'win_rate' in metrics:
                win_rate.set(metrics['win_rate'])
            
            if 'positions' in metrics:
                for symbol, count in metrics['positions'].items():
                    open_positions.labels(symbol=symbol).set(count)
            
        except Exception as e:
            logger.error(f"Error updating trading metrics: {e}")
    
    def update_ml_metrics(self, metrics: Dict[str, Any]):
        """Update ML model metrics"""
        try:
            if 'predictions' in metrics:
                for pred in metrics['predictions']:
                    model_predictions.labels(
                        model=pred['model'],
                        prediction=pred['prediction']
                    ).inc()
            
            if 'accuracy' in metrics:
                for model, accuracy in metrics['accuracy'].items():
                    model_accuracy.labels(model=model).set(accuracy)
            
            if 'training_time' in metrics:
                for model, time_taken in metrics['training_time'].items():
                    model_training_time.labels(model=model).set(time_taken)
            
        except Exception as e:
            logger.error(f"Error updating ML metrics: {e}")
    
    def update_risk_metrics(self, metrics: Dict[str, Any]):
        """Update risk management metrics"""
        try:
            if 'positions' in metrics:
                for pos in metrics['positions']:
                    position_size.labels(symbol=pos['symbol']).set(pos['size'])
                    leverage_used.labels(symbol=pos['symbol']).set(pos['leverage'])
            
            if 'risk_score' in metrics:
                risk_score.set(metrics['risk_score'])
            
            if 'max_drawdown' in metrics:
                max_drawdown.set(metrics['max_drawdown'])
            
        except Exception as e:
            logger.error(f"Error updating risk metrics: {e}")
    
    def record_api_call(self, endpoint: str, method: str, duration: float, error: str = None):
        """Record API call metrics"""
        api_request_duration.labels(endpoint=endpoint, method=method).observe(duration)
        
        if error:
            api_errors_total.labels(endpoint=endpoint, error_type=error).inc()
    
    def record_trade_execution(self, symbol: str, execution_time: float):
        """Record trade execution metrics"""
        trade_execution_time.labels(symbol=symbol).observe(execution_time)
    
    def record_alert(self, alert_type: str, severity: str):
        """Record alert metrics"""
        alerts_sent.labels(type=alert_type, severity=severity).inc()
    
    def record_telegram_message(self, message_type: str):
        """Record Telegram message metrics"""
        telegram_messages.labels(type=message_type).inc()
    
    def update_connection_metrics(self, ws_connections: int, db_connections: int):
        """Update connection metrics"""
        websocket_connections.set(ws_connections)
        database_connections.set(db_connections)
    
    def start(self):
        """Start metrics server"""
        logger.info(f"Starting metrics server on port {self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False)

# Custom metrics for specific strategies
strategy_signals = Counter(
    'trading_bot_strategy_signals_total',
    'Total signals generated by strategies',
    ['strategy', 'signal_type'],
    registry=registry
)

strategy_performance = Gauge(
    'trading_bot_strategy_performance',
    'Strategy performance score',
    ['strategy'],
    registry=registry
)

# Market data metrics
market_data_updates = Counter(
    'trading_bot_market_data_updates_total',
    'Total market data updates received',
    ['symbol', 'timeframe'],
    registry=registry
)

orderbook_spread = Gauge(
    'trading_bot_orderbook_spread',
    'Current orderbook spread',
    ['symbol'],
    registry=registry
)

# Create singleton instance
_metrics_collector = None

def get_metrics_collector(port: int = 9090) -> MetricsCollector:
    """Get singleton metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(port)
    return _metrics_collector

if __name__ == "__main__":
    # Start metrics server
    collector = get_metrics_collector()
    
    # Example: Update some metrics
    collector.update_trading_metrics({
        'balance': 10000,
        'profit': 500,
        'win_rate': 65.5,
        'positions': {'BTCUSDT': 2, 'ETHUSDT': 1}
    })
    
    collector.update_risk_metrics({
        'risk_score': 45,
        'max_drawdown': 12.5,
        'positions': [
            {'symbol': 'BTCUSDT', 'size': 5000, 'leverage': 10},
            {'symbol': 'ETHUSDT', 'size': 2000, 'leverage': 5}
        ]
    })
    
    # Start server
    collector.start()