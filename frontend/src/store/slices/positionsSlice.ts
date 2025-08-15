import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface Position {
  symbol: string;
  side: 'Buy' | 'Sell';
  size: number;
  entryPrice: number;
  markPrice: number;
  liquidationPrice?: number;
  unrealizedPnl: number;
  realizedPnl: number;
  pnlPercent: number;
  marginMode: 'cross' | 'isolated';
  leverage: number;
  stopLoss?: number;
  takeProfit?: number;
  trailingStop?: number;
  positionValue: number;
  marginUsed: number;
  createdTime: number;
  updatedTime: number;
}

interface PositionMetrics {
  totalUnrealizedPnl: number;
  totalRealizedPnl: number;
  totalPositionValue: number;
  totalMarginUsed: number;
  accountEquity: number;
  marginRatio: number;
  numberOfPositions: number;
}

interface PositionsState {
  positions: Position[];
  metrics: PositionMetrics;
  selectedPosition: Position | null;
  isLoading: boolean;
  lastUpdate: number;
}

const initialState: PositionsState = {
  positions: [],
  metrics: {
    totalUnrealizedPnl: 0,
    totalRealizedPnl: 0,
    totalPositionValue: 0,
    totalMarginUsed: 0,
    accountEquity: 10000,
    marginRatio: 0,
    numberOfPositions: 0,
  },
  selectedPosition: null,
  isLoading: false,
  lastUpdate: Date.now(),
};

const positionsSlice = createSlice({
  name: 'positions',
  initialState,
  reducers: {
    setPositions: (state, action: PayloadAction<Position[]>) => {
      state.positions = action.payload;
      state.lastUpdate = Date.now();
      // Recalculate metrics
      state.metrics = calculateMetrics(state.positions);
    },
    updatePosition: (state, action: PayloadAction<Position>) => {
      const index = state.positions.findIndex(p => p.symbol === action.payload.symbol);
      if (index >= 0) {
        state.positions[index] = action.payload;
      } else {
        state.positions.push(action.payload);
      }
      state.lastUpdate = Date.now();
      state.metrics = calculateMetrics(state.positions);
    },
    removePosition: (state, action: PayloadAction<string>) => {
      state.positions = state.positions.filter(p => p.symbol !== action.payload);
      if (state.selectedPosition?.symbol === action.payload) {
        state.selectedPosition = null;
      }
      state.metrics = calculateMetrics(state.positions);
    },
    setSelectedPosition: (state, action: PayloadAction<Position | null>) => {
      state.selectedPosition = action.payload;
    },
    updateMetrics: (state, action: PayloadAction<PositionMetrics>) => {
      state.metrics = action.payload;
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    clearPositions: (state) => {
      state.positions = [];
      state.selectedPosition = null;
      state.metrics = calculateMetrics([]);
    },
  },
});

function calculateMetrics(positions: Position[]): PositionMetrics {
  const metrics: PositionMetrics = {
    totalUnrealizedPnl: 0,
    totalRealizedPnl: 0,
    totalPositionValue: 0,
    totalMarginUsed: 0,
    accountEquity: 10000,
    marginRatio: 0,
    numberOfPositions: positions.length,
  };

  positions.forEach(position => {
    metrics.totalUnrealizedPnl += position.unrealizedPnl;
    metrics.totalRealizedPnl += position.realizedPnl;
    metrics.totalPositionValue += position.positionValue;
    metrics.totalMarginUsed += position.marginUsed;
  });

  metrics.accountEquity = 10000 + metrics.totalUnrealizedPnl + metrics.totalRealizedPnl;
  metrics.marginRatio = metrics.totalMarginUsed > 0 
    ? (metrics.totalMarginUsed / metrics.accountEquity) * 100 
    : 0;

  return metrics;
}

export const {
  setPositions,
  updatePosition,
  removePosition,
  setSelectedPosition,
  updateMetrics,
  setLoading,
  clearPositions,
} = positionsSlice.actions;

export default positionsSlice.reducer;