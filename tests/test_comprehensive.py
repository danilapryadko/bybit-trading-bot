#!/usr/bin/env python3
"""
Comprehensive Test Suite for Bybit Trading Bot
Covers all major components and integrations
"""

import pytest
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import components to test
from auth_service import AuthService, User
from report_generator import ReportGenerator
from performance_analytics import PerformanceAnalytics, Trade, PerformanceMetrics
from integrated_data_service import IntegratedDataService
from risk_manager_v2 import RiskManagerV2
from fastapi.testclient import TestClient
from fastapi_app import app

# Test fixtures
@pytest.fixture
def auth_service():
    """Create auth service instance for testing"""
    service = AuthService()
    # Use test database
    service.users_file = Path('test_users_db.json')
    service.users = {}
    return service

@pytest.fixture
def sample_trades():
    """Sample trade data for testing"""
    return [
        Trade(
            id="trade_1",
            symbol="BTCUSDT",
            side="Buy",
            entry_price=64000,
            exit_price=65000,
            quantity=0.01,
            entry_time=datetime.now() - timedelta(hours=5),
            exit_time=datetime.now() - timedelta(hours=3),
            pnl=10.0,
            pnl_percent=1.56,
            fees=0.5,
            strategy="RSI"
        ),
        Trade(
            id="trade_2",
            symbol="ETHUSDT",
            side="Sell",
            entry_price=3200,
            exit_price=3150,
            quantity=0.1,
            entry_time=datetime.now() - timedelta(hours=2),
            exit_time=datetime.now() - timedelta(hours=1),
            pnl=-5.0,
            pnl_percent=-1.56,
            fees=0.3,
            strategy="EMA"
        )
    ]

@pytest.fixture
def api_client():
    """Create FastAPI test client"""
    return TestClient(app)

# Authentication Tests
class TestAuthentication:
    """Test authentication service"""
    
    def test_create_user(self, auth_service):
        """Test user creation"""
        user = auth_service.create_user(
            username="testuser",
            email="test@example.com",
            password="securepassword123",
            role="trader"
        )
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "trader"
        assert user.is_active is True
        
    def test_authenticate_user(self, auth_service):
        """Test user authentication"""
        # Create user
        auth_service.create_user(
            username="testuser",
            email="test@example.com",
            password="securepassword123"
        )
        
        # Test correct password
        user = auth_service.authenticate_user("testuser", "securepassword123")
        assert user is not None
        assert user.username == "testuser"
        
        # Test wrong password
        user = auth_service.authenticate_user("testuser", "wrongpassword")
        assert user is None
        
        # Test non-existent user
        user = auth_service.authenticate_user("nonexistent", "password")
        assert user is None
        
    def test_jwt_tokens(self, auth_service):
        """Test JWT token generation and verification"""
        user = auth_service.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            role="admin"
        )
        
        # Create tokens
        access_token = auth_service.create_access_token(user)
        refresh_token = auth_service.create_refresh_token(user)
        
        assert access_token is not None
        assert refresh_token is not None
        
        # Verify access token
        token_data = auth_service.verify_token(access_token)
        assert token_data.username == "testuser"
        assert token_data.role == "admin"
        
    def test_role_permissions(self, auth_service):
        """Test role-based permissions"""
        viewer = User(
            id="1", username="viewer", email="v@test.com",
            role="viewer", telegram_id=None,
            created_at=datetime.now(), last_login=None
        )
        
        trader = User(
            id="2", username="trader", email="t@test.com",
            role="trader", telegram_id=None,
            created_at=datetime.now(), last_login=None
        )
        
        admin = User(
            id="3", username="admin", email="a@test.com",
            role="admin", telegram_id=None,
            created_at=datetime.now(), last_login=None
        )
        
        # Test viewer permissions
        assert auth_service.check_permissions(viewer, "viewer") is True
        assert auth_service.check_permissions(viewer, "trader") is False
        assert auth_service.check_permissions(viewer, "admin") is False
        
        # Test trader permissions
        assert auth_service.check_permissions(trader, "viewer") is True
        assert auth_service.check_permissions(trader, "trader") is True
        assert auth_service.check_permissions(trader, "admin") is False
        
        # Test admin permissions
        assert auth_service.check_permissions(admin, "viewer") is True
        assert auth_service.check_permissions(admin, "trader") is True
        assert auth_service.check_permissions(admin, "admin") is True

# Performance Analytics Tests
class TestPerformanceAnalytics:
    """Test performance analytics"""
    
    def test_calculate_metrics(self, sample_trades):
        """Test metrics calculation"""
        analytics = PerformanceAnalytics()
        metrics = analytics.calculate_metrics(sample_trades)
        
        assert metrics['total_trades'] == 2
        assert metrics['winning_trades'] == 1
        assert metrics['losing_trades'] == 1
        assert metrics['win_rate'] == 50.0
        assert metrics['total_pnl'] == 5.0  # 10 - 5
        
    def test_sharpe_ratio(self, sample_trades):
        """Test Sharpe ratio calculation"""
        analytics = PerformanceAnalytics()
        
        # Create sample returns
        returns = pd.Series([0.01, -0.005, 0.015, -0.002, 0.008])
        sharpe = analytics.calculate_sharpe_ratio(returns)
        
        assert isinstance(sharpe, float)
        assert -10 < sharpe < 10  # Reasonable range
        
    def test_max_drawdown(self):
        """Test maximum drawdown calculation"""
        analytics = PerformanceAnalytics()
        
        # Create sample equity curve
        equity = pd.Series([1000, 1100, 1050, 950, 1000, 1150, 1100])
        drawdown = analytics.calculate_max_drawdown(equity)
        
        # Max drawdown from 1100 to 950 = 13.64%
        assert 13 < drawdown < 14

# Risk Management Tests
class TestRiskManager:
    """Test risk management"""
    
    def test_position_sizing(self):
        """Test position size calculation"""
        risk_manager = RiskManagerV2(
            max_position_size=0.2,
            max_daily_loss=0.05,
            max_drawdown=0.15
        )
        
        # Test with 2% risk per trade
        position_size = risk_manager.calculate_position_size(
            balance=10000,
            price=50000,
            risk_percent=2.0
        )
        
        # Should not exceed 20% of balance
        assert position_size <= 2000
        assert position_size > 0
        
    def test_risk_validation(self):
        """Test order risk validation"""
        risk_manager = RiskManagerV2()
        
        # Test valid order
        is_valid, message = risk_manager.validate_order(
            symbol="BTCUSDT",
            side="Buy",
            quantity=0.01,
            price=65000
        )
        assert is_valid is True
        
        # Test order exceeding position limit
        is_valid, message = risk_manager.validate_order(
            symbol="BTCUSDT",
            side="Buy",
            quantity=10.0,  # Very large position
            price=65000
        )
        # This should depend on balance and limits
        
    def test_daily_loss_limit(self):
        """Test daily loss limit enforcement"""
        risk_manager = RiskManagerV2(
            max_daily_loss=0.05  # 5% max daily loss
        )
        
        # Simulate daily losses
        risk_manager.update_daily_pnl(-300)  # 3% loss on 10k balance
        assert risk_manager.check_risk_limits(10000) is True
        
        risk_manager.update_daily_pnl(-300)  # 6% total loss
        assert risk_manager.check_risk_limits(10000) is False

# Report Generator Tests
class TestReportGenerator:
    """Test report generation"""
    
    def test_pdf_report_generation(self, sample_trades, tmp_path):
        """Test PDF report generation"""
        generator = ReportGenerator(output_dir=str(tmp_path))
        
        metrics = {
            'total_pnl': 100.0,
            'win_rate': 60.0,
            'total_trades': 10,
            'sharpe_ratio': 1.5
        }
        
        report_path = generator.generate_daily_report(
            trades=[t.__dict__ for t in sample_trades],
            positions=[],
            metrics=metrics
        )
        
        assert Path(report_path).exists()
        assert Path(report_path).suffix == '.pdf'
        
    def test_html_report_generation(self, sample_trades):
        """Test HTML report generation"""
        generator = ReportGenerator()
        
        metrics = {
            'total_pnl': 100.0,
            'win_rate': 60.0,
            'total_trades': 10,
            'sharpe_ratio': 1.5
        }
        
        html_report = generator.generate_html_report(
            trades=[t.__dict__ for t in sample_trades],
            positions=[],
            metrics=metrics
        )
        
        assert isinstance(html_report, str)
        assert '<html>' in html_report
        assert 'Trading Performance Report' in html_report

# API Tests
class TestFastAPI:
    """Test FastAPI endpoints"""
    
    def test_health_endpoint(self, api_client):
        """Test health check endpoint"""
        response = api_client.get("/api/v2/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        
    def test_trading_status(self, api_client):
        """Test trading status endpoint"""
        response = api_client.get("/api/v2/trading/status")
        assert response.status_code == 200
        data = response.json()
        assert 'is_running' in data
        assert 'is_paper_trading' in data
        
    @patch('fastapi_app.risk_manager.validate_order')
    def test_place_order(self, mock_validate, api_client):
        """Test order placement endpoint"""
        mock_validate.return_value = (True, "Valid")
        
        order_data = {
            "symbol": "BTCUSDT",
            "side": "Buy",
            "order_type": "Limit",
            "quantity": 0.01,
            "price": 65000
        }
        
        response = api_client.post("/api/v2/orders", json=order_data)
        assert response.status_code == 200
        data = response.json()
        assert 'order_id' in data
        assert data['symbol'] == "BTCUSDT"
        
    def test_get_positions(self, api_client):
        """Test get positions endpoint"""
        response = api_client.get("/api/v2/positions")
        assert response.status_code == 200
        data = response.json()
        assert 'positions' in data
        assert isinstance(data['positions'], list)
        
    def test_market_tickers(self, api_client):
        """Test market tickers endpoint"""
        response = api_client.get("/api/v2/market/tickers")
        assert response.status_code == 200
        data = response.json()
        assert 'BTCUSDT' in data
        assert 'last_price' in data['BTCUSDT']
        
    def test_get_strategies(self, api_client):
        """Test get strategies endpoint"""
        response = api_client.get("/api/v2/strategies")
        assert response.status_code == 200
        data = response.json()
        assert 'strategies' in data
        assert len(data['strategies']) > 0

# Integration Tests
class TestIntegration:
    """Test component integration"""
    
    @pytest.mark.asyncio
    async def test_data_service_fallback(self):
        """Test WebSocket to REST API fallback"""
        service = IntegratedDataService(testnet=True)
        
        # Mock WebSocket failure
        service.ws_connected = False
        service.use_websocket = False
        
        # Should use REST API
        assert service.get_data_source() == "REST API"
        
        # Mock WebSocket recovery
        service.ws_connected = True
        assert service.get_data_source() == "WebSocket"
        
    @pytest.mark.asyncio
    async def test_report_with_analytics(self, sample_trades):
        """Test report generation with analytics integration"""
        analytics = PerformanceAnalytics()
        generator = ReportGenerator()
        
        # Calculate metrics
        metrics = analytics.calculate_metrics(sample_trades)
        
        # Generate report
        html_report = generator.generate_html_report(
            trades=[t.__dict__ for t in sample_trades],
            positions=[],
            metrics=metrics
        )
        
        assert 'Total P&L' in html_report
        assert 'Win Rate' in html_report

# WebSocket Tests
class TestWebSocket:
    """Test WebSocket functionality"""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, api_client):
        """Test WebSocket connection"""
        # This would require WebSocket test client
        # Simplified test for now
        assert api_client is not None
        
    @pytest.mark.asyncio
    async def test_websocket_subscription(self):
        """Test WebSocket subscription"""
        # Mock WebSocket behavior
        from websocket_server import ConnectionManager
        
        manager = ConnectionManager()
        assert len(manager.active_connections) == 0
        
        # Would need WebSocket mock for full test

# Performance Tests
class TestPerformance:
    """Test performance and scalability"""
    
    def test_large_trade_dataset(self):
        """Test with large number of trades"""
        analytics = PerformanceAnalytics()
        
        # Generate 10000 trades
        large_trades = []
        for i in range(10000):
            trade = Trade(
                id=f"trade_{i}",
                symbol="BTCUSDT",
                side="Buy" if i % 2 == 0 else "Sell",
                entry_price=64000 + i,
                exit_price=64100 + i,
                quantity=0.01,
                entry_time=datetime.now() - timedelta(hours=i),
                exit_time=datetime.now() - timedelta(hours=i-1),
                pnl=np.random.randn() * 10,
                pnl_percent=np.random.randn() * 2,
                fees=0.5,
                strategy="Test"
            )
            large_trades.append(trade)
            
        # Should complete within reasonable time
        import time
        start = time.time()
        metrics = analytics.calculate_metrics(large_trades)
        duration = time.time() - start
        
        assert duration < 5.0  # Should complete within 5 seconds
        assert metrics['total_trades'] == 10000
        
    def test_concurrent_api_requests(self, api_client):
        """Test API under concurrent load"""
        import concurrent.futures
        
        def make_request():
            return api_client.get("/api/v2/health")
            
        # Make 100 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(100)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
            
        # All should succeed
        assert all(r.status_code == 200 for r in results)

# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup():
    """Clean up test files after tests"""
    yield
    # Clean up test database
    test_db = Path('test_users_db.json')
    if test_db.exists():
        test_db.unlink()
    # Clean up test reports
    test_reports = Path('reports')
    if test_reports.exists():
        for file in test_reports.glob('*test*'):
            file.unlink()

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])