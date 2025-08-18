import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  IconButton,
  Tooltip,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Switch,
  FormControlLabel
} from '@mui/material';
import {
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Treemap,
  ScatterChart,
  Scatter
} from 'recharts';
import {
  AccountBalance,
  TrendingUp,
  Assessment,
  Refresh,
  Add,
  Delete,
  Edit,
  Warning,
  CheckCircle,
  Error,
  Autorenew,
  ShowChart,
  BubbleChart,
  DonutLarge
} from '@mui/icons-material';
import { useQuery, useMutation, gql } from '@apollo/client';

// GraphQL Queries
const GET_PORTFOLIO_SUMMARY = gql`
  query GetPortfolioSummary {
    getPortfolioSummary {
      totalValue
      dailyReturn
      totalReturn
      volatility
      sharpeRatio
      sortinoRatio
      maxDrawdown
      calmarRatio
      var95
      effectiveAssets
    }
    getPortfolioAssets {
      symbol
      weight
      value
      returns
      risk
    }
  }
`;

const OPTIMIZE_PORTFOLIO = gql`
  mutation OptimizePortfolio($method: String!, $assets: [String!]!) {
    optimizePortfolio(method: $method, assets: $assets) {
      weights
      expectedReturn
      expectedVolatility
      sharpeRatio
      method
      regime
      success
    }
  }
`;

const CHECK_REBALANCE = gql`
  query CheckRebalance {
    checkRebalanceNeeded {
      needed
      reason
      maxDeviation
      trades {
        symbol
        currentValue
        targetValue
        tradeValue
        tradeType
        tradeCost
      }
      transactionCost
    }
  }
`;

const GET_CORRELATION_MATRIX = gql`
  query GetCorrelationMatrix($assets: [String!]!) {
    getCorrelationMatrix(assets: $assets) {
      matrix
      averageCorrelation
      maxCorrelation
      minCorrelation
      highlyCorrelated {
        asset1
        asset2
        correlation
        pValue
        stable
      }
    }
  }
`;

const Portfolio: React.FC = () => {
  const [selectedMethod, setSelectedMethod] = useState('sharpe');
  const [showRebalanceDialog, setShowRebalanceDialog] = useState(false);
  const [showAddAssetDialog, setShowAddAssetDialog] = useState(false);
  const [autoRebalance, setAutoRebalance] = useState(false);
  const [newAsset, setNewAsset] = useState({ symbol: '', allocation: 0 });

  // Queries
  const { data: portfolioData, loading: portfolioLoading, refetch: refetchPortfolio } = 
    useQuery(GET_PORTFOLIO_SUMMARY, { pollInterval: 30000 });
  
  const { data: rebalanceData, loading: rebalanceLoading, refetch: refetchRebalance } = 
    useQuery(CHECK_REBALANCE);
  
  const { data: correlationData, loading: correlationLoading } = 
    useQuery(GET_CORRELATION_MATRIX, {
      variables: { 
        assets: portfolioData?.getPortfolioAssets?.map((a: any) => a.symbol) || []
      },
      skip: !portfolioData?.getPortfolioAssets
    });

  // Mutations
  const [optimizePortfolio] = useMutation(OPTIMIZE_PORTFOLIO);

  // Handle portfolio optimization
  const handleOptimize = async () => {
    try {
      const assets = portfolioData?.getPortfolioAssets?.map((a: any) => a.symbol) || [];
      const result = await optimizePortfolio({
        variables: { method: selectedMethod, assets }
      });
      
      if (result.data?.optimizePortfolio?.success) {
        refetchPortfolio();
        refetchRebalance();
      }
    } catch (error) {
      console.error('Optimization error:', error);
    }
  };

  // Prepare chart data
  const allocationData = portfolioData?.getPortfolioAssets?.map((asset: any) => ({
    name: asset.symbol,
    value: asset.weight * 100,
    actualValue: asset.value
  })) || [];

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

  // Risk-Return scatter data
  const riskReturnData = portfolioData?.getPortfolioAssets?.map((asset: any) => ({
    x: asset.risk * 100,
    y: asset.returns * 100,
    name: asset.symbol,
    size: asset.weight * 1000
  })) || [];

  // Performance metrics for radar chart
  const performanceMetrics = [
    { metric: 'Returns', value: portfolioData?.getPortfolioSummary?.totalReturn * 100 || 0, fullMark: 50 },
    { metric: 'Sharpe', value: portfolioData?.getPortfolioSummary?.sharpeRatio * 20 || 0, fullMark: 100 },
    { metric: 'Sortino', value: portfolioData?.getPortfolioSummary?.sortinoRatio * 20 || 0, fullMark: 100 },
    { metric: 'Calmar', value: portfolioData?.getPortfolioSummary?.calmarRatio * 20 || 0, fullMark: 100 },
    { metric: 'Diversification', value: portfolioData?.getPortfolioSummary?.effectiveAssets * 10 || 0, fullMark: 100 },
    { metric: 'Risk Control', value: (1 - Math.abs(portfolioData?.getPortfolioSummary?.maxDrawdown || 0)) * 100, fullMark: 100 }
  ];

  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  // Format percentage
  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(2)}%`;
  };

  if (portfolioLoading) {
    return (
      <Container>
        <Box sx={{ width: '100%', mt: 4 }}>
          <LinearProgress />
        </Box>
      </Container>
    );
  }

  const summary = portfolioData?.getPortfolioSummary;
  const assets = portfolioData?.getPortfolioAssets || [];

  return (
    <Container maxWidth="xl">
      <Box sx={{ mt: 4, mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          <AccountBalance sx={{ mr: 1, verticalAlign: 'bottom' }} />
          Portfolio Management
        </Typography>

        {/* Key Metrics */}
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Total Value
                </Typography>
                <Typography variant="h5">
                  {formatCurrency(summary?.totalValue || 0)}
                </Typography>
                <Typography variant="body2" color={summary?.dailyReturn >= 0 ? 'success.main' : 'error.main'}>
                  {summary?.dailyReturn >= 0 ? '+' : ''}{formatPercent(summary?.dailyReturn || 0)} today
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Total Return
                </Typography>
                <Typography variant="h5" color={summary?.totalReturn >= 0 ? 'success.main' : 'error.main'}>
                  {summary?.totalReturn >= 0 ? '+' : ''}{formatPercent(summary?.totalReturn || 0)}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Sharpe: {summary?.sharpeRatio?.toFixed(2) || '0.00'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Risk Metrics
                </Typography>
                <Typography variant="h5">
                  {formatPercent(summary?.volatility || 0)}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  VaR (95%): {formatCurrency(summary?.var95 || 0)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Max Drawdown
                </Typography>
                <Typography variant="h5" color="error.main">
                  {formatPercent(summary?.maxDrawdown || 0)}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Calmar: {summary?.calmarRatio?.toFixed(2) || '0.00'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Optimization Controls */}
        <Paper sx={{ p: 2, mb: 3 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Optimization Method</InputLabel>
                <Select
                  value={selectedMethod}
                  onChange={(e) => setSelectedMethod(e.target.value)}
                  label="Optimization Method"
                >
                  <MenuItem value="sharpe">Maximum Sharpe Ratio</MenuItem>
                  <MenuItem value="min_variance">Minimum Variance</MenuItem>
                  <MenuItem value="risk_parity">Risk Parity</MenuItem>
                  <MenuItem value="max_return">Maximum Return</MenuItem>
                  <MenuItem value="black_litterman">Black-Litterman</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Button
                variant="contained"
                startIcon={<Assessment />}
                onClick={handleOptimize}
                fullWidth
              >
                Optimize Portfolio
              </Button>
            </Grid>

            <Grid item xs={12} md={3}>
              <Button
                variant="outlined"
                startIcon={<Autorenew />}
                onClick={() => setShowRebalanceDialog(true)}
                fullWidth
                color={rebalanceData?.checkRebalanceNeeded?.needed ? 'warning' : 'primary'}
              >
                {rebalanceData?.checkRebalanceNeeded?.needed ? 'Rebalance Needed' : 'Check Rebalance'}
              </Button>
            </Grid>

            <Grid item xs={12} md={3}>
              <FormControlLabel
                control={
                  <Switch
                    checked={autoRebalance}
                    onChange={(e) => setAutoRebalance(e.target.checked)}
                  />
                }
                label="Auto-Rebalance"
              />
            </Grid>
          </Grid>
        </Paper>

        {/* Rebalance Alert */}
        {rebalanceData?.checkRebalanceNeeded?.needed && (
          <Alert 
            severity="warning" 
            sx={{ mb: 3 }}
            action={
              <Button color="inherit" size="small" onClick={() => setShowRebalanceDialog(true)}>
                View Details
              </Button>
            }
          >
            Portfolio rebalancing recommended: {rebalanceData.checkRebalanceNeeded.reason}
          </Alert>
        )}

        {/* Main Content Grid */}
        <Grid container spacing={3}>
          {/* Asset Allocation Pie Chart */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, height: 400 }}>
              <Typography variant="h6" gutterBottom>
                Asset Allocation
              </Typography>
              <ResponsiveContainer width="100%" height="90%">
                <PieChart>
                  <Pie
                    data={allocationData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={(entry) => `${entry.name}: ${entry.value.toFixed(1)}%`}
                    outerRadius={120}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {allocationData.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                </PieChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>

          {/* Risk-Return Scatter Plot */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, height: 400 }}>
              <Typography variant="h6" gutterBottom>
                Risk-Return Profile
              </Typography>
              <ResponsiveContainer width="100%" height="90%">
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="x" 
                    name="Risk" 
                    unit="%" 
                    label={{ value: 'Risk (%)', position: 'insideBottom', offset: -5 }}
                  />
                  <YAxis 
                    dataKey="y" 
                    name="Return" 
                    unit="%" 
                    label={{ value: 'Return (%)', angle: -90, position: 'insideLeft' }}
                  />
                  <RechartsTooltip cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter 
                    name="Assets" 
                    data={riskReturnData} 
                    fill="#8884d8"
                  >
                    {riskReturnData.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>

          {/* Performance Radar Chart */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, height: 400 }}>
              <Typography variant="h6" gutterBottom>
                Performance Metrics
              </Typography>
              <ResponsiveContainer width="100%" height="90%">
                <RadarChart data={performanceMetrics}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="metric" />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} />
                  <Radar
                    name="Portfolio"
                    dataKey="value"
                    stroke="#8884d8"
                    fill="#8884d8"
                    fillOpacity={0.6}
                  />
                  <RechartsTooltip />
                </RadarChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>

          {/* Correlation Heatmap */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, height: 400 }}>
              <Typography variant="h6" gutterBottom>
                Correlation Analysis
              </Typography>
              {correlationData?.getCorrelationMatrix?.highlyCorrelated?.length > 0 ? (
                <Box>
                  <Alert severity="info" sx={{ mb: 2 }}>
                    Average Correlation: {correlationData.getCorrelationMatrix.averageCorrelation.toFixed(3)}
                  </Alert>
                  <Typography variant="subtitle2" gutterBottom>
                    Highly Correlated Pairs:
                  </Typography>
                  {correlationData.getCorrelationMatrix.highlyCorrelated.map((pair: any, idx: number) => (
                    <Chip
                      key={idx}
                      label={`${pair.asset1}-${pair.asset2}: ${pair.correlation.toFixed(2)}`}
                      color={pair.correlation > 0.8 ? 'warning' : 'default'}
                      sx={{ mr: 1, mb: 1 }}
                    />
                  ))}
                </Box>
              ) : (
                <Typography color="textSecondary">
                  No significant correlations detected
                </Typography>
              )}
            </Paper>
          </Grid>

          {/* Asset Holdings Table */}
          <Grid item xs={12}>
            <Paper sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h6">
                  Portfolio Holdings
                </Typography>
                <Button
                  startIcon={<Add />}
                  onClick={() => setShowAddAssetDialog(true)}
                  size="small"
                >
                  Add Asset
                </Button>
              </Box>
              
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Asset</TableCell>
                      <TableCell align="right">Weight</TableCell>
                      <TableCell align="right">Value</TableCell>
                      <TableCell align="right">Returns</TableCell>
                      <TableCell align="right">Risk</TableCell>
                      <TableCell align="center">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {assets.map((asset: any) => (
                      <TableRow key={asset.symbol}>
                        <TableCell>
                          <Typography variant="subtitle2">{asset.symbol}</Typography>
                        </TableCell>
                        <TableCell align="right">
                          {formatPercent(asset.weight)}
                        </TableCell>
                        <TableCell align="right">
                          {formatCurrency(asset.value)}
                        </TableCell>
                        <TableCell align="right">
                          <Typography color={asset.returns >= 0 ? 'success.main' : 'error.main'}>
                            {asset.returns >= 0 ? '+' : ''}{formatPercent(asset.returns)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          {formatPercent(asset.risk)}
                        </TableCell>
                        <TableCell align="center">
                          <IconButton size="small">
                            <Edit />
                          </IconButton>
                          <IconButton size="small" color="error">
                            <Delete />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>
        </Grid>

        {/* Rebalance Dialog */}
        <Dialog
          open={showRebalanceDialog}
          onClose={() => setShowRebalanceDialog(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle>Portfolio Rebalancing</DialogTitle>
          <DialogContent>
            {rebalanceData?.checkRebalanceNeeded?.needed ? (
              <Box>
                <Alert severity="warning" sx={{ mb: 2 }}>
                  {rebalanceData.checkRebalanceNeeded.reason}
                </Alert>
                <Typography variant="subtitle1" gutterBottom>
                  Required Trades:
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Asset</TableCell>
                        <TableCell align="right">Current Value</TableCell>
                        <TableCell align="right">Target Value</TableCell>
                        <TableCell align="right">Trade Value</TableCell>
                        <TableCell align="center">Action</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {rebalanceData.checkRebalanceNeeded.trades.map((trade: any) => (
                        <TableRow key={trade.symbol}>
                          <TableCell>{trade.symbol}</TableCell>
                          <TableCell align="right">{formatCurrency(trade.currentValue)}</TableCell>
                          <TableCell align="right">{formatCurrency(trade.targetValue)}</TableCell>
                          <TableCell align="right">{formatCurrency(Math.abs(trade.tradeValue))}</TableCell>
                          <TableCell align="center">
                            <Chip
                              label={trade.tradeType}
                              color={trade.tradeType === 'BUY' ? 'success' : 'error'}
                              size="small"
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" color="textSecondary">
                    Estimated Transaction Cost: {formatCurrency(rebalanceData.checkRebalanceNeeded.transactionCost)}
                  </Typography>
                </Box>
              </Box>
            ) : (
              <Alert severity="success">
                Portfolio is balanced. No rebalancing needed at this time.
              </Alert>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowRebalanceDialog(false)}>
              Cancel
            </Button>
            {rebalanceData?.checkRebalanceNeeded?.needed && (
              <Button variant="contained" color="primary">
                Execute Rebalance
              </Button>
            )}
          </DialogActions>
        </Dialog>

        {/* Add Asset Dialog */}
        <Dialog
          open={showAddAssetDialog}
          onClose={() => setShowAddAssetDialog(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>Add Asset to Portfolio</DialogTitle>
          <DialogContent>
            <TextField
              fullWidth
              label="Asset Symbol"
              value={newAsset.symbol}
              onChange={(e) => setNewAsset({ ...newAsset, symbol: e.target.value })}
              sx={{ mb: 2, mt: 1 }}
            />
            <TextField
              fullWidth
              type="number"
              label="Allocation (%)"
              value={newAsset.allocation}
              onChange={(e) => setNewAsset({ ...newAsset, allocation: parseFloat(e.target.value) })}
              inputProps={{ min: 0, max: 100, step: 0.1 }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowAddAssetDialog(false)}>
              Cancel
            </Button>
            <Button variant="contained" color="primary">
              Add Asset
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Container>
  );
};

export default Portfolio;