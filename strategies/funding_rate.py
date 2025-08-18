"""
Funding Rate Arbitrage Strategy
Captures funding payments through market-neutral positions
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class FundingDirection(Enum):
    LONG = "long"  # Collect funding (negative rate)
    SHORT = "short"  # Pay funding (positive rate)
    NEUTRAL = "neutral"  # No position

class ArbitrageType(Enum):
    PERP_SPOT = "perp_spot"  # Perpetual vs Spot arbitrage
    CROSS_EXCHANGE = "cross_exchange"  # Cross-exchange arbitrage
    MULTI_ASSET = "multi_asset"  # Multiple asset arbitrage
    CALENDAR = "calendar"  # Calendar spread arbitrage

@dataclass
class FundingPosition:
    """Funding rate position"""
    symbol: str
    side: str  # Long or Short
    size: float
    entry_price: float
    current_funding_rate: float
    next_funding_time: datetime
    accumulated_funding: float = 0.0
    pnl: float = 0.0
    hedge_position: Optional[Dict] = None

@dataclass
class FundingConfig:
    """Funding strategy configuration"""
    symbols: List[str]
    min_funding_rate: float = 0.01  # 1% minimum to enter
    max_position_size: float = 10000  # Maximum position in USD
    use_spot_hedge: bool = True  # Hedge with spot
    auto_close_threshold: float = -0.005  # Close if rate goes negative
    funding_collection_times: List[int] = None  # UTC hours [0, 8, 16]
    max_positions: int = 5
    risk_limit: float = 0.1  # 10% of capital

class FundingRateStrategy:
    """Advanced funding rate arbitrage strategy"""
    
    def __init__(self, perp_client, spot_client=None):
        """
        Initialize Funding Rate Strategy
        
        Args:
            perp_client: Perpetual trading client
            spot_client: Spot trading client for hedging
        """
        self.perp_client = perp_client
        self.spot_client = spot_client
        self.positions: Dict[str, FundingPosition] = {}
        self.funding_history = []
        self.total_collected = 0.0
        self.active = False
        
        # Default funding times (UTC)
        self.funding_times = [0, 8, 16]
        
        self.statistics = {
            "total_collected": 0,
            "total_paid": 0,
            "net_funding": 0,
            "positions_opened": 0,
            "positions_closed": 0,
            "avg_funding_rate": 0,
            "best_rate_captured": 0
        }
    
    async def analyze_funding_rates(self) -> List[Dict[str, Any]]:
        """
        Analyze funding rates across all symbols
        
        Returns:
            List of funding opportunities
        """
        opportunities = []
        
        try:
            # Get all perpetual instruments
            instruments = await self.perp_client.get_instruments_info(
                category="linear"
            )
            
            if instruments["retCode"] != 0:
                return opportunities
            
            for instrument in instruments["result"]["list"]:
                symbol = instrument["symbol"]
                
                # Get funding rate
                funding_info = await self.perp_client.get_funding_rate_history(
                    category="linear",
                    symbol=symbol,
                    limit=1
                )
                
                if funding_info["retCode"] == 0 and funding_info["result"]["list"]:
                    current_rate = float(funding_info["result"]["list"][0]["fundingRate"])
                    
                    # Calculate annualized rate (funding every 8 hours)
                    annual_rate = current_rate * 3 * 365 * 100  # Percentage
                    
                    opportunity = {
                        "symbol": symbol,
                        "funding_rate": current_rate,
                        "annual_rate": annual_rate,
                        "next_funding": self._get_next_funding_time(),
                        "direction": self._determine_direction(current_rate),
                        "score": self._calculate_opportunity_score(current_rate, instrument)
                    }
                    
                    opportunities.append(opportunity)
            
            # Sort by score (best opportunities first)
            opportunities.sort(key=lambda x: x["score"], reverse=True)
            
            return opportunities[:10]  # Top 10 opportunities
            
        except Exception as e:
            logger.error(f"Error analyzing funding rates: {e}")
            return opportunities
    
    def _determine_direction(self, funding_rate: float) -> FundingDirection:
        """Determine position direction based on funding rate"""
        if funding_rate > 0.0005:  # Positive rate > 0.05%
            return FundingDirection.SHORT  # Collect funding by shorting
        elif funding_rate < -0.0005:  # Negative rate < -0.05%
            return FundingDirection.LONG  # Collect funding by longing
        else:
            return FundingDirection.NEUTRAL
    
    def _calculate_opportunity_score(self, funding_rate: float, instrument: Dict) -> float:
        """Calculate opportunity score for ranking"""
        score = 0.0
        
        # Base score from funding rate magnitude
        score += abs(funding_rate) * 1000
        
        # Bonus for high volume (liquidity)
        volume = float(instrument.get("volume24h", 0))
        if volume > 1000000:  # $1M+ volume
            score += 10
        
        # Penalty for low liquidity
        if volume < 100000:  # Less than $100k volume
            score -= 20
        
        # Bonus for major pairs
        if "BTC" in instrument["symbol"] or "ETH" in instrument["symbol"]:
            score += 5
        
        return score
    
    async def open_funding_position(
        self,
        symbol: str,
        funding_rate: float,
        size: float,
        use_hedge: bool = True
    ) -> Optional[FundingPosition]:
        """
        Open a position to capture funding
        
        Args:
            symbol: Trading symbol
            funding_rate: Current funding rate
            size: Position size in USD
            use_hedge: Whether to hedge with spot
            
        Returns:
            FundingPosition object or None
        """
        try:
            direction = self._determine_direction(funding_rate)
            
            if direction == FundingDirection.NEUTRAL:
                logger.info(f"Funding rate {funding_rate} too low for {symbol}")
                return None
            
            # Determine position side
            side = "Sell" if direction == FundingDirection.SHORT else "Buy"
            
            # Place perpetual position
            perp_order = await self.perp_client.place_order(
                category="linear",
                symbol=symbol,
                side=side,
                orderType="Market",
                qty=str(size),
                timeInForce="IOC"
            )
            
            if perp_order["retCode"] != 0:
                logger.error(f"Failed to open perpetual position: {perp_order}")
                return None
            
            entry_price = float(perp_order["result"]["avgPrice"])
            
            # Create position object
            position = FundingPosition(
                symbol=symbol,
                side=side,
                size=size,
                entry_price=entry_price,
                current_funding_rate=funding_rate,
                next_funding_time=self._get_next_funding_time()
            )
            
            # Open hedge position if requested
            if use_hedge and self.spot_client:
                hedge = await self._open_spot_hedge(symbol, side, size, entry_price)
                position.hedge_position = hedge
            
            # Store position
            self.positions[symbol] = position
            self.statistics["positions_opened"] += 1
            
            logger.info(f"Opened funding position: {symbol} {side} {size} @ {entry_price}")
            logger.info(f"Expected funding: {funding_rate * size:.2f} USDT")
            
            return position
            
        except Exception as e:
            logger.error(f"Error opening funding position: {e}")
            return None
    
    async def _open_spot_hedge(
        self,
        symbol: str,
        perp_side: str,
        size: float,
        price: float
    ) -> Optional[Dict]:
        """Open spot hedge position"""
        try:
            # Convert symbol (remove USDT for spot)
            spot_symbol = symbol.replace("USDT", "") + "USDT"
            
            # Opposite side for hedge
            spot_side = "Buy" if perp_side == "Sell" else "Sell"
            
            # Calculate quantity
            quantity = size / price
            
            # Place spot order
            spot_order = await self.spot_client.place_order(
                category="spot",
                symbol=spot_symbol,
                side=spot_side,
                orderType="Market",
                qty=str(quantity),
                timeInForce="IOC"
            )
            
            if spot_order["retCode"] == 0:
                return {
                    "symbol": spot_symbol,
                    "side": spot_side,
                    "quantity": quantity,
                    "price": float(spot_order["result"]["avgPrice"])
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error opening spot hedge: {e}")
            return None
    
    async def close_funding_position(self, symbol: str) -> bool:
        """
        Close a funding position
        
        Args:
            symbol: Position symbol to close
            
        Returns:
            Success status
        """
        try:
            if symbol not in self.positions:
                logger.warning(f"No position found for {symbol}")
                return False
            
            position = self.positions[symbol]
            
            # Close perpetual position
            close_side = "Buy" if position.side == "Sell" else "Sell"
            
            perp_close = await self.perp_client.place_order(
                category="linear",
                symbol=symbol,
                side=close_side,
                orderType="Market",
                qty=str(position.size),
                timeInForce="IOC",
                reduceOnly=True
            )
            
            if perp_close["retCode"] != 0:
                logger.error(f"Failed to close perpetual: {perp_close}")
                return False
            
            close_price = float(perp_close["result"]["avgPrice"])
            
            # Calculate P&L
            if position.side == "Buy":
                position.pnl = (close_price - position.entry_price) * position.size
            else:
                position.pnl = (position.entry_price - close_price) * position.size
            
            # Add funding collected
            position.pnl += position.accumulated_funding
            
            # Close hedge if exists
            if position.hedge_position and self.spot_client:
                await self._close_spot_hedge(position.hedge_position)
            
            # Update statistics
            self.statistics["positions_closed"] += 1
            self.statistics["net_funding"] += position.accumulated_funding
            
            # Store in history
            self.funding_history.append({
                "symbol": symbol,
                "closed_at": datetime.now(),
                "pnl": position.pnl,
                "funding_collected": position.accumulated_funding
            })
            
            # Remove from active positions
            del self.positions[symbol]
            
            logger.info(f"Closed funding position {symbol}: PnL=${position.pnl:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error closing funding position: {e}")
            return False
    
    async def _close_spot_hedge(self, hedge: Dict) -> bool:
        """Close spot hedge position"""
        try:
            close_side = "Sell" if hedge["side"] == "Buy" else "Buy"
            
            spot_close = await self.spot_client.place_order(
                category="spot",
                symbol=hedge["symbol"],
                side=close_side,
                orderType="Market",
                qty=str(hedge["quantity"]),
                timeInForce="IOC"
            )
            
            return spot_close["retCode"] == 0
            
        except Exception as e:
            logger.error(f"Error closing spot hedge: {e}")
            return False
    
    async def collect_funding_payments(self):
        """Collect funding payments for all positions"""
        try:
            current_time = datetime.now()
            
            for symbol, position in self.positions.items():
                # Check if funding time has passed
                if current_time >= position.next_funding_time:
                    # Get actual funding payment
                    funding_payment = await self._get_funding_payment(
                        symbol,
                        position.size,
                        position.side
                    )
                    
                    position.accumulated_funding += funding_payment
                    self.total_collected += funding_payment
                    
                    # Update statistics
                    if funding_payment > 0:
                        self.statistics["total_collected"] += funding_payment
                    else:
                        self.statistics["total_paid"] += abs(funding_payment)
                    
                    # Update next funding time
                    position.next_funding_time = self._get_next_funding_time()
                    
                    logger.info(f"Collected funding for {symbol}: ${funding_payment:.4f}")
                    
                    # Check if should close position
                    await self._check_position_exit(symbol, position)
            
        except Exception as e:
            logger.error(f"Error collecting funding payments: {e}")
    
    async def _get_funding_payment(self, symbol: str, size: float, side: str) -> float:
        """Calculate actual funding payment"""
        try:
            # Get current funding rate
            funding_info = await self.perp_client.get_funding_rate_history(
                category="linear",
                symbol=symbol,
                limit=1
            )
            
            if funding_info["retCode"] == 0 and funding_info["result"]["list"]:
                funding_rate = float(funding_info["result"]["list"][0]["fundingRate"])
                
                # Calculate payment
                # Positive rate: longs pay shorts
                # Negative rate: shorts pay longs
                if side == "Buy":  # Long position
                    payment = -funding_rate * size  # Pay if positive, receive if negative
                else:  # Short position
                    payment = funding_rate * size  # Receive if positive, pay if negative
                
                return payment
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting funding payment: {e}")
            return 0.0
    
    async def _check_position_exit(self, symbol: str, position: FundingPosition):
        """Check if position should be closed"""
        try:
            # Get current funding rate
            funding_info = await self.perp_client.get_funding_rate_history(
                category="linear",
                symbol=symbol,
                limit=1
            )
            
            if funding_info["retCode"] == 0 and funding_info["result"]["list"]:
                current_rate = float(funding_info["result"]["list"][0]["fundingRate"])
                
                # Close if rate has flipped significantly
                if position.side == "Sell" and current_rate < -0.0001:
                    # Was collecting positive funding, now would pay
                    await self.close_funding_position(symbol)
                    logger.info(f"Closed {symbol}: funding rate flipped negative")
                    
                elif position.side == "Buy" and current_rate > 0.0001:
                    # Was collecting negative funding, now would pay
                    await self.close_funding_position(symbol)
                    logger.info(f"Closed {symbol}: funding rate flipped positive")
                    
        except Exception as e:
            logger.error(f"Error checking position exit: {e}")
    
    def _get_next_funding_time(self) -> datetime:
        """Get next funding payment time"""
        now = datetime.now()
        current_hour = now.hour
        
        # Find next funding hour
        for funding_hour in self.funding_times:
            if funding_hour > current_hour:
                next_time = now.replace(hour=funding_hour, minute=0, second=0, microsecond=0)
                return next_time
        
        # Next day's first funding time
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=self.funding_times[0], minute=0, second=0, microsecond=0)
    
    async def start_strategy(self, config: FundingConfig):
        """Start the funding rate strategy"""
        try:
            self.active = True
            self.config = config
            
            if config.funding_collection_times:
                self.funding_times = config.funding_collection_times
            
            logger.info("Starting funding rate strategy")
            logger.info(f"Monitoring {len(config.symbols)} symbols")
            logger.info(f"Min rate threshold: {config.min_funding_rate * 100}%")
            
            while self.active:
                # Analyze opportunities
                opportunities = await self.analyze_funding_rates()
                
                # Open new positions for best opportunities
                for opp in opportunities[:config.max_positions - len(self.positions)]:
                    if abs(opp["funding_rate"]) >= config.min_funding_rate:
                        await self.open_funding_position(
                            opp["symbol"],
                            opp["funding_rate"],
                            min(config.max_position_size, 1000),  # Start small
                            use_hedge=config.use_spot_hedge
                        )
                
                # Collect funding payments
                await self.collect_funding_payments()
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
        except Exception as e:
            logger.error(f"Error in funding strategy: {e}")
        finally:
            await self.stop_strategy()
    
    async def stop_strategy(self):
        """Stop the funding rate strategy"""
        self.active = False
        
        logger.info("Stopping funding rate strategy...")
        
        # Close all positions
        symbols = list(self.positions.keys())
        for symbol in symbols:
            await self.close_funding_position(symbol)
        
        # Log final statistics
        logger.info(f"Total funding collected: ${self.statistics['total_collected']:.2f}")
        logger.info(f"Total funding paid: ${self.statistics['total_paid']:.2f}")
        logger.info(f"Net funding P&L: ${self.statistics['net_funding']:.2f}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        if self.statistics["positions_opened"] > 0:
            self.statistics["avg_funding_rate"] = (
                self.statistics["net_funding"] / self.statistics["positions_opened"]
            )
        
        return {
            **self.statistics,
            "active_positions": len(self.positions),
            "position_details": [
                {
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "size": pos.size,
                    "funding_rate": pos.current_funding_rate,
                    "accumulated": pos.accumulated_funding,
                    "next_funding": pos.next_funding_time.isoformat()
                }
                for pos in self.positions.values()
            ]
        }
    
    def calculate_apr(self, funding_rate: float) -> float:
        """
        Calculate Annual Percentage Rate from funding rate
        
        Args:
            funding_rate: 8-hour funding rate
            
        Returns:
            APR as percentage
        """
        # 3 funding periods per day, 365 days per year
        daily_rate = funding_rate * 3
        annual_rate = daily_rate * 365
        return annual_rate * 100  # Convert to percentage
    
    def estimate_daily_income(self, position_size: float, funding_rate: float) -> float:
        """
        Estimate daily income from funding
        
        Args:
            position_size: Position size in USD
            funding_rate: Current funding rate
            
        Returns:
            Estimated daily income
        """
        # 3 funding payments per day
        daily_income = position_size * funding_rate * 3
        return daily_income