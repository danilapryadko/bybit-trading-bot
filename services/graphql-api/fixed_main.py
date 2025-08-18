#!/usr/bin/env python3
"""
Fixed GraphQL API for Bybit Trading Bot with MAINNET support
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add parent directories to path for imports
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from ariadne import QueryType, MutationType, make_executable_schema
from ariadne.asgi import GraphQL
from pybit.unified_trading import HTTP
import uvicorn

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Bybit Trading Bot API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bybit connection
def get_bybit_session():
    """Get Bybit session based on environment"""
    use_mainnet = os.getenv('USE_MAINNET', 'false').lower() == 'true'
    
    if use_mainnet:
        # MAINNET configuration
        api_key = os.getenv('BYBIT_MAINNET_API_KEY', os.getenv('BYBIT_API_KEY', ''))
        api_secret = os.getenv('BYBIT_MAINNET_API_SECRET', os.getenv('BYBIT_API_SECRET', ''))
        testnet = False
    else:
        # TESTNET configuration
        api_key = os.getenv('BYBIT_API_KEY', '')
        api_secret = os.getenv('BYBIT_API_SECRET', '')
        testnet = True
    
    logger.info(f"Connecting to Bybit {'TESTNET' if testnet else 'MAINNET'}")
    logger.info(f"API Key: {api_key[:5]}..." if api_key else "No API key")
    
    return HTTP(
        testnet=testnet,
        api_key=api_key,
        api_secret=api_secret
    )

# Initialize Bybit session
try:
    bybit_session = get_bybit_session()
except Exception as e:
    logger.error(f"Failed to initialize Bybit session: {e}")
    bybit_session = None

# GraphQL Schema
type_defs = """
    type Query {
        balance: Balance!
        positions: [Position!]!
        marketData(symbol: String): MarketData
        health: Health!
    }
    
    type Mutation {
        placeOrder(symbol: String!, side: String!, amount: Float!): Order!
        closePosition(symbol: String!): Boolean!
    }
    
    type Balance {
        total: Float!
        available: Float!
        used: Float!
    }
    
    type Position {
        id: String!
        symbol: String!
        side: String!
        size: Float!
        entryPrice: Float!
        markPrice: Float!
        unrealizedPnl: Float!
        realizedPnl: Float!
    }
    
    type MarketData {
        symbol: String!
        lastPrice: Float!
        bidPrice: Float!
        askPrice: Float!
        volume24h: Float!
        change24h: Float!
    }
    
    type Order {
        id: String!
        symbol: String!
        side: String!
        amount: Float!
        status: String!
    }
    
    type Health {
        status: String!
        message: String!
        timestamp: String!
    }
"""

# GraphQL Resolvers
query = QueryType()
mutation = MutationType()

@query.field("balance")
async def resolve_balance(*_):
    """Get account balance"""
    try:
        if bybit_session:
            result = bybit_session.get_wallet_balance(accountType="UNIFIED")
            if result["retCode"] == 0:
                balance_info = result["result"]["list"][0]
                return {
                    "total": float(balance_info.get("totalEquity", 0)),
                    "available": float(balance_info.get("totalAvailableBalance", 0)),
                    "used": float(balance_info.get("totalMarginBalance", 0))
                }
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
    
    return {
        "total": 0.0,
        "available": 0.0,
        "used": 0.0
    }

@query.field("positions")
async def resolve_positions(*_):
    """Get open positions"""
    try:
        if bybit_session:
            result = bybit_session.get_positions(category="linear", settleCoin="USDT")
            if result["retCode"] == 0:
                positions = []
                for i, pos in enumerate(result["result"]["list"]):
                    if float(pos.get("size", 0)) > 0:
                        positions.append({
                            "id": str(i),
                            "symbol": pos.get("symbol", ""),
                            "side": pos.get("side", ""),
                            "size": float(pos.get("size", 0)),
                            "entryPrice": float(pos.get("avgPrice", 0)),
                            "markPrice": float(pos.get("markPrice", 0)),
                            "unrealizedPnl": float(pos.get("unrealisedPnl", 0)),
                            "realizedPnl": float(pos.get("realisedPnl", 0))
                        })
                return positions
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
    
    return []

@query.field("marketData")
async def resolve_market_data(*_, symbol="BTCUSDT"):
    """Get market data for a symbol"""
    try:
        if bybit_session:
            result = bybit_session.get_tickers(category="linear", symbol=symbol)
            if result["retCode"] == 0 and result["result"]["list"]:
                ticker = result["result"]["list"][0]
                return {
                    "symbol": symbol,
                    "lastPrice": float(ticker.get("lastPrice", 0)),
                    "bidPrice": float(ticker.get("bid1Price", 0)),
                    "askPrice": float(ticker.get("ask1Price", 0)),
                    "volume24h": float(ticker.get("volume24h", 0)),
                    "change24h": float(ticker.get("price24hPcnt", 0)) * 100
                }
    except Exception as e:
        logger.error(f"Error getting market data: {e}")
    
    return {
        "symbol": symbol,
        "lastPrice": 0.0,
        "bidPrice": 0.0,
        "askPrice": 0.0,
        "volume24h": 0.0,
        "change24h": 0.0
    }

@query.field("health")
async def resolve_health(*_):
    """Health check"""
    use_mainnet = os.getenv('USE_MAINNET', 'false').lower() == 'true'
    return {
        "status": "healthy",
        "message": f"API running in {'MAINNET' if use_mainnet else 'TESTNET'} mode",
        "timestamp": datetime.utcnow().isoformat()
    }

@mutation.field("placeOrder")
async def resolve_place_order(*_, symbol: str, side: str, amount: float):
    """Place a new order"""
    try:
        if bybit_session:
            # Calculate quantity based on current price
            ticker = bybit_session.get_tickers(category="linear", symbol=symbol)
            if ticker["retCode"] == 0:
                price = float(ticker["result"]["list"][0]["lastPrice"])
                qty = round(amount / price, 4)
                
                result = bybit_session.place_order(
                    category="linear",
                    symbol=symbol,
                    side=side.capitalize(),
                    orderType="Market",
                    qty=str(qty)
                )
                
                if result["retCode"] == 0:
                    return {
                        "id": result["result"]["orderId"],
                        "symbol": symbol,
                        "side": side,
                        "amount": amount,
                        "status": "Submitted"
                    }
    except Exception as e:
        logger.error(f"Error placing order: {e}")
    
    return {
        "id": "error",
        "symbol": symbol,
        "side": side,
        "amount": amount,
        "status": "Failed"
    }

@mutation.field("closePosition")
async def resolve_close_position(*_, symbol: str):
    """Close a position"""
    try:
        if bybit_session:
            # Get position info
            positions = bybit_session.get_positions(category="linear", symbol=symbol)
            if positions["retCode"] == 0 and positions["result"]["list"]:
                pos = positions["result"]["list"][0]
                if float(pos["size"]) > 0:
                    # Close position with opposite order
                    side = "Sell" if pos["side"] == "Buy" else "Buy"
                    result = bybit_session.place_order(
                        category="linear",
                        symbol=symbol,
                        side=side,
                        orderType="Market",
                        qty=pos["size"],
                        reduceOnly=True
                    )
                    return result["retCode"] == 0
    except Exception as e:
        logger.error(f"Error closing position: {e}")
    
    return False

# Create GraphQL app
schema = make_executable_schema(type_defs, query, mutation)
graphql_app = GraphQL(schema, debug=True)

# Mount GraphQL
app.mount("/graphql", graphql_app)

# Health endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    use_mainnet = os.getenv('USE_MAINNET', 'false').lower() == 'true'
    
    # Test Bybit connection
    bybit_connected = False
    try:
        if bybit_session:
            result = bybit_session.get_server_time()
            bybit_connected = result["retCode"] == 0
    except:
        pass
    
    return JSONResponse({
        "status": "healthy",
        "bybit_connected": bybit_connected,
        "server_time": str(int(datetime.utcnow().timestamp())),
        "mode": "MAINNET" if use_mainnet else "TESTNET"
    })

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Bybit Trading Bot API", "graphql": "/graphql", "health": "/health"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting API server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)