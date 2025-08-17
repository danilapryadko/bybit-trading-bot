import { useEffect, useState } from 'react';
import { useAppDispatch } from '../store/hooks';
import { updateKline } from '../store/slices/marketSlice';

const API_URL = import.meta.env.VITE_API_URL || 'https://bybit-danila-api.fly.dev';

interface Kline {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export const useRealKlines = (symbol: string, interval: string = '15') => {
  const dispatch = useAppDispatch();
  const [klines, setKlines] = useState<Kline[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchKlines = async () => {
    if (!symbol) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/graphql/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: `
            query GetKlines($symbol: String!, $interval: String!, $limit: Int!) {
              klines(symbol: $symbol, interval: $interval, limit: $limit) {
                timestamp
                open
                high
                low
                close
                volume
              }
            }
          `,
          variables: { 
            symbol,
            interval,
            limit: 100
          }
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.errors) {
        console.error('GraphQL error:', data.errors);
        return;
      }

      // Update local state and Redux store
      if (data.data?.klines) {
        const klineData = data.data.klines;
        setKlines(klineData);
        
        // Update Redux with latest kline
        if (klineData.length > 0) {
          const latestKline = klineData[klineData.length - 1];
          dispatch(updateKline({
            symbol,
            interval,
            openTime: latestKline.timestamp,
            open: latestKline.open,
            high: latestKline.high,
            low: latestKline.low,
            close: latestKline.close,
            volume: latestKline.volume,
            closeTime: latestKline.timestamp + (15 * 60 * 1000) // Add interval in ms
          }));
        }
      }
    } catch (err) {
      console.error(`Error fetching klines for ${symbol}:`, err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Fetch klines immediately
    fetchKlines();
    
    // Update klines every 10 seconds
    const intervalId = setInterval(fetchKlines, 10000);
    
    return () => clearInterval(intervalId);
  }, [symbol, interval]);

  return { klines, loading };
};