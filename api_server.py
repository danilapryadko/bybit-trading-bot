"""
FastAPI server with Phase 7 & 8 test endpoints
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ariadne import graphql, make_executable_schema
from ariadne.asgi import GraphQL
import uvicorn
import logging
from api import schema, resolvers, mutations, subscriptions
from api.test_phases import router as test_router
from monitoring import start_monitoring, metrics
from prometheus_client import make_asgi_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Bybit Trading Bot API",
    description="Advanced trading bot with Phase 7 & 8 features",
    version="8.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include test router
app.include_router(test_router)

# GraphQL setup
executable_schema = make_executable_schema(schema, resolvers + mutations + subscriptions)
graphql_app = GraphQL(executable_schema, debug=True)

# Mount GraphQL
app.add_route("/graphql", graphql_app)
app.add_websocket_route("/graphql", graphql_app)

# Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Bybit Trading Bot API",
        "version": "8.0.0",
        "status": "running",
        "features": {
            "phase_7": "Advanced Orders (Stop-Loss, Take-Profit, Trailing Stops)",
            "phase_8": "Grid Trading Strategy",
            "websocket": "Real-time data streaming",
            "ml": "Machine Learning predictions"
        },
        "endpoints": {
            "graphql": "/graphql",
            "test": "/test",
            "metrics": "/metrics",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "phase_7": "operational",
        "phase_8": "operational",
        "timestamp": datetime.now().isoformat()
    }

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting API server...")
    # Start monitoring in background
    await start_monitoring()
    logger.info("API server started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down API server...")

if __name__ == "__main__":
    import os
    from datetime import datetime
    
    port = int(os.getenv("PORT", 8000))
    
    # Run server
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )