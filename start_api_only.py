#!/usr/bin/env python3
"""
GraphQL API Only - без Telegram бота для избежания конфликтов
"""
import os
import logging
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
    """Main function to run GraphQL API only"""
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║     Bybit Trading Bot - GraphQL API Only            ║
    ║     Real-time Data from Bybit                       ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    logger.info("🚀 Starting GraphQL API service...")
    logger.info("📊 GraphQL endpoint: http://0.0.0.0:8000/graphql")
    logger.info("🏥 Health check: http://0.0.0.0:8000/health")
    logger.info("-" * 50)
    
    # Run database migration if needed
    try:
        if os.getenv('FLY_APP_NAME'):
            logger.info("Checking database migration...")
            from run_migration import main as migrate
            migrate()
    except Exception as e:
        logger.warning(f"Migration check: {e}")
    
    try:
        import uvicorn
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
        from ariadne import QueryType, make_executable_schema, graphql_sync
        from ariadne.asgi import GraphQL
        from bybit_connector import get_bybit_connector
        import json
        
        # Get real Bybit connector
        logger.info("Initializing Bybit connector...")
        connector = get_bybit_connector()
        
        # Create enhanced bot with real Bybit connection
        class EnhancedTradingBot:
            def __init__(self, bybit_connector):
                self.connector = bybit_connector
                self.is_running = False
                self.paper_trading = False  # Using real account
                self.strategy_name = "ML Ensemble"
                self.start_time = None
                
            def get_balance(self):
                """Get real balance from Bybit account"""
                try:
                    balance = self.connector.get_balance()
                    logger.info(f"Retrieved real balance: {balance} USDT")
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
                    return {
                        'lastPrice': ticker.get('price', 0),
                        'price24hPcnt': ticker.get('change24h', 0) / 100,
                        'volume24h': ticker.get('volume', 0)
                    }
                except Exception as e:
                    logger.error(f"Error getting ticker for {symbol}: {e}")
                    return {
                        'lastPrice': 0,
                        'price24hPcnt': 0,
                        'volume24h': 0
                    }
        
        # Create bot instance
        bot = EnhancedTradingBot(connector)
        
        # Test connection
        try:
            initial_balance = bot.get_balance()
            logger.info(f"✅ Initial balance from Bybit: {initial_balance} USDT")
        except Exception as e:
            logger.error(f"Could not get initial balance: {e}")
        
        # Create FastAPI app
        app = FastAPI(title="Bybit Trading Bot API")
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Health check endpoint
        @app.get("/health")
        async def health_check():
            """Health check endpoint"""
            try:
                balance = bot.get_balance()
                return {
                    "status": "healthy",
                    "service": "bybit-trading-bot",
                    "balance": balance,
                    "paper_trading": bot.paper_trading,
                    "is_running": bot.is_running
                }
            except Exception as e:
                logger.error(f"Health check error: {e}")
                return {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        # Root endpoint
        @app.get("/")
        async def root():
            return {
                "name": "Bybit Trading Bot API",
                "version": "1.0.0",
                "endpoints": [
                    "/health",
                    "/graphql"
                ]
            }
        
        # GraphQL schema
        type_defs = """
            type Query {
                botStatus: BotStatus
                positions: [Position]
                balance: Float
                recentTrades(limit: Int): [Trade]
            }
            
            type BotStatus {
                isRunning: Boolean
                paperTrading: Boolean
                balance: Float
                strategyName: String
            }
            
            type Position {
                symbol: String
                side: String
                size: Float
                avgPrice: Float
                unrealizedPnl: Float
                realizedPnl: Float
            }
            
            type Trade {
                symbol: String
                side: String
                price: Float
                quantity: Float
                timestamp: String
                pnl: Float
            }
        """
        
        # Create query resolvers
        query = QueryType()
        
        @query.field("botStatus")
        def resolve_bot_status(obj, info):
            return {
                "isRunning": bot.is_running,
                "paperTrading": bot.paper_trading,
                "balance": bot.get_balance(),
                "strategyName": bot.strategy_name
            }
        
        @query.field("balance")
        def resolve_balance(obj, info):
            return bot.get_balance()
        
        @query.field("positions")
        def resolve_positions(obj, info):
            positions = bot.get_positions()
            return [
                {
                    "symbol": pos.get("symbol", ""),
                    "side": pos.get("side", ""),
                    "size": float(pos.get("size", 0)),
                    "avgPrice": float(pos.get("avgPrice", 0)),
                    "unrealizedPnl": float(pos.get("unrealizedPnl", 0)),
                    "realizedPnl": float(pos.get("realizedPnl", 0))
                }
                for pos in positions
            ]
        
        @query.field("recentTrades")
        def resolve_recent_trades(obj, info, limit=10):
            # This would normally fetch from database
            return []
        
        # Make executable schema
        schema = make_executable_schema(type_defs, query)
        
        # Add GraphQL endpoint
        app.mount("/graphql", GraphQL(schema, debug=True))
        
        # Alternative GraphQL endpoint for POST requests
        @app.post("/graphql")
        async def graphql_post(request: dict):
            """Handle GraphQL POST requests"""
            try:
                success, result = graphql_sync(
                    schema,
                    request,
                    context_value={"bot": bot},
                    debug=True
                )
                return result
            except Exception as e:
                logger.error(f"GraphQL error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        logger.info("✅ GraphQL API initialized successfully!")
        logger.info("📊 Starting server on port 8000...")
        
        # Run server
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
            
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down API server...")
    except Exception as e:
        logger.error(f"❌ Error in main loop: {e}", exc_info=True)

if __name__ == "__main__":
    main()