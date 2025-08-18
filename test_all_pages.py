#!/usr/bin/env python3
"""
E2E Playwright test для проверки всех вкладок Bybit Trading Dashboard
Тестирует каждую страницу на наличие ошибок и корректную загрузку
"""
import asyncio
import os
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

class DashboardPagesTest:
    def __init__(self):
        self.dashboard_url = "https://bybit-danila-dashboard.fly.dev"
        self.api_url = "https://bybit-danila-api.fly.dev"
        self.results = []
        self.errors = []
        
        # Все страницы для тестирования
        self.pages_to_test = [
            ("Dashboard", "/dashboard", ["Total Balance", "Available Balance"]),
            ("Trading", "/trading", ["Order Book", "Place Order"]),
            ("Positions", "/positions", ["Open Positions", "Position History"]),
            ("Portfolio", "/portfolio", ["Portfolio Overview", "Asset Allocation"]),
            ("Strategies", "/strategies", ["Available Strategies", "Strategy Performance"]),
            ("Risk Management", "/risk", ["Risk Metrics", "Risk Settings"]),
            ("Analytics", "/analytics", ["Performance Analytics", "Trading Statistics"]),
            ("Backtest", "/backtest", ["Backtest Strategy", "Historical Data"]),
            ("Settings", "/settings", ["Account Settings", "API Configuration"])
        ]
        
    async def run_tests(self):
        """Запуск всех E2E тестов"""
        async with async_playwright() as p:
            print("🚀 Запуск Chromium браузера...")
            browser = await p.chromium.launch(
                headless=False,  # Показать браузер
                args=['--start-maximized']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True
            )
            
            page = await context.new_page()
            
            # Отслеживание ошибок консоли
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda err: self.errors.append(f"Page error: {err}"))
            
            # Создаем папку для скриншотов
            os.makedirs("screenshots", exist_ok=True)
            
            try:
                # 1. Первоначальная загрузка
                print("\n📊 Загрузка Dashboard...")
                await page.goto(self.dashboard_url, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Проверка начального соединения
                await self.check_connection_status(page)
                
                # 2. Тестирование каждой страницы
                for page_name, path, expected_elements in self.pages_to_test:
                    result = await self.test_page(page, page_name, path, expected_elements)
                    self.results.append((page_name, result))
                    
                    # Делаем скриншот каждой страницы
                    screenshot_name = f"screenshots/{page_name.lower().replace(' ', '_')}.png"
                    await page.screenshot(path=screenshot_name, full_page=True)
                    
                    # Небольшая пауза между страницами
                    await page.wait_for_timeout(1000)
                
                # 3. Проверка консольных ошибок
                if console_errors:
                    print(f"\n⚠️ Найдено {len(console_errors)} ошибок в консоли:")
                    for error in console_errors[:5]:  # Показать первые 5
                        print(f"   - {error[:100]}")
                
            except Exception as e:
                print(f"❌ Критическая ошибка: {e}")
                await page.screenshot(path="screenshots/error.png")
                self.results.append(("CRITICAL ERROR", False))
            
            finally:
                await browser.close()
                
            # Вывод результатов
            self.print_results()
    
    async def test_page(self, page, page_name, path, expected_elements):
        """Тест отдельной страницы"""
        print(f"\n🔍 Тестирование: {page_name}")
        print(f"   URL: {path}")
        
        try:
            # Переход на страницу
            if path != page.url.split(self.dashboard_url)[1] if self.dashboard_url in page.url else "":
                await page.goto(f"{self.dashboard_url}{path}", wait_until='networkidle', timeout=15000)
                await page.wait_for_timeout(2000)
            
            # Проверка загрузки страницы
            page_title = await page.title()
            print(f"   ✓ Страница загружена: {page_title}")
            
            # Проверка наличия ошибок
            error_messages = await page.locator('text=/error|Error|ERROR/i').count()
            if error_messages > 0:
                print(f"   ⚠️ Найдено {error_messages} сообщений об ошибках")
            
            # Проверка статуса соединения
            disconnected = await page.locator('text=Disconnected').count()
            if disconnected > 0:
                print(f"   ⚠️ Статус: Disconnected")
                
                # Ждем переподключения
                await page.wait_for_timeout(3000)
                disconnected = await page.locator('text=Disconnected').count()
                if disconnected == 0:
                    print(f"   ✓ Переподключено")
                else:
                    print(f"   ❌ Все еще отключено")
                    return False
            else:
                print(f"   ✓ Соединение активно")
            
            # Проверка баланса (если это Dashboard)
            if page_name == "Dashboard":
                balance_elements = await page.locator('text=/$[0-9,]+\\.[0-9]{2}/').all()
                if balance_elements:
                    for elem in balance_elements[:1]:
                        balance_text = await elem.text_content()
                        if "$0.00" not in balance_text:
                            print(f"   ✓ Баланс отображается: {balance_text}")
                            break
            
            # Проверка ожидаемых элементов
            found_elements = 0
            for expected in expected_elements:
                count = await page.locator(f'text=/{expected}/i').count()
                if count > 0:
                    found_elements += 1
            
            if found_elements > 0:
                print(f"   ✓ Найдено {found_elements}/{len(expected_elements)} ожидаемых элементов")
            else:
                print(f"   ⚠️ Не найдены ожидаемые элементы")
            
            # Проверка загрузки данных
            loading = await page.locator('text=/Loading|Загрузка/i').count()
            if loading > 0:
                print(f"   ⏳ Есть индикаторы загрузки")
                await page.wait_for_timeout(2000)
            
            # Проверка наличия графиков (для страниц с графиками)
            if page_name in ["Dashboard", "Trading", "Analytics"]:
                canvas = await page.locator('canvas').count()
                if canvas > 0:
                    print(f"   ✓ Найдено {canvas} график(ов)")
            
            # Успешно, если нет критических ошибок
            return disconnected == 0 and error_messages == 0
            
        except PlaywrightTimeout:
            print(f"   ❌ Timeout при загрузке страницы")
            return False
        except Exception as e:
            print(f"   ❌ Ошибка: {str(e)[:100]}")
            return False
    
    async def check_connection_status(self, page):
        """Проверка начального статуса соединения"""
        print("\n🔌 Проверка соединения с API...")
        
        # Ждем загрузки
        await page.wait_for_timeout(3000)
        
        # Проверяем статус
        connected = await page.locator('text=Connected').count()
        disconnected = await page.locator('text=Disconnected').count()
        
        if connected > 0:
            print("   ✓ Статус: Connected")
        elif disconnected > 0:
            print("   ⚠️ Статус: Disconnected")
            print("   Ожидание переподключения...")
            await page.wait_for_timeout(5000)
            
            # Проверяем снова
            connected = await page.locator('text=Connected').count()
            if connected > 0:
                print("   ✓ Переподключено успешно")
            else:
                print("   ❌ Не удалось подключиться")
        else:
            print("   ℹ️ Статус соединения не отображается")
    
    def print_results(self):
        """Вывод итоговых результатов"""
        print("\n" + "="*60)
        print("📊 РЕЗУЛЬТАТЫ E2E ТЕСТИРОВАНИЯ ВСЕХ СТРАНИЦ")
        print("="*60)
        print(f"Dashboard URL: {self.dashboard_url}")
        print(f"Время теста: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*60)
        
        passed = 0
        failed = 0
        
        print("\nРЕЗУЛЬТАТЫ ПО СТРАНИЦАМ:")
        for page_name, result in self.results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"  {page_name:.<25} {status}")
            if result:
                passed += 1
            else:
                failed += 1
        
        print("-"*60)
        print(f"\nИТОГО:")
        print(f"  ✅ Успешно: {passed}/{len(self.results)}")
        print(f"  ❌ Неудачно: {failed}/{len(self.results)}")
        
        if self.errors:
            print(f"\n⚠️ ОШИБКИ СТРАНИЦ:")
            for error in self.errors[:5]:
                print(f"  - {error[:100]}")
        
        print("-"*60)
        
        # Общий вердикт
        if failed == 0:
            print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            print("✅ Dashboard полностью функционален")
            print("✅ Все страницы загружаются корректно")
            print("✅ Соединение стабильно")
        elif failed <= 2:
            print("\n⚠️ ЧАСТИЧНЫЙ УСПЕХ")
            print(f"Проблемы на {failed} страницах")
            print("Проверьте скриншоты для деталей")
        else:
            print("\n❌ ОБНАРУЖЕНЫ КРИТИЧЕСКИЕ ПРОБЛЕМЫ")
            print(f"{failed} страниц не работают корректно")
            print("Требуется исправление")
        
        print("\n📸 Скриншоты сохранены в папке: screenshots/")
        print("="*60)

async def main():
    """Главная функция"""
    print("🎭 E2E ТЕСТИРОВАНИЕ ВСЕХ СТРАНИЦ BYBIT DASHBOARD")
    print("="*60)
    
    tester = DashboardPagesTest()
    await tester.run_tests()
    
    print("\n✅ Тестирование завершено!")

if __name__ == "__main__":
    # Проверяем наличие playwright
    try:
        import playwright
    except ImportError:
        print("❌ Playwright не установлен!")
        print("Установите командой: pip install playwright")
        print("Затем: playwright install chromium")
        exit(1)
    
    asyncio.run(main())