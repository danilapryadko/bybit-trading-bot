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
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  Divider,
  Chip,
  Grid,
  Tooltip,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Info as InfoIcon,
  TrendingUp as BuyIcon,
  TrendingDown as SellIcon,
} from '@mui/icons-material';
import { useMutation } from '@apollo/client';
import { gql } from '@apollo/client';

const PLACE_ORDER = gql`
  mutation PlaceOrder($order: OrderInput!) {
    placeOrder(order: $order) {
      success
      orderId
      message
    }
  }
`;

interface OrderForm {
  symbol: string;
  side: 'Buy' | 'Sell';
  orderType: 'Market' | 'Limit';
  quantity: string;
  price: string;
  stopLoss: string;
  takeProfit: string;
  timeInForce: string;
  
  // Safe Orders (DCA) settings
  useSafeOrders: boolean;
  baseOrderSize: string;
  safeOrderSize: string;
  maxSafeOrders: string;
  safeOrderVolumeScale: string;
  safeOrderStepScale: string;
  priceDeviation: string;
  takeProfitPercent: string;
  stopLossPercent: string;
  
  // Grid settings
  useGrid: boolean;
  gridLevels: string;
  gridSpacing: string;
  gridUpperLimit: string;
  gridLowerLimit: string;
}

const TradingPanel: React.FC = () => {
  const [placeOrder, { loading }] = useMutation(PLACE_ORDER);
  const [orderForm, setOrderForm] = useState<OrderForm>({
    symbol: 'BTCUSDT',
    side: 'Buy',
    orderType: 'Market',
    quantity: '0.001',
    price: '',
    stopLoss: '',
    takeProfit: '',
    timeInForce: 'GTC',
    
    // Safe Orders defaults
    useSafeOrders: false,
    baseOrderSize: '50',
    safeOrderSize: '100',
    maxSafeOrders: '5',
    safeOrderVolumeScale: '1.5',
    safeOrderStepScale: '1.2',
    priceDeviation: '1.0',
    takeProfitPercent: '2.0',
    stopLossPercent: '10.0',
    
    // Grid defaults
    useGrid: false,
    gridLevels: '10',
    gridSpacing: '0.5',
    gridUpperLimit: '120000',
    gridLowerLimit: '110000',
  });

  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = async () => {
    try {
      const orderData: any = {
        symbol: orderForm.symbol,
        side: orderForm.side,
        orderType: orderForm.orderType,
        quantity: parseFloat(orderForm.quantity),
        timeInForce: orderForm.timeInForce,
      };

      // Add price for limit orders
      if (orderForm.orderType === 'Limit' && orderForm.price) {
        orderData.price = parseFloat(orderForm.price);
      }

      // Add stop loss and take profit
      if (orderForm.stopLoss) {
        orderData.stopLoss = parseFloat(orderForm.stopLoss);
      }
      if (orderForm.takeProfit) {
        orderData.takeProfit = parseFloat(orderForm.takeProfit);
      }

      // Add Safe Orders configuration
      if (orderForm.useSafeOrders) {
        orderData.safeOrders = {
          enabled: true,
          baseOrderSize: parseFloat(orderForm.baseOrderSize),
          safeOrderSize: parseFloat(orderForm.safeOrderSize),
          maxSafeOrders: parseInt(orderForm.maxSafeOrders),
          volumeScale: parseFloat(orderForm.safeOrderVolumeScale),
          stepScale: parseFloat(orderForm.safeOrderStepScale),
          priceDeviation: parseFloat(orderForm.priceDeviation),
          takeProfitPercent: parseFloat(orderForm.takeProfitPercent),
        };
      }

      // Add Grid configuration
      if (orderForm.useGrid) {
        orderData.grid = {
          enabled: true,
          levels: parseInt(orderForm.gridLevels),
          spacing: parseFloat(orderForm.gridSpacing),
          upperLimit: parseFloat(orderForm.gridUpperLimit),
          lowerLimit: parseFloat(orderForm.gridLowerLimit),
        };
      }

      const result = await placeOrder({
        variables: { order: orderData },
      });

      if (result.data?.placeOrder?.success) {
        alert(`Order placed successfully! ID: ${result.data.placeOrder.orderId}`);
      } else {
        alert(`Failed to place order: ${result.data?.placeOrder?.message}`);
      }
    } catch (error) {
      alert(`Error: ${error}`);
    }
  };

  const calculateTotalInvestment = () => {
    if (!orderForm.useSafeOrders) {
      return parseFloat(orderForm.quantity || '0') * parseFloat(orderForm.price || '0');
    }

    const baseOrder = parseFloat(orderForm.baseOrderSize || '0');
    const safeOrderSize = parseFloat(orderForm.safeOrderSize || '0');
    const maxOrders = parseInt(orderForm.maxSafeOrders || '0');
    const volumeScale = parseFloat(orderForm.safeOrderVolumeScale || '1');

    let total = baseOrder;
    let currentVolume = safeOrderSize;

    for (let i = 0; i < maxOrders; i++) {
      total += currentVolume;
      currentVolume *= volumeScale;
    }

    return total;
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Advanced Trading Panel
        </Typography>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Basic Order Settings */}
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Symbol"
                value={orderForm.symbol}
                onChange={(e) => setOrderForm({ ...orderForm, symbol: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Side</InputLabel>
                <Select
                  value={orderForm.side}
                  label="Side"
                  onChange={(e) => setOrderForm({ ...orderForm, side: e.target.value as 'Buy' | 'Sell' })}
                >
                  <MenuItem value="Buy">
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <BuyIcon color="success" />
                      Buy / Long
                    </Box>
                  </MenuItem>
                  <MenuItem value="Sell">
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <SellIcon color="error" />
                      Sell / Short
                    </Box>
                  </MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>

          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Order Type</InputLabel>
                <Select
                  value={orderForm.orderType}
                  label="Order Type"
                  onChange={(e) => setOrderForm({ ...orderForm, orderType: e.target.value as 'Market' | 'Limit' })}
                >
                  <MenuItem value="Market">Market</MenuItem>
                  <MenuItem value="Limit">Limit</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Quantity"
                type="number"
                value={orderForm.quantity}
                onChange={(e) => setOrderForm({ ...orderForm, quantity: e.target.value })}
                helperText="Amount in base currency"
              />
            </Grid>
          </Grid>

          {orderForm.orderType === 'Limit' && (
            <TextField
              fullWidth
              label="Limit Price"
              type="number"
              value={orderForm.price}
              onChange={(e) => setOrderForm({ ...orderForm, price: e.target.value })}
            />
          )}

          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Stop Loss"
                type="number"
                value={orderForm.stopLoss}
                onChange={(e) => setOrderForm({ ...orderForm, stopLoss: e.target.value })}
                helperText="Optional - Price to stop loss"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Take Profit"
                type="number"
                value={orderForm.takeProfit}
                onChange={(e) => setOrderForm({ ...orderForm, takeProfit: e.target.value })}
                helperText="Optional - Price to take profit"
              />
            </Grid>
          </Grid>

          <Divider />

          {/* Safe Orders (DCA) Settings */}
          <Accordion expanded={orderForm.useSafeOrders} onChange={(_, expanded) => setOrderForm({ ...orderForm, useSafeOrders: expanded })}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <FormControlLabel
                control={<Switch checked={orderForm.useSafeOrders} />}
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography>Safe Orders (DCA)</Typography>
                    <Tooltip title="Dollar Cost Averaging - Automatically place additional orders if price moves against you">
                      <InfoIcon fontSize="small" />
                    </Tooltip>
                  </Box>
                }
                onClick={(e) => e.stopPropagation()}
              />
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Base Order Size ($)"
                    type="number"
                    value={orderForm.baseOrderSize}
                    onChange={(e) => setOrderForm({ ...orderForm, baseOrderSize: e.target.value })}
                    helperText="Initial order size in USDT"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Safety Order Size ($)"
                    type="number"
                    value={orderForm.safeOrderSize}
                    onChange={(e) => setOrderForm({ ...orderForm, safeOrderSize: e.target.value })}
                    helperText="First safety order size"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Max Safety Orders"
                    type="number"
                    value={orderForm.maxSafeOrders}
                    onChange={(e) => setOrderForm({ ...orderForm, maxSafeOrders: e.target.value })}
                    helperText="Maximum number of safety orders"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Price Deviation (%)"
                    type="number"
                    value={orderForm.priceDeviation}
                    onChange={(e) => setOrderForm({ ...orderForm, priceDeviation: e.target.value })}
                    helperText="Price drop for first SO"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Volume Scale"
                    type="number"
                    value={orderForm.safeOrderVolumeScale}
                    onChange={(e) => setOrderForm({ ...orderForm, safeOrderVolumeScale: e.target.value })}
                    helperText="Multiplier for each SO volume"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Step Scale"
                    type="number"
                    value={orderForm.safeOrderStepScale}
                    onChange={(e) => setOrderForm({ ...orderForm, safeOrderStepScale: e.target.value })}
                    helperText="Multiplier for SO price steps"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Take Profit (%)"
                    type="number"
                    value={orderForm.takeProfitPercent}
                    onChange={(e) => setOrderForm({ ...orderForm, takeProfitPercent: e.target.value })}
                    helperText="TP from average price"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Stop Loss (%)"
                    type="number"
                    value={orderForm.stopLossPercent}
                    onChange={(e) => setOrderForm({ ...orderForm, stopLossPercent: e.target.value })}
                    helperText="Optional SL from average"
                  />
                </Grid>
              </Grid>
              
              {orderForm.useSafeOrders && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  Total Investment: ${calculateTotalInvestment().toFixed(2)}
                </Alert>
              )}
            </AccordionDetails>
          </Accordion>

          {/* Grid Trading Settings */}
          <Accordion expanded={orderForm.useGrid} onChange={(_, expanded) => setOrderForm({ ...orderForm, useGrid: expanded })}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <FormControlLabel
                control={<Switch checked={orderForm.useGrid} />}
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography>Grid Trading</Typography>
                    <Tooltip title="Place multiple buy and sell orders in a price range">
                      <InfoIcon fontSize="small" />
                    </Tooltip>
                  </Box>
                }
                onClick={(e) => e.stopPropagation()}
              />
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Grid Levels"
                    type="number"
                    value={orderForm.gridLevels}
                    onChange={(e) => setOrderForm({ ...orderForm, gridLevels: e.target.value })}
                    helperText="Number of grid levels"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Grid Spacing (%)"
                    type="number"
                    value={orderForm.gridSpacing}
                    onChange={(e) => setOrderForm({ ...orderForm, gridSpacing: e.target.value })}
                    helperText="Space between levels"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Upper Limit"
                    type="number"
                    value={orderForm.gridUpperLimit}
                    onChange={(e) => setOrderForm({ ...orderForm, gridUpperLimit: e.target.value })}
                    helperText="Upper price boundary"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Lower Limit"
                    type="number"
                    value={orderForm.gridLowerLimit}
                    onChange={(e) => setOrderForm({ ...orderForm, gridLowerLimit: e.target.value })}
                    helperText="Lower price boundary"
                  />
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>

          <Divider />

          {/* Strategy Summary */}
          {(orderForm.useSafeOrders || orderForm.useGrid) && (
            <Box sx={{ p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
              <Typography variant="subtitle2" gutterBottom>
                Strategy Summary
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {orderForm.useSafeOrders && (
                  <Chip label="DCA Active" color="primary" size="small" />
                )}
                {orderForm.useGrid && (
                  <Chip label="Grid Active" color="secondary" size="small" />
                )}
                <Chip label={`Investment: $${calculateTotalInvestment().toFixed(2)}`} size="small" />
                {orderForm.useSafeOrders && (
                  <Chip label={`${orderForm.maxSafeOrders} Safety Orders`} size="small" />
                )}
                {orderForm.useGrid && (
                  <Chip label={`${orderForm.gridLevels} Grid Levels`} size="small" />
                )}
              </Box>
            </Box>
          )}

          {/* Submit Button */}
          <Button
            variant="contained"
            color={orderForm.side === 'Buy' ? 'success' : 'error'}
            size="large"
            onClick={handleSubmit}
            disabled={loading}
            fullWidth
          >
            {loading ? 'Placing Order...' : `${orderForm.side} ${orderForm.symbol}`}
          </Button>

          {/* Risk Warning */}
          <Alert severity="warning">
            <Typography variant="caption">
              Trading involves risk. Ensure you understand the strategy settings before placing orders.
              {orderForm.useSafeOrders && ' DCA will automatically place additional orders if price moves against you.'}
              {orderForm.useGrid && ' Grid trading works best in ranging markets.'}
            </Typography>
          </Alert>
        </Box>
      </CardContent>
    </Card>
  );
};

export default TradingPanel;