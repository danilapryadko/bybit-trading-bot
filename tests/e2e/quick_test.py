#!/usr/bin/env python3
"""
Быстрый E2E тест Dashboard без Playwright
Использует только стандартные библиотеки
"""
import urllib.request
import urllib.error
import json
import ssl
import time
from datetime import datetime

# Игнорируем SSL ошибки для тестирования
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

DASHBOARD_URL = "https://bybit-danila-dashboard.fly.dev"
API_URL = "https://bybit-danila-api.fly.dev"

def test_dashboard_availability():
    """Тест доступности Dashboard"""
    print("\n📱 Тест: Доступность Dashboard")
    print("-" * 40)
    
    try:
        req = urllib.request.Request(f"{DASHBOARD_URL}/dashboard")
        response = urllib.request.urlopen(req, context=ssl_context, timeout=10)
        status_code = response.getcode()
        
        if status_code == 200:
            print(f"✅ Dashboard доступен (HTTP {status_code})")
            
            # Читаем содержимое
            content = response.read().decode('utf-8')
            
            # Проверяем на наличие mock данных
            if "$10,000" in content or "10000" in content:
                print("⚠️  ВНИМАНИЕ: Возможно используются mock данные ($10,000)")
            else:
                print("✅ Mock данные не обнаружены в HTML")
                
            return True
        else:
            print(f"❌ Dashboard вернул код {status_code}")
            return False
            
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP ошибка: {e.code} - {e.reason}")
        return False
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def test_api_health():
    """Тест здоровья API"""
    print("\n🔌 Тест: API Health Check")
    print("-" * 40)
    
    try:
        req = urllib.request.Request(f"{API_URL}/health")
        response = urllib.request.urlopen(req, context=ssl_context, timeout=10)
        status_code = response.getcode()
        
        if status_code == 200:
            content = response.read().decode('utf-8')
            print(f"✅ API Health endpoint доступен")
            print(f"   Ответ: {content[:100]}...")
            return True
        else:
            print(f"⚠️  Health endpoint вернул код {status_code}")
            
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("⚠️  Health endpoint не найден (404)")
        else:
            print(f"❌ HTTP ошибка: {e.code}")
    except Exception as e:
        print(f"❌ Ошибка подключения к API: {e}")
    
    return False

def test_graphql_endpoint():
    """Тест GraphQL endpoint"""
    print("\n📊 Тест: GraphQL Endpoint")
    print("-" * 40)
    
    try:
        # Подготавливаем GraphQL запрос
        query = {
            "query": "{ botStatus { isRunning balance } }"
        }
        
        data = json.dumps(query).encode('utf-8')
        
        req = urllib.request.Request(
            f"{API_URL}/graphql/",
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )
        
        response = urllib.request.urlopen(req, context=ssl_context, timeout=10)
        status_code = response.getcode()
        
        if status_code == 200:
            content = response.read().decode('utf-8')
            
            try:
                result = json.loads(content)
                print("✅ GraphQL endpoint отвечает")
                
                # Проверяем данные
                if 'data' in result and result['data']:
                    bot_status = result['data'].get('botStatus', {})
                    
                    if bot_status:
                        balance = bot_status.get('balance', 0)
                        is_running = bot_status.get('isRunning', False)
                        
                        print(f"\n📈 Данные от API:")
                        print(f"   • Баланс: {balance} USDT")
                        print(f"   • Бот запущен: {is_running}")
                        
                        # Проверяем на mock данные
                        if balance == 10000 or balance == 10000.0:
                            print("\n⚠️  ВНИМАНИЕ: Баланс равен 10000 - возможно mock данные!")
                            return False
                        else:
                            print("\n✅ Баланс не является mock значением")
                            return True
                            
                elif 'errors' in result:
                    print(f"⚠️  GraphQL вернул ошибки: {result['errors']}")
                    
            except json.JSONDecodeError:
                print(f"⚠️  Не удалось разобрать JSON ответ")
                
        else:
            print(f"❌ GraphQL вернул код {status_code}")
            
    except urllib.error.HTTPError as e:
        if e.code == 307:
            print("⚠️  GraphQL endpoint перенаправляет (307)")
        elif e.code == 503:
            print("❌ Сервис недоступен (503)")
        else:
            print(f"❌ HTTP ошибка: {e.code}")
    except Exception as e:
        print(f"❌ Ошибка запроса к GraphQL: {e}")
    
    return False

def test_response_times():
    """Тест времени отклика"""
    print("\n⏱️  Тест: Время отклика")
    print("-" * 40)
    
    endpoints = [
        (f"{DASHBOARD_URL}/", "Dashboard главная"),
        (f"{DASHBOARD_URL}/dashboard", "Dashboard страница"),
        (f"{API_URL}/graphql/", "GraphQL endpoint")
    ]
    
    all_passed = True
    for url, name in endpoints:
        try:
            start_time = time.time()
            
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req, context=ssl_context, timeout=10)
            
            response_time = (time.time() - start_time) * 1000  # в миллисекундах
            
            if response_time < 1000:
                print(f"✅ {name}: {response_time:.0f}ms")
            elif response_time < 3000:
                print(f"⚠️  {name}: {response_time:.0f}ms (медленно)")
                all_passed = False
            else:
                print(f"❌ {name}: {response_time:.0f}ms (очень медленно)")
                all_passed = False
                
        except Exception as e:
            print(f"❌ {name}: Ошибка - {str(e)[:50]}")
            all_passed = False
    
    return all_passed

def test_api_data():
    """Проверка реальных данных от API"""
    print("\n💰 Тест: Проверка реальных данных")
    print("-" * 40)
    
    # Список запросов для проверки
    queries = [
        {
            "name": "Баланс аккаунта",
            "query": "{ botStatus { balance } }"
        },
        {
            "name": "Позиции",
            "query": "{ positions { symbol side size avgPrice unrealizedPnl } }"
        },
        {
            "name": "Последние сделки",
            "query": "{ recentTrades(limit: 5) { symbol side price quantity timestamp } }"
        }
    ]
    
    all_passed = True
    for test_query in queries:
        try:
            data = json.dumps({"query": test_query["query"]}).encode('utf-8')
            
            req = urllib.request.Request(
                f"{API_URL}/graphql/",
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            )
            
            response = urllib.request.urlopen(req, context=ssl_context, timeout=10)
            
            if response.getcode() == 200:
                content = response.read().decode('utf-8')
                result = json.loads(content)
                
                if 'data' in result:
                    print(f"✅ {test_query['name']}: Данные получены")
                    
                    # Показываем первые 200 символов данных
                    data_str = json.dumps(result['data'], indent=2)
                    if len(data_str) > 200:
                        print(f"   {data_str[:200]}...")
                    else:
                        print(f"   {data_str}")
                else:
                    print(f"⚠️  {test_query['name']}: Нет данных")
                    all_passed = False
            else:
                print(f"❌ {test_query['name']}: HTTP {response.getcode()}")
                all_passed = False
                    
        except Exception as e:
            print(f"❌ {test_query['name']}: {str(e)[:50]}")
            all_passed = False
    
    return all_passed

def main():
    """Главная функция запуска тестов"""
    print("\n" + "=" * 60)
    print("🧪 E2E ТЕСТИРОВАНИЕ BYBIT TRADING BOT DASHBOARD")
    print("=" * 60)
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Dashboard URL: {DASHBOARD_URL}")
    print(f"API URL: {API_URL}")
    print("=" * 60)
    
    # Запускаем тесты
    results = []
    
    tests = [
        ("Доступность Dashboard", test_dashboard_availability),
        ("API Health Check", test_api_health),
        ("GraphQL Endpoint", test_graphql_endpoint),
        ("Время отклика", test_response_times),
        ("Реальные данные", test_api_data)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, "✅ PASSED" if result else "❌ FAILED"))
        except Exception as e:
            results.append((test_name, f"⚠️ ERROR: {str(e)[:30]}"))
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if "PASSED" in r)
    failed = sum(1 for _, r in results if "FAILED" in r)
    errors = sum(1 for _, r in results if "ERROR" in r)
    
    for test_name, result in results:
        print(f"• {test_name}: {result}")
    
    print("\n📈 Статистика:")
    print(f"  ✅ Успешно: {passed}")
    print(f"  ❌ Провалено: {failed}")
    print(f"  ⚠️  Ошибки: {errors}")
    print(f"  📊 Всего: {len(tests)}")
    
    success_rate = (passed / len(tests) * 100) if tests else 0
    print(f"  🎯 Успешность: {success_rate:.1f}%")
    
    # Рекомендации
    print("\n💡 Рекомендации:")
    if failed > 0 or errors > 0:
        print("  • Проверьте логи: fly logs -a bybit-danila-bot")
        print("  • Проверьте статус: fly status -a bybit-danila-bot")
        print("  • Перезапустите если нужно: fly apps restart bybit-danila-bot")
        
        if "10000" in str(results) or "mock" in str(results).lower():
            print("\n  ⚠️  ВАЖНО: Обнаружены mock данные!")
            print("  • Проверьте переменную USE_MAINNET")
            print("  • Убедитесь что используется bybit_connector, а не MockTradingBot")
    else:
        print("  ✅ Все тесты пройдены успешно!")
        print("  • Dashboard работает корректно")
        print("  • API отвечает на запросы")
        print("  • Данные выглядят реальными")
    
    print("\n" + "=" * 60)
    
    return passed == len(tests)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)