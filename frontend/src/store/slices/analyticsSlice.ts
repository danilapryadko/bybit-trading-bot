import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface PerformanceMetric {
  date: string;
  pnl: number;
  winRate: number;
  totalTrades: number;
  profitFactor: number;
  sharpeRatio: number;
  maxDrawdown: number;
}

interface StrategyPerformance {
  strategyName: string;
  totalPnl: number;
  winRate: number;
  avgWin: number;
  avgLoss: number;
  profitFactor: number;
  sharpeRatio: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
}

interface MarketAnalysis {
  symbol: string;
  trend: 'bullish' | 'bearish' | 'neutral';
  volatility: number;
  volume: number;
  support: number[];
  resistance: number[];
  rsi: number;
  macd: {
    value: number;
    signal: number;
    histogram: number;
  };
  bollingerBands: {
    upper: number;
    middle: number;
    lower: number;
  };
}

interface BacktestResult {
  id: string;
  strategy: string;
  symbol: string;
  startDate: string;
  endDate: string;
  initialCapital: number;
  finalCapital: number;
  totalReturn: number;
  totalReturnPercent: number;
  maxDrawdown: number;
  winRate: number;
  profitFactor: number;
  sharpeRatio: number;
  totalTrades: number;
  timestamp: number;
}

interface AnalyticsState {
  performanceHistory: PerformanceMetric[];
  strategyPerformance: StrategyPerformance[];
  marketAnalysis: Record<string, MarketAnalysis>;
  backtestResults: BacktestResult[];
  selectedTimeframe: '1D' | '1W' | '1M' | '3M' | '1Y' | 'ALL';
  isLoading: boolean;
}

const initialState: AnalyticsState = {
  performanceHistory: [],
  strategyPerformance: [],
  marketAnalysis: {},
  backtestResults: [],
  selectedTimeframe: '1M',
  isLoading: false,
};

const analyticsSlice = createSlice({
  name: 'analytics',
  initialState,
  reducers: {
    setPerformanceHistory: (state, action: PayloadAction<PerformanceMetric[]>) => {
      state.performanceHistory = action.payload;
    },
    addPerformanceMetric: (state, action: PayloadAction<PerformanceMetric>) => {
      state.performanceHistory.push(action.payload);
      // Keep only last 365 days
      if (state.performanceHistory.length > 365) {
        state.performanceHistory = state.performanceHistory.slice(-365);
      }
    },
    setStrategyPerformance: (state, action: PayloadAction<StrategyPerformance[]>) => {
      state.strategyPerformance = action.payload;
    },
    updateMarketAnalysis: (state, action: PayloadAction<MarketAnalysis>) => {
      state.marketAnalysis[action.payload.symbol] = action.payload;
    },
    addBacktestResult: (state, action: PayloadAction<BacktestResult>) => {
      state.backtestResults.unshift(action.payload);
      // Keep only last 50 backtest results
      if (state.backtestResults.length > 50) {
        state.backtestResults = state.backtestResults.slice(0, 50);
      }
    },
    removeBacktestResult: (state, action: PayloadAction<string>) => {
      state.backtestResults = state.backtestResults.filter(r => r.id !== action.payload);
    },
    setSelectedTimeframe: (state, action: PayloadAction<'1D' | '1W' | '1M' | '3M' | '1Y' | 'ALL'>) => {
      state.selectedTimeframe = action.payload;
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    clearAnalytics: (state) => {
      state.performanceHistory = [];
      state.strategyPerformance = [];
      state.marketAnalysis = {};
    },
  },
});

export const {
  setPerformanceHistory,
  addPerformanceMetric,
  setStrategyPerformance,
  updateMarketAnalysis,
  addBacktestResult,
  removeBacktestResult,
  setSelectedTimeframe,
  setLoading,
  clearAnalytics,
} = analyticsSlice.actions;

export default analyticsSlice.reducer;