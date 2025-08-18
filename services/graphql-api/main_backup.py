#!/usr/bin/env python3
"""
GraphQL API Microservice
Provides GraphQL API for Dashboard and external integrations
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add parent directories to path for imports
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for GraphQL API service"""
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║     Bybit Trading Bot - GraphQL API Service         ║
    ║     Microservice Architecture v2.0                  ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    logger.info("🚀 Starting GraphQL API Microservice...")
    logger.info("📊 GraphQL endpoint: http://0.0.0.0:8000/graphql")
    logger.info("🏥 Health check: http://0.0.0.0:8000/health")
    logger.info("-" * 50)
    
    # Run database migration if needed
    try:
        if os.getenv('FLY_APP_NAME'):
            logger.info("Checking database migration...")
            from database.migrate_to_postgres import main as migrate
            migrate()
    except Exception as e:
        logger.warning(f"Migration check: {e}")
    
    try:
        import uvicorn
        from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
        from fastapi.middleware.cors import CORSMiddleware
        from ariadne import QueryType, make_executable_schema, graphql_sync
        from ariadne.asgi import GraphQL
        from bybit_connector import get_bybit_connector
        from database.service import DatabaseService
        import json
        import asyncio
        
        # Initialize services
        logger.info("Initializing Bybit connector...")
        connector = get_bybit_connector()
        
        # Debug DATABASE_URL
        db_url = os.getenv('DATABASE_URL', 'not set')
        logger.info(f"DATABASE_URL from env: {db_url[:50] if db_url != 'not set' else 'not set'}...")
        
        logger.info("Initializing database service...")
        db_service = DatabaseService()
        
        # Create enhanced API handler
        class APIHandler:
            def __init__(self, bybit_connector, db_service):
                self.connector = bybit_connector
                self.db = db_service
                self.is_mainnet = os.getenv('USE_MAINNET', 'false').lower() == 'true'
                
            def get_balance(self):
                """Get real balance from Bybit account"""
                try:
                    balance = self.connector.get_balance()
                    logger.info(f"Retrieved balance: {balance} USDT")
                    return float(balance)
                except Exception as e:
                    logger.error(f"Error getting balance: {e}")
                    return 0.0
                
            def get_positions(self):
                """Get real positions from Bybit"""
                try:
                    positions = self.connector.get_positions()
                    logger.info(f"Retrieved {len(positions)} positions")
                    return positions
                except Exception as e:
                    logger.error(f"Error getting positions: {e}")
                    return []
                
            def get_ticker(self, symbol):
                """Get real ticker data from Bybit"""
                try:
                    ticker = self.connector.get_ticker(symbol)
                    return ticker
                except Exception as e:
                    logger.error(f"Error getting ticker for {symbol}: {e}")
                    return None
            
            def get_klines(self, symbol, interval='15', limit=100):
                """Get kline/candlestick data from Bybit"""
                try:
                    klines = self.connector.get_klines(symbol, interval, limit)
                    return klines
                except Exception as e:
                    logger.error(f"Error getting klines for {symbol}: {e}")
                    return []
                    
            def get_recent_trades(self, limit=10):
                """Get recent trades from database"""
                try:
                    # Fetch from database
                    trades = self.db.get_recent_trades(limit)
                    return trades
                except Exception as e:
                    logger.error(f"Error getting recent trades: {e}")
                    return []
            
            def place_order(self, symbol, side, order_type, quantity, price=None, stop_price=None, time_in_force='GTC'):
                """Place an order on Bybit"""
                try:
                    # Validate balance
                    balance = self.get_balance()
                    required_margin = quantity * (price if price else self.get_ticker(symbol).get('price', 0))
                    
                    if required_margin > balance:
                        return {
                            'success': False,
                            'message': f'Insufficient balance. Required: {required_margin:.2f}, Available: {balance:.2f}'
                        }
                    
                    # Place order via connector
                    order_id = self.connector.place_order(
                        symbol=symbol,
                        side=side,
                        quantity=quantity,
                        order_type=order_type,
                        price=price
                    )
                    
                    if order_id:
                        return {
                            'success': True,
                            'orderId': order_id,
                            'message': 'Order placed successfully',
                            'order': {
                                'orderId': order_id,
                                'symbol': symbol,
                                'side': side,
                                'orderType': order_type,
                                'quantity': quantity,
                                'price': price,
                                'status': 'New',
                                'createdAt': datetime.now().isoformat()
                            }
                        }
                    else:
                        return {
                            'success': False,
                            'message': 'Failed to place order'
                        }
                        
                except Exception as e:
                    logger.error(f"Error placing order: {e}")
                    return {
                        'success': False,
                        'message': str(e)
                    }
            
            def cancel_order(self, order_id, symbol=None):
                """Cancel an order"""
                try:
                    # If symbol not provided, try to find it from open orders
                    if not symbol:
                        orders = self.connector.get_open_orders()
                        order = next((o for o in orders if o['orderId'] == order_id), None)
                        if order:
                            symbol = order['symbol']
                        else:
                            return {
                                'success': False,
                                'message': 'Order not found'
                            }
                    
                    success = self.connector.cancel_order(symbol, order_id)
                    
                    if success:
                        return {
                            'success': True,
                            'message': f'Order {order_id} cancelled successfully'
                        }
                    else:
                        return {
                            'success': False,
                            'message': 'Failed to cancel order'
                        }
                        
                except Exception as e:
                    logger.error(f"Error cancelling order: {e}")
                    return {
                        'success': False,
                        'message': str(e)
                    }
            
            def close_position(self, symbol):
                """Close a position"""
                try:
                    # Get position details
                    positions = self.get_positions()
                    position = next((p for p in positions if p['symbol'] == symbol), None)
                    
                    if not position:
                        return {
                            'success': False,
                            'message': f'No open position for {symbol}'
                        }
                    
                    # Place opposite order to close
                    side = 'Sell' if position['side'] == 'Buy' else 'Buy'
                    order_id = self.connector.place_order(
                        symbol=symbol,
                        side=side,
                        quantity=position['size'],
                        order_type='MARKET'
                    )
                    
                    if order_id:
                        return {
                            'success': True,
                            'message': f'Position {symbol} closed successfully',
                            'realizedPnl': position.get('unrealizedPnl', 0)
                        }
                    else:
                        return {
                            'success': False,
                            'message': 'Failed to close position'
                        }
                        
                except Exception as e:
                    logger.error(f"Error closing position: {e}")
                    return {
                        'success': False,
                        'message': str(e)
                    }
            
            def get_orders(self, status=None):
                """Get orders from Bybit"""
                try:
                    # Get open orders from Bybit
                    orders = self.connector.get_open_orders()
                    
                    # Format for GraphQL
                    formatted_orders = []
                    for order in orders:
                        formatted_orders.append({
                            'orderId': order.get('orderId'),
                            'symbol': order.get('symbol'),
                            'side': order.get('side'),
                            'orderType': order.get('type', 'Limit'),
                            'price': order.get('price'),
                            'quantity': order.get('quantity'),
                            'status': order.get('status', 'New'),
                            'createdAt': order.get('createdTime', datetime.now().isoformat())
                        })
                    
                    # Filter by status if provided
                    if status:
                        formatted_orders = [o for o in formatted_orders if o['status'] == status]
                    
                    return formatted_orders
                    
                except Exception as e:
                    logger.error(f"Error getting orders: {e}")
                    return []
        
        # Create API handler instance
        api_handler = APIHandler(connector, db_service)
        
        # Test connection
        try:
            initial_balance = api_handler.get_balance()
            logger.info(f"✅ Connected to Bybit. Initial balance: {initial_balance} USDT")
        except Exception as e:
            logger.error(f"Could not get initial balance: {e}")
        
        # Create FastAPI app
        app = FastAPI(
            title="Bybit Trading Bot GraphQL API",
            description="GraphQL API for Bybit Trading Bot Dashboard",
            version="2.0.0"
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Health check endpoint
        @app.get("/health")
        async def health_check():
            """Health check endpoint"""
            try:
                balance = api_handler.get_balance()
                return {
                    "status": "healthy",
                    "service": "graphql-api",
                    "balance": balance,
                    "mainnet": api_handler.is_mainnet,
                    "version": "2.0.0"
                }
            except Exception as e:
                logger.error(f"Health check error: {e}")
                raise HTTPException(status_code=503, detail=str(e))
        
        # Root endpoint
        @app.get("/")
        async def root():
            return {
                "name": "Bybit Trading Bot GraphQL API",
                "version": "2.0.0",
                "service": "graphql-api",
                "endpoints": [
                    "/health",
                    "/graphql",
                    "/docs"
                ]
            }
        
        # GraphQL schema
        type_defs = """
            type Query {
                botStatus: BotStatus
                positions: [Position]
                balance: Balance
                recentTrades(limit: Int): [Trade]
                ticker(symbol: String!): Ticker
                klines(symbol: String!, interval: String, limit: Int): [Kline]
                orders(status: String): [Order]
            }
            
            type Mutation {
                placeOrder(input: OrderInput!): OrderResponse
                cancelOrder(orderId: String!): CancelOrderResponse
                closePosition(symbol: String!): ClosePositionResponse
                updateSettings(input: SettingsInput!): SettingsResponse
            }
            
            type BotStatus {
                isRunning: Boolean
                mainnet: Boolean
                balance: Float
                positionsCount: Int
            }
            
            type Balance {
                total: Float
                available: Float
                currency: String
                timestamp: Float
            }
            
            type Position {
                symbol: String
                side: String
                size: Float
                avgPrice: Float
                markPrice: Float
                unrealizedPnl: Float
                realizedPnl: Float
                leverage: String
            }
            
            type Trade {
                symbol: String
                side: String
                price: Float
                quantity: Float
                timestamp: String
                pnl: Float
            }
            
            type Ticker {
                symbol: String
                price: Float
                bid: Float
                ask: Float
                volume: Float
                high24h: Float
                low24h: Float
                change24h: Float
                timestamp: Float
            }
            
            type Kline {
                timestamp: Float
                open: Float
                high: Float
                low: Float
                close: Float
                volume: Float
            }
            
            type Order {
                orderId: String
                symbol: String
                side: String
                orderType: String
                price: Float
                quantity: Float
                status: String
                createdAt: String
            }
            
            input OrderInput {
                symbol: String!
                side: String!
                orderType: String!
                quantity: Float!
                price: Float
                stopPrice: Float
                timeInForce: String
            }
            
            type OrderResponse {
                success: Boolean
                orderId: String
                message: String
                order: Order
            }
            
            type CancelOrderResponse {
                success: Boolean
                message: String
            }
            
            type ClosePositionResponse {
                success: Boolean
                message: String
                realizedPnl: Float
            }
            
            input SettingsInput {
                defaultLeverage: Int
                maxPositionSize: Float
                enableStopLoss: Boolean
                stopLossPercent: Float
            }
            
            type SettingsResponse {
                success: Boolean
                message: String
            }
        """
        
        # Create query resolvers
        query = QueryType()
        
        @query.field("botStatus")
        def resolve_bot_status(obj, info):
            positions = api_handler.get_positions()
            return {
                "isRunning": True,  # API is running
                "mainnet": api_handler.is_mainnet,
                "balance": api_handler.get_balance(),
                "positionsCount": len(positions)
            }
        
        @query.field("balance")
        def resolve_balance(obj, info):
            balance_value = api_handler.get_balance()
            return {
                "total": balance_value,
                "available": balance_value,  # For futures, total = available
                "currency": "USDT",
                "timestamp": datetime.now().timestamp()
            }
        
        @query.field("positions")
        def resolve_positions(obj, info):
            return api_handler.get_positions()
        
        @query.field("recentTrades")
        def resolve_recent_trades(obj, info, limit=10):
            return api_handler.get_recent_trades(limit)
            
        @query.field("ticker")
        def resolve_ticker(obj, info, symbol):
            ticker = api_handler.get_ticker(symbol)
            if ticker:
                ticker['timestamp'] = datetime.now().timestamp()
            return ticker
        
        @query.field("klines")
        def resolve_klines(obj, info, symbol, interval='15', limit=100):
            return api_handler.get_klines(symbol, interval, limit)
        
        @query.field("orders")
        def resolve_orders(obj, info, status=None):
            return api_handler.get_orders(status)
        
        # Import MutationType
        from ariadne import MutationType
        
        # Create mutation resolvers
        mutation = MutationType()
        
        @mutation.field("placeOrder")
        def resolve_place_order(obj, info, input):
            return api_handler.place_order(
                symbol=input.get('symbol'),
                side=input.get('side'),
                order_type=input.get('orderType'),
                quantity=input.get('quantity'),
                price=input.get('price'),
                stop_price=input.get('stopPrice'),
                time_in_force=input.get('timeInForce', 'GTC')
            )
        
        @mutation.field("cancelOrder")
        def resolve_cancel_order(obj, info, orderId):
            return api_handler.cancel_order(orderId)
        
        @mutation.field("closePosition")
        def resolve_close_position(obj, info, symbol):
            return api_handler.close_position(symbol)
        
        @mutation.field("updateSettings")
        def resolve_update_settings(obj, info, input):
            # Placeholder for settings update
            return {
                'success': True,
                'message': 'Settings updated successfully'
            }
        
        # Make executable schema with both query and mutation
        schema = make_executable_schema(type_defs, query, mutation)
        
        # Add GraphQL endpoint
        app.mount("/graphql", GraphQL(schema, debug=True))
        
        # WebSocket endpoint for real-time updates
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            logger.info("WebSocket client connected")
            
            try:
                while True:
                    # Send periodic updates
                    data = {
                        "type": "status",
                        "balance": api_handler.get_balance(),
                        "positions": len(api_handler.get_positions()),
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send_json(data)
                    
                    # Wait for 5 seconds before next update
                    await asyncio.sleep(5)
                    
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await websocket.close()
        
        logger.info("✅ GraphQL API initialized successfully!")
        logger.info("📊 Starting server on port 8000...")
        
        # Run server
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
            
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down GraphQL API service...")
    except Exception as e:
        logger.error(f"❌ Error in GraphQL API service: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()