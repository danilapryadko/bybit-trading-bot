#!/usr/bin/env python3
"""
GraphQL Server for Bybit Trading Bot
"""
import asyncio
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

from ariadne import QueryType, MutationType, SubscriptionType, make_executable_schema
from ariadne.asgi import GraphQL
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
import uvicorn

# Import bot components (optional, will use mock if not available)
try:
    from trading_bot import TradingBot
    from risk_manager_v2 import RiskManagerV2, RiskProfile
except ImportError:
    TradingBot = None
    RiskManagerV2 = None
    RiskProfile = None

# GraphQL Type Definitions
type_defs = """
    type Query {
        botStatus: BotStatus!
        balance: Balance!
        positions: [Position!]!
        marketData(symbol: String!): MarketData!
        tradingHistory(limit: Int = 10): [Trade!]!
        performance: Performance!
        strategies: [Strategy!]!
        riskMetrics: RiskMetrics!
    }
    
    type Mutation {
        startBot(config: BotConfigInput!): BotStatus!
        stopBot: BotStatus!
        pauseBot: BotStatus!
        resumeBot: BotStatus!
        updateStrategy(strategy: String!): BotStatus!
        updateRiskProfile(profile: RiskProfileInput!): RiskMetrics!
        placeOrder(order: OrderInput!): Order!
        cancelOrder(orderId: String!): Boolean!
        closePosition(symbol: String!): Boolean!
        closeAllPositions: Boolean!
    }
    
    type Subscription {
        priceUpdate(symbol: String!): PriceUpdate!
        positionUpdate: Position!
        orderUpdate: Order!
        botStatusUpdate: BotStatus!
        balanceUpdate: Balance!
    }
    
    type BotStatus {
        isRunning: Boolean!
        isPaused: Boolean!
        strategy: String!
        mode: String!
        startTime: String
        uptime: Int
        errorCount: Int
    }
    
    type Balance {
        total: Float!
        available: Float!
        used: Float!
        unrealizedPnl: Float!
        realizedPnl: Float!
        currency: String!
    }
    
    type Position {
        symbol: String!
        side: String!
        size: Float!
        entryPrice: Float!
        markPrice: Float!
        unrealizedPnl: Float!
        realizedPnl: Float!
        leverage: Float!
        stopLoss: Float
        takeProfit: Float
        createdAt: String!
    }
    
    type MarketData {
        symbol: String!
        lastPrice: Float!
        bidPrice: Float!
        askPrice: Float!
        volume24h: Float!
        high24h: Float!
        low24h: Float!
        priceChange24h: Float!
        priceChangePercent24h: Float!
    }
    
    type Trade {
        id: String!
        symbol: String!
        side: String!
        price: Float!
        quantity: Float!
        realizedPnl: Float!
        fee: Float!
        timestamp: String!
    }
    
    type Performance {
        totalTrades: Int!
        winningTrades: Int!
        losingTrades: Int!
        winRate: Float!
        totalPnl: Float!
        sharpeRatio: Float!
        maxDrawdown: Float!
        avgWin: Float!
        avgLoss: Float!
        profitFactor: Float!
    }
    
    type Strategy {
        name: String!
        description: String!
        isActive: Boolean!
        parameters: String!
        performance: StrategyPerformance!
    }
    
    type StrategyPerformance {
        trades: Int!
        winRate: Float!
        pnl: Float!
        sharpeRatio: Float!
    }
    
    type RiskMetrics {
        maxPositions: Int!
        maxLeverage: Float!
        riskPerTrade: Float!
        dailyLossLimit: Float!
        currentExposure: Float!
        valueAtRisk: Float!
        correlationRisk: Float!
    }
    
    type Order {
        id: String!
        symbol: String!
        side: String!
        type: String!
        price: Float
        quantity: Float!
        status: String!
        createdAt: String!
    }
    
    type PriceUpdate {
        symbol: String!
        price: Float!
        timestamp: String!
    }
    
    input BotConfigInput {
        strategy: String!
        symbols: [String!]!
        riskPerTrade: Float!
        maxPositions: Int!
        paperTrading: Boolean!
    }
    
    input RiskProfileInput {
        maxPositions: Int!
        maxLeverage: Float!
        riskPerTrade: Float!
        dailyLossLimit: Float!
        useTrailingStop: Boolean!
        trailingStopPercent: Float
    }
    
    input OrderInput {
        symbol: String!
        side: String!
        type: String!
        quantity: Float!
        price: Float
        stopLoss: Float
        takeProfit: Float
    }
"""

# Query Resolvers
query = QueryType()

@query.field("botStatus")
async def resolve_bot_status(obj, info):
    bot = info.context["bot"]
    return {
        "isRunning": bot.is_running,
        "isPaused": getattr(bot, 'is_paused', False),
        "strategy": bot.strategy_name,
        "mode": "paper" if bot.paper_trading else "live",
        "startTime": str(bot.start_time) if bot.start_time else None,
        "uptime": int((datetime.now() - bot.start_time).total_seconds()) if bot.start_time else 0,
        "errorCount": getattr(bot, 'error_count', 0)
    }

@query.field("balance")
async def resolve_balance(obj, info):
    bot = info.context["bot"]
    balance = bot.get_balance()
    return {
        "total": balance.get('totalWalletBalance', 0),
        "available": balance.get('availableBalance', 0),
        "used": balance.get('usedMargin', 0),
        "unrealizedPnl": balance.get('unrealisedPnl', 0),
        "realizedPnl": balance.get('realisedPnl', 0),
        "currency": "USDT"
    }

@query.field("positions")
async def resolve_positions(obj, info):
    bot = info.context["bot"]
    positions = bot.get_positions()
    return [{
        "symbol": pos['symbol'],
        "side": pos['side'],
        "size": pos['size'],
        "entryPrice": pos['avgPrice'],
        "markPrice": pos.get('markPrice', 0),
        "unrealizedPnl": pos.get('unrealisedPnl', 0),
        "realizedPnl": pos.get('realisedPnl', 0),
        "leverage": pos.get('leverage', 1),
        "stopLoss": pos.get('stopLoss'),
        "takeProfit": pos.get('takeProfit'),
        "createdAt": str(pos.get('createdTime', ''))
    } for pos in positions]

@query.field("marketData")
async def resolve_market_data(obj, info, symbol):
    bot = info.context["bot"]
    ticker = bot.get_ticker(symbol)
    return {
        "symbol": symbol,
        "lastPrice": ticker.get('lastPrice', 0),
        "bidPrice": ticker.get('bid1Price', 0),
        "askPrice": ticker.get('ask1Price', 0),
        "volume24h": ticker.get('volume24h', 0),
        "high24h": ticker.get('highPrice24h', 0),
        "low24h": ticker.get('lowPrice24h', 0),
        "priceChange24h": ticker.get('price24hPcnt', 0) * ticker.get('lastPrice', 0),
        "priceChangePercent24h": ticker.get('price24hPcnt', 0) * 100
    }

@query.field("performance")
async def resolve_performance(obj, info):
    bot = info.context["bot"]
    # Get performance metrics from bot
    trades = getattr(bot, 'trade_history', [])
    winning = [t for t in trades if t.get('pnl', 0) > 0]
    losing = [t for t in trades if t.get('pnl', 0) < 0]
    
    total_pnl = sum(t.get('pnl', 0) for t in trades)
    win_rate = len(winning) / len(trades) * 100 if trades else 0
    avg_win = sum(t.get('pnl', 0) for t in winning) / len(winning) if winning else 0
    avg_loss = abs(sum(t.get('pnl', 0) for t in losing) / len(losing)) if losing else 0
    
    return {
        "totalTrades": len(trades),
        "winningTrades": len(winning),
        "losingTrades": len(losing),
        "winRate": win_rate,
        "totalPnl": total_pnl,
        "sharpeRatio": 0,  # Calculate from returns
        "maxDrawdown": 0,  # Calculate from equity curve
        "avgWin": avg_win,
        "avgLoss": avg_loss,
        "profitFactor": avg_win / avg_loss if avg_loss > 0 else 0
    }

@query.field("strategies")
async def resolve_strategies(obj, info):
    return [
        {
            "name": "ML Ensemble",
            "description": "Machine Learning ensemble with LSTM, Random Forest, and XGBoost",
            "isActive": True,
            "parameters": json.dumps({"models": ["LSTM", "RF", "XGBoost"]}),
            "performance": {
                "trades": 0,
                "winRate": 0,
                "pnl": 0,
                "sharpeRatio": 0
            }
        },
        {
            "name": "RSI Mean Reversion",
            "description": "RSI-based mean reversion strategy",
            "isActive": False,
            "parameters": json.dumps({"rsi_period": 14, "oversold": 30, "overbought": 70}),
            "performance": {
                "trades": 0,
                "winRate": 0,
                "pnl": 0,
                "sharpeRatio": 0
            }
        },
        {
            "name": "Trend Following",
            "description": "EMA crossover trend following",
            "isActive": False,
            "parameters": json.dumps({"fast_ema": 12, "slow_ema": 26}),
            "performance": {
                "trades": 0,
                "winRate": 0,
                "pnl": 0,
                "sharpeRatio": 0
            }
        }
    ]

@query.field("riskMetrics")
async def resolve_risk_metrics(obj, info):
    bot = info.context["bot"]
    risk_manager = bot.risk_manager if hasattr(bot, 'risk_manager') else None
    
    if risk_manager:
        return {
            "maxPositions": risk_manager.risk_profile.max_positions,
            "maxLeverage": risk_manager.risk_profile.max_leverage,
            "riskPerTrade": risk_manager.risk_profile.risk_per_trade,
            "dailyLossLimit": risk_manager.risk_profile.daily_loss_limit,
            "currentExposure": risk_manager.get_current_exposure(),
            "valueAtRisk": risk_manager.calculate_var(0.95),
            "correlationRisk": risk_manager.calculate_correlation_risk()
        }
    
    return {
        "maxPositions": 3,
        "maxLeverage": 5,
        "riskPerTrade": 1.0,
        "dailyLossLimit": 5.0,
        "currentExposure": 0,
        "valueAtRisk": 0,
        "correlationRisk": 0
    }

# Mutation Resolvers
mutation = MutationType()

@mutation.field("startBot")
async def resolve_start_bot(obj, info, config):
    bot = info.context["bot"]
    
    # Update bot configuration
    bot.strategy_name = config["strategy"]
    bot.symbols = config["symbols"]
    bot.paper_trading = config.get("paperTrading", True)
    
    # Start the bot
    await bot.start()
    
    return await resolve_bot_status(obj, info)

@mutation.field("stopBot")
async def resolve_stop_bot(obj, info):
    bot = info.context["bot"]
    bot.stop()
    return await resolve_bot_status(obj, info)

@mutation.field("pauseBot")
async def resolve_pause_bot(obj, info):
    bot = info.context["bot"]
    bot.pause()
    return await resolve_bot_status(obj, info)

@mutation.field("resumeBot")
async def resolve_resume_bot(obj, info):
    bot = info.context["bot"]
    bot.resume()
    return await resolve_bot_status(obj, info)

@mutation.field("placeOrder")
async def resolve_place_order(obj, info, order):
    bot = info.context["bot"]
    
    # Place order through bot
    result = await bot.place_order(
        symbol=order["symbol"],
        side=order["side"],
        order_type=order["type"],
        quantity=order["quantity"],
        price=order.get("price"),
        stop_loss=order.get("stopLoss"),
        take_profit=order.get("takeProfit")
    )
    
    return {
        "id": result.get("orderId", ""),
        "symbol": order["symbol"],
        "side": order["side"],
        "type": order["type"],
        "price": order.get("price", 0),
        "quantity": order["quantity"],
        "status": "Submitted",
        "createdAt": str(datetime.now())
    }

@mutation.field("closePosition")
async def resolve_close_position(obj, info, symbol):
    bot = info.context["bot"]
    # Close specific position
    result = await bot.close_position(symbol)
    return result is not None

@mutation.field("closeAllPositions")
async def resolve_close_all_positions(obj, info):
    bot = info.context["bot"]
    bot.close_all_positions()
    return True

# Subscription Resolvers
subscription = SubscriptionType()

@subscription.source("priceUpdate")
async def price_update_generator(obj, info, symbol):
    bot = info.context["bot"]
    while True:
        ticker = bot.get_ticker(symbol)
        yield {
            "symbol": symbol,
            "price": ticker.get("lastPrice", 0),
            "timestamp": str(datetime.now())
        }
        await asyncio.sleep(1)  # Update every second

@subscription.field("priceUpdate")
def resolve_price_update(update, info, symbol):
    return update

# Create schema
schema = make_executable_schema(type_defs, query, mutation, subscription)

# Create Starlette app
def create_app(bot: Optional[TradingBot] = None):
    """Create GraphQL server app"""
    app = Starlette()
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Create mock bot if not provided
    if bot is None:
        from start_telegram_bot import MockTradingBot
        bot = MockTradingBot()
    
    # Add GraphQL route
    app.mount("/graphql", GraphQL(
        schema,
        context_value={"bot": bot},
        debug=True
    ))
    
    return app

# Main function
def main():
    """Run GraphQL server"""
    from start_telegram_bot import MockTradingBot
    
    # Create mock bot for testing
    bot = MockTradingBot()
    
    # Create app
    app = create_app(bot)
    
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║         Bybit Trading Bot - GraphQL Server          ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    print("🚀 GraphQL Server starting...")
    print("📍 GraphQL Playground: http://localhost:8000/graphql")
    print("📊 Mode: Development")
    print("-" * 50)
    
    # Run server
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()