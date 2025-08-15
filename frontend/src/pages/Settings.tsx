import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Tabs,
  Tab,
  Alert,
  InputAdornment,
  IconButton,
  Divider,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Save as SaveIcon,
} from '@mui/icons-material';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import {
  updateApiConfig,
  updateTradingConfig,
  updateNotificationConfig,
  updateUIPreferences,
  setSaving,
} from '../store/slices/settingsSlice';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const Settings: React.FC = () => {
  const dispatch = useAppDispatch();
  const [tabValue, setTabValue] = useState(0);
  const [showApiKey, setShowApiKey] = useState(false);
  const [showApiSecret, setShowApiSecret] = useState(false);
  
  const {
    apiConfig,
    tradingConfig,
    notificationConfig,
    uiPreferences,
    isConfigured,
    isSaving,
  } = useAppSelector(state => state.settings);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleSaveSettings = () => {
    dispatch(setSaving(true));
    // Simulate save operation
    setTimeout(() => {
      dispatch(setSaving(false));
      // TODO: Send settings to backend
    }, 1000);
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>

      {!isConfigured && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Please configure your API credentials to start trading.
        </Alert>
      )}

      <Card>
        <CardContent>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={tabValue} onChange={handleTabChange}>
              <Tab label="API Configuration" />
              <Tab label="Trading Settings" />
              <Tab label="Notifications" />
              <Tab label="UI Preferences" />
            </Tabs>
          </Box>

          <TabPanel value={tabValue} index={0}>
            <Typography variant="h6" gutterBottom>
              API Configuration
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 600 }}>
              <TextField
                label="API Key"
                type={showApiKey ? 'text' : 'password'}
                value={apiConfig.apiKey}
                onChange={(e) => dispatch(updateApiConfig({ apiKey: e.target.value }))}
                fullWidth
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowApiKey(!showApiKey)}
                        edge="end"
                      >
                        {showApiKey ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              <TextField
                label="API Secret"
                type={showApiSecret ? 'text' : 'password'}
                value={apiConfig.apiSecret}
                onChange={(e) => dispatch(updateApiConfig({ apiSecret: e.target.value }))}
                fullWidth
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowApiSecret(!showApiSecret)}
                        edge="end"
                      >
                        {showApiSecret ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={apiConfig.testnet}
                    onChange={(e) => dispatch(updateApiConfig({ testnet: e.target.checked }))}
                  />
                }
                label="Use Testnet"
              />

              <TextField
                label="Webhook URL (Optional)"
                value={apiConfig.webhookUrl}
                onChange={(e) => dispatch(updateApiConfig({ webhookUrl: e.target.value }))}
                fullWidth
                helperText="For receiving trading signals from external sources"
              />
            </Box>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <Typography variant="h6" gutterBottom>
              Trading Settings
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 600 }}>
              <TextField
                label="Default Leverage"
                type="number"
                value={tradingConfig.defaultLeverage}
                onChange={(e) => dispatch(updateTradingConfig({ defaultLeverage: parseInt(e.target.value) }))}
                fullWidth
                inputProps={{ min: 1, max: 100 }}
              />

              <FormControl fullWidth>
                <InputLabel>Default Order Type</InputLabel>
                <Select
                  value={tradingConfig.defaultOrderType}
                  label="Default Order Type"
                  onChange={(e) => dispatch(updateTradingConfig({ defaultOrderType: e.target.value as 'Limit' | 'Market' }))}
                >
                  <MenuItem value="Market">Market</MenuItem>
                  <MenuItem value="Limit">Limit</MenuItem>
                </Select>
              </FormControl>

              <TextField
                label="Max Position Size ($)"
                type="number"
                value={tradingConfig.maxPositionSize}
                onChange={(e) => dispatch(updateTradingConfig({ maxPositionSize: parseFloat(e.target.value) }))}
                fullWidth
              />

              <TextField
                label="Max Daily Loss ($)"
                type="number"
                value={tradingConfig.maxDailyLoss}
                onChange={(e) => dispatch(updateTradingConfig({ maxDailyLoss: parseFloat(e.target.value) }))}
                fullWidth
              />

              <TextField
                label="Risk Per Trade (%)"
                type="number"
                value={tradingConfig.riskPerTrade}
                onChange={(e) => dispatch(updateTradingConfig({ riskPerTrade: parseFloat(e.target.value) }))}
                fullWidth
                inputProps={{ step: 0.1 }}
              />

              <Divider sx={{ my: 1 }} />

              <FormControlLabel
                control={
                  <Switch
                    checked={tradingConfig.enableStopLoss}
                    onChange={(e) => dispatch(updateTradingConfig({ enableStopLoss: e.target.checked }))}
                  />
                }
                label="Enable Stop Loss"
              />

              {tradingConfig.enableStopLoss && (
                <TextField
                  label="Stop Loss (%)"
                  type="number"
                  value={tradingConfig.stopLossPercent}
                  onChange={(e) => dispatch(updateTradingConfig({ stopLossPercent: parseFloat(e.target.value) }))}
                  fullWidth
                  inputProps={{ step: 0.1 }}
                />
              )}

              <FormControlLabel
                control={
                  <Switch
                    checked={tradingConfig.enableTakeProfit}
                    onChange={(e) => dispatch(updateTradingConfig({ enableTakeProfit: e.target.checked }))}
                  />
                }
                label="Enable Take Profit"
              />

              {tradingConfig.enableTakeProfit && (
                <TextField
                  label="Take Profit (%)"
                  type="number"
                  value={tradingConfig.takeProfitPercent}
                  onChange={(e) => dispatch(updateTradingConfig({ takeProfitPercent: parseFloat(e.target.value) }))}
                  fullWidth
                  inputProps={{ step: 0.1 }}
                />
              )}

              <FormControlLabel
                control={
                  <Switch
                    checked={tradingConfig.enableTrailingStop}
                    onChange={(e) => dispatch(updateTradingConfig({ enableTrailingStop: e.target.checked }))}
                  />
                }
                label="Enable Trailing Stop"
              />

              {tradingConfig.enableTrailingStop && (
                <TextField
                  label="Trailing Stop (%)"
                  type="number"
                  value={tradingConfig.trailingStopPercent}
                  onChange={(e) => dispatch(updateTradingConfig({ trailingStopPercent: parseFloat(e.target.value) }))}
                  fullWidth
                  inputProps={{ step: 0.1 }}
                />
              )}
            </Box>
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <Typography variant="h6" gutterBottom>
              Notification Settings
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 600 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={notificationConfig.enableNotifications}
                    onChange={(e) => dispatch(updateNotificationConfig({ enableNotifications: e.target.checked }))}
                  />
                }
                label="Enable Notifications"
              />

              <Divider sx={{ my: 1 }} />

              <FormControlLabel
                control={
                  <Switch
                    checked={notificationConfig.enableEmailNotifications}
                    onChange={(e) => dispatch(updateNotificationConfig({ enableEmailNotifications: e.target.checked }))}
                    disabled={!notificationConfig.enableNotifications}
                  />
                }
                label="Email Notifications"
              />

              {notificationConfig.enableEmailNotifications && (
                <TextField
                  label="Email Address"
                  type="email"
                  value={notificationConfig.emailAddress}
                  onChange={(e) => dispatch(updateNotificationConfig({ emailAddress: e.target.value }))}
                  fullWidth
                />
              )}

              <FormControlLabel
                control={
                  <Switch
                    checked={notificationConfig.enableTelegramNotifications}
                    onChange={(e) => dispatch(updateNotificationConfig({ enableTelegramNotifications: e.target.checked }))}
                    disabled={!notificationConfig.enableNotifications}
                  />
                }
                label="Telegram Notifications"
              />

              {notificationConfig.enableTelegramNotifications && (
                <TextField
                  label="Telegram Chat ID"
                  value={notificationConfig.telegramChatId}
                  onChange={(e) => dispatch(updateNotificationConfig({ telegramChatId: e.target.value }))}
                  fullWidth
                />
              )}

              <Divider sx={{ my: 1 }} />

              <Typography variant="subtitle2">Notification Events</Typography>

              <FormControlLabel
                control={
                  <Switch
                    checked={notificationConfig.notifyOnOrderFilled}
                    onChange={(e) => dispatch(updateNotificationConfig({ notifyOnOrderFilled: e.target.checked }))}
                    disabled={!notificationConfig.enableNotifications}
                  />
                }
                label="Order Filled"
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={notificationConfig.notifyOnPositionClosed}
                    onChange={(e) => dispatch(updateNotificationConfig({ notifyOnPositionClosed: e.target.checked }))}
                    disabled={!notificationConfig.enableNotifications}
                  />
                }
                label="Position Closed"
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={notificationConfig.notifyOnSignal}
                    onChange={(e) => dispatch(updateNotificationConfig({ notifyOnSignal: e.target.checked }))}
                    disabled={!notificationConfig.enableNotifications}
                  />
                }
                label="Trading Signal"
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={notificationConfig.notifyOnError}
                    onChange={(e) => dispatch(updateNotificationConfig({ notifyOnError: e.target.checked }))}
                    disabled={!notificationConfig.enableNotifications}
                  />
                }
                label="Errors"
              />
            </Box>
          </TabPanel>

          <TabPanel value={tabValue} index={3}>
            <Typography variant="h6" gutterBottom>
              UI Preferences
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 600 }}>
              <FormControl fullWidth>
                <InputLabel>Theme</InputLabel>
                <Select
                  value={uiPreferences.theme}
                  label="Theme"
                  onChange={(e) => dispatch(updateUIPreferences({ theme: e.target.value as 'dark' | 'light' }))}
                >
                  <MenuItem value="dark">Dark</MenuItem>
                  <MenuItem value="light">Light</MenuItem>
                </Select>
              </FormControl>

              <FormControl fullWidth>
                <InputLabel>Chart Type</InputLabel>
                <Select
                  value={uiPreferences.chartType}
                  label="Chart Type"
                  onChange={(e) => dispatch(updateUIPreferences({ chartType: e.target.value as 'candlestick' | 'line' | 'area' }))}
                >
                  <MenuItem value="candlestick">Candlestick</MenuItem>
                  <MenuItem value="line">Line</MenuItem>
                  <MenuItem value="area">Area</MenuItem>
                </Select>
              </FormControl>

              <FormControl fullWidth>
                <InputLabel>Language</InputLabel>
                <Select
                  value={uiPreferences.language}
                  label="Language"
                  onChange={(e) => dispatch(updateUIPreferences({ language: e.target.value as 'en' | 'zh' | 'ko' | 'ja' }))}
                >
                  <MenuItem value="en">English</MenuItem>
                  <MenuItem value="zh">中文</MenuItem>
                  <MenuItem value="ko">한국어</MenuItem>
                  <MenuItem value="ja">日本語</MenuItem>
                </Select>
              </FormControl>

              <FormControl fullWidth>
                <InputLabel>Timezone</InputLabel>
                <Select
                  value={uiPreferences.timezone}
                  label="Timezone"
                  onChange={(e) => dispatch(updateUIPreferences({ timezone: e.target.value }))}
                >
                  <MenuItem value="UTC">UTC</MenuItem>
                  <MenuItem value="America/New_York">New York</MenuItem>
                  <MenuItem value="Europe/London">London</MenuItem>
                  <MenuItem value="Asia/Tokyo">Tokyo</MenuItem>
                  <MenuItem value="Asia/Shanghai">Shanghai</MenuItem>
                  <MenuItem value="Asia/Singapore">Singapore</MenuItem>
                </Select>
              </FormControl>

              <Divider sx={{ my: 1 }} />

              <FormControlLabel
                control={
                  <Switch
                    checked={uiPreferences.showOrderBook}
                    onChange={(e) => dispatch(updateUIPreferences({ showOrderBook: e.target.checked }))}
                  />
                }
                label="Show Order Book"
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={uiPreferences.showTrades}
                    onChange={(e) => dispatch(updateUIPreferences({ showTrades: e.target.checked }))}
                  />
                }
                label="Show Recent Trades"
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={uiPreferences.showPositions}
                    onChange={(e) => dispatch(updateUIPreferences({ showPositions: e.target.checked }))}
                  />
                }
                label="Show Positions Panel"
              />
            </Box>
          </TabPanel>

          <Box sx={{ p: 3, display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              variant="contained"
              color="primary"
              startIcon={<SaveIcon />}
              onClick={handleSaveSettings}
              disabled={isSaving}
            >
              {isSaving ? 'Saving...' : 'Save Settings'}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default Settings;