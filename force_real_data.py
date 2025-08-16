#!/usr/bin/env python3
"""
Force Real Data Fix - Replace MockTradingBot with Real BybitConnector
This script patches the system to always use real data
"""

import os
import sys

print("🔧 APPLYING REAL DATA FIX...")

# Fix 1: Patch start_telegram_bot.py to use real data
with open('start_telegram_bot.py', 'r') as f:
    content = f.read()

if 'class MockTradingBot' in content:
    print("❌ Found MockTradingBot in start_telegram_bot.py")
    
    # Replace MockTradingBot with real implementation
    new_content = content.replace(
        'class MockTradingBot:',
        'from bybit_connector import get_bybit_connector\n\nclass MockTradingBot:  # Actually REAL now!'
    ).replace(
        'return 10000.0',
        'return get_bybit_connector().get_balance()  # REAL balance'
    ).replace(
        'self.paper_trading = True',
        'self.paper_trading = False  # REAL trading'
    )
    
    with open('start_telegram_bot.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Patched start_telegram_bot.py to use real data")

# Fix 2: Create a startup script that ensures real data
startup_script = '''#!/usr/bin/env python3
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
'''

with open('startup_real.py', 'w') as f:
    f.write(startup_script)

print("✅ Created startup_real.py")

# Fix 3: Update Dockerfile to use the new startup script
with open('Dockerfile', 'r') as f:
    dockerfile = f.read()

if 'startup_real.py' not in dockerfile:
    dockerfile = dockerfile.replace(
        'CMD ["python", "start_with_graphql.py"]',
        'CMD ["python", "startup_real.py"]'
    )
    
    with open('Dockerfile', 'w') as f:
        f.write(dockerfile)
    
    print("✅ Updated Dockerfile to use startup_real.py")

print("\n" + "="*50)
print("✅ REAL DATA FIX APPLIED!")
print("="*50)
print("\nNow deploy with:")
print("  fly deploy -a bybit-danila-bot")
print("\nThe bot will now ALWAYS use real Bybit data!")
print("No more $10,000 fake balance!")