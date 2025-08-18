# Deployment Guide для Bybit Trading Bot

## 🚀 Варианты хостинга и деплоя

### 1. Railway.app (Самый простой)
```yaml
# railway.toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "python main.py --strategy adaptive"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

[healthcheck]
path = "/api/status"
port = 5000
```

**Деплой:**
```bash
# Установите Railway CLI
npm install -g @railway/cli

# Логин
railway login

# Создайте проект
railway init

# Добавьте переменные окружения
railway variables set API_KEY=Mx7Ut1KJMaarT5fXQP
railway variables set API_SECRET=o2QmhtAS7Oj1MObuPZIupp3cX5J7xNvQQPom

# Деплой
railway up
```

### 2. Heroku (Популярный выбор)
```
# Procfile
web: python web_api.py
worker: python main.py --strategy adaptive
```

```json
// app.json
{
  "name": "Bybit Trading Bot",
  "description": "Automated crypto trading bot",
  "repository": "https://github.com/yourusername/bybit-bot",
  "env": {
    "API_KEY": {
      "description": "Bybit API Key",
      "required": true
    },
    "API_SECRET": {
      "description": "Bybit API Secret",
      "required": true
    }
  },
  "formation": {
    "web": {
      "quantity": 1,
      "size": "free"
    },
    "worker": {
      "quantity": 1,
      "size": "free"
    }
  }
}
```

### 3. Docker (Для любого VPS)
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py", "--strategy", "adaptive"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  bot:
    build: .
    environment:
      - API_KEY=${API_KEY}
      - API_SECRET=${API_SECRET}
      - TESTNET=False
    restart: unless-stopped
    
  web:
    build: .
    command: python web_api.py
    ports:
      - "5000:5000"
    environment:
      - API_KEY=${API_KEY}
      - API_SECRET=${API_SECRET}
    restart: unless-stopped
```

### 4. DigitalOcean App Platform
```yaml
# .do/app.yaml
name: bybit-trading-bot
services:
- name: bot
  github:
    repo: yourusername/bybit-bot
    branch: main
  run_command: python main.py --strategy adaptive
  envs:
  - key: API_KEY
    value: ${API_KEY}
  - key: API_SECRET
    value: ${API_SECRET}
```

### 5. AWS EC2 / Lightsail
```bash
#!/bin/bash
# setup.sh для Ubuntu/Debian

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3-pip python3-venv -y

# Clone repo
git clone https://github.com/yourusername/bybit-bot.git
cd bybit-bot

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create systemd service
sudo tee /etc/systemd/system/bybit-bot.service > /dev/null <<EOF
[Unit]
Description=Bybit Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/bybit-bot
Environment="PATH=/home/ubuntu/bybit-bot/venv/bin"
ExecStart=/home/ubuntu/bybit-bot/venv/bin/python main.py --strategy adaptive
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable bybit-bot
sudo systemctl start bybit-bot
```

### 6. Google Cloud Run
```yaml
# cloudbuild.yaml
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', 'gcr.io/$PROJECT_ID/bybit-bot', '.']
- name: 'gcr.io/cloud-builders/docker'
  args: ['push', 'gcr.io/$PROJECT_ID/bybit-bot']
- name: 'gcr.io/cloud-builders/gcloud'
  args:
  - 'run'
  - 'deploy'
  - 'bybit-bot'
  - '--image=gcr.io/$PROJECT_ID/bybit-bot'
  - '--platform=managed'
  - '--region=us-central1'
  - '--allow-unauthenticated'
```

## 📱 Мониторинг и управление

### Telegram Bot для управления
```python
# telegram_bot.py
import telebot
from telebot import types
import subprocess
import json

BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
ALLOWED_USERS = [123456789]  # Your Telegram user ID

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id not in ALLOWED_USERS:
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('📊 Status', '💰 Balance')
    markup.add('▶️ Start Bot', '⏸️ Stop Bot')
    markup.add('📈 Positions', '📉 PnL')
    
    bot.send_message(message.chat.id, "Bot Control Panel", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.from_user.id not in ALLOWED_USERS:
        return
    
    if message.text == '📊 Status':
        # Get bot status
        status = get_bot_status()
        bot.send_message(message.chat.id, status)
    
    elif message.text == '💰 Balance':
        # Get balance
        balance = get_balance()
        bot.send_message(message.chat.id, f"Balance: ${balance}")
    
    # Add more handlers...

bot.polling()
```

## 🔒 Безопасность

### Настройка Nginx + SSL
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    location /socket.io {
        proxy_pass http://localhost:5000/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 📊 Мониторинг

### Grafana + Prometheus
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'bybit-bot'
    static_configs:
      - targets: ['localhost:5000']
```

### Healthchecks.io
```python
# В main.py добавить:
import requests

def ping_healthcheck():
    try:
        requests.get("https://hc-ping.com/YOUR-UUID", timeout=10)
    except:
        pass

# Вызывать каждые 5 минут
```

## 💵 Стоимость хостинга

| Платформа | Цена/месяц | Особенности |
|-----------|------------|-------------|
| Railway | $5 | Простой деплой, автоскейлинг |
| Heroku | $7 | Популярный, много аддонов |
| DigitalOcean | $6 | Полный контроль, VPS |
| AWS EC2 | $3.50 (t3.micro) | Первый год бесплатно |
| Google Cloud | $0-10 | $300 кредитов на старт |
| Vultr | $6 | Хорошая производительность |
| Hetzner | €4.51 | Самый дешевый в Европе |

## 🚀 Быстрый старт

1. Выберите платформу (рекомендую Railway или Heroku)
2. Форкните репозиторий
3. Настройте переменные окружения
4. Деплойте через CLI или веб-интерфейс
5. Настройте мониторинг

## ⚠️ Важные настройки для продакшена

```python
# production_settings.py
import os

# Security
DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY', 'generate-random-key')

# API Rate Limiting
RATE_LIMIT = "100/hour"

# Logging
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': '/var/log/bybit-bot.log',
        },
        'sentry': {
            'class': 'sentry_sdk.integrations.logging.EventHandler',
        }
    },
    'root': {
        'handlers': ['file', 'sentry'],
        'level': 'INFO',
    }
}

# Monitoring
SENTRY_DSN = os.environ.get('SENTRY_DSN')
DATADOG_API_KEY = os.environ.get('DATADOG_API_KEY')
```
