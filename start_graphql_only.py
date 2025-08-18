#!/usr/bin/env python3
"""
GraphQL Server only for Fly.io deployment
Runs without Telegram bot to avoid conflicts
"""
import os
import logging
import asyncio
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Run database migration on first startup
def run_migration():
    """Run database migration if needed"""
    try:
        if os.getenv('FLY_APP_NAME'):
            logger.info("Checking database migration...")
            from run_migration import main as migrate
            migrate()
    except Exception as e:
        logger.warning(f"Migration check failed (may already be complete): {e}")

def main():
    """Start GraphQL server only"""
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║     Bybit Trading Bot - GraphQL API Server          ║
    ║     Production Mode (No Telegram Bot)               ║
    ╔══════════════════════════════════════════════════════╗
    """)
    
    logger.info("🚀 Starting GraphQL API server for Fly.io...")
    logger.info(f"📊 GraphQL API: http://0.0.0.0:8000/graphql/")
    logger.info("--------------------------------------------------")
    
    # Run migration
    run_migration()
    
    # Start GraphQL server
    try:
        from graphql_server import app
        
        # Get port from environment or use default
        port = int(os.getenv('PORT', 8000))
        
        # Run server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Failed to start GraphQL server: {e}")
        raise

if __name__ == "__main__":
    main()