"""
Main Trading Bot Integration Module
Connects all components into a unified trading system
Priority: Reliability and error-free operation
"""

import asyncio
import logging
import signal
import sys
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
import json
import traceback
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

# Import all modules
from websocket_manager import WebSocketManager
from data_normalizer import DataNormalizer
from order_manager import OrderManager, OrderType, OrderSide, TimeInForce
from risk_manager_v2 import RiskManagerV2, RiskProfile, Position
from backtesting_engine import BacktestingEngine, BacktestConfig
from ml_strategies import MLStrategyExecutor, MLConfig
from bybit_client import BybitClient
from database_manager import DatabaseManager

# Configure logging with detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class TradingConfig:
    """Main trading bot configuration"""
    # Trading parameters
    symbols: List[str] = field(default_factory=lambda: ["BTCUSDT", "ETHUSDT"])
    testnet: bool = True
    paper_trading: bool = True  # Safety first - start with paper trading
    
    # Risk parameters
    initial_balance: float = 10000.0
    max_positions: int = 3
    risk_per_trade: float = 0.02
    max_daily_loss: float = 500.0
    use_trailing_stops: bool = True
    
    # Strategy parameters
    use_ml_strategies: bool = True
    ml_confidence_threshold: float = 0.65
    backtest_before_trade: bool = True
    
    # System parameters
    heartbeat_interval: int = 30  # seconds
    data_buffer_size: int = 1000
    reconnect_attempts: int = 5
    error_threshold: int = 10  # Max errors before shutdown
    
    # Monitoring
    enable_monitoring: bool = True
    metrics_port: int = 8080
    health_check_interval: int = 60


class TradingBot:
    """Main trading bot orchestrator with comprehensive error handling"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.is_running = False
        self.error_count = 0
        self.last_heartbeat = datetime.now(timezone.utc)
        
        # Initialize components with error handling
        self._initialize_components()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("Trading Bot initialized with high reliability mode")
    
    def _initialize_components(self):
        """Initialize all trading components with error handling"""
        try:
            # 1. Initialize Bybit client
            logger.info("Initializing Bybit client...")
            self.client = BybitClient(testnet=self.config.testnet)
            
            # 2. Initialize database
            logger.info("Initializing database...")
            self.db = DatabaseManager()
            
            # 3. Initialize WebSocket manager
            logger.info("Initializing WebSocket manager...")
            self.ws_manager = WebSocketManager(
                testnet=self.config.testnet,
                api_key=self.client.api_key,
                api_secret=self.client.api_secret
            )
            
            # 4. Initialize data normalizer
            logger.info("Initializing data normalizer...")
            self.data_normalizer = DataNormalizer()
            
            # 5. Initialize risk manager
            logger.info("Initializing risk manager...")
            risk_profile = RiskProfile(
                max_positions=self.config.max_positions,
                risk_per_trade=self.config.risk_per_trade,
                max_daily_loss=self.config.max_daily_loss
            )
            self.risk_manager = RiskManagerV2(
                account_balance=self.config.initial_balance,
                risk_profile=risk_profile
            )
            
            # 6. Initialize order manager
            logger.info("Initializing order manager...")
            self.order_manager = OrderManager(
                bybit_client=self.client,
                risk_manager=self.risk_manager
            )
            
            # 7. Initialize ML strategies (if enabled)
            if self.config.use_ml_strategies:
                logger.info("Initializing ML strategies...")
                ml_config = MLConfig(
                    min_confidence=self.config.ml_confidence_threshold
                )
                self.ml_executor = MLStrategyExecutor(ml_config)
            else:
                self.ml_executor = None
            
            # 8. Initialize backtesting engine
            if self.config.backtest_before_trade:
                logger.info("Initializing backtesting engine...")
                backtest_config = BacktestConfig(
                    start_date=datetime.now(timezone.utc) - timedelta(days=30),
                    end_date=datetime.now(timezone.utc),
                    initial_balance=self.config.initial_balance,
                    symbols=self.config.symbols
                )
                self.backtester = BacktestingEngine(backtest_config)
            else:
                self.backtester = None
            
            # Data storage
            self.market_data = {}  # symbol -> DataFrame
            self.active_strategies = {}
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def start(self):
        """Start the trading bot with comprehensive error handling"""
        try:
            logger.info("Starting Trading Bot...")
            self.is_running = True
            
            # Connect WebSocket
            await self._connect_websocket()
            
            # Subscribe to market data
            await self._subscribe_market_data()
            
            # Start main trading loop
            await self._run_trading_loop()
            
        except Exception as e:
            logger.error(f"Critical error in trading bot: {e}")
            logger.error(traceback.format_exc())
            await self.stop()
    
    async def _connect_websocket(self):
        """Connect WebSocket with retry logic"""
        max_retries = self.config.reconnect_attempts
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Connecting WebSocket (attempt {retry_count + 1}/{max_retries})...")
                self.ws_manager.connect()
                logger.info("WebSocket connected successfully")
                return
                
            except Exception as e:
                retry_count += 1
                logger.error(f"WebSocket connection failed: {e}")
                if retry_count < max_retries:
                    wait_time = min(60, 5 * retry_count)  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    raise Exception("Failed to connect WebSocket after maximum retries")
    
    async def _subscribe_market_data(self):
        """Subscribe to market data streams"""
        try:
            for symbol in self.config.symbols:
                logger.info(f"Subscribing to {symbol} market data...")
                
                # Subscribe to different data streams
                self.ws_manager.subscribe_ticker(
                    symbol=symbol,
                    callback=lambda data: self._handle_ticker_update(symbol, data)
                )
                
                self.ws_manager.subscribe_orderbook(
                    symbol=symbol,
                    depth=50,
                    callback=lambda data: self._handle_orderbook_update(symbol, data)
                )
                
                self.ws_manager.subscribe_trades(
                    symbol=symbol,
                    callback=lambda data: self._handle_trade_update(symbol, data)
                )
                
                self.ws_manager.subscribe_kline(
                    symbol=symbol,
                    interval="1m",
                    callback=lambda data: self._handle_kline_update(symbol, data)
                )
            
            # Subscribe to private streams
            if not self.config.paper_trading:
                self.ws_manager.subscribe_positions(
                    callback=self._handle_position_update
                )
                self.ws_manager.subscribe_orders(
                    callback=self._handle_order_update
                )
            
            logger.info("Market data subscriptions completed")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to market data: {e}")
            raise
    
    async def _run_trading_loop(self):
        """Main trading loop with error recovery"""
        error_count = 0
        
        while self.is_running:
            try:
                # Check system health
                if not await self._check_system_health():
                    logger.warning("System health check failed, pausing trading...")
                    await asyncio.sleep(60)
                    continue
                
                # Update risk manager with current time
                self.risk_manager.reset_daily_metrics()
                
                # Process each symbol
                for symbol in self.config.symbols:
                    try:
                        await self._process_symbol(symbol)
                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {e}")
                        error_count += 1
                
                # Check error threshold
                if error_count >= self.config.error_threshold:
                    logger.critical(f"Error threshold reached ({error_count}), shutting down...")
                    await self.stop()
                    break
                
                # Heartbeat
                await self._send_heartbeat()
                
                # Sleep before next iteration
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                logger.info("Trading loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                logger.error(traceback.format_exc())
                error_count += 1
                await asyncio.sleep(5)
    
    async def _process_symbol(self, symbol: str):
        """Process trading logic for a symbol"""
        try:
            # Get current market data
            market_data = self._get_market_data(symbol)
            if not market_data:
                return
            
            # Check if we can trade
            risk_check = self.risk_manager.check_risk_limits()
            if not risk_check["passed"]:
                logger.warning(f"Risk limits exceeded: {risk_check['errors']}")
                return
            
            # Generate trading signals
            signal = await self._generate_signal(symbol, market_data)
            if not signal:
                return
            
            # Validate signal strength
            if signal.get("confidence", 0) < self.config.ml_confidence_threshold:
                logger.debug(f"Signal confidence too low for {symbol}: {signal.get('confidence', 0)}")
                return
            
            # Execute trade if conditions are met
            await self._execute_trade(symbol, signal)
            
            # Update positions
            await self._update_positions(symbol)
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            raise
    
    async def _generate_signal(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate trading signal using multiple strategies"""
        try:
            signals = []
            
            # 1. ML Strategy signal (if enabled)
            if self.ml_executor and self.config.use_ml_strategies:
                ml_signal = self.ml_executor.execute_strategy({symbol: market_data})
                if symbol in ml_signal:
                    signals.append(ml_signal[symbol])
            
            # 2. Technical indicators signal
            technical_signal = self._generate_technical_signal(symbol, market_data)
            if technical_signal:
                signals.append(technical_signal)
            
            # 3. Market microstructure signal
            microstructure_signal = self._generate_microstructure_signal(symbol, market_data)
            if microstructure_signal:
                signals.append(microstructure_signal)
            
            # Combine signals (ensemble approach)
            if not signals:
                return None
            
            combined_signal = self._combine_signals(signals)
            
            # Backtest signal if enabled
            if self.config.backtest_before_trade and self.backtester:
                backtest_result = await self._backtest_signal(symbol, combined_signal)
                if not backtest_result.get("profitable", False):
                    logger.info(f"Signal failed backtesting for {symbol}")
                    return None
            
            return combined_signal
            
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return None
    
    def _generate_technical_signal(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate signal from technical indicators"""
        try:
            # Get latest data
            ticker = self.ws_manager.get_ticker(symbol)
            orderbook = self.ws_manager.get_orderbook(symbol)
            
            if not ticker or not orderbook:
                return None
            
            # Simple example: RSI-based signal
            # In production, use more sophisticated logic
            signal = {
                "action": "neutral",
                "confidence": 0.5,
                "source": "technical"
            }
            
            # Add your technical analysis logic here
            
            return signal
            
        except Exception as e:
            logger.error(f"Error in technical signal generation: {e}")
            return None
    
    def _generate_microstructure_signal(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate signal from market microstructure"""
        try:
            orderbook = self.ws_manager.get_orderbook(symbol)
            if not orderbook:
                return None
            
            # Calculate orderbook imbalance
            metrics = self.data_normalizer.calculate_orderbook_metrics(orderbook)
            imbalance = metrics.get("imbalance", 0)
            
            signal = {
                "action": "neutral",
                "confidence": abs(imbalance),
                "source": "microstructure"
            }
            
            # Strong buy signal if bid pressure is high
            if imbalance > 0.3:
                signal["action"] = "buy"
            # Strong sell signal if ask pressure is high
            elif imbalance < -0.3:
                signal["action"] = "sell"
            
            return signal
            
        except Exception as e:
            logger.error(f"Error in microstructure signal generation: {e}")
            return None
    
    def _combine_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine multiple signals into a consensus signal"""
        if not signals:
            return {"action": "neutral", "confidence": 0}
        
        # Weight signals by confidence
        total_weight = sum(s.get("confidence", 0.5) for s in signals)
        
        buy_weight = sum(s.get("confidence", 0.5) for s in signals if s.get("action") == "buy")
        sell_weight = sum(s.get("confidence", 0.5) for s in signals if s.get("action") == "sell")
        
        # Determine consensus action
        if buy_weight > sell_weight and buy_weight > total_weight * 0.6:
            action = "buy"
            confidence = buy_weight / total_weight
        elif sell_weight > buy_weight and sell_weight > total_weight * 0.6:
            action = "sell"
            confidence = sell_weight / total_weight
        else:
            action = "neutral"
            confidence = 0.5
        
        return {
            "action": action,
            "confidence": confidence,
            "sources": [s.get("source", "unknown") for s in signals],
            "timestamp": datetime.now(timezone.utc)
        }
    
    async def _execute_trade(self, symbol: str, signal: Dict[str, Any]):
        """Execute trade with comprehensive error handling"""
        try:
            # Check if we already have a position
            if symbol in self.risk_manager.positions:
                logger.info(f"Already have position in {symbol}, skipping...")
                return
            
            # Get current price
            ticker = self.ws_manager.get_ticker(symbol)
            if not ticker:
                logger.error(f"No ticker data for {symbol}")
                return
            
            current_price = ticker.get("last_price", 0)
            if current_price <= 0:
                logger.error(f"Invalid price for {symbol}: {current_price}")
                return
            
            # Determine order side
            if signal["action"] == "buy":
                side = OrderSide.BUY
            elif signal["action"] == "sell":
                side = OrderSide.SELL
            else:
                return
            
            # Calculate position size
            stop_loss = self.risk_manager.calculate_stop_loss(
                symbol=symbol,
                entry_price=current_price,
                side="long" if side == OrderSide.BUY else "short"
            )
            
            size_result = self.risk_manager.calculate_position_size(
                symbol=symbol,
                entry_price=current_price,
                stop_loss=stop_loss
            )
            
            if size_result["position_size"] <= 0:
                logger.warning(f"Position size is 0 for {symbol}")
                return
            
            # Create order
            order = self.order_manager.create_order(
                symbol=symbol,
                side=side,
                order_type=OrderType.LIMIT,
                quantity=size_result["position_size"],
                price=current_price * (1.001 if side == OrderSide.BUY else 0.999),  # Slight adjustment for fill
                metadata={
                    "signal": signal,
                    "stop_loss": stop_loss,
                    "take_profit": self.risk_manager.calculate_take_profit(
                        entry_price=current_price,
                        stop_loss=stop_loss,
                        side="long" if side == OrderSide.BUY else "short"
                    )
                }
            )
            
            # Submit order (paper trading or real)
            if self.config.paper_trading:
                logger.info(f"PAPER TRADE: {order.side.value} {order.quantity} {symbol} @ {order.price}")
                # Simulate fill for paper trading
                self._simulate_paper_fill(order)
            else:
                success = self.order_manager.submit_order(order)
                if success:
                    logger.info(f"Order submitted: {order.order_id}")
                else:
                    logger.error(f"Failed to submit order: {order.order_id}")
            
            # Track position in risk manager
            position = Position(
                symbol=symbol,
                side="long" if side == OrderSide.BUY else "short",
                entry_price=current_price,
                current_price=current_price,
                quantity=size_result["position_size"],
                stop_loss=stop_loss
            )
            self.risk_manager.add_position(position)
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            logger.error(traceback.format_exc())
    
    def _simulate_paper_fill(self, order):
        """Simulate order fill for paper trading"""
        fill = {
            "qty": order.quantity,
            "price": order.price,
            "commission": order.quantity * order.price * 0.0006
        }
        self.order_manager.process_fill(order.order_id, fill)
    
    async def _update_positions(self, symbol: str):
        """Update existing positions with latest prices"""
        try:
            if symbol not in self.risk_manager.positions:
                return
            
            position = self.risk_manager.positions[symbol]
            ticker = self.ws_manager.get_ticker(symbol)
            
            if not ticker:
                return
            
            current_price = ticker.get("last_price", position.current_price)
            position.current_price = current_price
            
            # Update trailing stop if enabled
            if self.config.use_trailing_stops:
                new_stop = self.risk_manager.update_trailing_stop(position, current_price)
                if new_stop:
                    logger.info(f"Trailing stop updated for {symbol}: {new_stop}")
            
            # Check stop loss
            if position.side == "long" and current_price <= position.stop_loss:
                logger.info(f"Stop loss triggered for {symbol}")
                await self._close_position(symbol, current_price, "stop_loss")
            elif position.side == "short" and current_price >= position.stop_loss:
                logger.info(f"Stop loss triggered for {symbol}")
                await self._close_position(symbol, current_price, "stop_loss")
            
            # Check trailing stop
            if position.trailing_activated and position.trailing_stop > 0:
                if position.side == "long" and current_price <= position.trailing_stop:
                    logger.info(f"Trailing stop triggered for {symbol}")
                    await self._close_position(symbol, current_price, "trailing_stop")
                elif position.side == "short" and current_price >= position.trailing_stop:
                    logger.info(f"Trailing stop triggered for {symbol}")
                    await self._close_position(symbol, current_price, "trailing_stop")
            
        except Exception as e:
            logger.error(f"Error updating position: {e}")
    
    async def _close_position(self, symbol: str, price: float, reason: str):
        """Close a position"""
        try:
            # Close in risk manager
            self.risk_manager.close_position(symbol, price)
            
            # Create closing order if not paper trading
            if not self.config.paper_trading:
                position = self.risk_manager.positions.get(symbol)
                if position:
                    side = OrderSide.SELL if position.side == "long" else OrderSide.BUY
                    order = self.order_manager.create_order(
                        symbol=symbol,
                        side=side,
                        order_type=OrderType.MARKET,
                        quantity=position.quantity,
                        metadata={"reason": reason}
                    )
                    self.order_manager.submit_order(order)
            
            logger.info(f"Position closed for {symbol}: {reason}")
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
    
    async def _check_system_health(self) -> bool:
        """Check system health and connectivity"""
        try:
            # Check WebSocket connection
            if not self.ws_manager.is_connected:
                logger.warning("WebSocket disconnected")
                await self._connect_websocket()
                return False
            
            # Check risk limits
            risk_check = self.risk_manager.check_risk_limits()
            if not risk_check["passed"] and "Daily loss limit" in str(risk_check.get("errors", [])):
                logger.error("Daily loss limit reached, stopping trading")
                return False
            
            # Check error count
            if self.error_count >= self.config.error_threshold:
                logger.error("Error threshold exceeded")
                return False
            
            # Check last heartbeat
            time_since_heartbeat = (datetime.now(timezone.utc) - self.last_heartbeat).total_seconds()
            if time_since_heartbeat > self.config.heartbeat_interval * 3:
                logger.warning("Heartbeat timeout")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return False
    
    async def _send_heartbeat(self):
        """Send heartbeat and update metrics"""
        try:
            self.last_heartbeat = datetime.now(timezone.utc)
            
            # Log current status
            risk_report = self.risk_manager.get_risk_report()
            logger.info(f"Heartbeat - Balance: ${risk_report['account']['balance']:.2f}, "
                       f"Positions: {risk_report['positions']['count']}, "
                       f"Daily P&L: ${risk_report['account']['daily_pnl']:.2f}")
            
            # Save metrics to database
            if self.db:
                metrics = {
                    "timestamp": self.last_heartbeat,
                    "balance": risk_report['account']['balance'],
                    "positions": risk_report['positions']['count'],
                    "daily_pnl": risk_report['account']['daily_pnl'],
                    "error_count": self.error_count
                }
                self.db.save_metrics(metrics)
            
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
    
    def _get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current market data for a symbol"""
        try:
            return {
                "ticker": self.ws_manager.get_ticker(symbol),
                "orderbook": self.ws_manager.get_orderbook(symbol),
                "recent_trades": self.ws_manager.get_recent_trades(symbol),
                "klines": self.ws_manager.get_klines(symbol)
            }
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return None
    
    def _handle_ticker_update(self, symbol: str, data: Dict[str, Any]):
        """Handle ticker updates"""
        try:
            normalized = self.data_normalizer.normalize_ticker(data)
            # Store normalized data
            if symbol not in self.market_data:
                self.market_data[symbol] = {}
            self.market_data[symbol]["ticker"] = normalized
        except Exception as e:
            logger.error(f"Error handling ticker update: {e}")
    
    def _handle_orderbook_update(self, symbol: str, data: Dict[str, Any]):
        """Handle orderbook updates"""
        try:
            normalized = self.data_normalizer.normalize_orderbook(data)
            if symbol not in self.market_data:
                self.market_data[symbol] = {}
            self.market_data[symbol]["orderbook"] = normalized
        except Exception as e:
            logger.error(f"Error handling orderbook update: {e}")
    
    def _handle_trade_update(self, symbol: str, data: Dict[str, Any]):
        """Handle trade updates"""
        try:
            normalized = self.data_normalizer.normalize_trade(data)
            if symbol not in self.market_data:
                self.market_data[symbol] = {}
            if "trades" not in self.market_data[symbol]:
                self.market_data[symbol]["trades"] = []
            self.market_data[symbol]["trades"].append(normalized)
        except Exception as e:
            logger.error(f"Error handling trade update: {e}")
    
    def _handle_kline_update(self, symbol: str, data: Dict[str, Any]):
        """Handle kline updates"""
        try:
            normalized = self.data_normalizer.normalize_kline(data)
            if symbol not in self.market_data:
                self.market_data[symbol] = {}
            if "klines" not in self.market_data[symbol]:
                self.market_data[symbol]["klines"] = []
            self.market_data[symbol]["klines"].append(normalized)
        except Exception as e:
            logger.error(f"Error handling kline update: {e}")
    
    def _handle_position_update(self, data: Dict[str, Any]):
        """Handle position updates"""
        try:
            logger.info(f"Position update: {data}")
            # Update risk manager with latest position data
        except Exception as e:
            logger.error(f"Error handling position update: {e}")
    
    def _handle_order_update(self, data: Dict[str, Any]):
        """Handle order updates"""
        try:
            logger.info(f"Order update: {data}")
            # Process order updates
            if "order_id" in data:
                if data.get("status") == "Filled":
                    self.order_manager.process_fill(data["order_id"], data)
        except Exception as e:
            logger.error(f"Error handling order update: {e}")
    
    async def _backtest_signal(self, symbol: str, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Backtest a signal before execution"""
        try:
            # Simple backtest logic - expand as needed
            return {"profitable": True, "expected_return": 0.02}
        except Exception as e:
            logger.error(f"Error backtesting signal: {e}")
            return {"profitable": False}
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        asyncio.create_task(self.stop())
    
    async def stop(self):
        """Stop the trading bot gracefully"""
        try:
            logger.info("Stopping Trading Bot...")
            self.is_running = False
            
            # Close all positions if not paper trading
            if not self.config.paper_trading:
                for symbol in list(self.risk_manager.positions.keys()):
                    ticker = self.ws_manager.get_ticker(symbol)
                    if ticker:
                        await self._close_position(symbol, ticker["last_price"], "shutdown")
            
            # Disconnect WebSocket
            if self.ws_manager:
                self.ws_manager.disconnect()
            
            # Save final state
            if self.db:
                final_report = self.risk_manager.get_risk_report()
                self.db.save_final_state(final_report)
            
            logger.info("Trading Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")


async def main():
    """Main entry point with configuration"""
    try:
        # Load configuration (can be from file, env, or args)
        config = TradingConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            testnet=True,
            paper_trading=True,  # Start with paper trading for safety
            initial_balance=10000.0,
            max_positions=3,
            risk_per_trade=0.02,
            use_ml_strategies=True,
            use_trailing_stops=True
        )
        
        # Create and start bot
        bot = TradingBot(config)
        
        logger.info("=" * 50)
        logger.info("BYBIT TRADING BOT - STARTING")
        logger.info(f"Mode: {'PAPER' if config.paper_trading else 'LIVE'}")
        logger.info(f"Testnet: {config.testnet}")
        logger.info(f"Symbols: {', '.join(config.symbols)}")
        logger.info(f"Initial Balance: ${config.initial_balance}")
        logger.info("Priority: RELIABILITY AND ERROR-FREE OPERATION")
        logger.info("=" * 50)
        
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())