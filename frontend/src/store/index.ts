import { configureStore } from '@reduxjs/toolkit';
import marketReducer from './slices/marketSlice';
import tradingReducer from './slices/tradingSlice';
import positionsReducer from './slices/positionsSlice';
import analyticsReducer from './slices/analyticsSlice';
import settingsReducer from './slices/settingsSlice';
import notificationsReducer from './slices/notificationsSlice';

export const store = configureStore({
  reducer: {
    market: marketReducer,
    trading: tradingReducer,
    positions: positionsReducer,
    analytics: analyticsReducer,
    settings: settingsReducer,
    notifications: notificationsReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;