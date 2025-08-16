#!/usr/bin/env python3
"""
Monitoring module tests
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from monitoring.metrics_collector import (
    MetricsCollector,
    get_metrics_collector,
    trades_total,
    trades_profit_total,
    account_balance,
    win_rate,
    model_accuracy,
    risk_score,
    cpu_usage,
    memory_usage
)
from prometheus_client import REGISTRY

class TestMetricsCollector:
    """Test metrics collector"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.collector = MetricsCollector(port=9999)
    
    def test_initialization(self):
        """Test collector initialization"""
        assert self.collector.port == 9999
        assert self.collector.app is not None
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_collect_system_metrics(self, mock_disk, mock_memory, mock_cpu):
        """Test system metrics collection"""
        # Mock system values
        mock_cpu.return_value = 50.0
        mock_memory.return_value = MagicMock(used=1024*1024*1024)
        mock_disk.return_value = MagicMock(percent=75.0)
        
        # Collect metrics
        self.collector.collect_system_metrics()
        
        # Verify calls
        mock_cpu.assert_called_once()
        mock_memory.assert_called_once()
        mock_disk.assert_called_once()
    
    def test_update_trading_metrics(self):
        """Test trading metrics update"""
        metrics = {
            'profit': 1000.0,
            'balance': 10000.0,
            'win_rate': 65.5,
            'positions': {
                'BTCUSDT': 2,
                'ETHUSDT': 1
            }
        }
        
        self.collector.update_trading_metrics(metrics)
        # No exceptions should be raised
        assert True
    
    def test_update_ml_metrics(self):
        """Test ML metrics update"""
        metrics = {
            'predictions': [
                {'model': 'xgboost', 'prediction': 'buy'},
                {'model': 'random_forest', 'prediction': 'sell'}
            ],
            'accuracy': {
                'xgboost': 0.85,
                'random_forest': 0.82
            },
            'training_time': {
                'xgboost': 120.5,
                'random_forest': 95.3
            }
        }
        
        self.collector.update_ml_metrics(metrics)
        # No exceptions should be raised
        assert True
    
    def test_update_risk_metrics(self):
        """Test risk metrics update"""
        metrics = {
            'risk_score': 45.0,
            'max_drawdown': 12.5,
            'positions': [
                {'symbol': 'BTCUSDT', 'size': 5000, 'leverage': 10},
                {'symbol': 'ETHUSDT', 'size': 2000, 'leverage': 5}
            ]
        }
        
        self.collector.update_risk_metrics(metrics)
        # No exceptions should be raised
        assert True
    
    def test_record_api_call(self):
        """Test API call recording"""
        self.collector.record_api_call(
            endpoint="/api/v2/trades",
            method="POST",
            duration=0.125
        )
        
        # With error
        self.collector.record_api_call(
            endpoint="/api/v2/trades",
            method="POST",
            duration=0.5,
            error="timeout"
        )
        
        # No exceptions should be raised
        assert True
    
    def test_record_trade_execution(self):
        """Test trade execution recording"""
        self.collector.record_trade_execution("BTCUSDT", 0.05)
        # No exceptions should be raised
        assert True
    
    def test_record_alert(self):
        """Test alert recording"""
        self.collector.record_alert("price_alert", "high")
        # No exceptions should be raised
        assert True
    
    def test_record_telegram_message(self):
        """Test Telegram message recording"""
        self.collector.record_telegram_message("trade_notification")
        # No exceptions should be raised
        assert True
    
    def test_update_connection_metrics(self):
        """Test connection metrics update"""
        self.collector.update_connection_metrics(
            ws_connections=3,
            db_connections=5
        )
        # No exceptions should be raised
        assert True
    
    def test_flask_routes(self):
        """Test Flask routes"""
        with self.collector.app.test_client() as client:
            # Test metrics endpoint
            response = client.get('/metrics')
            assert response.status_code == 200
            assert b'trading_bot' in response.data
            
            # Test health endpoint
            response = client.get('/health')
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'healthy'

class TestMetricsSingleton:
    """Test metrics collector singleton"""
    
    def test_singleton(self):
        """Test singleton pattern"""
        collector1 = get_metrics_collector(port=9998)
        collector2 = get_metrics_collector(port=9997)  # Different port ignored
        
        assert collector1 is collector2
        assert collector1.port == 9998  # First port is used

class TestPrometheusMetrics:
    """Test Prometheus metric definitions"""
    
    def test_counter_metrics(self):
        """Test counter metrics exist"""
        assert trades_total._name == 'trading_bot_trades_total'
    
    def test_gauge_metrics(self):
        """Test gauge metrics exist"""
        assert trades_profit_total._name == 'trading_bot_profit_total'
        assert account_balance._name == 'trading_bot_account_balance'
        assert win_rate._name == 'trading_bot_win_rate'
        assert risk_score._name == 'trading_bot_risk_score'
    
    def test_histogram_metrics(self):
        """Test histogram metrics exist"""
        from monitoring.metrics_collector import trade_execution_time
        assert trade_execution_time._name == 'trading_bot_trade_execution_seconds'
    
    def test_summary_metrics(self):
        """Test summary metrics exist"""
        from monitoring.metrics_collector import api_request_duration
        assert api_request_duration._name == 'trading_bot_api_request_duration_seconds'

@pytest.fixture
def metrics_collector():
    """Fixture for metrics collector"""
    return MetricsCollector(port=9997)

def test_metrics_error_handling(metrics_collector):
    """Test error handling in metrics updates"""
    # Should not raise exceptions with invalid data
    metrics_collector.update_trading_metrics({})
    metrics_collector.update_trading_metrics(None)
    metrics_collector.update_trading_metrics({"invalid": "data"})
    
    metrics_collector.update_ml_metrics({})
    metrics_collector.update_risk_metrics({})
    
    # All should complete without errors
    assert True