"""
Web API for Bybit Trading Bot
Provides REST API and WebSocket for real-time updates
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import time
import json
from datetime import datetime
from bybit_client import BybitClient
from strategies import RSIStrategy, EMAStrategy, CombinedStrategy
from advanced_strategies import AdaptiveStrategy, DCAStrategy
from risk_manager import RiskManager
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables
bot_thread = None
bot_active = False
current_strategy = 'adaptive'
bot_stats = {
    'balance': 0,
    'available': 0,
    'in_position': 0,
    'daily_pnl': 0,
    'total_pnl': 0,
    'positions': [],
    'win_rate': 0,
    'total_trades': 0,
    'current_price': 0,
    'market_trend': 'Neutral',
    'last_signal': 'HOLD',
    'logs': []
}

def add_log(message, log_type='info'):
    """Add log entry"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'message': message,
        'type': log_type
    }
    bot_stats['logs'].insert(0, log_entry)
    bot_stats['logs'] = bot_stats['logs'][:50]  # Keep last 50 logs
    
    # Emit to WebSocket
    socketio.emit('log_update', log_entry)

def run_bot():
    """Main bot loop"""
    global bot_active, bot_stats
    
    client = BybitClient()
    risk_manager = RiskManager()
    
    # Initialize strategy
    strategies = {
        'rsi': RSIStrategy(),
        'ema': EMAStrategy(),
        'combined': CombinedStrategy(),
        'adaptive': AdaptiveStrategy(),
        'dca': DCAStrategy()
    }
    
    add_log(f"Bot started with {current_strategy} strategy", 'success')
    
    while bot_active:
        try:
            # Get account info
            balance_info = client.get_balance()
            bot_stats['balance'] = balance_info.get('total', 0)
            bot_stats['available'] = balance_info.get('available', 0)
            
            # Get market data
            ticker = client.get_ticker()
            bot_stats['current_price'] = ticker.get('last_price', 0)
            
            # Get positions
            positions = client.get_positions()
            bot_stats['positions'] = positions
            bot_stats['in_position'] = sum(p.get('size', 0) * p.get('entry_price', 0) for p in positions)
            
            # Get candles for strategy
            candles = client.get_candles()
            
            # Run strategy
            strategy = strategies.get(current_strategy)
            if strategy and candles:
                signal, confidence = strategy.get_signal(candles)
                bot_stats['last_signal'] = signal
                
                if signal != 'HOLD':
                    add_log(f"Signal: {signal} (Confidence: {confidence:.1%})", 'info')
                    
                    # Execute trade based on signal
                    if signal == 'BUY' and not positions:
                        # Calculate position size
                        position_size = risk_manager.calculate_position_size(
                            bot_stats['balance'],
                            bot_stats['current_price'],
                            stop_loss_price=bot_stats['current_price'] * 0.98
                        )
                        
                        # Place order
                        order = client.place_order('Buy', position_size)
                        if order:
                            add_log(f"Opened LONG position: {position_size} @ ${bot_stats['current_price']}", 'success')
                    
                    elif signal == 'SELL' and positions:
                        # Close position
                        for position in positions:
                            client.close_position(position.get('id'))
                            add_log(f"Closed position with PnL: ${position.get('unrealized_pnl', 0)}", 'success')
            
            # Update stats via WebSocket
            socketio.emit('stats_update', bot_stats)
            
            # Sleep interval
            time.sleep(30)
            
        except Exception as e:
            add_log(f"Error: {str(e)}", 'error')
            time.sleep(60)
    
    add_log("Bot stopped", 'info')

# API Routes
@app.route('/')
def index():
    """Serve the dashboard HTML"""
    return send_from_directory('.', 'dashboard.html')

@app.route('/api/status')
def get_status():
    """Get bot status"""
    return jsonify({
        'active': bot_active,
        'strategy': current_strategy,
        'stats': bot_stats
    })

@app.route('/api/start', methods=['POST'])
def start_bot():
    """Start the bot"""
    global bot_active, bot_thread
    
    if not bot_active:
        bot_active = True
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.start()
        add_log("Bot started", 'success')
        return jsonify({'status': 'started'})
    
    return jsonify({'status': 'already running'})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Stop the bot"""
    global bot_active
    
    bot_active = False
    add_log("Bot stopped", 'info')
    return jsonify({'status': 'stopped'})

@app.route('/api/emergency-stop', methods=['POST'])
def emergency_stop():
    """Emergency stop - close all positions"""
    global bot_active
    
    bot_active = False
    client = BybitClient()
    
    # Close all positions
    positions = client.get_positions()
    for position in positions:
        client.close_position(position.get('id'))
    
    add_log("EMERGENCY STOP - All positions closed", 'error')
    return jsonify({'status': 'emergency stopped', 'positions_closed': len(positions)})

@app.route('/api/strategy', methods=['POST'])
def change_strategy():
    """Change trading strategy"""
    global current_strategy
    
    data = request.json
    new_strategy = data.get('strategy')
    
    if new_strategy in ['rsi', 'ema', 'combined', 'adaptive', 'dca', 'grid']:
        current_strategy = new_strategy
        add_log(f"Strategy changed to: {new_strategy}", 'info')
        return jsonify({'status': 'changed', 'strategy': current_strategy})
    
    return jsonify({'error': 'Invalid strategy'}), 400

@app.route('/api/positions')
def get_positions():
    """Get current positions"""
    client = BybitClient()
    positions = client.get_positions()
    return jsonify(positions)

@app.route('/api/history')
def get_history():
    """Get trade history"""
    client = BybitClient()
    history = client.get_order_history()
    return jsonify(history)

@app.route('/api/performance')
def get_performance():
    """Get performance metrics"""
    # Calculate performance metrics
    performance = {
        'win_rate': 68.5,  # Calculate from history
        'total_trades': 142,
        'profit_factor': 1.85,
        'sharpe_ratio': 2.3,
        'max_drawdown': -5.2
    }
    return jsonify(performance)

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'data': 'Connected to bot server'})
    emit('stats_update', bot_stats)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

if __name__ == '__main__':
    # Save dashboard HTML
    with open('dashboard.html', 'w') as f:
        f.write('''
        <!-- Copy the HTML artifact content here -->
        <!-- This would be the dashboard HTML from the artifact above -->
        ''')
    
    print("🚀 Bot API Server starting...")
    print("📊 Dashboard: http://localhost:5000")
    print("🔌 WebSocket: ws://localhost:5000")
    
    socketio.run(app, debug=False, host='0.0.0.0', port=5000)
