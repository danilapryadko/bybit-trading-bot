import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface Ticker {
  symbol: string;
  lastPrice: number;
  priceChange24h: number;
  priceChangePercent24h: number;
  volume24h: number;
  high24h: number;
  low24h: number;
  bid: number;
  ask: number;
  timestamp: number;
}

interface OrderBookLevel {
  price: number;
  quantity: number;
}

interface OrderBook {
  symbol: string;
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  timestamp: number;
}

interface Trade {
  id: string;
  symbol: string;
  price: number;
  quantity: number;
  side: 'buy' | 'sell';
  timestamp: number;
}

interface Kline {
  symbol: string;
  interval: string;
  openTime: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  closeTime: number;
}

interface MarketState {
  tickers: Record<string, Ticker>;
  orderBooks: Record<string, OrderBook>;
  trades: Record<string, Trade[]>;
  klines: Record<string, Kline[]>;
  activeSymbol: string;
  watchlist: string[];
  isConnected: boolean;
  lastUpdate: number;
}

const initialState: MarketState = {
  tickers: {},
  orderBooks: {},
  trades: {},
  klines: {},
  activeSymbol: 'BTCUSDT',
  watchlist: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
  isConnected: false,
  lastUpdate: Date.now(),
};

const marketSlice = createSlice({
  name: 'market',
  initialState,
  reducers: {
    updateTicker: (state, action: PayloadAction<Ticker>) => {
      const ticker = action.payload;
      state.tickers[ticker.symbol] = ticker;
      state.lastUpdate = Date.now();
    },
    updateOrderBook: (state, action: PayloadAction<OrderBook>) => {
      const orderBook = action.payload;
      state.orderBooks[orderBook.symbol] = orderBook;
      state.lastUpdate = Date.now();
    },
    addTrade: (state, action: PayloadAction<Trade>) => {
      const trade = action.payload;
      if (!state.trades[trade.symbol]) {
        state.trades[trade.symbol] = [];
      }
      state.trades[trade.symbol].unshift(trade);
      // Keep only last 100 trades
      if (state.trades[trade.symbol].length > 100) {
        state.trades[trade.symbol] = state.trades[trade.symbol].slice(0, 100);
      }
      state.lastUpdate = Date.now();
    },
    updateKline: (state, action: PayloadAction<Kline>) => {
      const kline = action.payload;
      const key = `${kline.symbol}_${kline.interval}`;
      if (!state.klines[key]) {
        state.klines[key] = [];
      }
      const existingIndex = state.klines[key].findIndex(k => k.openTime === kline.openTime);
      if (existingIndex >= 0) {
        state.klines[key][existingIndex] = kline;
      } else {
        state.klines[key].push(kline);
        // Keep only last 500 klines
        if (state.klines[key].length > 500) {
          state.klines[key] = state.klines[key].slice(-500);
        }
      }
      state.lastUpdate = Date.now();
    },
    setActiveSymbol: (state, action: PayloadAction<string>) => {
      state.activeSymbol = action.payload;
    },
    addToWatchlist: (state, action: PayloadAction<string>) => {
      if (!state.watchlist.includes(action.payload)) {
        state.watchlist.push(action.payload);
      }
    },
    removeFromWatchlist: (state, action: PayloadAction<string>) => {
      state.watchlist = state.watchlist.filter(s => s !== action.payload);
    },
    setConnectionStatus: (state, action: PayloadAction<boolean>) => {
      state.isConnected = action.payload;
    },
    clearMarketData: (state) => {
      state.tickers = {};
      state.orderBooks = {};
      state.trades = {};
      state.klines = {};
    },
  },
});

export const {
  updateTicker,
  updateOrderBook,
  addTrade,
  updateKline,
  setActiveSymbol,
  addToWatchlist,
  removeFromWatchlist,
  setConnectionStatus,
  clearMarketData,
} = marketSlice.actions;

export default marketSlice.reducer;