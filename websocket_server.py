import asyncio
import json
import logging
from typing import Set, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: Dict[WebSocket, Set[str]] = {}
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        self.subscriptions[websocket] = set()
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        self.subscriptions.pop(websocket, None)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")
        
    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            
    async def broadcast(self, message: str, channel: str = None):
        """Broadcast message to all connected clients subscribed to channel"""
        for connection in self.active_connections:
            if channel is None or channel in self.subscriptions.get(connection, set()):
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error broadcasting: {e}")
                    
    def subscribe(self, websocket: WebSocket, channel: str):
        if websocket in self.subscriptions:
            self.subscriptions[websocket].add(channel)
            logger.info(f"Client subscribed to {channel}")
            
    def unsubscribe(self, websocket: WebSocket, channel: str):
        if websocket in self.subscriptions:
            self.subscriptions[websocket].discard(channel)
            logger.info(f"Client unsubscribed from {channel}")

manager = ConnectionManager()

# Market data generator (simulated)
async def generate_market_data():
    """Generate simulated market data for testing"""
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
    
    while True:
        try:
            # Generate ticker updates
            for symbol in symbols:
                ticker_data = {
                    "type": "ticker",
                    "data": {
                        "symbol": symbol,
                        "lastPrice": round(random.uniform(30000, 70000) if symbol == 'BTCUSDT' else random.uniform(100, 5000), 2),
                        "bidPrice": round(random.uniform(30000, 70000) if symbol == 'BTCUSDT' else random.uniform(100, 5000), 2),
                        "askPrice": round(random.uniform(30000, 70000) if symbol == 'BTCUSDT' else random.uniform(100, 5000), 2),
                        "volume24h": round(random.uniform(1000000, 10000000), 2),
                        "priceChange24h": round(random.uniform(-5, 5), 2),
                        "priceChangePercent24h": round(random.uniform(-10, 10), 2),
                        "timestamp": datetime.now().isoformat()
                    }
                }
                await manager.broadcast(json.dumps(ticker_data), "ticker")
                
            # Generate trade updates
            symbol = random.choice(symbols)
            trade_data = {
                "type": "trade",
                "data": {
                    "symbol": symbol,
                    "price": round(random.uniform(30000, 70000) if symbol == 'BTCUSDT' else random.uniform(100, 5000), 2),
                    "quantity": round(random.uniform(0.001, 1), 4),
                    "side": random.choice(['buy', 'sell']),
                    "timestamp": datetime.now().isoformat()
                }
            }
            await manager.broadcast(json.dumps(trade_data), "trades")
            
            # Generate position updates occasionally
            if random.random() < 0.1:  # 10% chance
                position_data = {
                    "type": "position",
                    "data": {
                        "symbol": random.choice(symbols),
                        "side": random.choice(['Buy', 'Sell']),
                        "size": round(random.uniform(0.01, 1), 4),
                        "entryPrice": round(random.uniform(30000, 70000), 2),
                        "markPrice": round(random.uniform(30000, 70000), 2),
                        "unrealizedPnl": round(random.uniform(-1000, 1000), 2),
                        "realizedPnl": round(random.uniform(-500, 500), 2),
                        "margin": round(random.uniform(100, 10000), 2),
                        "leverage": random.choice([1, 2, 5, 10, 20]),
                        "timestamp": datetime.now().isoformat()
                    }
                }
                await manager.broadcast(json.dumps(position_data), "positions")
                
            # Generate trading signals occasionally
            if random.random() < 0.05:  # 5% chance
                signal_data = {
                    "type": "signal",
                    "data": {
                        "id": f"sig_{datetime.now().timestamp()}",
                        "symbol": random.choice(symbols),
                        "action": random.choice(['BUY', 'SELL', 'HOLD']),
                        "strategy": random.choice(['LSTM', 'RandomForest', 'XGBoost', 'Ensemble']),
                        "confidence": round(random.uniform(60, 95), 1),
                        "entryPrice": round(random.uniform(30000, 70000), 2),
                        "targetPrice": round(random.uniform(31000, 71000), 2),
                        "stopLoss": round(random.uniform(29000, 69000), 2),
                        "timestamp": datetime.now().isoformat()
                    }
                }
                await manager.broadcast(json.dumps(signal_data), "signals")
                
            await asyncio.sleep(2)  # Update every 2 seconds
            
        except Exception as e:
            logger.error(f"Error generating market data: {e}")
            await asyncio.sleep(5)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get('type') == 'subscribe':
                channel = message.get('channel', 'all')
                manager.subscribe(websocket, channel)
                await manager.send_personal_message(
                    json.dumps({"type": "subscribed", "channel": channel}),
                    websocket
                )
                
            elif message.get('type') == 'unsubscribe':
                channel = message.get('channel', 'all')
                manager.unsubscribe(websocket, channel)
                await manager.send_personal_message(
                    json.dumps({"type": "unsubscribed", "channel": channel}),
                    websocket
                )
                
            elif message.get('type') == 'ping':
                await manager.send_personal_message(
                    json.dumps({"type": "pong"}),
                    websocket
                )
                
            elif message.get('type') == 'place_order':
                # Handle order placement
                order_data = message.get('data', {})
                # In production, this would interface with the trading bot
                response = {
                    "type": "order",
                    "data": {
                        "orderId": f"ord_{datetime.now().timestamp()}",
                        "symbol": order_data.get('symbol'),
                        "side": order_data.get('side'),
                        "orderType": order_data.get('orderType'),
                        "quantity": order_data.get('quantity'),
                        "price": order_data.get('price'),
                        "status": "New",
                        "createdTime": datetime.now().isoformat()
                    }
                }
                await manager.send_personal_message(json.dumps(response), websocket)
                
            elif message.get('type') == 'cancel_order':
                # Handle order cancellation
                order_id = message.get('data', {}).get('orderId')
                response = {
                    "type": "order",
                    "data": {
                        "orderId": order_id,
                        "status": "Cancelled",
                        "updatedTime": datetime.now().isoformat()
                    }
                }
                await manager.send_personal_message(json.dumps(response), websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    # Start market data generator
    asyncio.create_task(generate_market_data())
    logger.info("WebSocket server started")

@app.get("/")
async def root():
    return {"message": "WebSocket server is running", "ws_endpoint": "/ws"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "connections": len(manager.active_connections),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)