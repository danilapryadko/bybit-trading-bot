#!/bin/bash

echo "🚀 Подготовка E2E тестирования Dashboard"
echo "========================================"

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не установлен"
    exit 1
fi

# Создаем виртуальное окружение
echo "📦 Создаем виртуальное окружение..."
python3 -m venv venv_e2e
source venv_e2e/bin/activate

# Устанавливаем зависимости
echo "📥 Устанавливаем зависимости..."
pip install --upgrade pip
pip install -r tests/e2e/requirements.txt

# Устанавливаем браузеры для Playwright
echo "🌐 Устанавливаем браузеры Playwright..."
playwright install chromium

# Запускаем тесты
echo ""
echo "🧪 Запускаем E2E тесты..."
echo "========================================"
python3 tests/e2e/test_dashboard.py

# Сохраняем код выхода
EXIT_CODE=$?

# Показываем где находятся скриншоты
echo ""
echo "📸 Скриншоты сохранены в: tests/e2e/screenshots/"
ls -la tests/e2e/screenshots/ 2>/dev/null

# Деактивируем виртуальное окружение
deactivate

exit $EXIT_CODE