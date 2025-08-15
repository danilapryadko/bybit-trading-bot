import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface ApiConfig {
  apiKey: string;
  apiSecret: string;
  testnet: boolean;
  webhookUrl?: string;
}

interface TradingConfig {
  defaultLeverage: number;
  defaultOrderType: 'Limit' | 'Market';
  defaultTimeInForce: 'GTC' | 'IOC' | 'FOK' | 'PostOnly';
  maxPositionSize: number;
  maxDailyLoss: number;
  riskPerTrade: number;
  enableStopLoss: boolean;
  stopLossPercent: number;
  enableTakeProfit: boolean;
  takeProfitPercent: number;
  enableTrailingStop: boolean;
  trailingStopPercent: number;
}

interface NotificationConfig {
  enableNotifications: boolean;
  enableEmailNotifications: boolean;
  emailAddress?: string;
  enableTelegramNotifications: boolean;
  telegramChatId?: string;
  notifyOnOrderFilled: boolean;
  notifyOnPositionClosed: boolean;
  notifyOnSignal: boolean;
  notifyOnError: boolean;
}

interface UIPreferences {
  theme: 'dark' | 'light';
  chartType: 'candlestick' | 'line' | 'area';
  showOrderBook: boolean;
  showTrades: boolean;
  showPositions: boolean;
  language: 'en' | 'zh' | 'ko' | 'ja';
  timezone: string;
}

interface SettingsState {
  apiConfig: ApiConfig;
  tradingConfig: TradingConfig;
  notificationConfig: NotificationConfig;
  uiPreferences: UIPreferences;
  isConfigured: boolean;
  isSaving: boolean;
}

const initialState: SettingsState = {
  apiConfig: {
    apiKey: '',
    apiSecret: '',
    testnet: true,
    webhookUrl: '',
  },
  tradingConfig: {
    defaultLeverage: 1,
    defaultOrderType: 'Limit',
    defaultTimeInForce: 'GTC',
    maxPositionSize: 10000,
    maxDailyLoss: 500,
    riskPerTrade: 1.0,
    enableStopLoss: true,
    stopLossPercent: 2.0,
    enableTakeProfit: true,
    takeProfitPercent: 3.0,
    enableTrailingStop: false,
    trailingStopPercent: 1.5,
  },
  notificationConfig: {
    enableNotifications: true,
    enableEmailNotifications: false,
    emailAddress: '',
    enableTelegramNotifications: false,
    telegramChatId: '',
    notifyOnOrderFilled: true,
    notifyOnPositionClosed: true,
    notifyOnSignal: true,
    notifyOnError: true,
  },
  uiPreferences: {
    theme: 'dark',
    chartType: 'candlestick',
    showOrderBook: true,
    showTrades: true,
    showPositions: true,
    language: 'en',
    timezone: 'UTC',
  },
  isConfigured: false,
  isSaving: false,
};

const settingsSlice = createSlice({
  name: 'settings',
  initialState,
  reducers: {
    updateApiConfig: (state, action: PayloadAction<Partial<ApiConfig>>) => {
      state.apiConfig = { ...state.apiConfig, ...action.payload };
      state.isConfigured = !!(state.apiConfig.apiKey && state.apiConfig.apiSecret);
    },
    updateTradingConfig: (state, action: PayloadAction<Partial<TradingConfig>>) => {
      state.tradingConfig = { ...state.tradingConfig, ...action.payload };
    },
    updateNotificationConfig: (state, action: PayloadAction<Partial<NotificationConfig>>) => {
      state.notificationConfig = { ...state.notificationConfig, ...action.payload };
    },
    updateUIPreferences: (state, action: PayloadAction<Partial<UIPreferences>>) => {
      state.uiPreferences = { ...state.uiPreferences, ...action.payload };
    },
    setConfigured: (state, action: PayloadAction<boolean>) => {
      state.isConfigured = action.payload;
    },
    setSaving: (state, action: PayloadAction<boolean>) => {
      state.isSaving = action.payload;
    },
    resetSettings: () => initialState,
  },
});

export const {
  updateApiConfig,
  updateTradingConfig,
  updateNotificationConfig,
  updateUIPreferences,
  setConfigured,
  setSaving,
  resetSettings,
} = settingsSlice.actions;

export default settingsSlice.reducer;