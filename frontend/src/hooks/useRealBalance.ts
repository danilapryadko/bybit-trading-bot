import { useEffect, useState } from 'react';
import { useAppDispatch } from '../store/hooks';
import { updateBalances, setPaperTrading } from '../store/slices/tradingSlice';
import { setConnectionStatus } from '../store/slices/marketSlice';

const API_URL = import.meta.env.VITE_API_URL || 'https://bybit-danila-api.fly.dev';

export const useRealBalance = () => {
  const dispatch = useAppDispatch();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);

  const fetchRealBalance = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/graphql/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: `
            query GetAccountInfo {
              botStatus {
                balance
                isRunning
              }
              positions {
                symbol
                side
                size
                avgPrice
                unrealizedPnl
              }
            }
          `
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.errors) {
        throw new Error(data.errors[0]?.message || 'GraphQL error');
      }

      // Update Redux store with real balance
      if (data.data?.botStatus) {
        const balance = data.data.botStatus.balance || 0;
        dispatch(updateBalances({
          current: balance,
          available: balance, // Will be adjusted based on positions
        }));
        
        // Set connection status to true when we get data
        dispatch(setConnectionStatus(true));
        
        // We're using real money now, not paper trading
        if (balance > 0) {
          dispatch(setPaperTrading(false));
        }
      }

      // Reset retry count on successful connection
      setRetryCount(0);
      setIsConnected(true);
      
      return data.data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch balance';
      setError(errorMessage);
      console.error('Error fetching real balance:', err);
      
      // Set disconnected status
      dispatch(setConnectionStatus(false));
      setIsConnected(false);
      
      // Increment retry count
      setRetryCount(prev => prev + 1);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Fetch balance immediately
    fetchRealBalance();
    
    // Dynamic polling interval based on connection status
    // If connected: poll every 10 seconds
    // If disconnected: exponential backoff with max 30 seconds
    const getInterval = () => {
      if (isConnected) {
        return 10000; // 10 seconds when connected
      } else {
        // Exponential backoff: 2s, 4s, 8s, 16s, 30s max
        const backoffInterval = Math.min(2000 * Math.pow(2, retryCount), 30000);
        console.log(`Reconnecting in ${backoffInterval/1000}s (attempt ${retryCount + 1})`);
        return backoffInterval;
      }
    };
    
    const interval = setInterval(fetchRealBalance, getInterval());
    
    return () => clearInterval(interval);
  }, [isConnected, retryCount]);

  // Auto-reconnect on network recovery
  useEffect(() => {
    const handleOnline = () => {
      console.log('Network connection restored, reconnecting...');
      setRetryCount(0);
      fetchRealBalance();
    };
    
    const handleOffline = () => {
      console.log('Network connection lost');
      dispatch(setConnectionStatus(false));
      setIsConnected(false);
    };
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return { loading, error, isConnected, retryCount, refetch: fetchRealBalance };
};