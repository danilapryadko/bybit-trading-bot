import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  TextField,
  Switch,
  FormControlLabel,
  Button,
  Divider,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Slider,
  InputAdornment,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Checkbox,
  Snackbar
} from '@mui/material';
import {
  Save,
  Security,
  Notifications,
  Speed,
  CurrencyExchange,
  Delete,
  Add,
  Edit,
  Visibility,
  VisibilityOff,
  ContentCopy,
  Warning,
  CheckCircle,
  Error,
  Sync
} from '@mui/icons-material';

interface TradingPair {
  symbol: string;
  enabled: boolean;
  leverage: number;
  maxPosition: number;
  minPosition: number;
  category: string;
  volatility: string;
}

const Settings: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [showApiKey, setShowApiKey] = useState(false);
  const [showApiSecret, setShowApiSecret] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [testConnectionStatus, setTestConnectionStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [addPairDialog, setAddPairDialog] = useState(false);

  // Settings state
  const [settings, setSettings] = useState({
    // API Settings
    apiKey: 'GKJ3m8PVwRkL9N2xQ5',
    apiSecret: '••••••••••••••••••••',
    useTestnet: false,
    
    // Trading Settings
    defaultLeverage: 10,
    maxPositionSize: 10000,
    riskPerTrade: 2,
    maxDailyLoss: 500,
    stopLossPercent: 2,
    takeProfitPercent: 3,
    trailingStop: true,
    
    // System Settings
    autoStart: true,
    paperTrading: false,
    debugMode: false,
    logLevel: 'INFO',
    timezone: 'UTC',
    language: 'en',
    
    // Notifications
    telegramEnabled: true,
    telegramChatId: '123456789',
    emailEnabled: false,
    emailAddress: '',
    notifyOnTrade: true,
    notifyOnError: true,
    notifyDailyReport: true,
    
    // Risk Management
    maxOpenPositions: 3,
    maxDrawdown: 10,
    dailyLossLimit: 5,
    positionSizeMode: 'fixed',
    
    // Performance
    dataUpdateInterval: 1000,
    orderRetryAttempts: 3,
    connectionTimeout: 30000,
    enableCache: true
  });

  const [tradingPairs, setTradingPairs] = useState<TradingPair[]>([
    { symbol: 'BTCUSDT', enabled: true, leverage: 10, maxPosition: 50000, minPosition: 10, category: 'major', volatility: 'medium' },
    { symbol: 'ETHUSDT', enabled: true, leverage: 15, maxPosition: 30000, minPosition: 10, category: 'major', volatility: 'medium' },
    { symbol: 'SOLUSDT', enabled: true, leverage: 15, maxPosition: 15000, minPosition: 10, category: 'layer1', volatility: 'high' },
    { symbol: 'BNBUSDT', enabled: true, leverage: 10, maxPosition: 20000, minPosition: 10, category: 'major', volatility: 'medium' },
    { symbol: 'MATICUSDT', enabled: true, leverage: 15, maxPosition: 10000, minPosition: 10, category: 'layer2', volatility: 'high' },
    { symbol: 'LINKUSDT', enabled: true, leverage: 10, maxPosition: 10000, minPosition: 10, category: 'defi', volatility: 'medium' },
    { symbol: 'ARBUSDT', enabled: false, leverage: 15, maxPosition: 8000, minPosition: 10, category: 'layer2', volatility: 'high' },
    { symbol: 'DOGEUSDT', enabled: false, leverage: 20, maxPosition: 10000, minPosition: 10, category: 'meme', volatility: 'extreme' },
    { symbol: 'AVAXUSDT', enabled: false, leverage: 15, maxPosition: 10000, minPosition: 10, category: 'layer1', volatility: 'high' },
    { symbol: 'OPUSDT', enabled: false, leverage: 15, maxPosition: 8000, minPosition: 10, category: 'layer2', volatility: 'high' }
  ]);

  const [newPair, setNewPair] = useState<TradingPair>({
    symbol: '',
    enabled: true,
    leverage: 10,
    maxPosition: 10000,
    minPosition: 10,
    category: 'major',
    volatility: 'medium'
  });

  const handleSaveSettings = () => {
    // Save settings logic
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const handleTestConnection = async () => {
    setTestConnectionStatus('testing');
    // Simulate API test
    setTimeout(() => {
      setTestConnectionStatus('success');
      setTimeout(() => setTestConnectionStatus('idle'), 3000);
    }, 2000);
  };

  const handleTogglePair = (symbol: string) => {
    setTradingPairs(prev => prev.map(pair => 
      pair.symbol === symbol ? { ...pair, enabled: !pair.enabled } : pair
    ));
  };

  const handleAddPair = () => {
    if (newPair.symbol && !tradingPairs.find(p => p.symbol === newPair.symbol)) {
      setTradingPairs([...tradingPairs, newPair]);
      setNewPair({
        symbol: '',
        enabled: true,
        leverage: 10,
        maxPosition: 10000,
        minPosition: 10,
        category: 'major',
        volatility: 'medium'
      });
      setAddPairDialog(false);
    }
  };

  const handleDeletePair = (symbol: string) => {
    setTradingPairs(prev => prev.filter(p => p.symbol !== symbol));
  };

  const getVolatilityColor = (level: string) => {
    switch (level) {
      case 'low': return 'success';
      case 'medium': return 'warning';
      case 'high': return 'error';
      case 'extreme': return 'error';
      default: return 'default';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>Settings</Typography>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab label="API Configuration" />
          <Tab label="Trading Pairs" />
          <Tab label="Risk Management" />
          <Tab label="Notifications" />
          <Tab label="System" />
        </Tabs>
      </Paper>

      {/* API Configuration Tab */}
      {tabValue === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Bybit API Configuration
              </Typography>
              <Alert severity="warning" sx={{ mb: 3 }}>
                Keep your API keys secure. Never share them with anyone.
              </Alert>
              
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="API Key"
                    value={settings.apiKey}
                    onChange={(e) => setSettings({ ...settings, apiKey: e.target.value })}
                    InputProps={{
                      endAdornment: (
                        <InputAdornment position="end">
                          <IconButton onClick={() => navigator.clipboard.writeText(settings.apiKey)}>
                            <ContentCopy />
                          </IconButton>
                        </InputAdornment>
                      )
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="API Secret"
                    type={showApiSecret ? 'text' : 'password'}
                    value={settings.apiSecret}
                    onChange={(e) => setSettings({ ...settings, apiSecret: e.target.value })}
                    InputProps={{
                      endAdornment: (
                        <InputAdornment position="end">
                          <IconButton onClick={() => setShowApiSecret(!showApiSecret)}>
                            {showApiSecret ? <VisibilityOff /> : <Visibility />}
                          </IconButton>
                        </InputAdornment>
                      )
                    }}
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.useTestnet}
                        onChange={(e) => setSettings({ ...settings, useTestnet: e.target.checked })}
                      />
                    }
                    label="Use Testnet (for testing)"
                  />
                </Grid>
                <Grid item xs={12}>
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Button
                      variant="outlined"
                      onClick={handleTestConnection}
                      disabled={testConnectionStatus === 'testing'}
                      startIcon={
                        testConnectionStatus === 'testing' ? <Sync /> :
                        testConnectionStatus === 'success' ? <CheckCircle /> :
                        testConnectionStatus === 'error' ? <Error /> :
                        <Speed />
                      }
                    >
                      {testConnectionStatus === 'testing' ? 'Testing...' :
                       testConnectionStatus === 'success' ? 'Connected' :
                       testConnectionStatus === 'error' ? 'Connection Failed' :
                       'Test Connection'}
                    </Button>
                    <Button variant="contained" startIcon={<Save />} onClick={handleSaveSettings}>
                      Save API Settings
                    </Button>
                  </Box>
                </Grid>
              </Grid>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* Trading Pairs Tab */}
      {tabValue === 1 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
                <Typography variant="h6">
                  Trading Pairs Configuration
                </Typography>
                <Button
                  variant="contained"
                  startIcon={<Add />}
                  onClick={() => setAddPairDialog(true)}
                >
                  Add Pair
                </Button>
              </Box>

              <Alert severity="info" sx={{ mb: 2 }}>
                Enable/disable trading pairs and configure leverage for each pair individually.
              </Alert>

              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Enabled</TableCell>
                      <TableCell>Symbol</TableCell>
                      <TableCell>Category</TableCell>
                      <TableCell>Volatility</TableCell>
                      <TableCell>Leverage</TableCell>
                      <TableCell>Min Position</TableCell>
                      <TableCell>Max Position</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {tradingPairs.map((pair) => (
                      <TableRow key={pair.symbol}>
                        <TableCell>
                          <Checkbox
                            checked={pair.enabled}
                            onChange={() => handleTogglePair(pair.symbol)}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography fontWeight="bold">{pair.symbol}</Typography>
                        </TableCell>
                        <TableCell>
                          <Chip label={pair.category} size="small" />
                        </TableCell>
                        <TableCell>
                          <Chip 
                            label={pair.volatility}
                            size="small"
                            color={getVolatilityColor(pair.volatility) as any}
                          />
                        </TableCell>
                        <TableCell>{pair.leverage}x</TableCell>
                        <TableCell>${pair.minPosition}</TableCell>
                        <TableCell>${pair.maxPosition.toLocaleString()}</TableCell>
                        <TableCell>
                          <IconButton size="small" onClick={() => {}}>
                            <Edit />
                          </IconButton>
                          <IconButton 
                            size="small" 
                            color="error"
                            onClick={() => handleDeletePair(pair.symbol)}
                          >
                            <Delete />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>

              <Box sx={{ mt: 3 }}>
                <Typography variant="body2" color="textSecondary">
                  Active pairs: {tradingPairs.filter(p => p.enabled).length} / {tradingPairs.length}
                </Typography>
              </Box>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* Risk Management Tab */}
      {tabValue === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Position Management
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <Typography gutterBottom>Default Leverage: {settings.defaultLeverage}x</Typography>
                  <Slider
                    value={settings.defaultLeverage}
                    onChange={(e, v) => setSettings({ ...settings, defaultLeverage: v as number })}
                    min={1}
                    max={100}
                    marks={[
                      { value: 1, label: '1x' },
                      { value: 25, label: '25x' },
                      { value: 50, label: '50x' },
                      { value: 75, label: '75x' },
                      { value: 100, label: '100x' }
                    ]}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Max Position Size (USDT)"
                    type="number"
                    value={settings.maxPositionSize}
                    onChange={(e) => setSettings({ ...settings, maxPositionSize: Number(e.target.value) })}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Risk Per Trade (%)"
                    type="number"
                    value={settings.riskPerTrade}
                    onChange={(e) => setSettings({ ...settings, riskPerTrade: Number(e.target.value) })}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Max Open Positions"
                    type="number"
                    value={settings.maxOpenPositions}
                    onChange={(e) => setSettings({ ...settings, maxOpenPositions: Number(e.target.value) })}
                  />
                </Grid>
              </Grid>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Stop Loss & Take Profit
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Default Stop Loss (%)"
                    type="number"
                    value={settings.stopLossPercent}
                    onChange={(e) => setSettings({ ...settings, stopLossPercent: Number(e.target.value) })}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Default Take Profit (%)"
                    type="number"
                    value={settings.takeProfitPercent}
                    onChange={(e) => setSettings({ ...settings, takeProfitPercent: Number(e.target.value) })}
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.trailingStop}
                        onChange={(e) => setSettings({ ...settings, trailingStop: e.target.checked })}
                      />
                    }
                    label="Enable Trailing Stop"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Max Daily Loss (USDT)"
                    type="number"
                    value={settings.maxDailyLoss}
                    onChange={(e) => setSettings({ ...settings, maxDailyLoss: Number(e.target.value) })}
                  />
                </Grid>
              </Grid>
            </Paper>
          </Grid>

          <Grid item xs={12}>
            <Button variant="contained" startIcon={<Save />} onClick={handleSaveSettings}>
              Save Risk Settings
            </Button>
          </Grid>
        </Grid>
      )}

      {/* Notifications Tab */}
      {tabValue === 3 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Telegram Notifications
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.telegramEnabled}
                        onChange={(e) => setSettings({ ...settings, telegramEnabled: e.target.checked })}
                      />
                    }
                    label="Enable Telegram Notifications"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Telegram Chat ID"
                    value={settings.telegramChatId}
                    onChange={(e) => setSettings({ ...settings, telegramChatId: e.target.value })}
                    disabled={!settings.telegramEnabled}
                  />
                </Grid>
              </Grid>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Notification Preferences
              </Typography>
              <List>
                <ListItem>
                  <ListItemText primary="Notify on Trade Execution" />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={settings.notifyOnTrade}
                      onChange={(e) => setSettings({ ...settings, notifyOnTrade: e.target.checked })}
                    />
                  </ListItemSecondaryAction>
                </ListItem>
                <ListItem>
                  <ListItemText primary="Notify on Errors" />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={settings.notifyOnError}
                      onChange={(e) => setSettings({ ...settings, notifyOnError: e.target.checked })}
                    />
                  </ListItemSecondaryAction>
                </ListItem>
                <ListItem>
                  <ListItemText primary="Daily Report" />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={settings.notifyDailyReport}
                      onChange={(e) => setSettings({ ...settings, notifyDailyReport: e.target.checked })}
                    />
                  </ListItemSecondaryAction>
                </ListItem>
              </List>
            </Paper>
          </Grid>

          <Grid item xs={12}>
            <Button variant="contained" startIcon={<Save />} onClick={handleSaveSettings}>
              Save Notification Settings
            </Button>
          </Grid>
        </Grid>
      )}

      {/* System Tab */}
      {tabValue === 4 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                System Configuration
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.autoStart}
                        onChange={(e) => setSettings({ ...settings, autoStart: e.target.checked })}
                      />
                    }
                    label="Auto-start trading on boot"
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.paperTrading}
                        onChange={(e) => setSettings({ ...settings, paperTrading: e.target.checked })}
                      />
                    }
                    label="Paper Trading Mode"
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.debugMode}
                        onChange={(e) => setSettings({ ...settings, debugMode: e.target.checked })}
                      />
                    }
                    label="Debug Mode"
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControl fullWidth>
                    <InputLabel>Log Level</InputLabel>
                    <Select
                      value={settings.logLevel}
                      label="Log Level"
                      onChange={(e) => setSettings({ ...settings, logLevel: e.target.value })}
                    >
                      <MenuItem value="DEBUG">DEBUG</MenuItem>
                      <MenuItem value="INFO">INFO</MenuItem>
                      <MenuItem value="WARNING">WARNING</MenuItem>
                      <MenuItem value="ERROR">ERROR</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Performance Settings
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Data Update Interval (ms)"
                    type="number"
                    value={settings.dataUpdateInterval}
                    onChange={(e) => setSettings({ ...settings, dataUpdateInterval: Number(e.target.value) })}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Order Retry Attempts"
                    type="number"
                    value={settings.orderRetryAttempts}
                    onChange={(e) => setSettings({ ...settings, orderRetryAttempts: Number(e.target.value) })}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Connection Timeout (ms)"
                    type="number"
                    value={settings.connectionTimeout}
                    onChange={(e) => setSettings({ ...settings, connectionTimeout: Number(e.target.value) })}
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.enableCache}
                        onChange={(e) => setSettings({ ...settings, enableCache: e.target.checked })}
                      />
                    }
                    label="Enable Cache"
                  />
                </Grid>
              </Grid>
            </Paper>
          </Grid>

          <Grid item xs={12}>
            <Button variant="contained" startIcon={<Save />} onClick={handleSaveSettings}>
              Save System Settings
            </Button>
          </Grid>
        </Grid>
      )}

      {/* Add Pair Dialog */}
      <Dialog open={addPairDialog} onClose={() => setAddPairDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Trading Pair</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Symbol (e.g., BTCUSDT)"
                value={newPair.symbol}
                onChange={(e) => setNewPair({ ...newPair, symbol: e.target.value.toUpperCase() })}
              />
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Category</InputLabel>
                <Select
                  value={newPair.category}
                  label="Category"
                  onChange={(e) => setNewPair({ ...newPair, category: e.target.value })}
                >
                  <MenuItem value="major">Major</MenuItem>
                  <MenuItem value="layer1">Layer 1</MenuItem>
                  <MenuItem value="layer2">Layer 2</MenuItem>
                  <MenuItem value="defi">DeFi</MenuItem>
                  <MenuItem value="gaming">Gaming</MenuItem>
                  <MenuItem value="ai">AI</MenuItem>
                  <MenuItem value="meme">Meme</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Volatility</InputLabel>
                <Select
                  value={newPair.volatility}
                  label="Volatility"
                  onChange={(e) => setNewPair({ ...newPair, volatility: e.target.value })}
                >
                  <MenuItem value="low">Low</MenuItem>
                  <MenuItem value="medium">Medium</MenuItem>
                  <MenuItem value="high">High</MenuItem>
                  <MenuItem value="extreme">Extreme</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <Typography gutterBottom>Leverage: {newPair.leverage}x</Typography>
              <Slider
                value={newPair.leverage}
                onChange={(e, v) => setNewPair({ ...newPair, leverage: v as number })}
                min={1}
                max={100}
                marks={[
                  { value: 1, label: '1x' },
                  { value: 50, label: '50x' },
                  { value: 100, label: '100x' }
                ]}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                fullWidth
                label="Min Position (USDT)"
                type="number"
                value={newPair.minPosition}
                onChange={(e) => setNewPair({ ...newPair, minPosition: Number(e.target.value) })}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                fullWidth
                label="Max Position (USDT)"
                type="number"
                value={newPair.maxPosition}
                onChange={(e) => setNewPair({ ...newPair, maxPosition: Number(e.target.value) })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddPairDialog(false)}>Cancel</Button>
          <Button onClick={handleAddPair} variant="contained">Add Pair</Button>
        </DialogActions>
      </Dialog>

      {/* Success Snackbar */}
      <Snackbar
        open={saveSuccess}
        autoHideDuration={3000}
        onClose={() => setSaveSuccess(false)}
        message="Settings saved successfully!"
      />
    </Box>
  );
};

export default Settings;