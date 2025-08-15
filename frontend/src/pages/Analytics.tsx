import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { setSelectedTimeframe } from '../store/slices/analyticsSlice';

const Analytics: React.FC = () => {
  const dispatch = useAppDispatch();
  const {
    // performanceHistory,
    strategyPerformance,
    marketAnalysis,
    selectedTimeframe,
  } = useAppSelector(state => state.analytics);

  const handleTimeframeChange = (
    _event: React.MouseEvent<HTMLElement>,
    newTimeframe: '1D' | '1W' | '1M' | '3M' | '1Y' | 'ALL'
  ) => {
    if (newTimeframe) {
      dispatch(setSelectedTimeframe(newTimeframe));
    }
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(price);
  };

  // const _formatPercent = (percent: number) => {
  //   const formatted = percent.toFixed(2);
  //   return percent >= 0 ? `+${formatted}%` : `${formatted}%`;
  // };

  // Calculate summary metrics
  const totalPnl = strategyPerformance.reduce((sum, s) => sum + s.totalPnl, 0);
  const avgWinRate = strategyPerformance.length > 0
    ? strategyPerformance.reduce((sum, s) => sum + s.winRate, 0) / strategyPerformance.length
    : 0;
  const totalTrades = strategyPerformance.reduce((sum, s) => sum + s.totalTrades, 0);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Analytics</Typography>
        <ToggleButtonGroup
          value={selectedTimeframe}
          exclusive
          onChange={handleTimeframeChange}
          size="small"
        >
          <ToggleButton value="1D">1D</ToggleButton>
          <ToggleButton value="1W">1W</ToggleButton>
          <ToggleButton value="1M">1M</ToggleButton>
          <ToggleButton value="3M">3M</ToggleButton>
          <ToggleButton value="1Y">1Y</ToggleButton>
          <ToggleButton value="ALL">ALL</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {/* Performance Summary */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="subtitle2" gutterBottom>
                Total P&L
              </Typography>
              <Typography
                variant="h5"
                color={totalPnl >= 0 ? 'success.main' : 'error.main'}
              >
                {formatPrice(totalPnl)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="subtitle2" gutterBottom>
                Win Rate
              </Typography>
              <Typography variant="h5">
                {avgWinRate.toFixed(1)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="subtitle2" gutterBottom>
                Total Trades
              </Typography>
              <Typography variant="h5">
                {totalTrades}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="subtitle2" gutterBottom>
                Active Strategies
              </Typography>
              <Typography variant="h5">
                {strategyPerformance.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Strategy Performance */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Strategy Performance
          </Typography>
          <TableContainer component={Paper} sx={{ bgcolor: 'background.default' }}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Strategy</TableCell>
                  <TableCell align="right">Total P&L</TableCell>
                  <TableCell align="center">Win Rate</TableCell>
                  <TableCell align="right">Avg Win</TableCell>
                  <TableCell align="right">Avg Loss</TableCell>
                  <TableCell align="right">Profit Factor</TableCell>
                  <TableCell align="right">Sharpe Ratio</TableCell>
                  <TableCell align="center">Total Trades</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {strategyPerformance.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} align="center">
                      <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
                        No strategy performance data available
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  strategyPerformance.map((strategy) => (
                    <TableRow key={strategy.strategyName}>
                      <TableCell>
                        <Typography variant="subtitle2">{strategy.strategyName}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography
                          variant="body2"
                          color={strategy.totalPnl >= 0 ? 'success.main' : 'error.main'}
                        >
                          {formatPrice(strategy.totalPnl)}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={`${strategy.winRate.toFixed(1)}%`}
                          size="small"
                          color={strategy.winRate >= 50 ? 'success' : 'error'}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell align="right">{formatPrice(strategy.avgWin)}</TableCell>
                      <TableCell align="right">{formatPrice(Math.abs(strategy.avgLoss))}</TableCell>
                      <TableCell align="right">
                        <Typography
                          variant="body2"
                          color={strategy.profitFactor >= 1 ? 'success.main' : 'error.main'}
                        >
                          {strategy.profitFactor.toFixed(2)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">{strategy.sharpeRatio.toFixed(2)}</TableCell>
                      <TableCell align="center">
                        <Box>
                          <Typography variant="body2">{strategy.totalTrades}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {strategy.winningTrades}W / {strategy.losingTrades}L
                          </Typography>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Market Analysis */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Market Analysis
          </Typography>
          <Grid container spacing={2}>
            {Object.entries(marketAnalysis).map(([symbol, analysis]) => (
              <Grid item xs={12} md={6} lg={4} key={symbol}>
                <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="subtitle1">{symbol}</Typography>
                    <Chip
                      label={analysis.trend}
                      size="small"
                      color={
                        analysis.trend === 'bullish'
                          ? 'success'
                          : analysis.trend === 'bearish'
                          ? 'error'
                          : 'default'
                      }
                    />
                  </Box>
                  <Grid container spacing={1}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        RSI
                      </Typography>
                      <Typography variant="body2">
                        {analysis.rsi.toFixed(1)}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Volatility
                      </Typography>
                      <Typography variant="body2">
                        {(analysis.volatility * 100).toFixed(1)}%
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        MACD
                      </Typography>
                      <Typography
                        variant="body2"
                        color={analysis.macd.histogram >= 0 ? 'success.main' : 'error.main'}
                      >
                        {analysis.macd.histogram.toFixed(2)}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        BB Position
                      </Typography>
                      <Typography variant="body2">
                        {analysis.bollingerBands.middle.toFixed(2)}
                      </Typography>
                    </Grid>
                  </Grid>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
};

export default Analytics;