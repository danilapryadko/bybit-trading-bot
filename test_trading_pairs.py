#!/usr/bin/env python3
"""
Test trading pairs availability on Bybit
"""

import asyncio
import logging
from typing import List, Dict
from pybit.unified_trading import HTTP
from trading_pairs_config import get_pairs_manager, PairCategory
from config import get_trading_config
from tabulate import tabulate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PairsTester:
    """Test trading pairs availability and liquidity"""
    
    def __init__(self):
        self.config = get_trading_config()
        self.pairs_manager = get_pairs_manager()
        self.client = HTTP(
            testnet=self.config.is_testnet,
            api_key=self.config.api_key,
            api_secret=self.config.api_secret
        )
    
    def test_pair_availability(self, symbol: str) -> Dict:
        """Test if a trading pair is available on Bybit"""
        try:
            # Get ticker info
            response = self.client.get_tickers(
                category="linear",
                symbol=symbol
            )
            
            if response.get('retCode') == 0:
                ticker = response.get('result', {}).get('list', [])[0] if response.get('result', {}).get('list') else {}
                
                return {
                    'symbol': symbol,
                    'available': True,
                    'price': float(ticker.get('lastPrice', 0)),
                    'volume_24h': float(ticker.get('volume24h', 0)),
                    'bid': float(ticker.get('bid1Price', 0)),
                    'ask': float(ticker.get('ask1Price', 0)),
                    'spread': float(ticker.get('ask1Price', 0)) - float(ticker.get('bid1Price', 0))
                }
            else:
                return {
                    'symbol': symbol,
                    'available': False,
                    'error': response.get('retMsg', 'Unknown error')
                }
                
        except Exception as e:
            return {
                'symbol': symbol,
                'available': False,
                'error': str(e)
            }
    
    def test_all_pairs(self) -> List[Dict]:
        """Test all configured trading pairs"""
        results = []
        
        all_symbols = self.pairs_manager.get_all_symbols()
        logger.info(f"Testing {len(all_symbols)} trading pairs...")
        
        for symbol in all_symbols:
            result = self.test_pair_availability(symbol)
            results.append(result)
            
            if result['available']:
                logger.info(f"✅ {symbol}: Available - Price: ${result['price']:,.2f}, Volume: ${result['volume_24h']:,.0f}")
            else:
                logger.warning(f"❌ {symbol}: Not available - {result.get('error', 'Unknown error')}")
        
        return results
    
    def analyze_results(self, results: List[Dict]):
        """Analyze test results"""
        available = [r for r in results if r['available']]
        unavailable = [r for r in results if not r['available']]
        
        print("\n" + "=" * 80)
        print("TRADING PAIRS AVAILABILITY REPORT")
        print("=" * 80)
        
        print(f"\n📊 Summary:")
        print(f"  • Total pairs tested: {len(results)}")
        print(f"  • Available: {len(available)} ({len(available)/len(results)*100:.1f}%)")
        print(f"  • Unavailable: {len(unavailable)} ({len(unavailable)/len(results)*100:.1f}%)")
        
        if available:
            print(f"\n✅ Available Trading Pairs ({len(available)}):")
            
            # Sort by volume
            available.sort(key=lambda x: x['volume_24h'], reverse=True)
            
            table_data = []
            for pair in available[:15]:  # Show top 15 by volume
                table_data.append([
                    pair['symbol'],
                    f"${pair['price']:,.2f}",
                    f"${pair['volume_24h']:,.0f}",
                    f"${pair['spread']:.4f}"
                ])
            
            print(tabulate(
                table_data,
                headers=['Symbol', 'Price', '24h Volume', 'Spread'],
                tablefmt='grid'
            ))
            
            # Volume analysis
            total_volume = sum(p['volume_24h'] for p in available)
            print(f"\n💰 Volume Analysis:")
            print(f"  • Total 24h volume: ${total_volume:,.0f}")
            print(f"  • Average volume per pair: ${total_volume/len(available):,.0f}")
            
            # Top 5 by volume
            print(f"\n🏆 Top 5 pairs by volume:")
            for i, pair in enumerate(available[:5], 1):
                print(f"  {i}. {pair['symbol']}: ${pair['volume_24h']:,.0f}")
        
        if unavailable:
            print(f"\n❌ Unavailable Pairs ({len(unavailable)}):")
            for pair in unavailable:
                print(f"  • {pair['symbol']}: {pair.get('error', 'Unknown error')}")
        
        # Recommendations
        print("\n💡 Recommendations:")
        
        if len(available) >= 10:
            print("  ✅ Sufficient pairs available for diversified trading")
            
            # Get recommended pairs based on balance
            recommended = self.pairs_manager.get_recommended_pairs_for_balance(500)
            available_symbols = [p['symbol'] for p in available]
            
            recommended_available = [
                p for p in recommended 
                if p.symbol in available_symbols
            ]
            
            if recommended_available:
                print(f"\n  📌 Recommended pairs for $500 balance:")
                for pair in recommended_available[:5]:
                    print(f"    • {pair.symbol}: {pair.description}")
        else:
            print("  ⚠️ Limited pairs available. Consider using testnet or checking API access.")
    
    def get_optimal_pairs(self, strategy: str = "balanced") -> List[str]:
        """Get optimal pairs for trading based on availability and strategy"""
        results = self.test_all_pairs()
        available = [r for r in results if r['available']]
        
        # Sort by volume
        available.sort(key=lambda x: x['volume_24h'], reverse=True)
        
        if strategy == "high_volume":
            # Top 10 by volume
            return [p['symbol'] for p in available[:10]]
        
        elif strategy == "low_spread":
            # Sort by spread
            available.sort(key=lambda x: x['spread'])
            return [p['symbol'] for p in available[:10]]
        
        elif strategy == "balanced":
            # Mix of high volume and low spread
            high_volume = [p['symbol'] for p in available[:5]]
            
            # Sort by spread
            available.sort(key=lambda x: x['spread'])
            low_spread = [p['symbol'] for p in available[:5]]
            
            # Combine unique
            combined = list(set(high_volume + low_spread))
            return combined[:10]
        
        else:
            # Default to high volume
            return [p['symbol'] for p in available[:10]]

def main():
    """Main function"""
    tester = PairsTester()
    
    # Test all pairs
    results = tester.test_all_pairs()
    
    # Analyze results
    tester.analyze_results(results)
    
    # Get optimal pairs
    print("\n" + "=" * 80)
    print("OPTIMAL TRADING PAIRS SELECTION")
    print("=" * 80)
    
    for strategy in ["high_volume", "low_spread", "balanced"]:
        optimal = tester.get_optimal_pairs(strategy)
        print(f"\n📈 Strategy: {strategy.upper()}")
        print(f"  Optimal pairs: {', '.join(optimal)}")
    
    # Save configuration
    print("\n💾 Saving optimal configuration...")
    
    optimal_pairs = tester.get_optimal_pairs("balanced")
    
    # Create environment variable format
    print("\n📝 Add to .env file:")
    print(f"TRADING_PAIRS={','.join(optimal_pairs)}")
    
    print("\n✅ Testing complete!")

if __name__ == "__main__":
    main()