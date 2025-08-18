import React, { useState } from 'react';
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
  Button,
  IconButton,
  LinearProgress,
  CircularProgress,
  Snackbar,
  Alert,
} from '@mui/material';
import {
  Close as CloseIcon,
  Edit as EditIcon,
} from '@mui/icons-material';
import { useQuery, useMutation } from '@apollo/client';
import { GET_POSITIONS } from '../graphql/queries';
import { CLOSE_POSITION } from '../graphql/mutations';
import apolloClient from '../services/apollo';

const Positions: React.FC = () => {
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'info' as 'success' | 'error' | 'info' });
  
  // GraphQL queries and mutations
  const { data: positionsData, loading: isLoading, refetch: refetchPositions } = useQuery(GET_POSITIONS, {
    client: apolloClient,
    pollInterval: 5000, // Refresh every 5 seconds
  });

  const [closePosition, { loading: closingPosition }] = useMutation(CLOSE_POSITION, {
    client: apolloClient,
    onCompleted: (data) => {
      if (data.closePosition.success) {
        setNotification({
          open: true,
          message: `Position closed successfully! Realized P&L: $${data.closePosition.realizedPnl?.toFixed(2) || '0.00'}`,
          severity: 'success',
        });
        refetchPositions();
      } else {
        setNotification({
          open: true,
          message: data.closePosition.message || 'Failed to close position',
          severity: 'error',
        });
      }
    },
    onError: (error) => {
      setNotification({
        open: true,
        message: error.message,
        severity: 'error',
      });
    },
  });

  const positions = positionsData?.positions || [];
  
  // Calculate metrics
  const metrics = {
    totalUnrealizedPnl: positions.reduce((sum: number, p: any) => sum + (p.unrealizedPnl || 0), 0),
    totalPositionValue: positions.reduce((sum: number, p: any) => sum + (p.size * p.markPrice), 0),
    totalMarginUsed: positions.reduce((sum: number, p: any) => sum + (p.size * p.avgPrice / (p.leverage || 1)), 0),
    marginRatio: 0,
    accountEquity: 0,
    numberOfPositions: positions.length,
  };

  const handleClosePosition = async (symbol: string) => {
    if (window.confirm(`Are you sure you want to close position for ${symbol}?`)) {
      await closePosition({
        variables: { symbol },
      });
    }
  };

  const handleCloseAllPositions = async () => {
    if (window.confirm('Are you sure you want to close ALL positions?')) {
      for (const position of positions) {
        await closePosition({
          variables: { symbol: position.symbol },
        });
      }
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

  const formatPercent = (percent: number) => {
    const formatted = percent.toFixed(2);
    return percent >= 0 ? `+${formatted}%` : `${formatted}%`;
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Positions
      </Typography>

      {/* Metrics Overview */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="subtitle2" gutterBottom>
                Total Unrealized P&L
              </Typography>
              <Typography
                variant="h5"
                color={metrics.totalUnrealizedPnl >= 0 ? 'success.main' : 'error.main'}
              >
                {formatPrice(metrics.totalUnrealizedPnl)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="subtitle2" gutterBottom>
                Total Position Value
              </Typography>
              <Typography variant="h5">
                {formatPrice(metrics.totalPositionValue)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="subtitle2" gutterBottom>
                Margin Used
              </Typography>
              <Typography variant="h5">
                {formatPrice(metrics.totalMarginUsed)}
              </Typography>
              <LinearProgress
                variant="determinate"
                value={metrics.marginRatio}
                sx={{ mt: 1 }}
                color={metrics.marginRatio > 80 ? 'error' : metrics.marginRatio > 60 ? 'warning' : 'success'}
              />
              <Typography variant="caption" color="text.secondary">
                {metrics.marginRatio.toFixed(1)}% of equity
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="subtitle2" gutterBottom>
                Account Equity
              </Typography>
              <Typography variant="h5">
                {formatPrice(metrics.accountEquity)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {metrics.numberOfPositions} open position{metrics.numberOfPositions !== 1 ? 's' : ''}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Positions Table */}
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              Open Positions
            </Typography>
            {positions.length > 0 && (
              <Button
                color="error"
                variant="outlined"
                onClick={handleCloseAllPositions}
                disabled={closingPosition}
              >
                {closingPosition ? <CircularProgress size={20} /> : 'Close All'}
              </Button>
            )}
          </Box>

          {isLoading ? (
            <LinearProgress />
          ) : (
            <TableContainer component={Paper} sx={{ bgcolor: 'background.default' }}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Symbol</TableCell>
                    <TableCell align="center">Side</TableCell>
                    <TableCell align="center">Leverage</TableCell>
                    <TableCell align="right">Size</TableCell>
                    <TableCell align="right">Entry Price</TableCell>
                    <TableCell align="right">Mark Price</TableCell>
                    <TableCell align="right">Liq. Price</TableCell>
                    <TableCell align="right">Unrealized P&L</TableCell>
                    <TableCell align="right">ROE</TableCell>
                    <TableCell align="center">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {positions.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={10} align="center">
                        <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
                          No open positions
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    positions.map((position) => (
                      <TableRow key={position.symbol}>
                        <TableCell>
                          <Typography variant="subtitle2">{position.symbol}</Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Chip
                            label={position.side}
                            size="small"
                            color={position.side === 'Buy' ? 'success' : 'error'}
                          />
                        </TableCell>
                        <TableCell align="center">
                          <Chip
                            label={`${position.leverage || 1}x`}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell align="right">{position.size}</TableCell>
                        <TableCell align="right">{formatPrice(position.avgPrice || 0)}</TableCell>
                        <TableCell align="right">{formatPrice(position.markPrice || 0)}</TableCell>
                        <TableCell align="right">
                          {position.liquidationPrice ? (
                            <Typography
                              variant="body2"
                              color={
                                Math.abs(position.markPrice - position.liquidationPrice) /
                                  position.markPrice < 0.1
                                  ? 'error.main'
                                  : 'text.primary'
                              }
                            >
                              {formatPrice(position.liquidationPrice)}
                            </Typography>
                          ) : (
                            '-'
                          )}
                        </TableCell>
                        <TableCell align="right">
                          <Typography
                            variant="body2"
                            color={position.unrealizedPnl >= 0 ? 'success.main' : 'error.main'}
                          >
                            {formatPrice(position.unrealizedPnl || 0)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography
                            variant="body2"
                            color={position.unrealizedPnl >= 0 ? 'success.main' : 'error.main'}
                          >
                            {position.size && position.avgPrice ? formatPercent((position.unrealizedPnl / (position.size * position.avgPrice)) * 100) : '0.00%'}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <IconButton
                              size="small"
                              onClick={() => {
                                // TODO: Open edit modal
                                console.log('Edit position', position.symbol);
                              }}
                            >
                              <EditIcon fontSize="small" />
                            </IconButton>
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => handleClosePosition(position.symbol)}
                              disabled={closingPosition}
                            >
                              {closingPosition ? <CircularProgress size={16} /> : <CloseIcon fontSize="small" />}
                            </IconButton>
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>
      
      {/* Notification Snackbar */}
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={() => setNotification({ ...notification, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setNotification({ ...notification, open: false })}
          severity={notification.severity}
          sx={{ width: '100%' }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Positions;