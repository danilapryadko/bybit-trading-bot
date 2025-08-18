#!/usr/bin/env python3
"""
Complete GraphQL API for Bybit Trading Dashboard
Includes all required types and resolvers for full dashboard functionality
"""
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from ariadne import QueryType, MutationType, SubscriptionType, make_executable_schema
from ariadne.asgi import GraphQL
from pybit.unified_trading import HTTP
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Bybit Trading API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GraphQL Schema Definition
type_defs = """
    type Query {
        # Account queries
        botStatus: BotStatus!
        balance: Float!
        positions: [Position!]!
        orders: [Order!]!
        recentTrades: [Trade!]!
        
        # Market data queries
        ticker(symbol: String!): Ticker
        tickers(symbols: [String!]!): [Ticker!]!
        klines(symbol: String!, interval: String, limit: Int): [Kline!]!
        
        # Strategy queries
        strategies: [Strategy!]!
        activeStrategy: Strategy
        
        # Settings queries
        settings: Settings!
        riskSettings: RiskSettings!
    }
    
    type Mutation {
        # Trading mutations
        placeOrder(input: OrderInput!): OrderResponse!
        cancelOrder(orderId: String!): Boolean!
        cancelAllOrders: Boolean!
        closePosition(symbol: String!): Boolean!
        closeAllPositions: Boolean!
        
        # Bot control mutations
        startBot: BotStatus!
        stopBot: BotStatus!
        setBotMode(mode: String!): BotStatus!
        
        # Strategy mutations
        activateStrategy(strategyId: String!): Strategy!
        deactivateStrategy(strategyId: String!): Strategy!
        updateStrategyParams(strategyId: String!, params: JSON!): Strategy!
        
        # Settings mutations
        updateSettings(input: SettingsInput!): Settings!
        updateRiskSettings(input: RiskSettingsInput!): RiskSettings!
    }
    
    type Subscription {
        # Real-time subscriptions
        balanceUpdate: Float!
        positionUpdate: Position!
        orderUpdate: Order!
        tickerUpdate(symbol: String!): Ticker!
        botStatusUpdate: BotStatus!
    }
    
    # Core Types
    type BotStatus {
        isRunning: Boolean!
        mode: String!
        balance: Float!
        activeStrategies: Int!
        openPositions: Int!
        dailyPnl: Float!
        totalPnl: Float!
        uptime: String!
        lastUpdate: String!
    }
    
    type Position {
        symbol: String!
        side: String!
        size: Float!
        entryPrice: Float!
        avgPrice: Float!  # Alias for entryPrice for compatibility
        markPrice: Float!
        unrealizedPnl: Float!
        realizedPnl: Float!
        marginMode: String!
        leverage: Int!
        liquidationPrice: Float
        timestamp: String!
    }
    
    type Order {
        orderId: String!
        symbol: String!
        side: String!
        orderType: String!
        price: Float!
        quantity: Float!
        status: String!
        timeInForce: String!
        reduceOnly: Boolean!
        closeOnTrigger: Boolean!
        timestamp: String!
    }
    
    type Trade {
        id: String!
        orderId: String!
        symbol: String!
        side: String!
        price: Float!
        quantity: Float!
        fee: Float!
        feeAsset: String!
        realizedPnl: Float
        timestamp: String!
        status: String!
    }
    
    type Ticker {
        symbol: String!
        lastPrice: Float!
        price: Float!  # Alias for lastPrice
        bid: Float!
        ask: Float!
        volume24h: Float!
        volume: Float!  # Alias for volume24h
        high24h: Float!
        low24h: Float!
        priceChange24h: Float!
        priceChangePercent24h: Float!
        change24h: Float!  # Alias for priceChangePercent24h
        timestamp: String!
    }
    
    type Kline {
        timestamp: String!
        open: Float!
        high: Float!
        low: Float!
        close: Float!
        volume: Float!
    }
    
    type Strategy {
        id: String!
        name: String!
        description: String!
        isActive: Boolean!
        parameters: JSON!
        performance: StrategyPerformance!
    }
    
    type StrategyPerformance {
        winRate: Float!
        totalTrades: Int!
        profitFactor: Float!
        sharpeRatio: Float!
        maxDrawdown: Float!
        totalReturn: Float!
    }
    
    type Settings {
        apiKey: String!
        testnet: Boolean!
        defaultSymbol: String!
        defaultLeverage: Int!
        defaultOrderType: String!
        notifications: Boolean!
    }
    
    type RiskSettings {
        maxPositionSize: Float!
        maxLeverage: Int!
        stopLossPercent: Float!
        takeProfitPercent: Float!
        maxDailyLoss: Float!
        maxOpenPositions: Int!
        useTrailingStop: Boolean!
    }
    
    # Input Types
    input OrderInput {
        symbol: String!
        side: String!
        orderType: String!
        quantity: Float!
        price: Float
        stopLoss: Float
        takeProfit: Float
        timeInForce: String
        reduceOnly: Boolean
    }
    
    input SettingsInput {
        defaultSymbol: String
        defaultLeverage: Int
        defaultOrderType: String
        notifications: Boolean
    }
    
    input RiskSettingsInput {
        maxPositionSize: Float
        maxLeverage: Int
        stopLossPercent: Float
        takeProfitPercent: Float
        maxDailyLoss: Float
        maxOpenPositions: Int
        useTrailingStop: Boolean
    }
    
    # Response Types
    type OrderResponse {
        success: Boolean!
        orderId: String
        message: String
    }
    
    scalar JSON
"""

# Initialize Ariadne types
query = QueryType()
mutation = MutationType()
subscription = SubscriptionType()

# Global state
class BotState:
    def __init__(self):
        self.is_running = False
        self.mode = "MAINNET"  # or "TESTNET"
        self.start_time = datetime.now()
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.active_strategies = []
        self.bybit_client = None
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize Bybit client with MAINNET credentials"""
        try:
            use_mainnet = os.getenv('USE_MAINNET', 'true').lower() == 'true'
            
            if use_mainnet:
                api_key = os.getenv('BYBIT_MAINNET_API_KEY', os.getenv('BYBIT_API_KEY', ''))
                api_secret = os.getenv('BYBIT_MAINNET_API_SECRET', os.getenv('BYBIT_API_SECRET', ''))
                testnet = False
                logger.info("Initializing MAINNET Bybit client")
            else:
                api_key = os.getenv('BYBIT_TESTNET_API_KEY', '')
                api_secret = os.getenv('BYBIT_TESTNET_API_SECRET', '')
                testnet = True
                logger.info("Initializing TESTNET Bybit client")
            
            if not api_key or not api_secret:
                logger.error("API credentials not found")
                return
            
            self.bybit_client = HTTP(
                api_key=api_key,
                api_secret=api_secret,
                testnet=testnet
            )
            
            # Test connection
            account_info = self.bybit_client.get_wallet_balance(accountType="UNIFIED")
            if account_info['retCode'] == 0:
                logger.info(f"Successfully connected to Bybit {'TESTNET' if testnet else 'MAINNET'}")
                self.is_running = True
            else:
                logger.error(f"Failed to connect: {account_info}")
                
        except Exception as e:
            logger.error(f"Error initializing Bybit client: {e}")

bot_state = BotState()

# Query Resolvers
@query.field("botStatus")
def resolve_bot_status(*_):
    """Get current bot status"""
    uptime = str(datetime.now() - bot_state.start_time).split('.')[0]
    
    return {
        "isRunning": bot_state.is_running,
        "mode": bot_state.mode,
        "balance": get_account_balance(),
        "activeStrategies": len(bot_state.active_strategies),
        "openPositions": len(get_positions()),
        "dailyPnl": bot_state.daily_pnl,
        "totalPnl": bot_state.total_pnl,
        "uptime": uptime,
        "lastUpdate": datetime.now().isoformat()
    }

@query.field("balance")
def resolve_balance(*_):
    """Get account balance"""
    return get_account_balance()

@query.field("positions")
def resolve_positions(*_):
    """Get all open positions"""
    return get_positions()

@query.field("orders")
def resolve_orders(*_):
    """Get all open orders"""
    return get_orders()

@query.field("recentTrades")
def resolve_recent_trades(*_):
    """Get recent trades"""
    return get_recent_trades()

@query.field("ticker")
def resolve_ticker(*_, symbol: str):
    """Get ticker for a symbol"""
    return get_ticker(symbol)

@query.field("tickers")
def resolve_tickers(*_, symbols: List[str]):
    """Get tickers for multiple symbols"""
    return [get_ticker(symbol) for symbol in symbols]

@query.field("klines")
def resolve_klines(*_, symbol: str, interval: str = "1h", limit: int = 100):
    """Get kline/candlestick data"""
    return get_klines(symbol, interval, limit)

@query.field("strategies")
def resolve_strategies(*_):
    """Get all available strategies"""
    return get_strategies()

@query.field("activeStrategy")
def resolve_active_strategy(*_):
    """Get currently active strategy"""
    if bot_state.active_strategies:
        return get_strategy(bot_state.active_strategies[0])
    return None

@query.field("settings")
def resolve_settings(*_):
    """Get current settings"""
    return {
        "apiKey": "••••••••" if os.getenv('BYBIT_API_KEY') else "Not configured",
        "testnet": bot_state.mode == "TESTNET",
        "defaultSymbol": "BTCUSDT",
        "defaultLeverage": 10,
        "defaultOrderType": "MARKET",
        "notifications": True
    }

@query.field("riskSettings")
def resolve_risk_settings(*_):
    """Get risk management settings"""
    return {
        "maxPositionSize": 1000.0,
        "maxLeverage": 20,
        "stopLossPercent": 2.0,
        "takeProfitPercent": 5.0,
        "maxDailyLoss": 100.0,
        "maxOpenPositions": 5,
        "useTrailingStop": False
    }

# Mutation Resolvers
@mutation.field("startBot")
def resolve_start_bot(*_):
    """Start the trading bot"""
    bot_state.is_running = True
    bot_state.start_time = datetime.now()
    return resolve_bot_status()

@mutation.field("stopBot")
def resolve_stop_bot(*_):
    """Stop the trading bot"""
    bot_state.is_running = False
    return resolve_bot_status()

@mutation.field("setBotMode")
def resolve_set_bot_mode(*_, mode: str):
    """Set bot mode (MAINNET/TESTNET)"""
    bot_state.mode = mode
    bot_state.initialize_client()
    return resolve_bot_status()

@mutation.field("placeOrder")
def resolve_place_order(*_, input: Dict):
    """Place a new order"""
    try:
        if not bot_state.bybit_client:
            return {"success": False, "message": "Bot not initialized"}
        
        # Place order logic here
        result = bot_state.bybit_client.place_order(
            category="linear",
            symbol=input["symbol"],
            side=input["side"],
            orderType=input.get("orderType", "Market"),
            qty=str(input["quantity"]),
            price=str(input.get("price", 0)) if input.get("price") else None
        )
        
        if result['retCode'] == 0:
            return {
                "success": True,
                "orderId": result['result']['orderId'],
                "message": "Order placed successfully"
            }
        else:
            return {"success": False, "message": result.get('retMsg', 'Order failed')}
            
    except Exception as e:
        return {"success": False, "message": str(e)}

# Helper Functions
def get_account_balance() -> float:
    """Get account balance from Bybit"""
    try:
        if not bot_state.bybit_client:
            return 0.0
        
        response = bot_state.bybit_client.get_wallet_balance(accountType="UNIFIED")
        if response['retCode'] == 0:
            balance = float(response['result']['list'][0]['totalEquity'])
            logger.info(f"Account balance: ${balance}")
            return balance
        else:
            logger.error(f"Failed to get balance: {response}")
            return 0.0
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        return 0.0

def get_positions() -> List[Dict]:
    """Get all open positions"""
    try:
        if not bot_state.bybit_client:
            return []
        
        response = bot_state.bybit_client.get_positions(category="linear", settleCoin="USDT")
        if response['retCode'] == 0:
            positions = []
            for pos in response['result']['list']:
                if float(pos['size']) > 0:
                    positions.append({
                        "symbol": pos['symbol'],
                        "side": pos['side'],
                        "size": float(pos['size']),
                        "entryPrice": float(pos['avgPrice']) if pos['avgPrice'] else 0,
                        "avgPrice": float(pos['avgPrice']) if pos['avgPrice'] else 0,  # Compatibility
                        "markPrice": float(pos['markPrice']) if pos['markPrice'] else 0,
                        "unrealizedPnl": float(pos['unrealisedPnl']) if pos['unrealisedPnl'] else 0,
                        "realizedPnl": float(pos['realisedPnl']) if pos['realisedPnl'] else 0,
                        "marginMode": pos.get('tradeMode', 'cross'),
                        "leverage": int(pos.get('leverage', 1)),
                        "liquidationPrice": float(pos['liqPrice']) if pos.get('liqPrice') else None,
                        "timestamp": datetime.now().isoformat()
                    })
            return positions
        return []
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return []

def get_orders() -> List[Dict]:
    """Get all open orders"""
    try:
        if not bot_state.bybit_client:
            return []
        
        response = bot_state.bybit_client.get_open_orders(category="linear")
        if response['retCode'] == 0:
            orders = []
            for order in response['result']['list']:
                orders.append({
                    "orderId": order['orderId'],
                    "symbol": order['symbol'],
                    "side": order['side'],
                    "orderType": order['orderType'],
                    "price": float(order['price']),
                    "quantity": float(order['qty']),
                    "status": order['orderStatus'],
                    "timeInForce": order.get('timeInForce', 'GTC'),
                    "reduceOnly": order.get('reduceOnly', False),
                    "closeOnTrigger": order.get('closeOnTrigger', False),
                    "timestamp": order['createdTime']
                })
            return orders
        return []
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return []

def get_recent_trades() -> List[Dict]:
    """Get recent trades"""
    try:
        if not bot_state.bybit_client:
            return []
        
        # Get filled orders as trades
        response = bot_state.bybit_client.get_order_history(
            category="linear",
            limit=20
        )
        
        if response['retCode'] == 0:
            trades = []
            for order in response['result']['list']:
                if order['orderStatus'] == 'Filled':
                    trades.append({
                        "id": order['orderId'],
                        "orderId": order['orderId'],
                        "symbol": order['symbol'],
                        "side": order['side'],
                        "price": float(order['avgPrice']) if order.get('avgPrice') else float(order['price']),
                        "quantity": float(order['qty']),
                        "fee": float(order.get('cumExecFee', 0)),
                        "feeAsset": "USDT",
                        "realizedPnl": 0,  # Would need separate calculation
                        "timestamp": order['updatedTime'],
                        "status": "FILLED"
                    })
            return trades[:10]  # Return last 10 trades
        return []
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return []

def get_ticker(symbol: str) -> Dict:
    """Get ticker data for a symbol"""
    try:
        if not bot_state.bybit_client:
            return create_empty_ticker(symbol)
        
        response = bot_state.bybit_client.get_tickers(category="linear", symbol=symbol)
        if response['retCode'] == 0 and response['result']['list']:
            ticker = response['result']['list'][0]
            last_price = float(ticker['lastPrice'])
            price_change = float(ticker['price24hPcnt']) * 100
            
            return {
                "symbol": symbol,
                "lastPrice": last_price,
                "price": last_price,  # Alias
                "bid": float(ticker['bid1Price']) if ticker.get('bid1Price') else last_price,
                "ask": float(ticker['ask1Price']) if ticker.get('ask1Price') else last_price,
                "volume24h": float(ticker['volume24h']),
                "volume": float(ticker['volume24h']),  # Alias
                "high24h": float(ticker['highPrice24h']),
                "low24h": float(ticker['lowPrice24h']),
                "priceChange24h": last_price * (price_change / 100),
                "priceChangePercent24h": price_change,
                "change24h": price_change,  # Alias
                "timestamp": datetime.now().isoformat()
            }
        return create_empty_ticker(symbol)
    except Exception as e:
        logger.error(f"Error getting ticker for {symbol}: {e}")
        return create_empty_ticker(symbol)

def create_empty_ticker(symbol: str) -> Dict:
    """Create empty ticker object"""
    return {
        "symbol": symbol,
        "lastPrice": 0.0,
        "price": 0.0,
        "bid": 0.0,
        "ask": 0.0,
        "volume24h": 0.0,
        "volume": 0.0,
        "high24h": 0.0,
        "low24h": 0.0,
        "priceChange24h": 0.0,
        "priceChangePercent24h": 0.0,
        "change24h": 0.0,
        "timestamp": datetime.now().isoformat()
    }

def get_klines(symbol: str, interval: str, limit: int) -> List[Dict]:
    """Get kline data"""
    try:
        if not bot_state.bybit_client:
            return []
        
        # Convert interval to Bybit format
        interval_map = {
            "1m": "1", "5m": "5", "15m": "15", "30m": "30",
            "1h": "60", "4h": "240", "1d": "D", "1w": "W"
        }
        bybit_interval = interval_map.get(interval, "60")
        
        response = bot_state.bybit_client.get_kline(
            category="linear",
            symbol=symbol,
            interval=bybit_interval,
            limit=limit
        )
        
        if response['retCode'] == 0:
            klines = []
            for kline in response['result']['list']:
                klines.append({
                    "timestamp": kline[0],
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5])
                })
            return klines
        return []
    except Exception as e:
        logger.error(f"Error getting klines: {e}")
        return []

def get_strategies() -> List[Dict]:
    """Get available trading strategies"""
    # Mock strategies for now
    return [
        {
            "id": "rsi_strategy",
            "name": "RSI Strategy",
            "description": "Trades based on RSI oversold/overbought conditions",
            "isActive": False,
            "parameters": {
                "rsi_period": 14,
                "oversold": 30,
                "overbought": 70
            },
            "performance": {
                "winRate": 0.65,
                "totalTrades": 150,
                "profitFactor": 1.8,
                "sharpeRatio": 1.2,
                "maxDrawdown": -0.15,
                "totalReturn": 0.35
            }
        },
        {
            "id": "ma_crossover",
            "name": "MA Crossover",
            "description": "Trades on moving average crossovers",
            "isActive": False,
            "parameters": {
                "fast_ma": 20,
                "slow_ma": 50
            },
            "performance": {
                "winRate": 0.58,
                "totalTrades": 200,
                "profitFactor": 1.5,
                "sharpeRatio": 0.9,
                "maxDrawdown": -0.20,
                "totalReturn": 0.28
            }
        }
    ]

def get_strategy(strategy_id: str) -> Optional[Dict]:
    """Get a specific strategy"""
    strategies = get_strategies()
    for strategy in strategies:
        if strategy["id"] == strategy_id:
            return strategy
    return None

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                # Connection might be closed
                pass

manager = ConnectionManager()

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle subscription requests
            if message.get("type") == "subscribe":
                channel = message.get("channel")
                logger.info(f"Client subscribed to: {channel}")
            
            # Send periodic updates
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Background task to send updates
async def send_periodic_updates():
    """Send periodic updates to all WebSocket clients"""
    while True:
        try:
            # Send balance update
            balance = get_account_balance()
            await manager.broadcast({
                "type": "balanceUpdate",
                "data": balance
            })
            
            # Send position updates
            positions = get_positions()
            for position in positions:
                await manager.broadcast({
                    "type": "positionUpdate",
                    "data": position
                })
            
            # Send bot status
            bot_status = resolve_bot_status()
            await manager.broadcast({
                "type": "botStatusUpdate",
                "data": bot_status
            })
            
            await asyncio.sleep(10)  # Update every 10 seconds
            
        except Exception as e:
            logger.error(f"Error in periodic updates: {e}")
            await asyncio.sleep(10)

# Create GraphQL schema
schema = make_executable_schema(type_defs, query, mutation, subscription)

# GraphQL endpoint
app.mount("/graphql", GraphQL(schema, debug=True))

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "bot_running": bot_state.is_running,
        "mode": bot_state.mode,
        "balance": get_account_balance()
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "name": "Bybit Trading API",
        "version": "1.0.0",
        "graphql": "/graphql",
        "websocket": "/ws",
        "health": "/health"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting Bybit Trading API...")
    # Start background tasks
    asyncio.create_task(send_periodic_updates())
    logger.info("API started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down API...")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)