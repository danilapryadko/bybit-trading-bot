import { useEffect } from 'react';
import { useAppDispatch } from '../store/hooks';
import { updateTicker } from '../store/slices/marketSlice';

const API_URL = import.meta.env.VITE_API_URL || 'https://bybit-danila-api.fly.dev';

export const useRealTickers = (symbols: string[]) => {
  const dispatch = useAppDispatch();

  const fetchTicker = async (symbol: string) => {
    try {
      const response = await fetch(`${API_URL}/graphql/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: `
            query GetTicker($symbol: String!) {
              ticker(symbol: $symbol) {
                symbol
                price
                bid
                ask
                volume
                high24h
                low24h
                change24h
              }
            }
          `,
          variables: { symbol }
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.errors) {
        throw new Error(data.errors[0]?.message || 'GraphQL error');
      }

      // Update Redux store with real ticker data
      if (data.data?.ticker) {
        const ticker = data.data.ticker;
        dispatch(updateTicker({
          symbol: ticker.symbol,
          lastPrice: ticker.price || 0,
          bid: ticker.bid || 0,
          ask: ticker.ask || 0,
          volume24h: ticker.volume || 0,
          high24h: ticker.high24h || 0,
          low24h: ticker.low24h || 0,
          priceChange24h: ticker.price - ticker.low24h, // Calculate actual price change
          priceChangePercent24h: ticker.change24h || 0,
          timestamp: Date.now()
        }));
      }
      
      return data.data?.ticker;
    } catch (err) {
      console.error(`Error fetching ticker for ${symbol}:`, err);
    }
  };

  useEffect(() => {
    // Fetch all tickers immediately
    symbols.forEach(symbol => {
      fetchTicker(symbol);
    });
    
    // Update tickers every 5 seconds
    const interval = setInterval(() => {
      symbols.forEach(symbol => {
        fetchTicker(symbol);
      });
    }, 5000);
    
    return () => clearInterval(interval);
  }, [symbols.join(',')]); // Re-run when symbols change
};