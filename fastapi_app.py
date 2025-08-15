#!/usr/bin/env python3
"""
FastAPI REST API v2 - Complete Trading Bot API
Provides comprehensive REST endpoints with WebSocket support
"""

from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import logging
import asyncio
from pathlib import Path

# Import bot components
from report_generator import ReportGenerator
from performance_analytics import PerformanceAnalytics
from integrated_data_service import IntegratedDataService
from risk_manager_v2 import RiskManagerV2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Bybit Trading Bot API",
    description="Professional cryptocurrency trading bot API for Bybit exchange",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security (placeholder for JWT)
security = HTTPBearer()

# Global instances
data_service = IntegratedDataService(testnet=True)
report_generator = ReportGenerator()
analytics = PerformanceAnalytics()
risk_manager = RiskManagerV2()

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# Pydantic models
class OrderRequest(BaseModel):
    symbol: str = Field(..., example="BTCUSDT")
    side: str = Field(..., example="Buy")
    order_type: str = Field("Limit", example="Limit")
    quantity: float = Field(..., example=0.01)
    price: Optional[float] = Field(None, example=65000)
    stop_loss: Optional[float] = Field(None, example=63000)
    take_profit: Optional[float] = Field(None, example=67000)
    leverage: int = Field(1, example=10)
    
class PositionResponse(BaseModel):
    symbol: str
    side: str
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    realized_pnl: float
    margin: float
    leverage: int
    
class StrategyConfig(BaseModel):
    name: str = Field(..., example="RSI")
    enabled: bool = Field(True)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    symbols: List[str] = Field(default_factory=list)
    
class RiskSettings(BaseModel):
    max_position_size: float = Field(0.2, example=0.2)
    max_daily_loss: float = Field(0.05, example=0.05)
    max_drawdown: float = Field(0.15, example=0.15)
    stop_loss_percent: float = Field(2.0, example=2.0)
    take_profit_percent: float = Field(3.0, example=3.0)
    use_trailing_stop: bool = Field(False)
    
class TradingStatus(BaseModel):
    is_running: bool
    is_paper_trading: bool
    active_strategies: List[str]
    open_positions: int
    daily_pnl: float
    total_pnl: float
    
# API Endpoints

@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "name": "Bybit Trading Bot API",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/api/docs",
        "health": "/api/v2/health"
    }

@app.get("/api/v2/health", tags=["General"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "operational",
            "data_service": data_service.get_status(),
            "risk_manager": "operational",
            "analytics": "operational"
        }
    }

# Trading endpoints
@app.get("/api/v2/trading/status", response_model=TradingStatus, tags=["Trading"])
async def get_trading_status():
    """Get current trading bot status"""
    # Mock data for now
    return TradingStatus(
        is_running=True,
        is_paper_trading=True,
        active_strategies=["RSI", "EMA"],
        open_positions=2,
        daily_pnl=250.50,
        total_pnl=1850.75
    )

@app.post("/api/v2/trading/start", tags=["Trading"])
async def start_trading(
    paper_mode: bool = True,
    strategies: List[str] = ["RSI"]
):
    """Start the trading bot"""
    try:
        # Start trading logic here
        return {
            "status": "started",
            "paper_mode": paper_mode,
            "strategies": strategies,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v2/trading/stop", tags=["Trading"])
async def stop_trading():
    """Stop the trading bot"""
    try:
        # Stop trading logic here
        return {
            "status": "stopped",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Order endpoints
@app.post("/api/v2/orders", tags=["Orders"])
async def place_order(order: OrderRequest):
    """Place a new order"""
    try:
        # Validate order with risk manager
        is_valid, message = risk_manager.validate_order(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=order.price
        )
        
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
            
        # Place order logic here
        order_id = f"ORD_{datetime.now().timestamp()}"
        
        return {
            "order_id": order_id,
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "price": order.price,
            "status": "New",
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/orders", tags=["Orders"])
async def get_orders(
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 100
):
    """Get orders"""
    # Mock data
    orders = [
        {
            "order_id": "ORD_001",
            "symbol": "BTCUSDT",
            "side": "Buy",
            "quantity": 0.01,
            "price": 65000,
            "status": "Filled",
            "created_at": datetime.now().isoformat()
        }
    ]
    
    if status:
        orders = [o for o in orders if o["status"] == status]
    if symbol:
        orders = [o for o in orders if o["symbol"] == symbol]
        
    return {"orders": orders[:limit], "total": len(orders)}

@app.delete("/api/v2/orders/{order_id}", tags=["Orders"])
async def cancel_order(order_id: str):
    """Cancel an order"""
    try:
        # Cancel order logic here
        return {
            "order_id": order_id,
            "status": "Cancelled",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail="Order not found")

# Position endpoints
@app.get("/api/v2/positions", tags=["Positions"])
async def get_positions(symbol: Optional[str] = None):
    """Get open positions"""
    positions = [
        {
            "symbol": "BTCUSDT",
            "side": "Buy",
            "size": 0.01,
            "entry_price": 64500,
            "mark_price": 65000,
            "unrealized_pnl": 50.00,
            "realized_pnl": 0,
            "margin": 645,
            "leverage": 10
        }
    ]
    
    if symbol:
        positions = [p for p in positions if p["symbol"] == symbol]
        
    return {"positions": positions, "total": len(positions)}

@app.post("/api/v2/positions/{symbol}/close", tags=["Positions"])
async def close_position(symbol: str, quantity: Optional[float] = None):
    """Close a position"""
    try:
        # Close position logic here
        return {
            "symbol": symbol,
            "action": "closed",
            "quantity": quantity,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail="Position not found")

# Market Data endpoints
@app.get("/api/v2/market/tickers", tags=["Market Data"])
async def get_tickers(symbols: Optional[List[str]] = None):
    """Get market tickers"""
    tickers = {
        "BTCUSDT": {
            "symbol": "BTCUSDT",
            "last_price": 65000,
            "bid": 64995,
            "ask": 65005,
            "volume_24h": 1500000000,
            "price_change_24h": 500,
            "price_change_percent_24h": 0.77
        },
        "ETHUSDT": {
            "symbol": "ETHUSDT",
            "last_price": 3200,
            "bid": 3199,
            "ask": 3201,
            "volume_24h": 500000000,
            "price_change_24h": 25,
            "price_change_percent_24h": 0.78
        }
    }
    
    if symbols:
        tickers = {k: v for k, v in tickers.items() if k in symbols}
        
    return tickers

@app.get("/api/v2/market/orderbook/{symbol}", tags=["Market Data"])
async def get_orderbook(symbol: str, depth: int = 20):
    """Get orderbook for a symbol"""
    return {
        "symbol": symbol,
        "bids": [[64995, 0.5], [64990, 1.2], [64985, 0.8]],
        "asks": [[65005, 0.6], [65010, 1.0], [65015, 0.9]],
        "timestamp": datetime.now().timestamp()
    }

@app.get("/api/v2/market/klines/{symbol}", tags=["Market Data"])
async def get_klines(
    symbol: str,
    interval: str = "1h",
    limit: int = 100
):
    """Get kline/candlestick data"""
    # Mock kline data
    klines = []
    base_price = 65000 if symbol == "BTCUSDT" else 3200
    
    for i in range(limit):
        timestamp = datetime.now() - timedelta(hours=limit-i)
        klines.append({
            "timestamp": timestamp.isoformat(),
            "open": base_price + (i * 10),
            "high": base_price + (i * 10) + 50,
            "low": base_price + (i * 10) - 30,
            "close": base_price + (i * 10) + 20,
            "volume": 1000000 + (i * 10000)
        })
        
    return {"symbol": symbol, "interval": interval, "klines": klines}

# Analytics endpoints
@app.get("/api/v2/analytics/performance", tags=["Analytics"])
async def get_performance_metrics():
    """Get trading performance metrics"""
    metrics = analytics.calculate_metrics([])
    return metrics

@app.get("/api/v2/analytics/strategies", tags=["Analytics"])
async def get_strategy_performance():
    """Get performance metrics by strategy"""
    return {
        "strategies": [
            {
                "name": "RSI",
                "total_trades": 45,
                "win_rate": 62.5,
                "total_pnl": 1250.50,
                "sharpe_ratio": 1.85
            },
            {
                "name": "EMA",
                "total_trades": 38,
                "win_rate": 58.3,
                "total_pnl": 850.25,
                "sharpe_ratio": 1.65
            }
        ]
    }

@app.get("/api/v2/analytics/report", tags=["Analytics"])
async def generate_report(
    format: str = "pdf",
    period: str = "daily"
):
    """Generate trading report"""
    try:
        # Get trading data
        trades = []
        positions = []
        metrics = analytics.calculate_metrics(trades)
        
        if format == "pdf":
            report_path = report_generator.generate_daily_report(
                trades=trades,
                positions=positions,
                metrics=metrics
            )
            return FileResponse(
                path=report_path,
                media_type="application/pdf",
                filename=Path(report_path).name
            )
        else:
            html_report = report_generator.generate_html_report(
                trades=trades,
                positions=positions,
                metrics=metrics
            )
            return JSONResponse(content={"html": html_report})
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Strategy endpoints
@app.get("/api/v2/strategies", tags=["Strategies"])
async def get_strategies():
    """Get available strategies"""
    return {
        "strategies": [
            {
                "name": "RSI",
                "description": "RSI-based trading strategy",
                "enabled": True,
                "parameters": {"period": 14, "oversold": 30, "overbought": 70}
            },
            {
                "name": "EMA",
                "description": "EMA crossover strategy",
                "enabled": True,
                "parameters": {"short_period": 9, "long_period": 21}
            },
            {
                "name": "MACD",
                "description": "MACD strategy",
                "enabled": False,
                "parameters": {"fast": 12, "slow": 26, "signal": 9}
            }
        ]
    }

@app.post("/api/v2/strategies", tags=["Strategies"])
async def configure_strategy(strategy: StrategyConfig):
    """Configure a trading strategy"""
    try:
        # Configure strategy logic here
        return {
            "status": "configured",
            "strategy": strategy.name,
            "enabled": strategy.enabled,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Risk Management endpoints
@app.get("/api/v2/risk/settings", tags=["Risk Management"])
async def get_risk_settings():
    """Get current risk management settings"""
    return RiskSettings(
        max_position_size=0.2,
        max_daily_loss=0.05,
        max_drawdown=0.15,
        stop_loss_percent=2.0,
        take_profit_percent=3.0,
        use_trailing_stop=False
    )

@app.put("/api/v2/risk/settings", tags=["Risk Management"])
async def update_risk_settings(settings: RiskSettings):
    """Update risk management settings"""
    try:
        # Update risk settings logic here
        risk_manager.update_settings(
            max_position_size=settings.max_position_size,
            max_daily_loss=settings.max_daily_loss,
            max_drawdown=settings.max_drawdown
        )
        
        return {
            "status": "updated",
            "settings": settings,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/risk/exposure", tags=["Risk Management"])
async def get_risk_exposure():
    """Get current risk exposure"""
    return {
        "total_exposure": 1500.00,
        "position_count": 2,
        "leverage_used": 5.5,
        "margin_used": 750.00,
        "available_margin": 9250.00,
        "current_drawdown": 2.5,
        "daily_loss": -125.50,
        "risk_level": "medium"
    }

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data"""
    await manager.connect(websocket)
    
    try:
        # Register data callbacks
        async def on_ticker(data):
            await manager.broadcast({"type": "ticker", "data": data})
            
        async def on_trade(data):
            await manager.broadcast({"type": "trade", "data": data})
            
        data_service.register_callback('ticker', on_ticker)
        data_service.register_callback('trade', on_trade)
        
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get('type') == 'subscribe':
                channel = message.get('channel')
                await websocket.send_json({
                    "type": "subscribed",
                    "channel": channel
                })
            elif message.get('type') == 'ping':
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting FastAPI application...")
    
    # Start data service
    asyncio.create_task(data_service.start())
    
    logger.info("All services initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down FastAPI application...")
    
    # Stop services
    await data_service.stop()
    
    logger.info("Shutdown complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)