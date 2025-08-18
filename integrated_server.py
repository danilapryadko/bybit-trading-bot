#!/usr/bin/env python3
"""
Integrated GraphQL + WebSocket Server for Bybit Trading Bot
"""
import asyncio
import json
import logging
from typing import Set, Dict, Any
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
import uvicorn

# Import GraphQL components
from ariadne import QueryType, MutationType, make_executable_schema
from ariadne.asgi import GraphQL

# Import bot components
try:
    from bybit_connector import get_bybit_connector
    from database.service import DatabaseService
except ImportError:
    get_bybit_connector = None
    DatabaseService = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Bybit Trading Bot API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: Dict[WebSocket, Set[str]] = {}
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        self.subscriptions[websocket] = set()
        logger.info(f"WebSocket client connected. Total: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        self.subscriptions.pop(websocket, None)
        logger.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")
        
    async def broadcast(self, message: dict, channel: str = None):
        """Broadcast message to all connected clients"""
        message_str = json.dumps(message)
        disconnected = set()
        
        for connection in self.active_connections:
            if channel is None or channel in self.subscriptions.get(connection, set()):
                try:
                    await connection.send_text(message_str)
                except Exception as e:
                    logger.error(f"Error broadcasting: {e}")
                    disconnected.add(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# GraphQL Schema
type_defs = """
    type Query {
        health: Health!
        marketData(symbol: String): MarketData
        positions: [Position!]!
        balance: Balance!
        strategies: [Strategy!]!
    }
    
    type Mutation {
        placeOrder(symbol: String!, side: String!, amount: Float!): Order!
        cancelOrder(orderId: String!): Boolean!
        closePosition(symbol: String!): Boolean!
    }
    
    type Health {
        status: String!
        message: String!
        timestamp: String!
    }
    
    type MarketData {
        symbol: String!
        lastPrice: Float!
        volume24h: Float!
        change24h: Float!
    }
    
    type Position {
        id: String!
        symbol: String!
        side: String!
        size: Float!
        entryPrice: Float!
        unrealizedPnl: Float!
    }
    
    type Balance {
        total: Float!
        available: Float!
        used: Float!
    }
    
    type Order {
        id: String!
        symbol: String!
        side: String!
        amount: Float!
        price: Float
        status: String!
    }
    
    type Strategy {
        id: String!
        name: String!
        enabled: Boolean!
        performance: Float!
    }
"""

# GraphQL Resolvers
query = QueryType()
mutation = MutationType()

@query.field("health")
async def resolve_health(*_):
    try:
        connector = get_bybit_connector() if get_bybit_connector else None
        return {
            "status": "healthy",
            "message": "API is running",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@query.field("marketData")
async def resolve_market_data(*_, symbol="BTCUSDT"):
    try:
        if get_bybit_connector:
            connector = get_bybit_connector()
            ticker = connector.get_ticker(symbol)
            return {
                "symbol": symbol,
                "lastPrice": float(ticker.get("lastPrice", 0)),
                "volume24h": float(ticker.get("volume24h", 0)),
                "change24h": float(ticker.get("price24hPcnt", 0)) * 100
            }
    except:
        pass
    
    # Return mock data if connector not available
    return {
        "symbol": symbol,
        "lastPrice": 50000.0,
        "volume24h": 1000000.0,
        "change24h": 2.5
    }

@query.field("positions")
async def resolve_positions(*_):
    try:
        if get_bybit_connector:
            connector = get_bybit_connector()
            positions = connector.get_positions()
            return [{
                "id": str(i),
                "symbol": p.get("symbol"),
                "side": p.get("side"),
                "size": float(p.get("size", 0)),
                "entryPrice": float(p.get("avgPrice", 0)),
                "unrealizedPnl": float(p.get("unrealisedPnl", 0))
            } for i, p in enumerate(positions)]
    except:
        pass
    return []

@query.field("balance")
async def resolve_balance(*_):
    try:
        if get_bybit_connector:
            connector = get_bybit_connector()
            balance = connector.get_balance()
            return {
                "total": float(balance.get("totalEquity", 0)),
                "available": float(balance.get("availableBalance", 0)),
                "used": float(balance.get("totalMarginBalance", 0))
            }
    except:
        pass
    
    return {
        "total": 10000.0,
        "available": 8000.0,
        "used": 2000.0
    }

@query.field("strategies")
async def resolve_strategies(*_):
    return [
        {"id": "1", "name": "RSI Strategy", "enabled": True, "performance": 15.5},
        {"id": "2", "name": "MA Crossover", "enabled": False, "performance": 8.2},
        {"id": "3", "name": "Grid Trading", "enabled": True, "performance": 22.1}
    ]

# Create GraphQL app
schema = make_executable_schema(type_defs, query, mutation)
graphql_app = GraphQL(schema, debug=True)

# Mount GraphQL
app.mount("/graphql", graphql_app)

# Health endpoint
@app.get("/health")
async def health():
    try:
        connector = get_bybit_connector() if get_bybit_connector else None
        bybit_connected = connector is not None
        
        return JSONResponse({
            "status": "healthy",
            "bybit_connected": bybit_connected,
            "server_time": str(int(datetime.utcnow().timestamp())),
            "mode": "MAINNET" if bybit_connected else "TESTNET"
        })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle subscriptions
            if message.get("type") == "subscribe":
                channel = message.get("channel")
                if channel:
                    manager.subscriptions[websocket].add(channel)
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "channel": channel
                    }))
            
            # Handle unsubscribe
            elif message.get("type") == "unsubscribe":
                channel = message.get("channel")
                if channel:
                    manager.subscriptions[websocket].discard(channel)
                    await websocket.send_text(json.dumps({
                        "type": "unsubscribed",
                        "channel": channel
                    }))
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Background task to send market updates
async def market_update_task():
    """Send market updates every 5 seconds"""
    while True:
        try:
            if manager.active_connections:
                # Get market data
                if get_bybit_connector:
                    connector = get_bybit_connector()
                    ticker = connector.get_ticker("BTCUSDT")
                    price = float(ticker.get("lastPrice", 0))
                else:
                    # Mock data
                    import random
                    price = 50000 + random.uniform(-500, 500)
                
                # Broadcast to subscribed clients
                await manager.broadcast({
                    "type": "market_update",
                    "data": {
                        "symbol": "BTCUSDT",
                        "price": price,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }, channel="market")
                
        except Exception as e:
            logger.error(f"Market update error: {e}")
        
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    asyncio.create_task(market_update_task())
    logger.info("Started market update background task")

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)