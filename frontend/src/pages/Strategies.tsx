import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Alert,
  Snackbar,
  CircularProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useQuery, useMutation } from '@apollo/client';
import { gql } from '@apollo/client';
import apolloClient from '../services/apollo';

// GraphQL Queries
const GET_STRATEGIES = gql`
  query GetStrategies {
    strategies {
      name
      type
      symbol
      isActive
      params
      lastSignal
      lastSignalTime
      confidence
    }
    strategyStatus {
      isRunning
      totalStrategies
      activeStrategies
      consensus {
        signal
        confidence
        strategiesAgree
        totalStrategies
      }
    }
  }
`;

const GET_STRATEGY_SIGNALS = gql`
  query GetStrategySignals {
    strategySignals {
      strategyName
      signal
      confidence
      metadata
      timestamp
    }
  }
`;

// GraphQL Mutations
const CREATE_STRATEGY = gql`
  mutation CreateStrategy($input: StrategyInput!) {
    createStrategy(input: $input) {
      success
      message
      strategy {
        name
        type
        symbol
        isActive
      }
    }
  }
`;

const ACTIVATE_STRATEGY = gql`
  mutation ActivateStrategy($name: String!) {
    activateStrategy(name: $name) {
      success
      message
    }
  }
`;

const DEACTIVATE_STRATEGY = gql`
  mutation DeactivateStrategy($name: String!) {
    deactivateStrategy(name: $name) {
      success
      message
    }
  }
`;

const DELETE_STRATEGY = gql`
  mutation DeleteStrategy($name: String!) {
    deleteStrategy(name: $name) {
      success
      message
    }
  }
`;

const RUN_ANALYSIS = gql`
  mutation RunStrategyAnalysis {
    runStrategyAnalysis {
      success
      signals {
        strategyName
        signal
        confidence
        metadata
        timestamp
      }
      consensus {
        signal
        confidence
        strategiesAgree
        totalStrategies
      }
    }
  }
`;

const Strategies: React.FC = () => {
  const [openDialog, setOpenDialog] = useState(false);
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'info' as 'success' | 'error' | 'info' });
  const [newStrategy, setNewStrategy] = useState({
    name: '',
    type: 'RSI',
    symbol: 'BTCUSDT',
    params: {
      rsi_period: 14,
      rsi_oversold: 30,
      rsi_overbought: 70,
      leverage: 10,
      position_size: 100,
      stop_loss_percent: 2,
      take_profit_percent: 3,
    },
  });

  // Queries
  const { data: strategiesData, loading, refetch } = useQuery(GET_STRATEGIES, {
    client: apolloClient,
    pollInterval: 10000, // Refresh every 10 seconds
  });

  const { data: signalsData } = useQuery(GET_STRATEGY_SIGNALS, {
    client: apolloClient,
    pollInterval: 5000, // Refresh every 5 seconds
  });

  // Mutations
  const [createStrategy] = useMutation(CREATE_STRATEGY, {
    client: apolloClient,
    onCompleted: (data) => {
      if (data.createStrategy.success) {
        setNotification({
          open: true,
          message: data.createStrategy.message,
          severity: 'success',
        });
        setOpenDialog(false);
        refetch();
      } else {
        setNotification({
          open: true,
          message: data.createStrategy.message,
          severity: 'error',
        });
      }
    },
  });

  const [activateStrategy] = useMutation(ACTIVATE_STRATEGY, {
    client: apolloClient,
    onCompleted: (data) => {
      setNotification({
        open: true,
        message: data.activateStrategy.message,
        severity: data.activateStrategy.success ? 'success' : 'error',
      });
      refetch();
    },
  });

  const [deactivateStrategy] = useMutation(DEACTIVATE_STRATEGY, {
    client: apolloClient,
    onCompleted: (data) => {
      setNotification({
        open: true,
        message: data.deactivateStrategy.message,
        severity: data.deactivateStrategy.success ? 'success' : 'error',
      });
      refetch();
    },
  });

  const [deleteStrategy] = useMutation(DELETE_STRATEGY, {
    client: apolloClient,
    onCompleted: (data) => {
      setNotification({
        open: true,
        message: data.deleteStrategy.message,
        severity: data.deleteStrategy.success ? 'success' : 'error',
      });
      refetch();
    },
  });

  const [runAnalysis, { loading: analyzing }] = useMutation(RUN_ANALYSIS, {
    client: apolloClient,
    onCompleted: (data) => {
      if (data.runStrategyAnalysis.success) {
        setNotification({
          open: true,
          message: `Analysis complete. Consensus: ${data.runStrategyAnalysis.consensus?.signal || 'HOLD'}`,
          severity: 'info',
        });
      }
    },
  });

  const strategies = strategiesData?.strategies || [];
  const status = strategiesData?.strategyStatus;
  const signals = signalsData?.strategySignals || [];

  const handleCreateStrategy = () => {
    createStrategy({
      variables: {
        input: {
          name: newStrategy.name,
          type: newStrategy.type,
          symbol: newStrategy.symbol,
          params: JSON.stringify(newStrategy.params),
        },
      },
    });
  };

  const handleToggleStrategy = (name: string, isActive: boolean) => {
    if (isActive) {
      deactivateStrategy({ variables: { name } });
    } else {
      activateStrategy({ variables: { name } });
    }
  };

  const handleDeleteStrategy = (name: string) => {
    if (window.confirm(`Are you sure you want to delete strategy "${name}"?`)) {
      deleteStrategy({ variables: { name } });
    }
  };

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case 'BUY':
        return 'success';
      case 'SELL':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Trading Strategies</Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => runAnalysis()}
            disabled={analyzing}
          >
            {analyzing ? 'Analyzing...' : 'Run Analysis'}
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenDialog(true)}
          >
            Add Strategy
          </Button>
        </Box>
      </Box>

      {/* Status Overview */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="subtitle2" gutterBottom>
                Total Strategies
              </Typography>
              <Typography variant="h5">
                {status?.totalStrategies || 0}
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
                {status?.activeStrategies?.length || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="subtitle2" gutterBottom>
                Consensus Signal
              </Typography>
              <Chip
                label={status?.consensus?.signal || 'HOLD'}
                color={getSignalColor(status?.consensus?.signal || 'HOLD')}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="subtitle2" gutterBottom>
                Consensus Confidence
              </Typography>
              <Typography variant="h5">
                {((status?.consensus?.confidence || 0) * 100).toFixed(1)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Strategies Table */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Strategy List
          </Typography>

          {loading ? (
            <CircularProgress />
          ) : (
            <TableContainer component={Paper} sx={{ bgcolor: 'background.default' }}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Symbol</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Last Signal</TableCell>
                    <TableCell>Confidence</TableCell>
                    <TableCell align="center">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {strategies.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} align="center">
                        <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
                          No strategies configured
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    strategies.map((strategy: any) => (
                      <TableRow key={strategy.name}>
                        <TableCell>{strategy.name}</TableCell>
                        <TableCell>{strategy.type}</TableCell>
                        <TableCell>{strategy.symbol}</TableCell>
                        <TableCell>
                          <Chip
                            label={strategy.isActive ? 'Active' : 'Inactive'}
                            color={strategy.isActive ? 'success' : 'default'}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          {strategy.lastSignal && (
                            <Chip
                              label={strategy.lastSignal}
                              color={getSignalColor(strategy.lastSignal)}
                              size="small"
                            />
                          )}
                        </TableCell>
                        <TableCell>
                          {strategy.confidence ? `${(strategy.confidence * 100).toFixed(1)}%` : '-'}
                        </TableCell>
                        <TableCell align="center">
                          <IconButton
                            size="small"
                            onClick={() => handleToggleStrategy(strategy.name, strategy.isActive)}
                            color={strategy.isActive ? 'error' : 'success'}
                          >
                            {strategy.isActive ? <StopIcon /> : <PlayIcon />}
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => handleDeleteStrategy(strategy.name)}
                            color="error"
                          >
                            <DeleteIcon />
                          </IconButton>
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

      {/* Recent Signals */}
      {signals.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Recent Signals
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {signals.slice(0, 5).map((signal: any, index: number) => (
                <Alert
                  key={index}
                  severity={signal.signal === 'BUY' ? 'success' : signal.signal === 'SELL' ? 'error' : 'info'}
                >
                  <strong>{signal.strategyName}</strong>: {signal.signal} with {(signal.confidence * 100).toFixed(1)}% confidence
                  {signal.timestamp && ` at ${new Date(signal.timestamp).toLocaleTimeString()}`}
                </Alert>
              ))}
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Add Strategy Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add New Strategy</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Strategy Name"
              value={newStrategy.name}
              onChange={(e) => setNewStrategy({ ...newStrategy, name: e.target.value })}
              fullWidth
            />
            
            <FormControl fullWidth>
              <InputLabel>Strategy Type</InputLabel>
              <Select
                value={newStrategy.type}
                label="Strategy Type"
                onChange={(e) => setNewStrategy({ ...newStrategy, type: e.target.value })}
              >
                <MenuItem value="RSI">RSI Strategy</MenuItem>
                <MenuItem value="MA">Moving Average</MenuItem>
                <MenuItem value="Combined">Combined Strategy</MenuItem>
              </Select>
            </FormControl>

            <TextField
              label="Symbol"
              value={newStrategy.symbol}
              onChange={(e) => setNewStrategy({ ...newStrategy, symbol: e.target.value })}
              fullWidth
            />

            <Typography variant="subtitle2" sx={{ mt: 2 }}>
              Strategy Parameters
            </Typography>

            {newStrategy.type === 'RSI' && (
              <>
                <TextField
                  label="RSI Period"
                  type="number"
                  value={newStrategy.params.rsi_period}
                  onChange={(e) => setNewStrategy({
                    ...newStrategy,
                    params: { ...newStrategy.params, rsi_period: parseInt(e.target.value) }
                  })}
                  fullWidth
                />
                <TextField
                  label="RSI Oversold"
                  type="number"
                  value={newStrategy.params.rsi_oversold}
                  onChange={(e) => setNewStrategy({
                    ...newStrategy,
                    params: { ...newStrategy.params, rsi_oversold: parseInt(e.target.value) }
                  })}
                  fullWidth
                />
                <TextField
                  label="RSI Overbought"
                  type="number"
                  value={newStrategy.params.rsi_overbought}
                  onChange={(e) => setNewStrategy({
                    ...newStrategy,
                    params: { ...newStrategy.params, rsi_overbought: parseInt(e.target.value) }
                  })}
                  fullWidth
                />
              </>
            )}

            <TextField
              label="Position Size (USDT)"
              type="number"
              value={newStrategy.params.position_size}
              onChange={(e) => setNewStrategy({
                ...newStrategy,
                params: { ...newStrategy.params, position_size: parseFloat(e.target.value) }
              })}
              fullWidth
            />

            <TextField
              label="Stop Loss %"
              type="number"
              value={newStrategy.params.stop_loss_percent}
              onChange={(e) => setNewStrategy({
                ...newStrategy,
                params: { ...newStrategy.params, stop_loss_percent: parseFloat(e.target.value) }
              })}
              fullWidth
            />

            <TextField
              label="Take Profit %"
              type="number"
              value={newStrategy.params.take_profit_percent}
              onChange={(e) => setNewStrategy({
                ...newStrategy,
                params: { ...newStrategy.params, take_profit_percent: parseFloat(e.target.value) }
              })}
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button onClick={handleCreateStrategy} variant="contained">
            Create Strategy
          </Button>
        </DialogActions>
      </Dialog>

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

export default Strategies;