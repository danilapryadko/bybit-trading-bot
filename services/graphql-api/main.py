#!/usr/bin/env python3
"""
GraphQL API Microservice
Provides GraphQL API for Dashboard and external integrations
"""
import os
import sys
import logging
from pathlib import Path

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
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
        from ariadne import QueryType, make_executable_schema, graphql_sync
        from ariadne.asgi import GraphQL
        from bybit_connector import get_bybit_connector
        from database.service import DatabaseService
        import json
        
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
                    
            def get_recent_trades(self, limit=10):
                """Get recent trades from database"""
                try:
                    # Fetch from database
                    trades = self.db.get_recent_trades(limit)
                    return trades
                except Exception as e:
                    logger.error(f"Error getting recent trades: {e}")
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
                balance: Float
                recentTrades(limit: Int): [Trade]
                ticker(symbol: String!): Ticker
            }
            
            type BotStatus {
                isRunning: Boolean
                mainnet: Boolean
                balance: Float
                positionsCount: Int
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
            
            type Ticker {
                symbol: String
                lastPrice: Float
                bidPrice: Float
                askPrice: Float
                volume24h: Float
                change24h: Float
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
            return api_handler.get_balance()
        
        @query.field("positions")
        def resolve_positions(obj, info):
            return api_handler.get_positions()
        
        @query.field("recentTrades")
        def resolve_recent_trades(obj, info, limit=10):
            return api_handler.get_recent_trades(limit)
            
        @query.field("ticker")
        def resolve_ticker(obj, info, symbol):
            return api_handler.get_ticker(symbol)
        
        # Make executable schema
        schema = make_executable_schema(type_defs, query)
        
        # Add GraphQL endpoint
        app.mount("/graphql", GraphQL(schema, debug=True))
        
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