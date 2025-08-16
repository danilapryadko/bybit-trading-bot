#!/usr/bin/env python3
"""
Trading Pairs Configuration
30 carefully selected pairs for algorithmic trading on Bybit
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class PairCategory(Enum):
    """Trading pair categories"""
    MAJOR = "major"           # Top cryptocurrencies
    DEFI = "defi"            # DeFi tokens
    LAYER1 = "layer1"        # Layer 1 blockchains
    LAYER2 = "layer2"        # Layer 2 solutions
    GAMING = "gaming"        # Gaming/Metaverse tokens
    AI = "ai"                # AI-related tokens
    MEME = "meme"            # Meme coins (high volatility)

@dataclass
class TradingPair:
    """Trading pair configuration"""
    symbol: str
    category: PairCategory
    min_position_size: float  # Minimum position in USDT
    max_position_size: float  # Maximum position in USDT
    default_leverage: int
    volatility_level: str     # low, medium, high, extreme
    recommended_timeframe: str # 1m, 5m, 15m, 1h, 4h
    description: str
    active: bool = True

# 30 BEST TRADING PAIRS FOR ALGORITHMIC TRADING
TRADING_PAIRS = {
    # ============= MAJOR CRYPTOCURRENCIES (High Liquidity) =============
    "BTCUSDT": TradingPair(
        symbol="BTCUSDT",
        category=PairCategory.MAJOR,
        min_position_size=10,
        max_position_size=50000,
        default_leverage=10,
        volatility_level="medium",
        recommended_timeframe="15m",
        description="Bitcoin - Most liquid, stable for algorithms"
    ),
    
    "ETHUSDT": TradingPair(
        symbol="ETHUSDT",
        category=PairCategory.MAJOR,
        min_position_size=10,
        max_position_size=30000,
        default_leverage=15,
        volatility_level="medium",
        recommended_timeframe="15m",
        description="Ethereum - High liquidity, good trends"
    ),
    
    "BNBUSDT": TradingPair(
        symbol="BNBUSDT",
        category=PairCategory.MAJOR,
        min_position_size=10,
        max_position_size=20000,
        default_leverage=10,
        volatility_level="medium",
        recommended_timeframe="15m",
        description="Binance Coin - Exchange token, stable movements"
    ),
    
    # ============= LAYER 1 BLOCKCHAINS =============
    "SOLUSDT": TradingPair(
        symbol="SOLUSDT",
        category=PairCategory.LAYER1,
        min_position_size=10,
        max_position_size=15000,
        default_leverage=15,
        volatility_level="high",
        recommended_timeframe="5m",
        description="Solana - Fast chain, good volatility for scalping"
    ),
    
    "ADAUSDT": TradingPair(
        symbol="ADAUSDT",
        category=PairCategory.LAYER1,
        min_position_size=10,
        max_position_size=10000,
        default_leverage=10,
        volatility_level="medium",
        recommended_timeframe="15m",
        description="Cardano - Academic approach, predictable patterns"
    ),
    
    "AVAXUSDT": TradingPair(
        symbol="AVAXUSDT",
        category=PairCategory.LAYER1,
        min_position_size=10,
        max_position_size=10000,
        default_leverage=15,
        volatility_level="high",
        recommended_timeframe="5m",
        description="Avalanche - High throughput chain"
    ),
    
    "DOTUSDT": TradingPair(
        symbol="DOTUSDT",
        category=PairCategory.LAYER1,
        min_position_size=10,
        max_position_size=8000,
        default_leverage=10,
        volatility_level="medium",
        recommended_timeframe="15m",
        description="Polkadot - Interoperability focused"
    ),
    
    "ATOMUSDT": TradingPair(
        symbol="ATOMUSDT",
        category=PairCategory.LAYER1,
        min_position_size=10,
        max_position_size=8000,
        default_leverage=10,
        volatility_level="medium",
        recommended_timeframe="15m",
        description="Cosmos - Hub for interconnected blockchains"
    ),
    
    "NEARUSDT": TradingPair(
        symbol="NEARUSDT",
        category=PairCategory.LAYER1,
        min_position_size=10,
        max_position_size=8000,
        default_leverage=15,
        volatility_level="high",
        recommended_timeframe="5m",
        description="NEAR Protocol - Sharded blockchain"
    ),
    
    "APTUSDT": TradingPair(
        symbol="APTUSDT",
        category=PairCategory.LAYER1,
        min_position_size=10,
        max_position_size=8000,
        default_leverage=15,
        volatility_level="high",
        recommended_timeframe="5m",
        description="Aptos - New L1 with Move language"
    ),
    
    "SUIUSDT": TradingPair(
        symbol="SUIUSDT",
        category=PairCategory.LAYER1,
        min_position_size=10,
        max_position_size=5000,
        default_leverage=20,
        volatility_level="high",
        recommended_timeframe="5m",
        description="Sui - High performance L1"
    ),
    
    # ============= LAYER 2 SOLUTIONS =============
    "MATICUSDT": TradingPair(
        symbol="MATICUSDT",
        category=PairCategory.LAYER2,
        min_position_size=10,
        max_position_size=10000,
        default_leverage=15,
        volatility_level="high",
        recommended_timeframe="5m",
        description="Polygon - Ethereum scaling solution"
    ),
    
    "ARBUSDT": TradingPair(
        symbol="ARBUSDT",
        category=PairCategory.LAYER2,
        min_position_size=10,
        max_position_size=8000,
        default_leverage=15,
        volatility_level="high",
        recommended_timeframe="5m",
        description="Arbitrum - Optimistic rollup for Ethereum"
    ),
    
    "OPUSDT": TradingPair(
        symbol="OPUSDT",
        category=PairCategory.LAYER2,
        min_position_size=10,
        max_position_size=8000,
        default_leverage=15,
        volatility_level="high",
        recommended_timeframe="5m",
        description="Optimism - Ethereum L2 scaling"
    ),
    
    # ============= DEFI TOKENS =============
    "LINKUSDT": TradingPair(
        symbol="LINKUSDT",
        category=PairCategory.DEFI,
        min_position_size=10,
        max_position_size=10000,
        default_leverage=10,
        volatility_level="medium",
        recommended_timeframe="15m",
        description="Chainlink - Oracle network, steady trends"
    ),
    
    "UNIUSDT": TradingPair(
        symbol="UNIUSDT",
        category=PairCategory.DEFI,
        min_position_size=10,
        max_position_size=8000,
        default_leverage=10,
        volatility_level="medium",
        recommended_timeframe="15m",
        description="Uniswap - Leading DEX token"
    ),
    
    "AAVEUSDT": TradingPair(
        symbol="AAVEUSDT",
        category=PairCategory.DEFI,
        min_position_size=10,
        max_position_size=5000,
        default_leverage=10,
        volatility_level="medium",
        recommended_timeframe="15m",
        description="Aave - Lending protocol"
    ),
    
    "LDOUSDT": TradingPair(
        symbol="LDOUSDT",
        category=PairCategory.DEFI,
        min_position_size=10,
        max_position_size=5000,
        default_leverage=15,
        volatility_level="high",
        recommended_timeframe="5m",
        description="Lido DAO - Liquid staking"
    ),
    
    "CRVUSDT": TradingPair(
        symbol="CRVUSDT",
        category=PairCategory.DEFI,
        min_position_size=10,
        max_position_size=5000,
        default_leverage=15,
        volatility_level="high",
        recommended_timeframe="5m",
        description="Curve - Stablecoin DEX"
    ),
    
    # ============= AI & EMERGING TECH =============
    "FETUSDT": TradingPair(
        symbol="FETUSDT",
        category=PairCategory.AI,
        min_position_size=10,
        max_position_size=5000,
        default_leverage=20,
        volatility_level="extreme",
        recommended_timeframe="5m",
        description="Fetch.ai - AI and autonomous agents"
    ),
    
    "RENDERUSDT": TradingPair(
        symbol="RENDERUSDT",
        category=PairCategory.AI,
        min_position_size=10,
        max_position_size=5000,
        default_leverage=15,
        volatility_level="high",
        recommended_timeframe="5m",
        description="Render - Distributed GPU rendering"
    ),
    
    "OCEANUSDT": TradingPair(
        symbol="OCEANUSDT",
        category=PairCategory.AI,
        min_position_size=10,
        max_position_size=3000,
        default_leverage=20,
        volatility_level="extreme",
        recommended_timeframe="5m",
        description="Ocean Protocol - Data exchange for AI"
    ),
    
    # ============= GAMING & METAVERSE =============
    "SANDUSDT": TradingPair(
        symbol="SANDUSDT",
        category=PairCategory.GAMING,
        min_position_size=10,
        max_position_size=5000,
        default_leverage=15,
        volatility_level="high",
        recommended_timeframe="5m",
        description="The Sandbox - Metaverse gaming"
    ),
    
    "AXSUSDT": TradingPair(
        symbol="AXSUSDT",
        category=PairCategory.GAMING,
        min_position_size=10,
        max_position_size=5000,
        default_leverage=15,
        volatility_level="high",
        recommended_timeframe="5m",
        description="Axie Infinity - Play-to-earn pioneer"
    ),
    
    "IMXUSDT": TradingPair(
        symbol="IMXUSDT",
        category=PairCategory.GAMING,
        min_position_size=10,
        max_position_size=5000,
        default_leverage=15,
        volatility_level="high",
        recommended_timeframe="5m",
        description="Immutable X - NFT scaling for games"
    ),
    
    # ============= HIGH VOLATILITY PAIRS (Good for Scalping) =============
    "DOGEUSDT": TradingPair(
        symbol="DOGEUSDT",
        category=PairCategory.MEME,
        min_position_size=10,
        max_position_size=10000,
        default_leverage=20,
        volatility_level="extreme",
        recommended_timeframe="1m",
        description="Dogecoin - High volume meme coin"
    ),
    
    "SHIBUSDT": TradingPair(
        symbol="SHIBUSDT",
        category=PairCategory.MEME,
        min_position_size=10,
        max_position_size=5000,
        default_leverage=20,
        volatility_level="extreme",
        recommended_timeframe="1m",
        description="Shiba Inu - Extreme volatility for scalping"
    ),
    
    "PEPEUSDT": TradingPair(
        symbol="PEPEUSDT",
        category=PairCategory.MEME,
        min_position_size=10,
        max_position_size=3000,
        default_leverage=20,
        volatility_level="extreme",
        recommended_timeframe="1m",
        description="Pepe - Meme coin with high volatility"
    ),
    
    # ============= ADDITIONAL HIGH-LIQUIDITY PAIRS =============
    "XRPUSDT": TradingPair(
        symbol="XRPUSDT",
        category=PairCategory.MAJOR,
        min_position_size=10,
        max_position_size=15000,
        default_leverage=15,
        volatility_level="medium",
        recommended_timeframe="15m",
        description="Ripple - Banking focused, good liquidity"
    ),
    
    "LTCUSDT": TradingPair(
        symbol="LTCUSDT",
        category=PairCategory.MAJOR,
        min_position_size=10,
        max_position_size=10000,
        default_leverage=10,
        volatility_level="medium",
        recommended_timeframe="15m",
        description="Litecoin - Bitcoin's silver, stable patterns"
    )
}

class TradingPairsManager:
    """Manage trading pairs dynamically"""
    
    def __init__(self):
        self.pairs = TRADING_PAIRS
        self.active_pairs = self._load_active_pairs()
    
    def _load_active_pairs(self) -> Dict[str, TradingPair]:
        """Load only active pairs"""
        return {
            symbol: pair 
            for symbol, pair in self.pairs.items() 
            if pair.active
        }
    
    def get_pairs_by_category(self, category: PairCategory) -> List[TradingPair]:
        """Get all pairs in a specific category"""
        return [
            pair for pair in self.active_pairs.values()
            if pair.category == category
        ]
    
    def get_pairs_by_volatility(self, level: str) -> List[TradingPair]:
        """Get pairs by volatility level"""
        return [
            pair for pair in self.active_pairs.values()
            if pair.volatility_level == level
        ]
    
    def get_recommended_pairs_for_balance(self, balance: float) -> List[TradingPair]:
        """Get recommended pairs based on account balance"""
        if balance < 1000:
            # Small account - focus on high volatility
            return self.get_pairs_by_volatility("extreme")[:5]
        elif balance < 10000:
            # Medium account - mix of volatility
            high_vol = self.get_pairs_by_volatility("high")[:5]
            med_vol = self.get_pairs_by_volatility("medium")[:5]
            return high_vol + med_vol
        else:
            # Large account - focus on majors and stable pairs
            majors = self.get_pairs_by_category(PairCategory.MAJOR)
            defi = self.get_pairs_by_category(PairCategory.DEFI)[:5]
            return majors + defi
    
    def add_pair(self, symbol: str, config: TradingPair):
        """Add new trading pair"""
        self.pairs[symbol] = config
        if config.active:
            self.active_pairs[symbol] = config
    
    def remove_pair(self, symbol: str):
        """Remove trading pair"""
        if symbol in self.pairs:
            del self.pairs[symbol]
        if symbol in self.active_pairs:
            del self.active_pairs[symbol]
    
    def toggle_pair(self, symbol: str, active: bool):
        """Enable/disable trading pair"""
        if symbol in self.pairs:
            self.pairs[symbol].active = active
            if active:
                self.active_pairs[symbol] = self.pairs[symbol]
            elif symbol in self.active_pairs:
                del self.active_pairs[symbol]
    
    def get_pair_config(self, symbol: str) -> Optional[TradingPair]:
        """Get configuration for specific pair"""
        return self.active_pairs.get(symbol)
    
    def get_all_symbols(self) -> List[str]:
        """Get list of all active symbols"""
        return list(self.active_pairs.keys())
    
    def get_optimal_pairs_for_strategy(self, strategy_type: str) -> List[str]:
        """Get optimal pairs for specific strategy"""
        if strategy_type == "scalping":
            # High volatility, low timeframe
            pairs = self.get_pairs_by_volatility("extreme")
            return [p.symbol for p in pairs[:10]]
        
        elif strategy_type == "swing":
            # Medium volatility, higher timeframe
            pairs = self.get_pairs_by_volatility("medium")
            return [p.symbol for p in pairs[:10]]
        
        elif strategy_type == "trend_following":
            # Major pairs with good liquidity
            pairs = self.get_pairs_by_category(PairCategory.MAJOR)
            return [p.symbol for p in pairs]
        
        elif strategy_type == "arbitrage":
            # High liquidity pairs
            majors = self.get_pairs_by_category(PairCategory.MAJOR)
            return [p.symbol for p in majors[:5]]
        
        else:
            # Default: balanced selection
            return self.get_default_pairs()
    
    def get_default_pairs(self) -> List[str]:
        """Get default trading pairs for general use"""
        return [
            "BTCUSDT",   # Most liquid
            "ETHUSDT",   # Second most liquid
            "SOLUSDT",   # Good volatility
            "BNBUSDT",   # Exchange token
            "MATICUSDT", # L2 representation
            "LINKUSDT",  # DeFi representation
            "ARBUSDT",   # L2 with volatility
            "DOGEUSDT",  # Meme for volatility
            "AVAXUSDT",  # L1 alternative
            "OPUSDT"     # Optimism L2
        ]
    
    def get_risk_adjusted_pairs(self, risk_level: str) -> List[str]:
        """Get pairs based on risk tolerance"""
        if risk_level == "conservative":
            # Only major pairs
            return ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        
        elif risk_level == "moderate":
            # Mix of majors and established alts
            return [
                "BTCUSDT", "ETHUSDT", "BNBUSDT",
                "SOLUSDT", "ADAUSDT", "LINKUSDT"
            ]
        
        elif risk_level == "aggressive":
            # Include high volatility
            return self.get_default_pairs()
        
        elif risk_level == "very_aggressive":
            # All pairs including memes
            return self.get_all_symbols()
        
        else:
            return self.get_default_pairs()

# Singleton instance
_manager = None

def get_pairs_manager() -> TradingPairsManager:
    """Get singleton pairs manager"""
    global _manager
    if _manager is None:
        _manager = TradingPairsManager()
    return _manager

if __name__ == "__main__":
    # Test the configuration
    manager = get_pairs_manager()
    
    print("=" * 60)
    print("TRADING PAIRS CONFIGURATION")
    print("=" * 60)
    
    print(f"\nTotal configured pairs: {len(manager.pairs)}")
    print(f"Active pairs: {len(manager.active_pairs)}")
    
    print("\n📊 Pairs by category:")
    for category in PairCategory:
        pairs = manager.get_pairs_by_category(category)
        symbols = [p.symbol for p in pairs]
        print(f"  {category.value}: {len(pairs)} pairs - {', '.join(symbols[:5])}")
    
    print("\n⚡ Pairs by volatility:")
    for level in ["low", "medium", "high", "extreme"]:
        pairs = manager.get_pairs_by_volatility(level)
        print(f"  {level}: {len(pairs)} pairs")
    
    print("\n🎯 Default trading pairs (10):")
    for symbol in manager.get_default_pairs():
        pair = manager.get_pair_config(symbol)
        print(f"  • {symbol}: {pair.description}")
    
    print("\n💰 Recommended for $500 balance:")
    for pair in manager.get_recommended_pairs_for_balance(500):
        print(f"  • {pair.symbol}: Leverage {pair.default_leverage}x, {pair.volatility_level} volatility")