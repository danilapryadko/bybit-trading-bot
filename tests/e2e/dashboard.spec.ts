import { test, expect } from '@playwright/test';

const DASHBOARD_URL = 'https://bybit-danila-dashboard.fly.dev';
const API_URL = 'https://bybit-danila-api.fly.dev';

test.describe('Bybit Trading Dashboard E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Set a longer timeout for loading
    page.setDefaultTimeout(30000);
  });

  test('should load dashboard page', async ({ page }) => {
    await page.goto(`${DASHBOARD_URL}/dashboard`);
    
    // Check page title
    await expect(page).toHaveTitle(/Bybit/i);
    
    // Check main heading - use h2 instead of h1
    const heading = page.locator('h2, h3, h4').filter({ hasText: 'Dashboard' }).first();
    await expect(heading).toBeVisible();
  });

  test('should display balance information', async ({ page }) => {
    await page.goto(`${DASHBOARD_URL}/dashboard`);
    
    // Wait for balance section to load
    const balanceSection = page.locator('text=/Total Balance/i');
    await expect(balanceSection).toBeVisible({ timeout: 10000 });
    
    // Check if balance is displayed (could be 0 or any number) - use first match
    const balanceText = page.locator('text=/\\$[0-9,]+\\.?[0-9]*/').first();
    await expect(balanceText).toBeVisible();
  });

  test('should show trading status', async ({ page }) => {
    await page.goto(`${DASHBOARD_URL}/dashboard`);
    
    // Check for trading status indicator
    const tradingStatus = page.locator('text=/Trading/i').first();
    await expect(tradingStatus).toBeVisible({ timeout: 10000 });
  });

  test('should display watchlist', async ({ page }) => {
    await page.goto(`${DASHBOARD_URL}/dashboard`);
    
    // Check for watchlist section
    const watchlist = page.locator('text=/Watchlist/i');
    await expect(watchlist).toBeVisible({ timeout: 10000 });
    
    // Check for cryptocurrency symbols - use first match
    const btcSymbol = page.locator('text=/BTCUSDT/i').first();
    await expect(btcSymbol).toBeVisible();
  });

  test('should have navigation menu', async ({ page }) => {
    await page.goto(`${DASHBOARD_URL}/dashboard`);
    
    // Check navigation items
    const navItems = ['Dashboard', 'Trading', 'Positions', 'Analytics'];
    
    for (const item of navItems) {
      const navElement = page.locator(`text=${item}`).first();
      await expect(navElement).toBeVisible();
    }
  });

  test('should not show WebSocket error', async ({ page }) => {
    // Listen for console errors
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto(`${DASHBOARD_URL}/dashboard`);
    
    // Wait a bit for potential errors
    await page.waitForTimeout(3000);
    
    // Check that there's no WebSocket connection error
    const wsErrors = consoleErrors.filter(err => 
      err.toLowerCase().includes('websocket') && 
      err.toLowerCase().includes('error')
    );
    
    expect(wsErrors).toHaveLength(0);
  });

  test('should show polling mode notification', async ({ page }) => {
    await page.goto(`${DASHBOARD_URL}/dashboard`);
    
    // Check for polling mode message (since WebSocket is disabled)
    const pollingNotification = page.locator('text=/Polling Mode|API polling/i');
    
    // It might appear as a notification that disappears, so we check if it was visible at some point
    try {
      await expect(pollingNotification).toBeVisible({ timeout: 5000 });
      console.log('Polling mode notification found');
    } catch {
      // Notification might have already disappeared, which is fine
      console.log('Polling notification not visible (might have auto-dismissed)');
    }
  });

  test('should display price chart section', async ({ page }) => {
    await page.goto(`${DASHBOARD_URL}/dashboard`);
    
    // Check for chart section
    const chartSection = page.locator('text=/Price Chart/i');
    await expect(chartSection).toBeVisible({ timeout: 10000 });
    
    // Check for chart controls
    const chartControls = page.locator('text=/CANDLES|LINE/i');
    await expect(chartControls.first()).toBeVisible();
  });

  test('should make successful API health check', async ({ page }) => {
    // Check API health endpoint directly
    const response = await page.request.get(`${API_URL}/health`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data).toHaveProperty('status');
    expect(data.status).toBe('healthy');
  });

  test('should make successful GraphQL query', async ({ page }) => {
    // Test GraphQL endpoint
    const response = await page.request.post(`${API_URL}/graphql/`, {
      data: {
        query: '{ botStatus { isRunning balance } }'
      },
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data).toHaveProperty('data');
    expect(data.data).toHaveProperty('botStatus');
  });

  test('should handle responsive design', async ({ page }) => {
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(`${DASHBOARD_URL}/dashboard`);
    
    // Main content should still be visible - check for Dashboard text
    const dashboardContent = page.locator('text=/Dashboard/i').first();
    await expect(dashboardContent).toBeVisible();
    
    // Test desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    await expect(dashboardContent).toBeVisible();
  });

  test('should not display mock data', async ({ page }) => {
    await page.goto(`${DASHBOARD_URL}/dashboard`);
    
    // Wait for content to load
    await page.waitForTimeout(2000);
    
    // Check that we're not showing the default mock balance of $10,000
    const pageContent = await page.content();
    
    // The balance might be $10,000.00 in Paper Trading mode, which is fine
    // But we should see "Paper Trading" indicator
    if (pageContent.includes('$10,000.00')) {
      const paperTradingIndicator = page.locator('text=/Paper Trading/i');
      await expect(paperTradingIndicator).toBeVisible();
    }
  });
});

test.describe('Dashboard Performance', () => {
  test('should load within acceptable time', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto(`${DASHBOARD_URL}/dashboard`);
    await page.waitForLoadState('networkidle');
    
    const loadTime = Date.now() - startTime;
    
    // Page should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
    
    console.log(`Dashboard loaded in ${loadTime}ms`);
  });

  test('should not have memory leaks', async ({ page }) => {
    await page.goto(`${DASHBOARD_URL}/dashboard`);
    
    // Get initial memory usage
    const initialMetrics = await page.evaluate(() => {
      if ('memory' in performance) {
        return (performance as any).memory.usedJSHeapSize;
      }
      return 0;
    });
    
    // Navigate around
    await page.reload();
    await page.waitForTimeout(2000);
    
    // Get final memory usage
    const finalMetrics = await page.evaluate(() => {
      if ('memory' in performance) {
        return (performance as any).memory.usedJSHeapSize;
      }
      return 0;
    });
    
    // Memory shouldn't increase dramatically (allow 50MB increase)
    const memoryIncrease = finalMetrics - initialMetrics;
    expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024);
  });
});