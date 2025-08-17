import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface Order {
  orderId: string;
  symbol: string;
  side: 'Buy' | 'Sell';
  orderType: 'Limit' | 'Market' | 'StopLimit' | 'StopMarket';
  price?: number;
  quantity: number;
  filledQuantity: number;
  status: 'New' | 'PartiallyFilled' | 'Filled' | 'Cancelled' | 'Rejected' | 'Expired';
  timeInForce: 'GTC' | 'IOC' | 'FOK' | 'PostOnly';
  stopPrice?: number;
  createdTime: number;
  updatedTime: number;
}

interface TradingSignal {
  id: string;
  symbol: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  strategy: string;
  entryPrice?: number;
  stopLoss?: number;
  takeProfit?: number;
  timestamp: number;
}

interface TradingState {
  activeOrders: Order[];
  orderHistory: Order[];
  tradingSignals: TradingSignal[];
  isTradingEnabled: boolean;
  isPaperTrading: boolean;
  selectedStrategy: string;
  riskPerTrade: number;
  maxPositions: number;
  currentBalance: number;
  availableBalance: number;
}

const initialState: TradingState = {
  activeOrders: [],
  orderHistory: [],
  tradingSignals: [],
  isTradingEnabled: false,
  isPaperTrading: false, // Real trading by default
  selectedStrategy: 'ml_ensemble',
  riskPerTrade: 1.0,
  maxPositions: 3,
  currentBalance: 0, // Will be fetched from API
  availableBalance: 0, // Will be fetched from API
};

const tradingSlice = createSlice({
  name: 'trading',
  initialState,
  reducers: {
    addOrder: (state, action: PayloadAction<Order>) => {
      state.activeOrders.push(action.payload);
    },
    updateOrder: (state, action: PayloadAction<Order>) => {
      const index = state.activeOrders.findIndex(o => o.orderId === action.payload.orderId);
      if (index >= 0) {
        const order = action.payload;
        if (order.status === 'Filled' || order.status === 'Cancelled' || order.status === 'Rejected') {
          state.activeOrders.splice(index, 1);
          state.orderHistory.unshift(order);
          // Keep only last 100 orders in history
          if (state.orderHistory.length > 100) {
            state.orderHistory = state.orderHistory.slice(0, 100);
          }
        } else {
          state.activeOrders[index] = order;
        }
      }
    },
    removeOrder: (state, action: PayloadAction<string>) => {
      state.activeOrders = state.activeOrders.filter(o => o.orderId !== action.payload);
    },
    addTradingSignal: (state, action: PayloadAction<TradingSignal>) => {
      state.tradingSignals.unshift(action.payload);
      // Keep only last 50 signals
      if (state.tradingSignals.length > 50) {
        state.tradingSignals = state.tradingSignals.slice(0, 50);
      }
    },
    setTradingEnabled: (state, action: PayloadAction<boolean>) => {
      state.isTradingEnabled = action.payload;
    },
    setPaperTrading: (state, action: PayloadAction<boolean>) => {
      state.isPaperTrading = action.payload;
    },
    setSelectedStrategy: (state, action: PayloadAction<string>) => {
      state.selectedStrategy = action.payload;
    },
    setRiskPerTrade: (state, action: PayloadAction<number>) => {
      state.riskPerTrade = action.payload;
    },
    setMaxPositions: (state, action: PayloadAction<number>) => {
      state.maxPositions = action.payload;
    },
    updateBalances: (state, action: PayloadAction<{ current: number; available: number }>) => {
      state.currentBalance = action.payload.current;
      state.availableBalance = action.payload.available;
    },
    clearOrders: (state) => {
      state.activeOrders = [];
    },
    clearOrderHistory: (state) => {
      state.orderHistory = [];
    },
    clearTradingSignals: (state) => {
      state.tradingSignals = [];
    },
  },
});

export const {
  addOrder,
  updateOrder,
  removeOrder,
  addTradingSignal,
  setTradingEnabled,
  setPaperTrading,
  setSelectedStrategy,
  setRiskPerTrade,
  setMaxPositions,
  updateBalances,
  clearOrders,
  clearOrderHistory,
  clearTradingSignals,
} = tradingSlice.actions;

export default tradingSlice.reducer;