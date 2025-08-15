"""
Data Normalization Pipeline for Bybit Trading Bot
Normalizes and processes market data for consistent format
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from collections import deque
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class NormalizedTicker:
    """Normalized ticker data structure"""
    symbol: str
    exchange: str = "bybit"
    last_price: float = 0.0
    bid_price: float = 0.0
    ask_price: float = 0.0
    bid_size: float = 0.0
    ask_size: float = 0.0
    volume_24h: float = 0.0
    volume_quote_24h: float = 0.0
    price_change_24h: float = 0.0
    price_change_pct_24h: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    open_24h: float = 0.0
    timestamp: int = 0
    local_timestamp: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedOrderBook:
    """Normalized order book data structure"""
    symbol: str
    exchange: str = "bybit"
    bids: List[Tuple[float, float]] = None  # [(price, size), ...]
    asks: List[Tuple[float, float]] = None  # [(price, size), ...]
    timestamp: int = 0
    local_timestamp: int = 0
    update_id: int = 0
    
    def __post_init__(self):
        if self.bids is None:
            self.bids = []
        if self.asks is None:
            self.asks = []
    
    def get_best_bid(self) -> Tuple[float, float]:
        """Get best bid price and size"""
        return self.bids[0] if self.bids else (0.0, 0.0)
    
    def get_best_ask(self) -> Tuple[float, float]:
        """Get best ask price and size"""
        return self.asks[0] if self.asks else (0.0, 0.0)
    
    def get_mid_price(self) -> float:
        """Calculate mid price"""
        best_bid, _ = self.get_best_bid()
        best_ask, _ = self.get_best_ask()
        if best_bid and best_ask:
            return (best_bid + best_ask) / 2
        return 0.0
    
    def get_spread(self) -> float:
        """Calculate bid-ask spread"""
        best_bid, _ = self.get_best_bid()
        best_ask, _ = self.get_best_ask()
        if best_bid and best_ask:
            return best_ask - best_bid
        return 0.0
    
    def get_spread_percentage(self) -> float:
        """Calculate spread as percentage of mid price"""
        mid_price = self.get_mid_price()
        if mid_price > 0:
            return (self.get_spread() / mid_price) * 100
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "bids": self.bids,
            "asks": self.asks,
            "timestamp": self.timestamp,
            "local_timestamp": self.local_timestamp,
            "update_id": self.update_id,
            "best_bid": self.get_best_bid(),
            "best_ask": self.get_best_ask(),
            "mid_price": self.get_mid_price(),
            "spread": self.get_spread(),
            "spread_pct": self.get_spread_percentage()
        }


@dataclass
class NormalizedTrade:
    """Normalized trade data structure"""
    symbol: str
    exchange: str = "bybit"
    trade_id: str = ""
    price: float = 0.0
    quantity: float = 0.0
    side: str = ""  # "buy" or "sell"
    timestamp: int = 0
    local_timestamp: int = 0
    is_buyer_maker: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedKline:
    """Normalized kline/candlestick data structure"""
    symbol: str
    exchange: str = "bybit"
    interval: str = "1m"
    open_time: int = 0
    close_time: int = 0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    volume_quote: float = 0.0
    trades_count: int = 0
    is_closed: bool = False
    local_timestamp: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DataNormalizer:
    """Normalizes market data from various sources to consistent format"""
    
    def __init__(self):
        self.symbol_mapping = {}  # Map exchange symbols to normalized symbols
        self.data_buffer = {
            "tickers": {},
            "orderbooks": {},
            "trades": deque(maxlen=10000),
            "klines": {}
        }
        self.statistics = {
            "messages_processed": 0,
            "errors": 0,
            "last_update": None
        }
        
        logger.info("Data Normalizer initialized")
    
    def normalize_ticker(self, raw_data: Dict[str, Any], exchange: str = "bybit") -> NormalizedTicker:
        """Normalize ticker data from exchange format"""
        try:
            normalized = NormalizedTicker(
                symbol=raw_data.get("symbol", ""),
                exchange=exchange,
                last_price=self._safe_float(raw_data.get("last_price", raw_data.get("lastPrice", 0))),
                bid_price=self._safe_float(raw_data.get("bid_price", raw_data.get("bidPrice", 0))),
                ask_price=self._safe_float(raw_data.get("ask_price", raw_data.get("askPrice", 0))),
                bid_size=self._safe_float(raw_data.get("bid_size", raw_data.get("bidSize", 0))),
                ask_size=self._safe_float(raw_data.get("ask_size", raw_data.get("askSize", 0))),
                volume_24h=self._safe_float(raw_data.get("volume_24h", raw_data.get("volume24h", 0))),
                volume_quote_24h=self._safe_float(raw_data.get("turnover_24h", raw_data.get("turnover24h", 0))),
                high_24h=self._safe_float(raw_data.get("high_24h", raw_data.get("highPrice24h", 0))),
                low_24h=self._safe_float(raw_data.get("low_24h", raw_data.get("lowPrice24h", 0))),
                timestamp=self._safe_int(raw_data.get("timestamp", raw_data.get("t", 0))),
                local_timestamp=int(datetime.now(timezone.utc).timestamp() * 1000)
            )
            
            # Calculate price changes
            if normalized.last_price > 0 and normalized.open_24h > 0:
                normalized.price_change_24h = normalized.last_price - normalized.open_24h
                normalized.price_change_pct_24h = (normalized.price_change_24h / normalized.open_24h) * 100
            elif "price_24h_pcnt" in raw_data or "price24hPcnt" in raw_data:
                normalized.price_change_pct_24h = self._safe_float(
                    raw_data.get("price_24h_pcnt", raw_data.get("price24hPcnt", 0))
                ) * 100
            
            # Store in buffer
            self.data_buffer["tickers"][normalized.symbol] = normalized
            self.statistics["messages_processed"] += 1
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing ticker data: {e}")
            self.statistics["errors"] += 1
            return NormalizedTicker(symbol=raw_data.get("symbol", "unknown"))
    
    def normalize_orderbook(self, raw_data: Dict[str, Any], exchange: str = "bybit") -> NormalizedOrderBook:
        """Normalize orderbook data from exchange format"""
        try:
            # Parse bids and asks
            bids = []
            asks = []
            
            raw_bids = raw_data.get("bids", raw_data.get("b", []))
            raw_asks = raw_data.get("asks", raw_data.get("a", []))
            
            # Normalize bid/ask format
            for bid in raw_bids[:50]:  # Limit to top 50 levels
                if isinstance(bid, list) and len(bid) >= 2:
                    bids.append((self._safe_float(bid[0]), self._safe_float(bid[1])))
                elif isinstance(bid, dict):
                    bids.append((
                        self._safe_float(bid.get("price", 0)),
                        self._safe_float(bid.get("size", bid.get("qty", 0)))
                    ))
            
            for ask in raw_asks[:50]:  # Limit to top 50 levels
                if isinstance(ask, list) and len(ask) >= 2:
                    asks.append((self._safe_float(ask[0]), self._safe_float(ask[1])))
                elif isinstance(ask, dict):
                    asks.append((
                        self._safe_float(ask.get("price", 0)),
                        self._safe_float(ask.get("size", ask.get("qty", 0)))
                    ))
            
            # Sort bids descending, asks ascending
            bids.sort(key=lambda x: x[0], reverse=True)
            asks.sort(key=lambda x: x[0])
            
            normalized = NormalizedOrderBook(
                symbol=raw_data.get("symbol", raw_data.get("s", "")),
                exchange=exchange,
                bids=bids,
                asks=asks,
                timestamp=self._safe_int(raw_data.get("timestamp", raw_data.get("t", 0))),
                local_timestamp=int(datetime.now(timezone.utc).timestamp() * 1000),
                update_id=self._safe_int(raw_data.get("update_id", raw_data.get("u", 0)))
            )
            
            # Store in buffer
            self.data_buffer["orderbooks"][normalized.symbol] = normalized
            self.statistics["messages_processed"] += 1
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing orderbook data: {e}")
            self.statistics["errors"] += 1
            return NormalizedOrderBook(symbol=raw_data.get("symbol", "unknown"))
    
    def normalize_trade(self, raw_data: Dict[str, Any], exchange: str = "bybit") -> NormalizedTrade:
        """Normalize trade data from exchange format"""
        try:
            # Determine trade side
            is_buyer_maker = raw_data.get("is_buyer_maker", raw_data.get("m", False))
            side = "sell" if is_buyer_maker else "buy"
            
            normalized = NormalizedTrade(
                symbol=raw_data.get("symbol", raw_data.get("s", "")),
                exchange=exchange,
                trade_id=str(raw_data.get("trade_id", raw_data.get("i", ""))),
                price=self._safe_float(raw_data.get("price", raw_data.get("p", 0))),
                quantity=self._safe_float(raw_data.get("quantity", raw_data.get("v", raw_data.get("q", 0)))),
                side=side,
                timestamp=self._safe_int(raw_data.get("timestamp", raw_data.get("t", 0))),
                local_timestamp=int(datetime.now(timezone.utc).timestamp() * 1000),
                is_buyer_maker=is_buyer_maker
            )
            
            # Store in buffer
            self.data_buffer["trades"].append(normalized)
            self.statistics["messages_processed"] += 1
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing trade data: {e}")
            self.statistics["errors"] += 1
            return NormalizedTrade(symbol=raw_data.get("symbol", "unknown"))
    
    def normalize_kline(self, raw_data: Dict[str, Any], exchange: str = "bybit") -> NormalizedKline:
        """Normalize kline data from exchange format"""
        try:
            normalized = NormalizedKline(
                symbol=raw_data.get("symbol", ""),
                exchange=exchange,
                interval=raw_data.get("interval", "1m"),
                open_time=self._safe_int(raw_data.get("open_time", raw_data.get("start", 0))),
                close_time=self._safe_int(raw_data.get("close_time", raw_data.get("end", 0))),
                open=self._safe_float(raw_data.get("open", 0)),
                high=self._safe_float(raw_data.get("high", 0)),
                low=self._safe_float(raw_data.get("low", 0)),
                close=self._safe_float(raw_data.get("close", 0)),
                volume=self._safe_float(raw_data.get("volume", 0)),
                volume_quote=self._safe_float(raw_data.get("turnover", raw_data.get("volume_quote", 0))),
                trades_count=self._safe_int(raw_data.get("trades_count", 0)),
                is_closed=raw_data.get("confirm", raw_data.get("is_closed", False)),
                local_timestamp=int(datetime.now(timezone.utc).timestamp() * 1000)
            )
            
            # Store in buffer
            key = f"{normalized.symbol}_{normalized.interval}"
            if key not in self.data_buffer["klines"]:
                self.data_buffer["klines"][key] = deque(maxlen=1000)
            self.data_buffer["klines"][key].append(normalized)
            self.statistics["messages_processed"] += 1
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing kline data: {e}")
            self.statistics["errors"] += 1
            return NormalizedKline(symbol=raw_data.get("symbol", "unknown"))
    
    def aggregate_trades(self, trades: List[NormalizedTrade], interval_seconds: int = 60) -> Dict[str, Any]:
        """Aggregate trades into volume-weighted statistics"""
        if not trades:
            return {}
        
        try:
            df = pd.DataFrame([t.to_dict() for t in trades])
            
            # Calculate VWAP (Volume Weighted Average Price)
            total_volume = df["quantity"].sum()
            if total_volume > 0:
                vwap = (df["price"] * df["quantity"]).sum() / total_volume
            else:
                vwap = df["price"].mean()
            
            # Calculate buy/sell volume
            buy_volume = df[df["side"] == "buy"]["quantity"].sum()
            sell_volume = df[df["side"] == "sell"]["quantity"].sum()
            
            # Calculate order flow imbalance
            if (buy_volume + sell_volume) > 0:
                order_flow_imbalance = (buy_volume - sell_volume) / (buy_volume + sell_volume)
            else:
                order_flow_imbalance = 0
            
            return {
                "vwap": vwap,
                "total_volume": total_volume,
                "buy_volume": buy_volume,
                "sell_volume": sell_volume,
                "order_flow_imbalance": order_flow_imbalance,
                "trade_count": len(trades),
                "avg_trade_size": total_volume / len(trades) if trades else 0,
                "price_high": df["price"].max(),
                "price_low": df["price"].min(),
                "price_std": df["price"].std()
            }
            
        except Exception as e:
            logger.error(f"Error aggregating trades: {e}")
            return {}
    
    def calculate_orderbook_metrics(self, orderbook: NormalizedOrderBook, levels: int = 10) -> Dict[str, Any]:
        """Calculate orderbook imbalance and other metrics"""
        try:
            # Get top N levels
            top_bids = orderbook.bids[:levels]
            top_asks = orderbook.asks[:levels]
            
            # Calculate total bid/ask volume
            bid_volume = sum(size for _, size in top_bids)
            ask_volume = sum(size for _, size in top_asks)
            
            # Calculate orderbook imbalance
            if (bid_volume + ask_volume) > 0:
                imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
            else:
                imbalance = 0
            
            # Calculate weighted mid price
            if top_bids and top_asks:
                best_bid_price, best_bid_size = top_bids[0]
                best_ask_price, best_ask_size = top_asks[0]
                weighted_mid = (
                    (best_bid_price * best_ask_size + best_ask_price * best_bid_size) /
                    (best_bid_size + best_ask_size)
                )
            else:
                weighted_mid = orderbook.get_mid_price()
            
            return {
                "mid_price": orderbook.get_mid_price(),
                "weighted_mid_price": weighted_mid,
                "spread": orderbook.get_spread(),
                "spread_pct": orderbook.get_spread_percentage(),
                "bid_volume": bid_volume,
                "ask_volume": ask_volume,
                "imbalance": imbalance,
                "bid_levels": len(top_bids),
                "ask_levels": len(top_asks)
            }
            
        except Exception as e:
            logger.error(f"Error calculating orderbook metrics: {e}")
            return {}
    
    def get_market_depth(self, orderbook: NormalizedOrderBook, price_levels: List[float] = None) -> Dict[str, Any]:
        """Calculate market depth at specific price levels"""
        if price_levels is None:
            # Default to 0.1%, 0.5%, 1% from mid price
            mid_price = orderbook.get_mid_price()
            if mid_price > 0:
                price_levels = [0.001, 0.005, 0.01]
            else:
                return {}
        
        try:
            mid_price = orderbook.get_mid_price()
            depth = {}
            
            for level in price_levels:
                bid_threshold = mid_price * (1 - level)
                ask_threshold = mid_price * (1 + level)
                
                bid_depth = sum(
                    size for price, size in orderbook.bids
                    if price >= bid_threshold
                )
                ask_depth = sum(
                    size for price, size in orderbook.asks
                    if price <= ask_threshold
                )
                
                depth[f"bid_depth_{level*100:.1f}%"] = bid_depth
                depth[f"ask_depth_{level*100:.1f}%"] = ask_depth
                depth[f"total_depth_{level*100:.1f}%"] = bid_depth + ask_depth
            
            return depth
            
        except Exception as e:
            logger.error(f"Error calculating market depth: {e}")
            return {}
    
    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Safely convert value to float"""
        try:
            if value is None:
                return default
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def _safe_int(self, value: Any, default: int = 0) -> int:
        """Safely convert value to int"""
        try:
            if value is None:
                return default
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get normalizer statistics"""
        self.statistics["last_update"] = datetime.now(timezone.utc).isoformat()
        return self.statistics
    
    def clear_buffer(self):
        """Clear data buffer"""
        self.data_buffer = {
            "tickers": {},
            "orderbooks": {},
            "trades": deque(maxlen=10000),
            "klines": {}
        }
        logger.info("Data buffer cleared")