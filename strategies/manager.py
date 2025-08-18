"""
Strategy Manager - Handles multiple trading strategies
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd

from .base import BaseStrategy
from .rsi_strategy import RSIStrategy
from .ma_strategy import MovingAverageStrategy  
from .combined_strategy import CombinedStrategy

logger = logging.getLogger(__name__)

class StrategyManager:
    """Manages multiple trading strategies"""
    
    def __init__(self, bybit_connector=None):
        self.connector = bybit_connector
        self.strategies: Dict[str, BaseStrategy] = {}
        self.active_strategies: List[str] = []
        self.strategy_results: Dict[str, Dict] = {}
        self.is_running = False
        
        # Available strategy classes
        self.strategy_classes = {
            'RSI': RSIStrategy,
            'MA': MovingAverageStrategy,
            'Combined': CombinedStrategy
        }
        
    def create_strategy(self, name: str, strategy_type: str, symbol: str, params: Dict[str, Any] = None) -> bool:
        """Create and register a new strategy"""
        try:
            if strategy_type not in self.strategy_classes:
                logger.error(f"Unknown strategy type: {strategy_type}")
                return False
            
            if name in self.strategies:
                logger.warning(f"Strategy {name} already exists")
                return False
            
            # Create strategy instance
            strategy_class = self.strategy_classes[strategy_type]
            strategy = strategy_class(symbol, params)
            
            # Register strategy
            self.strategies[name] = strategy
            logger.info(f"Created strategy {name} of type {strategy_type} for {symbol}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating strategy: {e}")
            return False
    
    def activate_strategy(self, name: str) -> bool:
        """Activate a strategy"""
        if name not in self.strategies:
            logger.error(f"Strategy {name} not found")
            return False
        
        if name in self.active_strategies:
            logger.warning(f"Strategy {name} already active")
            return False
        
        self.active_strategies.append(name)
        self.strategies[name].is_active = True
        logger.info(f"Activated strategy {name}")
        return True
    
    def deactivate_strategy(self, name: str) -> bool:
        """Deactivate a strategy"""
        if name not in self.strategies:
            logger.error(f"Strategy {name} not found")
            return False
        
        if name not in self.active_strategies:
            logger.warning(f"Strategy {name} not active")
            return False
        
        self.active_strategies.remove(name)
        self.strategies[name].is_active = False
        logger.info(f"Deactivated strategy {name}")
        return True
    
    def delete_strategy(self, name: str) -> bool:
        """Delete a strategy"""
        if name not in self.strategies:
            logger.error(f"Strategy {name} not found")
            return False
        
        # Deactivate if active
        if name in self.active_strategies:
            self.deactivate_strategy(name)
        
        del self.strategies[name]
        if name in self.strategy_results:
            del self.strategy_results[name]
        
        logger.info(f"Deleted strategy {name}")
        return True
    
    def get_market_data(self, symbol: str, interval: str = "15", limit: int = 100) -> Dict[str, Any]:
        """Get market data for analysis"""
        try:
            market_data = {}
            
            if self.connector:
                # Get klines
                klines = self.connector.get_klines(symbol, interval, limit)
                if klines:
                    market_data['klines'] = klines
                
                # Get ticker
                ticker = self.connector.get_ticker(symbol)
                if ticker:
                    market_data['ticker'] = ticker
                
                # Get current position
                positions = self.connector.get_positions()
                position = next((p for p in positions if p['symbol'] == symbol), None)
                market_data['position'] = position
                
                # Get account balance
                balance = self.connector.get_balance()
                market_data['balance'] = balance
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return {}
    
    def analyze_strategies(self, market_data: Dict[str, Any] = None) -> Dict[str, Dict]:
        """Run analysis for all active strategies"""
        results = {}
        
        for name in self.active_strategies:
            strategy = self.strategies[name]
            
            try:
                # Get market data if not provided
                if not market_data:
                    market_data = self.get_market_data(strategy.symbol)
                
                # Analyze
                signal, confidence, metadata = strategy.analyze(market_data)
                
                # Store result
                result = {
                    'name': name,
                    'type': strategy.__class__.__name__,
                    'symbol': strategy.symbol,
                    'signal': signal,
                    'confidence': confidence,
                    'metadata': metadata,
                    'timestamp': datetime.now().isoformat(),
                    'params': strategy.params
                }
                
                results[name] = result
                self.strategy_results[name] = result
                
                logger.info(f"Strategy {name}: {signal} (confidence: {confidence:.2%})")
                
            except Exception as e:
                logger.error(f"Error analyzing strategy {name}: {e}")
                results[name] = {
                    'name': name,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
        
        return results
    
    def get_consensus_signal(self, min_confidence: float = 0.5) -> Dict[str, Any]:
        """Get consensus signal from all active strategies"""
        if not self.strategy_results:
            return {'signal': 'HOLD', 'confidence': 0, 'strategies_agree': 0}
        
        buy_votes = 0
        sell_votes = 0
        hold_votes = 0
        total_confidence = 0
        
        for result in self.strategy_results.values():
            if 'error' in result:
                continue
            
            signal = result.get('signal', 'HOLD')
            confidence = result.get('confidence', 0)
            
            if confidence < min_confidence:
                hold_votes += 1
            elif signal == 'BUY':
                buy_votes += 1
                total_confidence += confidence
            elif signal == 'SELL':
                sell_votes += 1
                total_confidence += confidence
            else:
                hold_votes += 1
        
        # Determine consensus
        total_votes = buy_votes + sell_votes + hold_votes
        if total_votes == 0:
            return {'signal': 'HOLD', 'confidence': 0, 'strategies_agree': 0}
        
        if buy_votes > sell_votes and buy_votes > hold_votes:
            consensus_signal = 'BUY'
            consensus_confidence = total_confidence / buy_votes if buy_votes > 0 else 0
            strategies_agree = buy_votes
        elif sell_votes > buy_votes and sell_votes > hold_votes:
            consensus_signal = 'SELL'
            consensus_confidence = total_confidence / sell_votes if sell_votes > 0 else 0
            strategies_agree = sell_votes
        else:
            consensus_signal = 'HOLD'
            consensus_confidence = 0
            strategies_agree = hold_votes
        
        return {
            'signal': consensus_signal,
            'confidence': consensus_confidence,
            'strategies_agree': strategies_agree,
            'total_strategies': total_votes,
            'vote_distribution': {
                'buy': buy_votes,
                'sell': sell_votes,
                'hold': hold_votes
            }
        }
    
    def should_execute_trade(self, consensus: Dict[str, Any], min_strategies: int = 2) -> bool:
        """Determine if trade should be executed based on consensus"""
        if consensus['signal'] == 'HOLD':
            return False
        
        if consensus['strategies_agree'] < min_strategies:
            return False
        
        if consensus['confidence'] < 0.6:
            return False
        
        return True
    
    async def run_strategies_loop(self, interval: int = 60):
        """Run strategies in a loop"""
        self.is_running = True
        logger.info("Starting strategy manager loop")
        
        while self.is_running:
            try:
                # Analyze all strategies
                results = self.analyze_strategies()
                
                # Get consensus
                consensus = self.get_consensus_signal()
                logger.info(f"Consensus: {consensus}")
                
                # Execute trade if conditions met
                if self.connector and self.should_execute_trade(consensus):
                    await self.execute_trade(consensus)
                
                # Wait for next iteration
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in strategy loop: {e}")
                await asyncio.sleep(interval)
    
    async def execute_trade(self, consensus: Dict[str, Any]):
        """Execute trade based on consensus"""
        try:
            signal = consensus['signal']
            
            # Get representative strategy for parameters
            strategy = list(self.strategies.values())[0] if self.strategies else None
            if not strategy:
                return
            
            # Check current position
            positions = self.connector.get_positions()
            position = next((p for p in positions if p['symbol'] == strategy.symbol), None)
            
            if signal == 'BUY' and not position:
                # Place buy order
                logger.info(f"Executing BUY order for {strategy.symbol}")
                # Implementation depends on connector
                
            elif signal == 'SELL' and not position:
                # Place sell order
                logger.info(f"Executing SELL order for {strategy.symbol}")
                # Implementation depends on connector
                
            elif position:
                # Check if should close position
                for name in self.active_strategies:
                    strat = self.strategies[name]
                    market_data = self.get_market_data(strat.symbol)
                    if strat.should_exit_position(position, market_data):
                        logger.info(f"Closing position for {strat.symbol}")
                        # Close position
                        break
                        
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
    
    def stop(self):
        """Stop the strategy manager"""
        self.is_running = False
        logger.info("Strategy manager stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all strategies"""
        return {
            'is_running': self.is_running,
            'total_strategies': len(self.strategies),
            'active_strategies': self.active_strategies,
            'strategies': {
                name: {
                    'type': strategy.__class__.__name__,
                    'symbol': strategy.symbol,
                    'is_active': strategy.is_active,
                    'last_signal': strategy.last_signal,
                    'params': strategy.params
                }
                for name, strategy in self.strategies.items()
            },
            'latest_results': self.strategy_results,
            'consensus': self.get_consensus_signal() if self.strategy_results else None
        }