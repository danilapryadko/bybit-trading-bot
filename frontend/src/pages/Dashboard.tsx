import React, { useEffect, useState } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  LinearProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  FormControl,
  Select,
  MenuItem,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  AccountBalance as BalanceIcon,
  ShowChart as ChartIcon,
} from '@mui/icons-material';
import { useAppSelector } from '../store/hooks';
import { subscribeToChannel } from '../services/websocket';
import TradingChart from '../components/TradingChart';
import { useRealBalance } from '../hooks/useRealBalance';
import { useRealTickers } from '../hooks/useRealTickers';

const Dashboard: React.FC = () => {
  // Fetch real balance from API with auto-reconnect
  const { error: connectionError, retryCount } = useRealBalance();
  const { tickers, watchlist, isConnected } = useAppSelector(state => state.market);
  const { currentBalance, availableBalance } = useAppSelector(state => state.trading);
  const { positions, metrics } = useAppSelector(state => state.positions);
  const { isTradingEnabled, isPaperTrading, activeOrders } = useAppSelector(state => state.trading);
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT');

  // Fetch real ticker data for watchlist
  useRealTickers(watchlist);

  useEffect(() => {
    // Subscribe to watchlist symbols (disabled as we're using polling)
    // watchlist.forEach(symbol => {
    //   subscribeToChannel('ticker', { symbol });
    // });
  }, [watchlist]);

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
        Dashboard
      </Typography>

      {!isConnected && (
        <Box sx={{ mb: 3 }}>
          <LinearProgress color={retryCount > 3 ? "error" : "warning"} />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {retryCount === 0 
              ? 'Connecting to trading server...'
              : `Reconnecting... (attempt ${retryCount})`
            }
            {connectionError && (
              <Typography variant="caption" display="block" color="error">
                {connectionError}
              </Typography>
            )}
          </Typography>
        </Box>
      )}

      {/* Account Overview */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <BalanceIcon sx={{ mr: 1, color: 'primary.main' }} />
                <Typography color="text.secondary" variant="subtitle2">
                  Total Balance
                </Typography>
              </Box>
              <Typography variant="h5">{formatPrice(currentBalance)}</Typography>
              <Box sx={{ mt: 1 }}>
                <Chip
                  label={isPaperTrading ? 'Paper Trading' : 'Live Trading'}
                  size="small"
                  color={isPaperTrading ? 'warning' : 'success'}
                  variant="outlined"
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <ChartIcon sx={{ mr: 1, color: 'secondary.main' }} />
                <Typography color="text.secondary" variant="subtitle2">
                  Available Balance
                </Typography>
              </Box>
              <Typography variant="h5">{formatPrice(availableBalance)}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                {((availableBalance / currentBalance) * 100).toFixed(1)}% available
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                {metrics.totalUnrealizedPnl >= 0 ? (
                  <TrendingUpIcon sx={{ mr: 1, color: 'success.main' }} />
                ) : (
                  <TrendingDownIcon sx={{ mr: 1, color: 'error.main' }} />
                )}
                <Typography color="text.secondary" variant="subtitle2">
                  Unrealized P&L
                </Typography>
              </Box>
              <Typography
                variant="h5"
                color={metrics.totalUnrealizedPnl >= 0 ? 'success.main' : 'error.main'}
              >
                {formatPrice(metrics.totalUnrealizedPnl)}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                {positions.length} open position{positions.length !== 1 ? 's' : ''}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <ChartIcon sx={{ mr: 1, color: 'info.main' }} />
                <Typography color="text.secondary" variant="subtitle2">
                  Active Orders
                </Typography>
              </Box>
              <Typography variant="h5">{activeOrders.length}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                {isTradingEnabled ? 'Trading Enabled' : 'Trading Disabled'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Watchlist */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Watchlist
          </Typography>
          <TableContainer component={Paper} sx={{ bgcolor: 'background.default' }}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Symbol</TableCell>
                  <TableCell align="right">Price</TableCell>
                  <TableCell align="right">24h Change</TableCell>
                  <TableCell align="right">24h Volume</TableCell>
                  <TableCell align="right">High</TableCell>
                  <TableCell align="right">Low</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {watchlist.map((symbol) => {
                  const ticker = tickers[symbol];
                  if (!ticker) {
                    return (
                      <TableRow key={symbol}>
                        <TableCell>{symbol}</TableCell>
                        <TableCell colSpan={5} align="center">
                          <Typography variant="body2" color="text.secondary">
                            Loading...
                          </Typography>
                        </TableCell>
                      </TableRow>
                    );
                  }
                  return (
                    <TableRow key={symbol}>
                      <TableCell>
                        <Typography variant="subtitle2">{symbol}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2">{formatPrice(ticker.lastPrice)}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                          <Typography
                            variant="body2"
                            color={ticker.priceChange24h >= 0 ? 'success.main' : 'error.main'}
                          >
                            {formatPrice(ticker.priceChange24h)}
                          </Typography>
                          <Chip
                            label={formatPercent(ticker.priceChangePercent24h)}
                            size="small"
                            color={ticker.priceChangePercent24h >= 0 ? 'success' : 'error'}
                            sx={{ ml: 1 }}
                          />
                        </Box>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2">
                          ${(ticker.volume24h / 1000000).toFixed(2)}M
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2">{formatPrice(ticker.high24h)}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2">{formatPrice(ticker.low24h)}</Typography>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* TradingView Chart */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              Price Chart
            </Typography>
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <Select
                value={selectedSymbol}
                onChange={(e) => setSelectedSymbol(e.target.value)}
              >
                {watchlist.map(symbol => (
                  <MenuItem key={symbol} value={symbol}>{symbol}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
          <TradingChart symbol={selectedSymbol} height={400} />
        </CardContent>
      </Card>

      {/* Open Positions Summary */}
      {positions.length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Open Positions
            </Typography>
            <TableContainer component={Paper} sx={{ bgcolor: 'background.default' }}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Symbol</TableCell>
                    <TableCell align="center">Side</TableCell>
                    <TableCell align="right">Size</TableCell>
                    <TableCell align="right">Entry Price</TableCell>
                    <TableCell align="right">Mark Price</TableCell>
                    <TableCell align="right">P&L</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {positions.slice(0, 5).map((position) => (
                    <TableRow key={position.symbol}>
                      <TableCell>
                        <Typography variant="subtitle2">{position.symbol}</Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={position.side}
                          size="small"
                          color={position.side === 'Buy' ? 'success' : 'error'}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell align="right">{position.size}</TableCell>
                      <TableCell align="right">{formatPrice(position.entryPrice)}</TableCell>
                      <TableCell align="right">{formatPrice(position.markPrice)}</TableCell>
                      <TableCell align="right">
                        <Typography
                          variant="body2"
                          color={position.unrealizedPnl >= 0 ? 'success.main' : 'error.main'}
                        >
                          {formatPrice(position.unrealizedPnl)} ({formatPercent(position.pnlPercent)})
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default Dashboard;