"""
Cross-Exchange and Perpetual-Spot Arbitrage
Advanced arbitrage strategies for funding rate optimization
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class ArbitrageOpportunity:
    """Arbitrage opportunity details"""
    type: str  # perp_spot, cross_exchange, funding_diff
    symbol: str
    exchange_a: str
    exchange_b: str
    price_a: float
    price_b: float
    spread: float  # Price difference
    spread_pct: float  # Percentage spread
    funding_rate_a: float
    funding_rate_b: float
    estimated_profit: float
    confidence: float  # 0-100
    expires_at: datetime

@dataclass
class HedgedPosition:
    """Hedged position across markets"""
    id: str
    symbol: str
    perp_position: Dict[str, Any]
    spot_position: Dict[str, Any]
    entry_spread: float
    current_spread: float
    accumulated_funding: float
    unrealized_pnl: float
    created_at: datetime

class CrossExchangeArbitrage:
    """Cross-exchange and market arbitrage strategies"""
    
    def __init__(self, exchanges: Dict[str, Any]):
        """
        Initialize Cross-Exchange Arbitrage
        
        Args:
            exchanges: Dictionary of exchange clients
        """
        self.exchanges = exchanges
        self.opportunities = []
        self.positions: Dict[str, HedgedPosition] = {}
        self.monitoring = False
        
        self.config = {
            "min_spread_pct": 0.1,  # 0.1% minimum spread
            "max_position_size": 10000,  # USD
            "confidence_threshold": 70,  # Minimum confidence
            "max_positions": 10,
            "use_maker_orders": True,
            "slippage_tolerance": 0.05  # 0.05%
        }
        
        self.statistics = {
            "opportunities_found": 0,
            "positions_opened": 0,
            "total_profit": 0,
            "best_spread_captured": 0,
            "avg_holding_time": timedelta()
        }
    
    async def scan_arbitrage_opportunities(self) -> List[ArbitrageOpportunity]:
        """
        Scan for arbitrage opportunities across exchanges
        
        Returns:
            List of arbitrage opportunities
        """
        opportunities = []
        
        try:
            # Get common symbols across exchanges
            common_symbols = await self._get_common_symbols()
            
            for symbol in common_symbols:
                # Check perpetual vs spot arbitrage
                perp_spot_opp = await self._check_perp_spot_arbitrage(symbol)
                if perp_spot_opp:
                    opportunities.append(perp_spot_opp)
                
                # Check cross-exchange arbitrage
                cross_opp = await self._check_cross_exchange_arbitrage(symbol)
                if cross_opp:
                    opportunities.extend(cross_opp)
                
                # Check funding rate differentials
                funding_opp = await self._check_funding_differentials(symbol)
                if funding_opp:
                    opportunities.append(funding_opp)
            
            # Sort by estimated profit
            opportunities.sort(key=lambda x: x.estimated_profit, reverse=True)
            
            self.opportunities = opportunities
            self.statistics["opportunities_found"] += len(opportunities)
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error scanning arbitrage: {e}")
            return []
    
    async def _check_perp_spot_arbitrage(self, symbol: str) -> Optional[ArbitrageOpportunity]:
        """Check for perpetual vs spot arbitrage"""
        try:
            # Get perpetual price
            perp_ticker = await self.exchanges["bybit_perp"].get_tickers(
                category="linear",
                symbol=f"{symbol}USDT"
            )
            
            if not perp_ticker["result"]["list"]:
                return None
            
            perp_price = float(perp_ticker["result"]["list"][0]["lastPrice"])
            
            # Get spot price
            spot_ticker = await self.exchanges["bybit_spot"].get_tickers(
                category="spot",
                symbol=f"{symbol}USDT"
            )
            
            if not spot_ticker["result"]["list"]:
                return None
            
            spot_price = float(spot_ticker["result"]["list"][0]["lastPrice"])
            
            # Calculate spread
            spread = perp_price - spot_price
            spread_pct = (spread / spot_price) * 100
            
            # Get funding rate
            funding_info = await self.exchanges["bybit_perp"].get_funding_rate_history(
                category="linear",
                symbol=f"{symbol}USDT",
                limit=1
            )
            
            funding_rate = 0
            if funding_info["result"]["list"]:
                funding_rate = float(funding_info["result"]["list"][0]["fundingRate"])
            
            # Check if profitable
            if abs(spread_pct) > self.config["min_spread_pct"]:
                # Estimate profit (simplified)
                position_size = min(self.config["max_position_size"], 1000)
                
                # Profit from spread convergence + funding collection
                spread_profit = abs(spread) * (position_size / perp_price)
                funding_profit = abs(funding_rate) * position_size * 3  # Daily funding
                estimated_profit = spread_profit + funding_profit
                
                # Calculate confidence based on spread size and volume
                confidence = min(100, 50 + abs(spread_pct) * 10)
                
                return ArbitrageOpportunity(
                    type="perp_spot",
                    symbol=symbol,
                    exchange_a="bybit_perp",
                    exchange_b="bybit_spot",
                    price_a=perp_price,
                    price_b=spot_price,
                    spread=spread,
                    spread_pct=spread_pct,
                    funding_rate_a=funding_rate,
                    funding_rate_b=0,  # Spot has no funding
                    estimated_profit=estimated_profit,
                    confidence=confidence,
                    expires_at=datetime.now() + timedelta(minutes=5)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking perp-spot arbitrage: {e}")
            return None
    
    async def _check_cross_exchange_arbitrage(self, symbol: str) -> List[ArbitrageOpportunity]:
        """Check for arbitrage across different exchanges"""
        opportunities = []
        
        try:
            prices = {}
            
            # Get prices from all exchanges
            for exchange_name, client in self.exchanges.items():
                try:
                    ticker = await client.get_tickers(
                        category="linear" if "perp" in exchange_name else "spot",
                        symbol=f"{symbol}USDT"
                    )
                    
                    if ticker["result"]["list"]:
                        prices[exchange_name] = float(ticker["result"]["list"][0]["lastPrice"])
                except:
                    continue
            
            # Compare all price pairs
            exchanges = list(prices.keys())
            for i in range(len(exchanges)):
                for j in range(i + 1, len(exchanges)):
                    ex_a = exchanges[i]
                    ex_b = exchanges[j]
                    
                    price_a = prices[ex_a]
                    price_b = prices[ex_b]
                    
                    spread = abs(price_a - price_b)
                    spread_pct = (spread / min(price_a, price_b)) * 100
                    
                    if spread_pct > self.config["min_spread_pct"]:
                        # Estimate profit
                        position_size = min(self.config["max_position_size"], 1000)
                        estimated_profit = spread * (position_size / max(price_a, price_b))
                        
                        opportunities.append(ArbitrageOpportunity(
                            type="cross_exchange",
                            symbol=symbol,
                            exchange_a=ex_a,
                            exchange_b=ex_b,
                            price_a=price_a,
                            price_b=price_b,
                            spread=spread,
                            spread_pct=spread_pct,
                            funding_rate_a=0,
                            funding_rate_b=0,
                            estimated_profit=estimated_profit,
                            confidence=60 + spread_pct * 5,
                            expires_at=datetime.now() + timedelta(minutes=1)
                        ))
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error checking cross-exchange arbitrage: {e}")
            return []
    
    async def _check_funding_differentials(self, symbol: str) -> Optional[ArbitrageOpportunity]:
        """Check for funding rate differentials"""
        try:
            funding_rates = {}
            
            # Get funding rates from perpetual exchanges
            for exchange_name, client in self.exchanges.items():
                if "perp" in exchange_name:
                    try:
                        funding_info = await client.get_funding_rate_history(
                            category="linear",
                            symbol=f"{symbol}USDT",
                            limit=1
                        )
                        
                        if funding_info["result"]["list"]:
                            funding_rates[exchange_name] = float(
                                funding_info["result"]["list"][0]["fundingRate"]
                            )
                    except:
                        continue
            
            if len(funding_rates) < 2:
                return None
            
            # Find maximum differential
            max_rate = max(funding_rates.values())
            min_rate = min(funding_rates.values())
            differential = max_rate - min_rate
            
            # Check if significant differential
            if abs(differential) > 0.0001:  # 0.01% differential
                max_exchange = max(funding_rates, key=funding_rates.get)
                min_exchange = min(funding_rates, key=funding_rates.get)
                
                # Estimate profit from funding differential
                position_size = self.config["max_position_size"]
                daily_profit = position_size * abs(differential) * 3  # 3 funding periods
                
                return ArbitrageOpportunity(
                    type="funding_diff",
                    symbol=symbol,
                    exchange_a=max_exchange,
                    exchange_b=min_exchange,
                    price_a=0,  # Will fetch when executing
                    price_b=0,
                    spread=differential,
                    spread_pct=abs(differential) * 100,
                    funding_rate_a=max_rate,
                    funding_rate_b=min_rate,
                    estimated_profit=daily_profit,
                    confidence=70,
                    expires_at=datetime.now() + timedelta(hours=8)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking funding differentials: {e}")
            return None
    
    async def execute_arbitrage(self, opportunity: ArbitrageOpportunity) -> Optional[HedgedPosition]:
        """
        Execute an arbitrage opportunity
        
        Args:
            opportunity: Arbitrage opportunity to execute
            
        Returns:
            HedgedPosition if successful
        """
        try:
            if opportunity.confidence < self.config["confidence_threshold"]:
                logger.info(f"Skipping low confidence opportunity: {opportunity.confidence}%")
                return None
            
            position_id = f"arb_{datetime.now().timestamp()}"
            
            if opportunity.type == "perp_spot":
                position = await self._execute_perp_spot_arbitrage(opportunity, position_id)
            elif opportunity.type == "cross_exchange":
                position = await self._execute_cross_exchange_arbitrage(opportunity, position_id)
            elif opportunity.type == "funding_diff":
                position = await self._execute_funding_differential(opportunity, position_id)
            else:
                return None
            
            if position:
                self.positions[position_id] = position
                self.statistics["positions_opened"] += 1
                
                if opportunity.spread_pct > self.statistics["best_spread_captured"]:
                    self.statistics["best_spread_captured"] = opportunity.spread_pct
                
                logger.info(f"Executed arbitrage: {opportunity.type} for {opportunity.symbol}")
                logger.info(f"Spread: {opportunity.spread_pct:.3f}%, Est profit: ${opportunity.estimated_profit:.2f}")
            
            return position
            
        except Exception as e:
            logger.error(f"Error executing arbitrage: {e}")
            return None
    
    async def _execute_perp_spot_arbitrage(
        self,
        opp: ArbitrageOpportunity,
        position_id: str
    ) -> Optional[HedgedPosition]:
        """Execute perpetual vs spot arbitrage"""
        try:
            position_size = min(self.config["max_position_size"], 1000)
            
            # Determine direction based on spread
            if opp.spread > 0:  # Perp > Spot
                # Short perp, buy spot
                perp_side = "Sell"
                spot_side = "Buy"
            else:  # Spot > Perp
                # Long perp, sell spot (if possible)
                perp_side = "Buy"
                spot_side = "Sell"
            
            # Execute perpetual order
            perp_order = await self.exchanges["bybit_perp"].place_order(
                category="linear",
                symbol=f"{opp.symbol}USDT",
                side=perp_side,
                orderType="Limit" if self.config["use_maker_orders"] else "Market",
                qty=str(position_size / opp.price_a),
                price=str(opp.price_a) if self.config["use_maker_orders"] else None,
                timeInForce="PostOnly" if self.config["use_maker_orders"] else "IOC"
            )
            
            if perp_order["retCode"] != 0:
                logger.error(f"Failed to place perp order: {perp_order}")
                return None
            
            # Execute spot order
            spot_order = await self.exchanges["bybit_spot"].place_order(
                category="spot",
                symbol=f"{opp.symbol}USDT",
                side=spot_side,
                orderType="Limit" if self.config["use_maker_orders"] else "Market",
                qty=str(position_size / opp.price_b),
                price=str(opp.price_b) if self.config["use_maker_orders"] else None,
                timeInForce="PostOnly" if self.config["use_maker_orders"] else "IOC"
            )
            
            if spot_order["retCode"] != 0:
                logger.error(f"Failed to place spot order: {spot_order}")
                # Reverse perp order
                await self._reverse_order(
                    self.exchanges["bybit_perp"],
                    f"{opp.symbol}USDT",
                    perp_side,
                    position_size / opp.price_a
                )
                return None
            
            return HedgedPosition(
                id=position_id,
                symbol=opp.symbol,
                perp_position={
                    "side": perp_side,
                    "size": position_size / opp.price_a,
                    "entry_price": opp.price_a,
                    "order_id": perp_order["result"]["orderId"]
                },
                spot_position={
                    "side": spot_side,
                    "size": position_size / opp.price_b,
                    "entry_price": opp.price_b,
                    "order_id": spot_order["result"]["orderId"]
                },
                entry_spread=opp.spread,
                current_spread=opp.spread,
                accumulated_funding=0,
                unrealized_pnl=0,
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error executing perp-spot arbitrage: {e}")
            return None
    
    async def _execute_cross_exchange_arbitrage(
        self,
        opp: ArbitrageOpportunity,
        position_id: str
    ) -> Optional[HedgedPosition]:
        """Execute cross-exchange arbitrage"""
        # Implementation would be similar to perp-spot but across different exchanges
        # This is a placeholder for the concept
        logger.info(f"Cross-exchange arbitrage execution for {opp.symbol}")
        return None
    
    async def _execute_funding_differential(
        self,
        opp: ArbitrageOpportunity,
        position_id: str
    ) -> Optional[HedgedPosition]:
        """Execute funding rate differential arbitrage"""
        # Short on high funding exchange, long on low funding exchange
        logger.info(f"Funding differential arbitrage for {opp.symbol}")
        return None
    
    async def _reverse_order(self, client, symbol: str, side: str, quantity: float):
        """Reverse an order in case of failure"""
        try:
            reverse_side = "Buy" if side == "Sell" else "Sell"
            await client.place_order(
                category="linear",
                symbol=symbol,
                side=reverse_side,
                orderType="Market",
                qty=str(quantity),
                timeInForce="IOC",
                reduceOnly=True
            )
        except Exception as e:
            logger.error(f"Error reversing order: {e}")
    
    async def close_position(self, position_id: str) -> bool:
        """
        Close an arbitrage position
        
        Args:
            position_id: Position ID to close
            
        Returns:
            Success status
        """
        try:
            if position_id not in self.positions:
                return False
            
            position = self.positions[position_id]
            
            # Close perpetual position
            perp_close_side = "Buy" if position.perp_position["side"] == "Sell" else "Sell"
            perp_close = await self.exchanges["bybit_perp"].place_order(
                category="linear",
                symbol=f"{position.symbol}USDT",
                side=perp_close_side,
                orderType="Market",
                qty=str(position.perp_position["size"]),
                timeInForce="IOC",
                reduceOnly=True
            )
            
            # Close spot position
            spot_close_side = "Sell" if position.spot_position["side"] == "Buy" else "Buy"
            spot_close = await self.exchanges["bybit_spot"].place_order(
                category="spot",
                symbol=f"{position.symbol}USDT",
                side=spot_close_side,
                orderType="Market",
                qty=str(position.spot_position["size"]),
                timeInForce="IOC"
            )
            
            # Calculate final P&L
            # This would need actual fill prices from the orders
            position.unrealized_pnl = self._calculate_pnl(position)
            
            self.statistics["total_profit"] += position.unrealized_pnl
            
            # Remove position
            del self.positions[position_id]
            
            logger.info(f"Closed arbitrage position {position_id}: PnL=${position.unrealized_pnl:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False
    
    def _calculate_pnl(self, position: HedgedPosition) -> float:
        """Calculate P&L for a hedged position"""
        # Simplified P&L calculation
        # Would need actual exit prices in production
        pnl = 0
        
        # Add spread capture profit
        pnl += abs(position.entry_spread) * min(
            position.perp_position["size"],
            position.spot_position["size"]
        )
        
        # Add accumulated funding
        pnl += position.accumulated_funding
        
        return pnl
    
    async def _get_common_symbols(self) -> List[str]:
        """Get symbols available on all exchanges"""
        # Simplified - return major pairs
        return ["BTC", "ETH", "SOL", "AVAX", "MATIC"]
    
    async def monitor_positions(self):
        """Monitor and manage open positions"""
        while self.monitoring:
            try:
                for position_id, position in list(self.positions.items()):
                    # Update current spread
                    perp_price = await self._get_current_price(
                        self.exchanges["bybit_perp"],
                        f"{position.symbol}USDT",
                        "linear"
                    )
                    
                    spot_price = await self._get_current_price(
                        self.exchanges["bybit_spot"],
                        f"{position.symbol}USDT",
                        "spot"
                    )
                    
                    if perp_price and spot_price:
                        position.current_spread = perp_price - spot_price
                        
                        # Check if spread has converged enough to close
                        if abs(position.current_spread) < abs(position.entry_spread) * 0.2:
                            # Spread has converged 80%
                            await self.close_position(position_id)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring positions: {e}")
                await asyncio.sleep(30)
    
    async def _get_current_price(self, client, symbol: str, category: str) -> Optional[float]:
        """Get current price from exchange"""
        try:
            ticker = await client.get_tickers(category=category, symbol=symbol)
            if ticker["result"]["list"]:
                return float(ticker["result"]["list"][0]["lastPrice"])
            return None
        except:
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get arbitrage statistics"""
        return {
            **self.statistics,
            "active_positions": len(self.positions),
            "current_opportunities": len(self.opportunities),
            "position_details": [
                {
                    "id": pos.id,
                    "symbol": pos.symbol,
                    "entry_spread": pos.entry_spread,
                    "current_spread": pos.current_spread,
                    "pnl": pos.unrealized_pnl + pos.accumulated_funding,
                    "age": (datetime.now() - pos.created_at).total_seconds() / 60  # Minutes
                }
                for pos in self.positions.values()
            ]
        }