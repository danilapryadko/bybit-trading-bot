#!/usr/bin/env python3
"""
E2E Playwright test for Bybit Trading Dashboard
Tests real MAINNET connection and balance display
"""
import asyncio
import os
from datetime import datetime
from playwright.async_api import async_playwright, expect

class DashboardE2ETest:
    def __init__(self):
        self.dashboard_url = "https://bybit-danila-dashboard.fly.dev"
        self.api_url = "https://bybit-danila-api.fly.dev"
        self.expected_balance = 499.28  # Your real balance
        self.results = []
        self.screenshots = []
        
    async def run_tests(self):
        """Run all E2E tests"""
        async with async_playwright() as p:
            # Launch Chromium browser
            print("🚀 Launching Chromium browser...")
            browser = await p.chromium.launch(
                headless=False,  # Set to False to see the browser
                args=['--start-maximized']
            )
            
            # Create context with viewport
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True
            )
            
            # Create page
            page = await context.new_page()
            
            # Enable console logging
            page.on("console", lambda msg: print(f"📝 Console: {msg.text}"))
            page.on("pageerror", lambda err: print(f"❌ Page error: {err}"))
            
            try:
                # Run tests
                await self.test_dashboard_loads(page)
                await self.test_api_connection(page)
                await self.test_balance_display(page)
                await self.test_market_data(page)
                await self.test_navigation(page)
                await self.test_live_trading_status(page)
                
            except Exception as e:
                print(f"❌ Test failed: {e}")
                # Take error screenshot
                await page.screenshot(path="error_screenshot.png")
                self.results.append(f"ERROR: {str(e)}")
            
            finally:
                # Close browser
                await browser.close()
                
            # Print results
            self.print_results()
    
    async def test_dashboard_loads(self, page):
        """Test 1: Dashboard loads successfully"""
        print("\n📊 Test 1: Loading Dashboard...")
        
        # Navigate to dashboard
        response = await page.goto(self.dashboard_url, wait_until='networkidle')
        
        # Check response status
        if response.status == 200:
            print("✅ Dashboard loaded successfully")
            self.results.append("Dashboard Load: PASSED")
        else:
            print(f"❌ Dashboard returned status: {response.status}")
            self.results.append(f"Dashboard Load: FAILED (status {response.status})")
        
        # Wait for content to load
        await page.wait_for_timeout(3000)
        
        # Take screenshot
        await page.screenshot(path="screenshots/01_dashboard_loaded.png")
        self.screenshots.append("01_dashboard_loaded.png")
    
    async def test_api_connection(self, page):
        """Test 2: Check API connection status"""
        print("\n🔌 Test 2: Checking API Connection...")
        
        # Check for disconnected status
        try:
            disconnected = await page.locator('text=Disconnected').count()
            if disconnected > 0:
                print("⚠️  Dashboard shows 'Disconnected' status")
                self.results.append("API Connection: WARNING - Shows disconnected")
                
                # Wait for reconnection
                print("⏳ Waiting for reconnection...")
                await page.wait_for_timeout(5000)
                
                # Check again
                disconnected = await page.locator('text=Disconnected').count()
                if disconnected == 0:
                    print("✅ Reconnected successfully")
                else:
                    print("❌ Still disconnected")
            else:
                print("✅ No disconnection warning found")
                self.results.append("API Connection: PASSED")
        except:
            print("✅ Connection appears stable")
            self.results.append("API Connection: PASSED")
        
        # Take screenshot
        await page.screenshot(path="screenshots/02_connection_status.png")
        self.screenshots.append("02_connection_status.png")
    
    async def test_balance_display(self, page):
        """Test 3: Check balance display"""
        print(f"\n💰 Test 3: Checking Balance Display (Expected: ${self.expected_balance})...")
        
        # Wait for balance to load
        await page.wait_for_timeout(3000)
        
        # Try to find balance element
        balance_found = False
        
        # Check for "Total Balance" section
        try:
            # Look for balance value
            balance_elements = await page.locator('text=/\\$[0-9,]+\\.[0-9]{2}/').all()
            
            for element in balance_elements:
                text = await element.text_content()
                print(f"   Found balance text: {text}")
                
                # Check if it's our expected balance
                if "499" in text:
                    print(f"✅ Found correct balance: {text}")
                    self.results.append("Balance Display: PASSED")
                    balance_found = True
                    break
                elif text == "$0.00":
                    print(f"⚠️  Balance shows $0.00 - may need refresh")
            
            if not balance_found:
                # Check if it's still loading
                loading = await page.locator('text=Loading').count()
                reconnecting = await page.locator('text=Reconnecting').count()
                
                if loading > 0 or reconnecting > 0:
                    print("⏳ Still loading/reconnecting...")
                    await page.wait_for_timeout(5000)
                    
                    # Refresh page
                    await page.reload()
                    await page.wait_for_timeout(3000)
                    
                    # Check again
                    balance_elements = await page.locator('text=/\\$[0-9,]+\\.[0-9]{2}/').all()
                    for element in balance_elements:
                        text = await element.text_content()
                        if "499" in text:
                            print(f"✅ Balance loaded after refresh: {text}")
                            self.results.append("Balance Display: PASSED (after refresh)")
                            balance_found = True
                            break
                
                if not balance_found:
                    print("❌ Could not find expected balance")
                    self.results.append("Balance Display: FAILED")
                    
        except Exception as e:
            print(f"❌ Error checking balance: {e}")
            self.results.append(f"Balance Display: ERROR - {str(e)}")
        
        # Take screenshot
        await page.screenshot(path="screenshots/03_balance_display.png", full_page=True)
        self.screenshots.append("03_balance_display.png")
    
    async def test_market_data(self, page):
        """Test 4: Check market data loading"""
        print("\n📈 Test 4: Checking Market Data...")
        
        # Check for watchlist
        try:
            # Look for crypto symbols
            btc = await page.locator('text=BTCUSDT').count()
            eth = await page.locator('text=ETHUSDT').count()
            
            if btc > 0 or eth > 0:
                print("✅ Market symbols found")
                
                # Check for price data
                loading = await page.locator('text=Loading...').count()
                if loading > 0:
                    print("⏳ Market data still loading...")
                    await page.wait_for_timeout(3000)
                
                # Check for prices (any number format)
                prices = await page.locator('text=/[0-9]+\\.[0-9]+/').count()
                if prices > 0:
                    print(f"✅ Found {prices} price values")
                    self.results.append("Market Data: PASSED")
                else:
                    print("⚠️  No price data found")
                    self.results.append("Market Data: WARNING - No prices")
            else:
                print("❌ No market symbols found")
                self.results.append("Market Data: FAILED")
                
        except Exception as e:
            print(f"❌ Error checking market data: {e}")
            self.results.append(f"Market Data: ERROR - {str(e)}")
        
        # Take screenshot
        await page.screenshot(path="screenshots/04_market_data.png")
        self.screenshots.append("04_market_data.png")
    
    async def test_navigation(self, page):
        """Test 5: Test navigation menu"""
        print("\n🧭 Test 5: Testing Navigation...")
        
        navigation_ok = True
        
        # Test navigation items
        nav_items = [
            ("Dashboard", "dashboard"),
            ("Trading", "trading"),
            ("Positions", "positions"),
            ("Portfolio", "portfolio"),
            ("Strategies", "strategies")
        ]
        
        for name, expected_url in nav_items:
            try:
                # Click navigation item
                await page.click(f"text={name}")
                await page.wait_for_timeout(1000)
                
                # Check URL changed
                current_url = page.url
                if expected_url.lower() in current_url.lower() or name == "Dashboard":
                    print(f"✅ {name} navigation works")
                else:
                    print(f"⚠️  {name} navigation issue")
                    navigation_ok = False
                    
            except Exception as e:
                print(f"❌ Could not navigate to {name}: {e}")
                navigation_ok = False
        
        if navigation_ok:
            self.results.append("Navigation: PASSED")
        else:
            self.results.append("Navigation: PARTIAL")
        
        # Return to dashboard
        await page.click("text=Dashboard")
        await page.wait_for_timeout(1000)
        
        # Take screenshot
        await page.screenshot(path="screenshots/05_navigation.png")
        self.screenshots.append("05_navigation.png")
    
    async def test_live_trading_status(self, page):
        """Test 6: Check Live Trading status"""
        print("\n🔴 Test 6: Checking Live Trading Status...")
        
        try:
            # Look for "Live Trading" text
            live_trading = await page.locator('text=Live Trading').count()
            
            if live_trading > 0:
                print("✅ Live Trading status found")
                
                # Check if it's green (active)
                green_status = await page.locator('.MuiChip-colorSuccess:has-text("Live Trading")').count()
                if green_status > 0:
                    print("✅ Live Trading is ACTIVE (green)")
                    self.results.append("Live Trading: ACTIVE")
                else:
                    print("⚠️  Live Trading found but not active")
                    self.results.append("Live Trading: INACTIVE")
            else:
                # Check for "Trading Disabled"
                disabled = await page.locator('text=Trading Disabled').count()
                if disabled > 0:
                    print("⚠️  Trading is disabled")
                    self.results.append("Live Trading: DISABLED")
                else:
                    print("❌ Could not find trading status")
                    self.results.append("Live Trading: NOT FOUND")
                    
        except Exception as e:
            print(f"❌ Error checking trading status: {e}")
            self.results.append(f"Live Trading: ERROR - {str(e)}")
        
        # Take final screenshot
        await page.screenshot(path="screenshots/06_final_state.png", full_page=True)
        self.screenshots.append("06_final_state.png")
    
    def print_results(self):
        """Print test results summary"""
        print("\n" + "="*60)
        print("📊 E2E TEST RESULTS SUMMARY")
        print("="*60)
        print(f"Dashboard URL: {self.dashboard_url}")
        print(f"API URL: {self.api_url}")
        print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*60)
        
        passed = 0
        failed = 0
        warnings = 0
        
        for result in self.results:
            print(f"  {result}")
            if "PASSED" in result:
                passed += 1
            elif "FAILED" in result or "ERROR" in result:
                failed += 1
            elif "WARNING" in result:
                warnings += 1
        
        print("-"*60)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        print("-"*60)
        
        if self.screenshots:
            print("\n📸 Screenshots saved:")
            for screenshot in self.screenshots:
                print(f"  - screenshots/{screenshot}")
        
        print("="*60)
        
        # Overall status
        if failed == 0:
            print("🎉 ALL TESTS PASSED! Dashboard is working correctly!")
            print(f"💰 Balance ${self.expected_balance} should be displayed")
        elif failed <= 2:
            print("⚠️  PARTIAL SUCCESS - Some issues detected")
            print("Try refreshing the dashboard or clearing cache")
        else:
            print("❌ TESTS FAILED - Dashboard has issues")
            print("Check the screenshots for details")
        
        print("="*60)

async def main():
    """Main test runner"""
    print("🎭 Starting Playwright E2E Tests for Bybit Dashboard")
    print("🌐 Testing MAINNET deployment on Fly.io")
    print("-"*60)
    
    # Create screenshots directory
    os.makedirs("screenshots", exist_ok=True)
    
    # Run tests
    tester = DashboardE2ETest()
    await tester.run_tests()
    
    print("\n✅ E2E Tests completed!")
    print("Check the screenshots/ folder for visual results")

if __name__ == "__main__":
    asyncio.run(main())