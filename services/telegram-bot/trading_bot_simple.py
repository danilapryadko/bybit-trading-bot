#!/usr/bin/env python3
"""
Simplified Trading Bot for Telegram Microservice
Without WebSocket dependencies - uses REST API only
"""
import os
import logging
from dataclasses import dataclass
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import asyncio

# Import modules without WebSocket dependencies
from bybit_connector import get_bybit_connector
from config import get_trading_config
from database.service import get_db_service

logger = logging.getLogger(__name__)

class TradingBot:
    """Simplified Trading Bot for Telegram service"""
    
    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = True):
        """Initialize the trading bot with REST API only"""
        self.config = get_trading_config()
        self.connector = get_bybit_connector()
        self.db = get_db_service()
        self.testnet = testnet
        self.is_running = False
        
        logger.info(f"Trading Bot initialized (REST API mode)")
        logger.info(f"Testnet: {testnet}")
        
    def start(self):
        """Start the trading bot"""
        self.is_running = True
        logger.info("✅ Trading Bot started (simplified mode)")
        return {"status": "started", "mode": "rest_api"}
        
    def stop(self):
        """Stop the trading bot"""
        self.is_running = False
        logger.info("⏸️ Trading Bot stopped")
        return {"status": "stopped"}
        
    def get_balance(self) -> float:
        """Get account balance"""
        try:
            return self.connector.get_balance()
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0.0
            
    def get_positions(self) -> List[Dict]:
        """Get open positions"""
        try:
            positions = self.connector.get_positions()
            return positions if positions else []
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
            
    def place_order(self, symbol: str, side: str, amount: float, 
                   order_type: str = "Market", price: float = None) -> Dict:
        """Place an order"""
        try:
            result = self.connector.place_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                qty=amount,
                price=price
            )
            
            # Log to database
            self.db.log_trade({
                'symbol': symbol,
                'side': side,
                'quantity': amount,
                'price': price or 0,
                'order_type': order_type,
                'timestamp': datetime.now()
            })
            
            logger.info(f"Order placed: {symbol} {side} {amount}")
            return result
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"error": str(e)}
            
    def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """Cancel an order"""
        try:
            result = self.connector.cancel_order(symbol=symbol, order_id=order_id)
            logger.info(f"Order cancelled: {order_id}")
            return result
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return {"error": str(e)}
            
    def close_position(self, symbol: str) -> Dict:
        """Close a position"""
        try:
            # Get current position
            positions = self.get_positions()
            position = next((p for p in positions if p.get('symbol') == symbol), None)
            
            if not position:
                return {"error": "Position not found"}
                
            # Place opposite order to close
            side = "Sell" if position.get('side') == "Buy" else "Buy"
            qty = abs(float(position.get('size', 0)))
            
            if qty > 0:
                result = self.place_order(symbol, side, qty, "Market")
                logger.info(f"Position closed: {symbol}")
                return result
            else:
                return {"error": "Position size is 0"}
                
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {"error": str(e)}
            
    def get_market_data(self, symbol: str) -> Dict:
        """Get market data for a symbol"""
        try:
            ticker = self.connector.client.Market.Market_symbolInfo(symbol=symbol).result()
            return ticker[0]['result'][0] if ticker[0]['result'] else {}
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return {}
            
    def get_account_info(self) -> Dict:
        """Get account information"""
        try:
            balance = self.get_balance()
            positions = self.get_positions()
            
            total_pnl = sum(float(p.get('unrealisedPnl', 0)) for p in positions)
            
            return {
                "balance": balance,
                "positions_count": len(positions),
                "total_unrealized_pnl": total_pnl,
                "is_running": self.is_running,
                "mode": "rest_api",
                "testnet": self.testnet
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {
                "balance": 0,
                "positions_count": 0,
                "total_unrealized_pnl": 0,
                "is_running": self.is_running,
                "error": str(e)
            }
            
    def get_trading_history(self, limit: int = 50) -> List[Dict]:
        """Get trading history"""
        try:
            trades = self.db.get_recent_trades(limit=limit)
            return trades
        except Exception as e:
            logger.error(f"Error getting trading history: {e}")
            return []
            
    def run_strategy(self, strategy_name: str, params: Dict = None) -> Dict:
        """Run a trading strategy (simplified)"""
        try:
            logger.info(f"Running strategy: {strategy_name} with params: {params}")
            
            # Simple strategy implementation
            if strategy_name == "test":
                return {"status": "success", "message": "Test strategy executed"}
            else:
                return {"status": "error", "message": f"Strategy {strategy_name} not implemented"}
                
        except Exception as e:
            logger.error(f"Error running strategy: {e}")
            return {"status": "error", "message": str(e)}
            
    def get_status(self) -> Dict:
        """Get bot status"""
        return {
            "is_running": self.is_running,
            "testnet": self.testnet,
            "mode": "rest_api",
            "simplified": True,
            "timestamp": datetime.now().isoformat()
        }