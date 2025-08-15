"""Tests for Data Normalizer"""

import pytest
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_normalizer import DataNormalizer, NormalizedTicker, NormalizedOrderBook


class TestDataNormalizer:
    """Test Data Normalizer functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.normalizer = DataNormalizer()
    
    def test_initialization(self):
        """Test data normalizer initialization"""
        assert self.normalizer is not None
        assert len(self.normalizer.symbol_mapping) == 0
        assert "tickers" in self.normalizer.data_buffer
    
    def test_normalize_ticker(self):
        """Test ticker normalization"""
        raw_data = {
            "symbol": "BTCUSDT",
            "lastPrice": "50000.00",
            "bidPrice": "49999.00",
            "askPrice": "50001.00",
            "volume24h": "1000000",
            "turnover24h": "50000000000",
            "highPrice24h": "51000.00",
            "lowPrice24h": "49000.00",
            "t": 1234567890000
        }
        
        normalized = self.normalizer.normalize_ticker(raw_data)
        
        assert normalized.symbol == "BTCUSDT"
        assert normalized.last_price == 50000.0
        assert normalized.bid_price == 49999.0
        assert normalized.ask_price == 50001.0
        assert normalized.exchange == "bybit"
    
    def test_normalize_orderbook(self):
        """Test orderbook normalization"""
        raw_data = {
            "symbol": "BTCUSDT",
            "b": [["49999", "1"], ["49998", "2"]],  # bids
            "a": [["50001", "1"], ["50002", "2"]],  # asks
            "t": 1234567890000,
            "u": 12345
        }
        
        normalized = self.normalizer.normalize_orderbook(raw_data)
        
        assert normalized.symbol == "BTCUSDT"
        assert len(normalized.bids) == 2
        assert len(normalized.asks) == 2
        assert normalized.bids[0] == (49999.0, 1.0)
        assert normalized.asks[0] == (50001.0, 1.0)
    
    def test_safe_float_conversion(self):
        """Test safe float conversion"""
        assert self.normalizer._safe_float("123.45") == 123.45
        assert self.normalizer._safe_float(None) == 0.0
        assert self.normalizer._safe_float("invalid") == 0.0
        assert self.normalizer._safe_float(100) == 100.0
    
    def test_safe_int_conversion(self):
        """Test safe int conversion"""
        assert self.normalizer._safe_int("123") == 123
        assert self.normalizer._safe_int(None) == 0
        assert self.normalizer._safe_int("invalid") == 0
        assert self.normalizer._safe_int(100.5) == 100
    
    def test_calculate_orderbook_metrics(self):
        """Test orderbook metrics calculation"""
        orderbook = NormalizedOrderBook(
            symbol="BTCUSDT",
            bids=[(49999, 10), (49998, 20)],
            asks=[(50001, 10), (50002, 20)]
        )
        
        metrics = self.normalizer.calculate_orderbook_metrics(orderbook, levels=2)
        
        assert "mid_price" in metrics
        assert "spread" in metrics
        assert "imbalance" in metrics
        assert metrics["mid_price"] == 50000.0
        assert metrics["spread"] == 2.0