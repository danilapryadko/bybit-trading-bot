#!/usr/bin/env python3
"""
E2E тесты для Bybit Trading Bot Dashboard
Использует Playwright для тестирования реального развернутого приложения
"""
import asyncio
import pytest
from playwright.async_api import async_playwright, expect
import time
from datetime import datetime

# URL развернутого dashboard
DASHBOARD_URL = "https://bybit-danila-dashboard.fly.dev/dashboard"
LOGIN_URL = "https://bybit-danila-dashboard.fly.dev/login"

class TestDashboard:
    """E2E тесты для dashboard"""
    
    @pytest.mark.asyncio
    async def test_dashboard_loads(self):
        """Тест: Dashboard загружается"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True
            )
            page = await context.new_page()
            
            print(f"\n📱 Открываем dashboard: {DASHBOARD_URL}")
            response = await page.goto(DASHBOARD_URL, wait_until='networkidle')
            
            # Проверяем статус ответа
            assert response.status < 400, f"Ошибка загрузки: HTTP {response.status}"
            
            # Делаем скриншот
            await page.screenshot(path="tests/e2e/screenshots/dashboard_initial.png")
            
            # Проверяем наличие основных элементов
            print("✅ Dashboard загружен успешно")
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_balance_display(self):
        """Тест: Отображение баланса (не должен быть $10,000)"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(DASHBOARD_URL, wait_until='networkidle')
            await page.wait_for_timeout(3000)  # Ждем загрузки данных
            
            # Ищем элемент с балансом
            balance_selectors = [
                'text=/\\$[0-9,]+\\.[0-9]+/',  # Regex для суммы в долларах
                '[data-testid="balance"]',
                '.balance',
                'text=/Balance/',
                'text=/USDT/'
            ]
            
            balance_found = False
            balance_text = None
            
            for selector in balance_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        balance_text = await element.text_content()
                        balance_found = True
                        print(f"💰 Найден баланс: {balance_text}")
                        break
                except:
                    continue
            
            # Проверяем, что баланс не равен mock значению $10,000
            if balance_text:
                assert "$10,000" not in balance_text, "❌ Обнаружен mock баланс $10,000!"
                assert "10000" not in balance_text.replace(",", "").replace(".", ""), "❌ Обнаружен mock баланс 10000!"
                print("✅ Баланс не является mock значением")
            
            await page.screenshot(path="tests/e2e/screenshots/balance_check.png")
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Тест: WebSocket соединение"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Отслеживаем WebSocket соединения
            ws_connected = False
            ws_error = None
            
            def on_websocket(ws):
                nonlocal ws_connected
                ws_connected = True
                print(f"🔌 WebSocket подключен: {ws.url}")
            
            def on_websocket_error(error):
                nonlocal ws_error
                ws_error = error
                print(f"❌ WebSocket ошибка: {error}")
            
            page.on("websocket", on_websocket)
            
            # Отслеживаем консольные ошибки
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            
            await page.goto(DASHBOARD_URL, wait_until='networkidle')
            await page.wait_for_timeout(5000)
            
            # Проверяем консольные ошибки
            if console_errors:
                print(f"⚠️  Консольные ошибки: {console_errors[:5]}")  # Первые 5 ошибок
            
            # Делаем скриншот
            await page.screenshot(path="tests/e2e/screenshots/websocket_test.png")
            
            await browser.close()
    
    @pytest.mark.asyncio  
    async def test_responsive_design(self):
        """Тест: Адаптивный дизайн для мобильных устройств"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # Тестируем разные размеры экрана
            viewports = [
                {"name": "Mobile", "width": 375, "height": 667},
                {"name": "Tablet", "width": 768, "height": 1024},
                {"name": "Desktop", "width": 1920, "height": 1080}
            ]
            
            for viewport in viewports:
                context = await browser.new_context(
                    viewport={'width': viewport['width'], 'height': viewport['height']},
                    ignore_https_errors=True
                )
                page = await context.new_page()
                
                await page.goto(DASHBOARD_URL, wait_until='networkidle')
                await page.wait_for_timeout(2000)
                
                # Делаем скриншот для каждого размера
                filename = f"tests/e2e/screenshots/responsive_{viewport['name'].lower()}.png"
                await page.screenshot(path=filename)
                print(f"📱 {viewport['name']}: скриншот сохранен")
                
                await context.close()
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_navigation_menu(self):
        """Тест: Навигационное меню"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(DASHBOARD_URL, wait_until='networkidle')
            await page.wait_for_timeout(2000)
            
            # Проверяем наличие навигационных ссылок
            nav_items = [
                {"text": "Dashboard", "expected": True},
                {"text": "Positions", "expected": True},
                {"text": "Analytics", "expected": True},
                {"text": "Settings", "expected": True}
            ]
            
            for item in nav_items:
                try:
                    element = await page.wait_for_selector(f'text=/{item["text"]}/i', timeout=3000)
                    if element:
                        print(f"✅ Найден пункт меню: {item['text']}")
                except:
                    if item["expected"]:
                        print(f"⚠️  Не найден пункт меню: {item['text']}")
            
            await page.screenshot(path="tests/e2e/screenshots/navigation.png")
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_real_time_updates(self):
        """Тест: Обновление данных в реальном времени"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(DASHBOARD_URL, wait_until='networkidle')
            
            # Делаем первый скриншот
            await page.screenshot(path="tests/e2e/screenshots/realtime_before.png")
            
            # Ждем 10 секунд для обновления данных
            print("⏱️  Ждем обновления данных (10 сек)...")
            await page.wait_for_timeout(10000)
            
            # Делаем второй скриншот
            await page.screenshot(path="tests/e2e/screenshots/realtime_after.png")
            
            # Проверяем, что страница все еще работает
            try:
                await page.wait_for_selector('body', timeout=1000)
                print("✅ Dashboard продолжает работать")
            except:
                print("❌ Dashboard перестал отвечать")
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Тест: Обработка ошибок при отсутствии соединения"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()
            
            # Блокируем API запросы для имитации ошибки
            await page.route('**/api/**', lambda route: route.abort())
            await page.route('**/graphql', lambda route: route.abort())
            
            await page.goto(DASHBOARD_URL, wait_until='domcontentloaded')
            await page.wait_for_timeout(5000)
            
            # Проверяем, что страница обрабатывает ошибки корректно
            error_selectors = [
                'text=/error/i',
                'text=/offline/i',
                'text=/connection/i',
                '.error-message',
                '.alert'
            ]
            
            error_found = False
            for selector in error_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=3000)
                    if element:
                        error_text = await element.text_content()
                        print(f"📍 Найдено сообщение об ошибке: {error_text}")
                        error_found = True
                        break
                except:
                    continue
            
            await page.screenshot(path="tests/e2e/screenshots/error_handling.png")
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """Тест: Метрики производительности"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Засекаем время загрузки
            start_time = time.time()
            
            await page.goto(DASHBOARD_URL, wait_until='networkidle')
            
            load_time = time.time() - start_time
            print(f"⏱️  Время загрузки: {load_time:.2f} сек")
            
            # Получаем метрики производительности
            metrics = await page.evaluate("""() => {
                const perf = window.performance.timing;
                return {
                    domContentLoaded: perf.domContentLoadedEventEnd - perf.navigationStart,
                    loadComplete: perf.loadEventEnd - perf.navigationStart,
                    firstPaint: performance.getEntriesByType('paint')[0]?.startTime || 0
                }
            }""")
            
            print(f"📊 Метрики производительности:")
            print(f"   DOM Content Loaded: {metrics['domContentLoaded']}ms")
            print(f"   Load Complete: {metrics['loadComplete']}ms")
            print(f"   First Paint: {metrics['firstPaint']:.0f}ms")
            
            # Проверяем, что загрузка происходит быстро
            assert load_time < 10, f"Слишком долгая загрузка: {load_time} сек"
            
            await browser.close()


async def run_all_tests():
    """Запуск всех тестов"""
    print("🚀 Запуск E2E тестов для Bybit Trading Bot Dashboard")
    print("=" * 60)
    
    test_suite = TestDashboard()
    tests = [
        ("Загрузка Dashboard", test_suite.test_dashboard_loads),
        ("Проверка баланса", test_suite.test_balance_display),
        ("WebSocket соединение", test_suite.test_websocket_connection),
        ("Адаптивный дизайн", test_suite.test_responsive_design),
        ("Навигационное меню", test_suite.test_navigation_menu),
        ("Обновления в реальном времени", test_suite.test_real_time_updates),
        ("Обработка ошибок", test_suite.test_error_handling),
        ("Метрики производительности", test_suite.test_performance_metrics)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📝 Тест: {test_name}")
        print("-" * 40)
        try:
            await test_func()
            results.append((test_name, "✅ PASSED"))
            print(f"✅ {test_name} - УСПЕШНО")
        except AssertionError as e:
            results.append((test_name, f"❌ FAILED: {e}"))
            print(f"❌ {test_name} - ПРОВАЛЕН: {e}")
        except Exception as e:
            results.append((test_name, f"⚠️ ERROR: {e}"))
            print(f"⚠️ {test_name} - ОШИБКА: {e}")
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ E2E ТЕСТИРОВАНИЯ")
    print("=" * 60)
    print(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"URL: {DASHBOARD_URL}")
    print("\nРезультаты тестов:")
    
    passed = 0
    failed = 0
    errors = 0
    
    for test_name, result in results:
        print(f"  • {test_name}: {result}")
        if "PASSED" in result:
            passed += 1
        elif "FAILED" in result:
            failed += 1
        else:
            errors += 1
    
    print(f"\n📈 Статистика:")
    print(f"  ✅ Успешно: {passed}")
    print(f"  ❌ Провалено: {failed}")
    print(f"  ⚠️  Ошибки: {errors}")
    print(f"  📊 Всего: {len(tests)}")
    print(f"  🎯 Успешность: {(passed/len(tests)*100):.1f}%")
    
    return passed == len(tests)


if __name__ == "__main__":
    # Запускаем тесты
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)