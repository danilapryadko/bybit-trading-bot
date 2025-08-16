#!/usr/bin/env python3
"""
Startup script that ensures REAL data is used
"""
import os
os.environ['USE_REAL_DATA'] = 'true'
os.environ['PAPER_TRADING'] = 'false'

# Import and monkey-patch if needed
import start_telegram_bot
if hasattr(start_telegram_bot, 'MockTradingBot'):
    from bybit_connector import get_bybit_connector
    
    class RealTradingBot:
        def __init__(self):
            self.connector = get_bybit_connector()
            self.is_running = False
            self.paper_trading = False
            self.strategy_name = "ML Ensemble"
            
        def get_balance(self):
            return self.connector.get_balance()
            
        def get_positions(self):
            return self.connector.get_positions()
            
        def get_ticker(self, symbol):
            return self.connector.get_ticker(symbol)
    
    # Replace MockTradingBot with RealTradingBot
    start_telegram_bot.MockTradingBot = RealTradingBot
    print("✅ Replaced MockTradingBot with RealTradingBot")

# Now run the actual application
if __name__ == "__main__":
    import start_with_graphql
