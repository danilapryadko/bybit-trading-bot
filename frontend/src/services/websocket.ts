import { AppDispatch } from '../store';
import {
  updateTicker,
  updateOrderBook,
  addTrade,
  updateKline,
  setConnectionStatus,
} from '../store/slices/marketSlice';
import {
  updateOrder,
  addTradingSignal,
  updateBalances,
} from '../store/slices/tradingSlice';
import {
  updatePosition,
  removePosition,
} from '../store/slices/positionsSlice';
import {
  addNotification,
} from '../store/slices/notificationsSlice';

class WebSocketService {
  private ws: WebSocket | null = null;
  private dispatch: AppDispatch | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private pingInterval: NodeJS.Timeout | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000; // Start with 1 second
  private subscriptions = new Set<string>();

  connect(dispatch: AppDispatch) {
    this.dispatch = dispatch;
    this.establishConnection();
  }

  private establishConnection() {
    try {
      // Connect to backend WebSocket server
      const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        
        if (this.dispatch) {
          this.dispatch(setConnectionStatus(true));
          this.dispatch(addNotification({
            type: 'success',
            title: 'Connected',
            message: 'Successfully connected to trading server',
          }));
        }

        // Resubscribe to previous subscriptions
        this.subscriptions.forEach(sub => {
          this.send({ type: 'subscribe', data: sub });
        });

        // Start ping interval
        this.startPingInterval();
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (this.dispatch) {
          this.dispatch(addNotification({
            type: 'error',
            title: 'Connection Error',
            message: 'WebSocket connection error occurred',
          }));
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        
        if (this.dispatch) {
          this.dispatch(setConnectionStatus(false));
        }

        this.stopPingInterval();
        this.attemptReconnect();
      };
    } catch (error) {
      console.error('Failed to establish WebSocket connection:', error);
      this.attemptReconnect();
    }
  }

  private handleMessage(message: any) {
    if (!this.dispatch) return;

    switch (message.type) {
      case 'ticker':
        this.dispatch(updateTicker(message.data));
        break;
      
      case 'orderbook':
        this.dispatch(updateOrderBook(message.data));
        break;
      
      case 'trade':
        this.dispatch(addTrade(message.data));
        break;
      
      case 'kline':
        this.dispatch(updateKline(message.data));
        break;
      
      case 'order':
        this.dispatch(updateOrder(message.data));
        break;
      
      case 'position':
        if (message.data.size === 0) {
          this.dispatch(removePosition(message.data.symbol));
        } else {
          this.dispatch(updatePosition(message.data));
        }
        break;
      
      case 'signal':
        this.dispatch(addTradingSignal(message.data));
        this.dispatch(addNotification({
          type: 'info',
          title: 'Trading Signal',
          message: `${message.data.action} signal for ${message.data.symbol} (${message.data.confidence}% confidence)`,
        }));
        break;
      
      case 'balance':
        this.dispatch(updateBalances(message.data));
        break;
      
      case 'notification':
        this.dispatch(addNotification(message.data));
        break;
      
      case 'pong':
        // Heartbeat response
        break;
      
      default:
        console.warn('Unknown message type:', message.type);
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      if (this.dispatch) {
        this.dispatch(addNotification({
          type: 'error',
          title: 'Connection Failed',
          message: 'Unable to reconnect to trading server. Please refresh the page.',
          persistent: true,
        }));
      }
      return;
    }

    this.reconnectAttempts++;
    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

    this.reconnectTimeout = setTimeout(() => {
      this.establishConnection();
    }, this.reconnectDelay);

    // Exponential backoff with max delay of 30 seconds
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
  }

  private startPingInterval() {
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' });
      }
    }, 30000); // Ping every 30 seconds
  }

  private stopPingInterval() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  send(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }

  subscribe(channel: string, params?: any) {
    const subscription = JSON.stringify({ channel, params });
    this.subscriptions.add(subscription);
    this.send({
      type: 'subscribe',
      channel,
      params,
    });
  }

  unsubscribe(channel: string, params?: any) {
    const subscription = JSON.stringify({ channel, params });
    this.subscriptions.delete(subscription);
    this.send({
      type: 'unsubscribe',
      channel,
      params,
    });
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    this.stopPingInterval();
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.subscriptions.clear();
    this.dispatch = null;
  }
}

// Create singleton instance
const wsService = new WebSocketService();

// Export functions for React components
export const connectWebSocket = (dispatch: AppDispatch) => {
  wsService.connect(dispatch);
};

export const disconnectWebSocket = () => {
  wsService.disconnect();
};

export const subscribeToChannel = (channel: string, params?: any) => {
  wsService.subscribe(channel, params);
};

export const unsubscribeFromChannel = (channel: string, params?: any) => {
  wsService.unsubscribe(channel, params);
};

export const sendMessage = (message: any) => {
  wsService.send(message);
};

export default wsService;