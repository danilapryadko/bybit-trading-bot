import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Alert,
  Snackbar,
  CircularProgress,
} from '@mui/material';
import {
  Delete as DeleteIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
} from '@mui/icons-material';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { setTradingEnabled, setPaperTrading } from '../store/slices/tradingSlice';
import { useMutation, useQuery } from '@apollo/client';
import { PLACE_ORDER, CANCEL_ORDER } from '../graphql/mutations';
import { GET_ORDERS } from '../graphql/queries';
import apolloClient from '../services/apollo';

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
      id={`trading-tabpanel-${index}`}
      aria-labelledby={`trading-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const Trading: React.FC = () => {
  const dispatch = useAppDispatch();
  const [tabValue, setTabValue] = useState(0);
  const [orderForm, setOrderForm] = useState({
    symbol: 'BTCUSDT',
    side: 'Buy',
    orderType: 'Limit',
    quantity: '',
    price: '',
    stopPrice: '',
    timeInForce: 'GTC',
  });
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'info' as 'success' | 'error' | 'info' });

  const { activeSymbol, tickers } = useAppSelector(state => state.market);
  const {
    isTradingEnabled,
    isPaperTrading,
    orderHistory,
    tradingSignals,
  } = useAppSelector(state => state.trading);

  // GraphQL queries and mutations
  const { data: ordersData, loading: ordersLoading, refetch: refetchOrders } = useQuery(GET_ORDERS, {
    client: apolloClient,
    pollInterval: 5000, // Refresh every 5 seconds
  });

  const [placeOrder, { loading: placingOrder }] = useMutation(PLACE_ORDER, {
    client: apolloClient,
    onCompleted: (data) => {
      if (data.placeOrder.success) {
        setNotification({
          open: true,
          message: `Order placed successfully! Order ID: ${data.placeOrder.orderId}`,
          severity: 'success',
        });
        setOrderForm({
          ...orderForm,
          quantity: '',
          price: '',
          stopPrice: '',
        });
        refetchOrders();
      } else {
        setNotification({
          open: true,
          message: data.placeOrder.message || 'Failed to place order',
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

  const [cancelOrder, { loading: cancellingOrder }] = useMutation(CANCEL_ORDER, {
    client: apolloClient,
    onCompleted: (data) => {
      if (data.cancelOrder.success) {
        setNotification({
          open: true,
          message: 'Order cancelled successfully',
          severity: 'success',
        });
        refetchOrders();
      } else {
        setNotification({
          open: true,
          message: data.cancelOrder.message || 'Failed to cancel order',
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

  const activeOrders = ordersData?.recentTrades || [];

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleOrderSubmit = async () => {
    if (!orderForm.quantity) {
      setNotification({
        open: true,
        message: 'Please enter quantity',
        severity: 'error',
      });
      return;
    }

    if (orderForm.orderType === 'Limit' && !orderForm.price) {
      setNotification({
        open: true,
        message: 'Please enter price for limit order',
        severity: 'error',
      });
      return;
    }

    // Check if trading is enabled
    if (!isTradingEnabled) {
      setNotification({
        open: true,
        message: 'Please enable trading first',
        severity: 'error',
      });
      return;
    }

    // Paper trading check
    if (isPaperTrading) {
      setNotification({
        open: true,
        message: 'Paper trading mode - order will be simulated',
        severity: 'info',
      });
    }

    // Place order via GraphQL
    await placeOrder({
      variables: {
        input: {
          symbol: orderForm.symbol,
          side: orderForm.side,
          orderType: orderForm.orderType,
          quantity: parseFloat(orderForm.quantity),
          price: orderForm.price ? parseFloat(orderForm.price) : null,
          stopPrice: orderForm.stopPrice ? parseFloat(orderForm.stopPrice) : null,
          timeInForce: orderForm.timeInForce,
        },
      },
    });
  };

  const handleCancelOrder = async (orderId: string) => {
    await cancelOrder({
      variables: { orderId },
    });
  };

  const ticker = tickers[activeSymbol];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Trading</Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <FormControlLabel
            control={
              <Switch
                checked={isPaperTrading}
                onChange={(e) => dispatch(setPaperTrading(e.target.checked))}
              />
            }
            label="Paper Trading"
          />
          <Button
            variant="contained"
            color={isTradingEnabled ? 'error' : 'success'}
            startIcon={isTradingEnabled ? <StopIcon /> : <PlayIcon />}
            onClick={() => dispatch(setTradingEnabled(!isTradingEnabled))}
          >
            {isTradingEnabled ? 'Stop Trading' : 'Start Trading'}
          </Button>
        </Box>
      </Box>

      {isPaperTrading && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Paper trading mode is active. Orders will be simulated and not sent to the exchange.
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Order Form */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Place Order
              </Typography>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField
                  label="Symbol"
                  value={orderForm.symbol}
                  onChange={(e) => setOrderForm({ ...orderForm, symbol: e.target.value })}
                  fullWidth
                />

                <FormControl fullWidth>
                  <InputLabel>Side</InputLabel>
                  <Select
                    value={orderForm.side}
                    label="Side"
                    onChange={(e) => setOrderForm({ ...orderForm, side: e.target.value })}
                  >
                    <MenuItem value="Buy">Buy</MenuItem>
                    <MenuItem value="Sell">Sell</MenuItem>
                  </Select>
                </FormControl>

                <FormControl fullWidth>
                  <InputLabel>Order Type</InputLabel>
                  <Select
                    value={orderForm.orderType}
                    label="Order Type"
                    onChange={(e) => setOrderForm({ ...orderForm, orderType: e.target.value })}
                  >
                    <MenuItem value="Market">Market</MenuItem>
                    <MenuItem value="Limit">Limit</MenuItem>
                    <MenuItem value="StopLimit">Stop Limit</MenuItem>
                    <MenuItem value="StopMarket">Stop Market</MenuItem>
                  </Select>
                </FormControl>

                <TextField
                  label="Quantity"
                  type="number"
                  value={orderForm.quantity}
                  onChange={(e) => setOrderForm({ ...orderForm, quantity: e.target.value })}
                  fullWidth
                />

                {(orderForm.orderType === 'Limit' || orderForm.orderType === 'StopLimit') && (
                  <TextField
                    label="Price"
                    type="number"
                    value={orderForm.price}
                    onChange={(e) => setOrderForm({ ...orderForm, price: e.target.value })}
                    fullWidth
                    helperText={ticker ? `Last: $${ticker.lastPrice.toFixed(2)}` : ''}
                  />
                )}

                {(orderForm.orderType === 'StopLimit' || orderForm.orderType === 'StopMarket') && (
                  <TextField
                    label="Stop Price"
                    type="number"
                    value={orderForm.stopPrice}
                    onChange={(e) => setOrderForm({ ...orderForm, stopPrice: e.target.value })}
                    fullWidth
                  />
                )}

                <FormControl fullWidth>
                  <InputLabel>Time in Force</InputLabel>
                  <Select
                    value={orderForm.timeInForce}
                    label="Time in Force"
                    onChange={(e) => setOrderForm({ ...orderForm, timeInForce: e.target.value })}
                  >
                    <MenuItem value="GTC">GTC (Good Till Cancel)</MenuItem>
                    <MenuItem value="IOC">IOC (Immediate or Cancel)</MenuItem>
                    <MenuItem value="FOK">FOK (Fill or Kill)</MenuItem>
                    <MenuItem value="PostOnly">Post Only</MenuItem>
                  </Select>
                </FormControl>

                <Button
                  variant="contained"
                  color={orderForm.side === 'Buy' ? 'success' : 'error'}
                  onClick={handleOrderSubmit}
                  disabled={!isTradingEnabled || placingOrder}
                  fullWidth
                >
                  {placingOrder ? (
                    <CircularProgress size={24} color="inherit" />
                  ) : (
                    `${orderForm.side} ${orderForm.symbol}`
                  )}
                </Button>
              </Box>
            </CardContent>
          </Card>

          {/* Trading Signals */}
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Latest Signals
              </Typography>
              {tradingSignals.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No trading signals yet
                </Typography>
              ) : (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {tradingSignals.slice(0, 3).map((signal) => (
                    <Box
                      key={signal.id}
                      sx={{
                        p: 1,
                        border: '1px solid',
                        borderColor: 'divider',
                        borderRadius: 1,
                      }}
                    >
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="subtitle2">{signal.symbol}</Typography>
                        <Chip
                          label={signal.action}
                          size="small"
                          color={signal.action === 'BUY' ? 'success' : signal.action === 'SELL' ? 'error' : 'default'}
                        />
                      </Box>
                      <Typography variant="caption" color="text.secondary">
                        {signal.strategy} - {signal.confidence}% confidence
                      </Typography>
                    </Box>
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Orders Table */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs value={tabValue} onChange={handleTabChange}>
                  <Tab label={`Active Orders (${activeOrders.length})`} />
                  <Tab label="Order History" />
                </Tabs>
              </Box>

              <TabPanel value={tabValue} index={0}>
                <TableContainer component={Paper} sx={{ bgcolor: 'background.default' }}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Symbol</TableCell>
                        <TableCell>Side</TableCell>
                        <TableCell>Type</TableCell>
                        <TableCell align="right">Quantity</TableCell>
                        <TableCell align="right">Price</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell align="center">Action</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {activeOrders.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={7} align="center">
                            <Typography variant="body2" color="text.secondary">
                              No active orders
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ) : (
                        activeOrders.map((order) => (
                          <TableRow key={order.id}>
                            <TableCell>{order.symbol}</TableCell>
                            <TableCell>
                              <Chip
                                label={order.side}
                                size="small"
                                color={order.side === 'Buy' ? 'success' : 'error'}
                                variant="outlined"
                              />
                            </TableCell>
                            <TableCell>Market</TableCell>
                            <TableCell align="right">{order.quantity}</TableCell>
                            <TableCell align="right">
                              {order.price ? `$${order.price.toFixed(2)}` : 'Market'}
                            </TableCell>
                            <TableCell>
                              <Chip label={order.status || 'Filled'} size="small" />
                            </TableCell>
                            <TableCell align="center">
                              <IconButton
                                size="small"
                                onClick={() => handleCancelOrder(order.id)}
                                color="error"
                                disabled={cancellingOrder}
                              >
                                {cancellingOrder ? (
                                  <CircularProgress size={20} />
                                ) : (
                                  <DeleteIcon />
                                )}
                              </IconButton>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </TabPanel>

              <TabPanel value={tabValue} index={1}>
                <TableContainer component={Paper} sx={{ bgcolor: 'background.default' }}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Time</TableCell>
                        <TableCell>Symbol</TableCell>
                        <TableCell>Side</TableCell>
                        <TableCell>Type</TableCell>
                        <TableCell align="right">Quantity</TableCell>
                        <TableCell align="right">Price</TableCell>
                        <TableCell>Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {orderHistory.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={7} align="center">
                            <Typography variant="body2" color="text.secondary">
                              No order history
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ) : (
                        orderHistory.map((order) => (
                          <TableRow key={order.orderId}>
                            <TableCell>
                              {new Date(order.updatedTime).toLocaleString()}
                            </TableCell>
                            <TableCell>{order.symbol}</TableCell>
                            <TableCell>
                              <Chip
                                label={order.side}
                                size="small"
                                color={order.side === 'Buy' ? 'success' : 'error'}
                                variant="outlined"
                              />
                            </TableCell>
                            <TableCell>{order.orderType}</TableCell>
                            <TableCell align="right">{order.quantity}</TableCell>
                            <TableCell align="right">
                              {order.price ? `$${order.price.toFixed(2)}` : 'Market'}
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={order.status}
                                size="small"
                                color={
                                  order.status === 'Filled'
                                    ? 'success'
                                    : order.status === 'Cancelled' || order.status === 'Rejected'
                                    ? 'error'
                                    : 'default'
                                }
                              />
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </TabPanel>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      
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

export default Trading;