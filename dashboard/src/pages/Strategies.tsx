import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Switch,
  Button,
  Slider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Chip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Tabs,
  Tab,
  LinearProgress
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Settings,
  TrendingUp,
  Psychology,
  Speed,
  ShowChart,
  Delete,
  Add,
  Edit,
  Save,
  Cancel
} from '@mui/icons-material';
import { useAppDispatch, useAppSelector } from '../hooks/redux';

interface Strategy {
  id: string;
  name: string;
  type: 'scalping' | 'swing' | 'trend' | 'ml' | 'arbitrage';
  enabled: boolean;
  performance: {
    winRate: number;
    totalPnL: number;
    trades: number;
    sharpeRatio: number;
  };
  parameters: {
    [key: string]: any;
  };
  pairs: string[];
  riskLevel: 'low' | 'medium' | 'high' | 'extreme';
}

const Strategies: React.FC = () => {
  const [strategies, setStrategies] = useState<Strategy[]>([
    {
      id: 'ml_ensemble',
      name: 'ML Ensemble',
      type: 'ml',
      enabled: true,
      performance: {
        winRate: 68.5,
        totalPnL: 2845.30,
        trades: 156,
        sharpeRatio: 1.85
      },
      parameters: {
        confidence_threshold: 0.65,
        models: ['LSTM', 'XGBoost', 'RandomForest'],
        feature_count: 60,
        lookback_period: 100
      },
      pairs: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
      riskLevel: 'medium'
    },
    {
      id: 'scalping_bot',
      name: 'High Frequency Scalper',
      type: 'scalping',
      enabled: false,
      performance: {
        winRate: 62.3,
        totalPnL: 1234.50,
        trades: 523,
        sharpeRatio: 1.45
      },
      parameters: {
        timeframe: '1m',
        take_profit: 0.003,
        stop_loss: 0.002,
        volume_threshold: 1000000
      },
      pairs: ['DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT'],
      riskLevel: 'extreme'
    },
    {
      id: 'trend_follower',
      name: 'Trend Following System',
      type: 'trend',
      enabled: true,
      performance: {
        winRate: 55.2,
        totalPnL: 3567.80,
        trades: 89,
        sharpeRatio: 2.15
      },
      parameters: {
        ema_fast: 12,
        ema_slow: 26,
        macd_signal: 9,
        atr_multiplier: 2
      },
      pairs: ['BTCUSDT', 'ETHUSDT', 'LINKUSDT'],
      riskLevel: 'low'
    }
  ]);

  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [tabValue, setTabValue] = useState(0);
  const [newStrategyDialog, setNewStrategyDialog] = useState(false);

  const handleToggleStrategy = (strategyId: string) => {
    setStrategies(prev => prev.map(s => 
      s.id === strategyId ? { ...s, enabled: !s.enabled } : s
    ));
  };

  const handleEditStrategy = (strategy: Strategy) => {
    setSelectedStrategy(strategy);
    setEditMode(true);
  };

  const handleSaveStrategy = () => {
    if (selectedStrategy) {
      setStrategies(prev => prev.map(s => 
        s.id === selectedStrategy.id ? selectedStrategy : s
      ));
      setEditMode(false);
    }
  };

  const handleDeleteStrategy = (strategyId: string) => {
    setStrategies(prev => prev.filter(s => s.id !== strategyId));
  };

  const getStrategyIcon = (type: string) => {
    switch (type) {
      case 'ml': return <Psychology />;
      case 'scalping': return <Speed />;
      case 'trend': return <TrendingUp />;
      case 'swing': return <ShowChart />;
      default: return <ShowChart />;
    }
  };

  const getRiskColor = (level: string) => {
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
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Trading Strategies</Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => setNewStrategyDialog(true)}
        >
          Add Strategy
        </Button>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Active Strategies
              </Typography>
              <Typography variant="h4">
                {strategies.filter(s => s.enabled).length}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                of {strategies.length} total
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total P&L
              </Typography>
              <Typography variant="h4" color="success.main">
                ${strategies.reduce((sum, s) => sum + s.performance.totalPnL, 0).toFixed(2)}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                All strategies combined
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Average Win Rate
              </Typography>
              <Typography variant="h4">
                {(strategies.reduce((sum, s) => sum + s.performance.winRate, 0) / strategies.length).toFixed(1)}%
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Across all strategies
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Trades
              </Typography>
              <Typography variant="h4">
                {strategies.reduce((sum, s) => sum + s.performance.trades, 0)}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Last 30 days
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab label="All Strategies" />
          <Tab label="Machine Learning" />
          <Tab label="Technical Analysis" />
          <Tab label="High Frequency" />
        </Tabs>
      </Paper>

      {/* Strategy Cards */}
      <Grid container spacing={3}>
        {strategies
          .filter(s => {
            if (tabValue === 0) return true;
            if (tabValue === 1) return s.type === 'ml';
            if (tabValue === 2) return s.type === 'trend' || s.type === 'swing';
            if (tabValue === 3) return s.type === 'scalping';
            return true;
          })
          .map(strategy => (
          <Grid item xs={12} md={6} lg={4} key={strategy.id}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {getStrategyIcon(strategy.type)}
                    <Typography variant="h6">{strategy.name}</Typography>
                  </Box>
                  <Switch
                    checked={strategy.enabled}
                    onChange={() => handleToggleStrategy(strategy.id)}
                    color="primary"
                  />
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Chip 
                    label={strategy.type.toUpperCase()} 
                    size="small" 
                    sx={{ mr: 1 }}
                  />
                  <Chip 
                    label={`Risk: ${strategy.riskLevel}`}
                    size="small"
                    color={getRiskColor(strategy.riskLevel) as any}
                  />
                </Box>

                <Grid container spacing={2} sx={{ mb: 2 }}>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="textSecondary">
                      Win Rate
                    </Typography>
                    <Typography variant="h6">
                      {strategy.performance.winRate}%
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="textSecondary">
                      Total P&L
                    </Typography>
                    <Typography variant="h6" color={strategy.performance.totalPnL > 0 ? 'success.main' : 'error.main'}>
                      ${strategy.performance.totalPnL.toFixed(2)}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="textSecondary">
                      Trades
                    </Typography>
                    <Typography variant="h6">
                      {strategy.performance.trades}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="textSecondary">
                      Sharpe Ratio
                    </Typography>
                    <Typography variant="h6">
                      {strategy.performance.sharpeRatio}
                    </Typography>
                  </Grid>
                </Grid>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="textSecondary" gutterBottom>
                    Trading Pairs
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {strategy.pairs.map(pair => (
                      <Chip key={pair} label={pair} size="small" variant="outlined" />
                    ))}
                  </Box>
                </Box>

                {strategy.enabled && (
                  <LinearProgress 
                    variant="determinate" 
                    value={strategy.performance.winRate} 
                    sx={{ mb: 2 }}
                  />
                )}
              </CardContent>
              <CardActions>
                <Button 
                  size="small" 
                  startIcon={<Settings />}
                  onClick={() => handleEditStrategy(strategy)}
                >
                  Configure
                </Button>
                <Button 
                  size="small" 
                  startIcon={<ShowChart />}
                >
                  Backtest
                </Button>
                <IconButton 
                  size="small" 
                  color="error"
                  onClick={() => handleDeleteStrategy(strategy.id)}
                >
                  <Delete />
                </IconButton>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Edit Strategy Dialog */}
      <Dialog open={editMode} onClose={() => setEditMode(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          Edit Strategy: {selectedStrategy?.name}
        </DialogTitle>
        <DialogContent>
          {selectedStrategy && (
            <Box sx={{ pt: 2 }}>
              <TextField
                fullWidth
                label="Strategy Name"
                value={selectedStrategy.name}
                onChange={(e) => setSelectedStrategy({
                  ...selectedStrategy,
                  name: e.target.value
                })}
                sx={{ mb: 2 }}
              />
              
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Risk Level</InputLabel>
                <Select
                  value={selectedStrategy.riskLevel}
                  label="Risk Level"
                  onChange={(e) => setSelectedStrategy({
                    ...selectedStrategy,
                    riskLevel: e.target.value as any
                  })}
                >
                  <MenuItem value="low">Low</MenuItem>
                  <MenuItem value="medium">Medium</MenuItem>
                  <MenuItem value="high">High</MenuItem>
                  <MenuItem value="extreme">Extreme</MenuItem>
                </Select>
              </FormControl>

              <Typography gutterBottom>Parameters</Typography>
              <Box sx={{ pl: 2, mb: 2 }}>
                {Object.entries(selectedStrategy.parameters).map(([key, value]) => (
                  <Box key={key} sx={{ mb: 2 }}>
                    <Typography variant="body2" gutterBottom>
                      {key.replace(/_/g, ' ').toUpperCase()}
                    </Typography>
                    {typeof value === 'number' ? (
                      <Slider
                        value={value}
                        onChange={(e, v) => setSelectedStrategy({
                          ...selectedStrategy,
                          parameters: {
                            ...selectedStrategy.parameters,
                            [key]: v
                          }
                        })}
                        min={0}
                        max={key.includes('threshold') ? 1 : 100}
                        step={key.includes('threshold') ? 0.01 : 1}
                        valueLabelDisplay="auto"
                      />
                    ) : (
                      <TextField
                        fullWidth
                        size="small"
                        value={value}
                        onChange={(e) => setSelectedStrategy({
                          ...selectedStrategy,
                          parameters: {
                            ...selectedStrategy.parameters,
                            [key]: e.target.value
                          }
                        })}
                      />
                    )}
                  </Box>
                ))}
              </Box>

              <Typography gutterBottom>Trading Pairs</Typography>
              <FormControl fullWidth sx={{ mb: 2 }}>
                <Select
                  multiple
                  value={selectedStrategy.pairs}
                  onChange={(e) => setSelectedStrategy({
                    ...selectedStrategy,
                    pairs: e.target.value as string[]
                  })}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'MATICUSDT', 'LINKUSDT', 'ARBUSDT', 'DOGEUSDT'].map(pair => (
                    <MenuItem key={pair} value={pair}>
                      {pair}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditMode(false)}>Cancel</Button>
          <Button onClick={handleSaveStrategy} variant="contained">Save Changes</Button>
        </DialogActions>
      </Dialog>

      {/* New Strategy Dialog */}
      <Dialog open={newStrategyDialog} onClose={() => setNewStrategyDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Strategy</DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mt: 2 }}>
            Choose from pre-configured strategy templates or create a custom one
          </Alert>
          <List>
            <ListItem button>
              <ListItemText 
                primary="ML Ensemble Strategy"
                secondary="Machine learning with multiple models"
              />
            </ListItem>
            <ListItem button>
              <ListItemText 
                primary="Scalping Strategy"
                secondary="High frequency trading on volatile pairs"
              />
            </ListItem>
            <ListItem button>
              <ListItemText 
                primary="Trend Following"
                secondary="Classic technical analysis approach"
              />
            </ListItem>
            <ListItem button>
              <ListItemText 
                primary="Custom Strategy"
                secondary="Build your own from scratch"
              />
            </ListItem>
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setNewStrategyDialog(false)}>Cancel</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Strategies;