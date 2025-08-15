"""
Health check and monitoring endpoints for Fly.io
"""

from fastapi import FastAPI, Response
from datetime import datetime
import psutil
import os
from prometheus_client import Counter, Gauge, Histogram, generate_latest
import logging

# Импортируем существующий web_api если есть
try:
    from web_api import app
except ImportError:
    app = FastAPI(title="Bybit Trading Bot API")

logger = logging.getLogger(__name__)

# Prometheus метрики
trades_total = Counter('trades_total', 'Total number of trades', ['strategy', 'symbol', 'side'])
active_positions = Gauge('active_positions', 'Number of active positions', ['symbol'])
account_balance = Gauge('account_balance', 'Account balance in USDT')
profit_loss = Gauge('profit_loss', 'Current P&L', ['type'])
bot_uptime = Gauge('bot_uptime_seconds', 'Bot uptime in seconds')
api_requests = Counter('api_requests_total', 'Total API requests', ['endpoint', 'method'])
api_latency = Histogram('api_request_duration_seconds', 'API request latency')

# Глобальные переменные для статуса
bot_start_time = datetime.now()
bot_status = {
    "status": "running",
    "strategy": os.getenv("STRATEGY", "adaptive"),
    "testnet": os.getenv("BYBIT_TESTNET", "true") == "true",
    "last_trade": None,
    "positions": 0,
    "balance": 0.0,
    "daily_pnl": 0.0
}


@app.get("/health")
async def health_check():
    """Health check endpoint for Fly.io"""
    try:
        # Проверяем основные компоненты
        uptime = (datetime.now() - bot_start_time).total_seconds()
        
        # Базовая проверка системных ресурсов
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        health_status = {
            "status": "healthy" if bot_status["status"] == "running" else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime,
            "checks": {
                "bot": bot_status["status"] == "running",
                "cpu_ok": cpu_percent < 80,
                "memory_ok": memory.percent < 90,
            },
            "metrics": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "active_positions": bot_status["positions"],
                "daily_pnl": bot_status["daily_pnl"]
            }
        }
        
        # Обновляем метрики Prometheus
        bot_uptime.set(uptime)
        active_positions.labels(symbol="ALL").set(bot_status["positions"])
        account_balance.set(bot_status["balance"])
        profit_loss.labels(type="daily").set(bot_status["daily_pnl"])
        
        # Возвращаем соответствующий HTTP статус
        if health_status["status"] == "healthy":
            return health_status
        else:
            return Response(content=str(health_status), status_code=503)
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return Response(
            content=f"Health check failed: {str(e)}", 
            status_code=503
        )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    api_requests.labels(endpoint="/metrics", method="GET").inc()
    return Response(content=generate_latest(), media_type="text/plain")


@app.get("/status")
async def get_status():
    """Get bot status"""
    api_requests.labels(endpoint="/status", method="GET").inc()
    
    uptime = (datetime.now() - bot_start_time).total_seconds()
    
    return {
        "status": bot_status["status"],
        "uptime": {
            "seconds": uptime,
            "human_readable": f"{uptime/3600:.1f} hours"
        },
        "configuration": {
            "strategy": bot_status["strategy"],
            "testnet": bot_status["testnet"],
            "symbol": os.getenv("SYMBOL", "BTCUSDT")
        },
        "trading": {
            "positions": bot_status["positions"],
            "last_trade": bot_status["last_trade"],
            "balance": bot_status["balance"],
            "daily_pnl": bot_status["daily_pnl"]
        },
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    }


@app.post("/shutdown")
async def shutdown():
    """Graceful shutdown endpoint"""
    api_requests.labels(endpoint="/shutdown", method="POST").inc()
    
    logger.info("Shutdown requested via API")
    bot_status["status"] = "stopping"
    
    # Здесь должна быть логика для graceful shutdown
    # - Закрытие позиций
    # - Отмена ордеров
    # - Сохранение состояния
    
    return {"message": "Shutdown initiated"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Bybit Trading Bot",
        "version": "1.0.0",
        "status": bot_status["status"],
        "endpoints": [
            "/health - Health check",
            "/status - Bot status",
            "/metrics - Prometheus metrics",
            "/docs - API documentation"
        ]
    }


# Функция для обновления статуса (вызывается из main.py)
def update_bot_status(updates: dict):
    """Update bot status from main trading loop"""
    global bot_status
    bot_status.update(updates)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
