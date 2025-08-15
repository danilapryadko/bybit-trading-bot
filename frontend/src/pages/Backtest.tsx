import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  LinearProgress,
  Alert,
  IconButton,
} from '@mui/material';
import {
  PlayArrow as RunIcon,
  Download as DownloadIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { addBacktestResult } from '../store/slices/analyticsSlice';
import { sendMessage } from '../services/websocket';

const Backtest: React.FC = () => {
  const dispatch = useAppDispatch();
  const { backtestResults } = useAppSelector(state => state.analytics);
  const [isRunning, setIsRunning] = useState(false);
  const [backtestConfig, setBacktestConfig] = useState({
    strategy: 'ml_ensemble',
    symbol: 'BTCUSDT',
    startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    endDate: new Date().toISOString().split('T')[0],
    initialCapital: '10000',
    leverage: '1',
    commission: '0.06',
    slippage: '0.05',
  });

  const handleRunBacktest = async () => {
    setIsRunning(true);
    
    sendMessage({
      type: 'run_backtest',
      data: {
        ...backtestConfig,
        initialCapital: parseFloat(backtestConfig.initialCapital),
        leverage: parseInt(backtestConfig.leverage),
        commission: parseFloat(backtestConfig.commission) / 100,
        slippage: parseFloat(backtestConfig.slippage) / 100,
      },
    });

    // Simulate backtest completion (in real app, this would come from WebSocket)
    setTimeout(() => {
      const result = {
        id: Date.now().toString(),
        strategy: backtestConfig.strategy,
        symbol: backtestConfig.symbol,
        startDate: backtestConfig.startDate,
        endDate: backtestConfig.endDate,
        initialCapital: parseFloat(backtestConfig.initialCapital),
        finalCapital: parseFloat(backtestConfig.initialCapital) * 1.25,
        totalReturn: parseFloat(backtestConfig.initialCapital) * 0.25,
        totalReturnPercent: 25,
        maxDrawdown: -15.5,
        winRate: 58.3,
        profitFactor: 1.8,
        sharpeRatio: 1.2,
        totalTrades: 143,
        timestamp: Date.now(),
      };
      dispatch(addBacktestResult(result));
      setIsRunning(false);
    }, 3000);
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(price);
  };

  const formatPercent = (percent: number) => {
    const formatted = percent.toFixed(2);
    return percent >= 0 ? `+${formatted}%` : `${formatted}%`;
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Backtest
      </Typography>

      <Grid container spacing={3}>
        {/* Backtest Configuration */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Configuration
              </Typography>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <FormControl fullWidth>
                  <InputLabel>Strategy</InputLabel>
                  <Select
                    value={backtestConfig.strategy}
                    label="Strategy"
                    onChange={(e) => setBacktestConfig({ ...backtestConfig, strategy: e.target.value })}
                  >
                    <MenuItem value="ml_ensemble">ML Ensemble</MenuItem>
                    <MenuItem value="lstm">LSTM Neural Network</MenuItem>
                    <MenuItem value="random_forest">Random Forest</MenuItem>
                    <MenuItem value="xgboost">XGBoost</MenuItem>
                    <MenuItem value="momentum">Momentum</MenuItem>
                    <MenuItem value="mean_reversion">Mean Reversion</MenuItem>
                  </Select>
                </FormControl>

                <TextField
                  label="Symbol"
                  value={backtestConfig.symbol}
                  onChange={(e) => setBacktestConfig({ ...backtestConfig, symbol: e.target.value })}
                  fullWidth
                />

                <TextField
                  label="Start Date"
                  type="date"
                  value={backtestConfig.startDate}
                  onChange={(e) => setBacktestConfig({ ...backtestConfig, startDate: e.target.value })}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                />

                <TextField
                  label="End Date"
                  type="date"
                  value={backtestConfig.endDate}
                  onChange={(e) => setBacktestConfig({ ...backtestConfig, endDate: e.target.value })}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                />

                <TextField
                  label="Initial Capital ($)"
                  type="number"
                  value={backtestConfig.initialCapital}
                  onChange={(e) => setBacktestConfig({ ...backtestConfig, initialCapital: e.target.value })}
                  fullWidth
                />

                <TextField
                  label="Leverage"
                  type="number"
                  value={backtestConfig.leverage}
                  onChange={(e) => setBacktestConfig({ ...backtestConfig, leverage: e.target.value })}
                  fullWidth
                  inputProps={{ min: 1, max: 100 }}
                />

                <TextField
                  label="Commission (%)"
                  type="number"
                  value={backtestConfig.commission}
                  onChange={(e) => setBacktestConfig({ ...backtestConfig, commission: e.target.value })}
                  fullWidth
                  inputProps={{ step: 0.01 }}
                />

                <TextField
                  label="Slippage (%)"
                  type="number"
                  value={backtestConfig.slippage}
                  onChange={(e) => setBacktestConfig({ ...backtestConfig, slippage: e.target.value })}
                  fullWidth
                  inputProps={{ step: 0.01 }}
                />

                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<RunIcon />}
                  onClick={handleRunBacktest}
                  disabled={isRunning}
                  fullWidth
                >
                  {isRunning ? 'Running...' : 'Run Backtest'}
                </Button>
              </Box>

              {isRunning && (
                <Box sx={{ mt: 2 }}>
                  <LinearProgress />
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                    Running backtest simulation...
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>

          <Alert severity="info" sx={{ mt: 2 }}>
            Backtests use historical data to simulate trading performance. Past results do not guarantee future performance.
          </Alert>
        </Grid>

        {/* Backtest Results */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  Results History
                </Typography>
                {backtestResults.length > 0 && (
                  <Button
                    startIcon={<DownloadIcon />}
                    onClick={() => {
                      // TODO: Export results to CSV
                      console.log('Export results');
                    }}
                  >
                    Export CSV
                  </Button>
                )}
              </Box>

              <TableContainer component={Paper} sx={{ bgcolor: 'background.default' }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Strategy</TableCell>
                      <TableCell>Symbol</TableCell>
                      <TableCell>Period</TableCell>
                      <TableCell align="right">Return</TableCell>
                      <TableCell align="right">Max DD</TableCell>
                      <TableCell align="center">Win Rate</TableCell>
                      <TableCell align="right">Sharpe</TableCell>
                      <TableCell align="center">Trades</TableCell>
                      <TableCell align="center">Action</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {backtestResults.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={9} align="center">
                          <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
                            No backtest results yet. Run a backtest to see results here.
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      backtestResults.map((result) => (
                        <TableRow key={result.id}>
                          <TableCell>
                            <Typography variant="subtitle2">{result.strategy}</Typography>
                          </TableCell>
                          <TableCell>{result.symbol}</TableCell>
                          <TableCell>
                            <Typography variant="caption">
                              {result.startDate} to {result.endDate}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography
                              variant="body2"
                              color={result.totalReturn >= 0 ? 'success.main' : 'error.main'}
                            >
                              {formatPrice(result.totalReturn)}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {formatPercent(result.totalReturnPercent)}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body2" color="error.main">
                              {result.maxDrawdown.toFixed(1)}%
                            </Typography>
                          </TableCell>
                          <TableCell align="center">
                            <Chip
                              label={`${result.winRate.toFixed(1)}%`}
                              size="small"
                              color={result.winRate >= 50 ? 'success' : 'error'}
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell align="right">{result.sharpeRatio.toFixed(2)}</TableCell>
                          <TableCell align="center">{result.totalTrades}</TableCell>
                          <TableCell align="center">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => {
                                // TODO: Remove result
                                console.log('Remove result', result.id);
                              }}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Backtest;