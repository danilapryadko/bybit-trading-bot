import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  LinearProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Alert,
  AlertTitle,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Badge,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
} from '@mui/material';
import {
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Notifications as NotificationIcon,
  Settings as SettingsIcon,
  Assessment as AssessmentIcon,
  Security as SecurityIcon,
  AccountBalance as BalanceIcon,
} from '@mui/icons-material';
import { useQuery, useMutation } from '@apollo/client';
import { gql } from '@apollo/client';
import apolloClient from '../services/apollo';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

// GraphQL Queries
const GET_RISK_METRICS = gql`
  query GetRiskMetrics {
    riskMetrics {
      riskScore
      riskLevel
      riskColor
      totalExposure
      exposurePercent
      dailyPnl
      dailyPnlPercent
      unrealizedPnl
      unrealizedPnlPercent
      consecutiveLosses
      consecutiveWins
      dailyTrades
      positionsCount
      maxPositions
      canTrade
    }
    performanceMetrics(period: 30) {
      totalTrades
      winningTrades
      losingTrades
      winRate
      totalPnl
      avgPnl
      bestTrade
      worstTrade
      sharpeRatio
      maxDrawdown
      profitFactor
      avgWin
      avgLoss
      expectancy
      avgTradesPerDay
    }
    alerts {
      id
      type
      priority
      title
      message
      timestamp
      isRead
      isResolved
    }
  }
`;

const UPDATE_RISK_SETTINGS = gql`
  mutation UpdateRiskSettings($input: RiskSettingsInput!) {
    updateRiskSettings(input: $input) {
      success
      message
    }
  }
`;

const CALCULATE_POSITION_SIZE = gql`
  query CalculatePositionSize($balance: Float!, $entryPrice: Float!, $stopLoss: Float!, $leverage: Int) {
    calculatePositionSize(
      balance: $balance
      entryPrice: $entryPrice
      stopLoss: $stopLoss
      leverage: $leverage
    ) {
      positionSize
      positionValue
      riskAmount
      potentialLoss
      riskPercentage
      marginRequired
    }
  }
`;

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div hidden={value !== index} {...other}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const RiskManagement: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [settingsDialog, setSettingsDialog] = useState(false);
  const [calculatorDialog, setCalculatorDialog] = useState(false);
  const [riskSettings, setRiskSettings] = useState({
    maxRiskPerTrade: 2,
    maxRiskTotal: 6,
    maxLeverage: 10,
    minRiskRewardRatio: 1.5,
    maxDailyLoss: 5,
    maxPositions: 3,
  });
  const [positionCalc, setPositionCalc] = useState({
    balance: 1000,
    entryPrice: 50000,
    stopLoss: 49000,
    leverage: 1,
  });

  // Queries
  const { data, loading, refetch } = useQuery(GET_RISK_METRICS, {
    client: apolloClient,
    pollInterval: 10000,
  });

  const [updateSettings] = useMutation(UPDATE_RISK_SETTINGS, {
    client: apolloClient,
    onCompleted: () => {
      setSettingsDialog(false);
      refetch();
    },
  });

  const riskMetrics = data?.riskMetrics || {};
  const performanceMetrics = data?.performanceMetrics || {};
  const alerts = data?.alerts || [];

  const getRiskColor = (level: string): "success" | "warning" | "error" | "info" => {
    switch (level) {
      case 'LOW':
        return 'success';
      case 'MEDIUM':
        return 'warning';
      case 'HIGH':
        return 'error';
      case 'CRITICAL':
        return 'error';
      default:
        return 'info';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'low':
        return 'default';
      case 'medium':
        return 'info';
      case 'high':
        return 'warning';
      case 'critical':
        return 'error';
      default:
        return 'default';
    }
  };

  const unreadAlerts = alerts.filter((a: any) => !a.isRead).length;

  // Sample chart data (would come from API)
  const pnlChartData = [
    { date: '2024-01-01', pnl: 100, cumulative: 100 },
    { date: '2024-01-02', pnl: -50, cumulative: 50 },
    { date: '2024-01-03', pnl: 200, cumulative: 250 },
    { date: '2024-01-04', pnl: -30, cumulative: 220 },
    { date: '2024-01-05', pnl: 150, cumulative: 370 },
  ];

  const riskDistribution = [
    { name: 'Available', value: 100 - riskMetrics.exposurePercent },
    { name: 'Exposed', value: riskMetrics.exposurePercent },
  ];

  const COLORS = ['#4caf50', '#ff9800'];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Risk Management</Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<AssessmentIcon />}
            onClick={() => setCalculatorDialog(true)}
          >
            Position Calculator
          </Button>
          <Button
            variant="outlined"
            startIcon={<SettingsIcon />}
            onClick={() => setSettingsDialog(true)}
          >
            Risk Settings
          </Button>
          <IconButton>
            <Badge badgeContent={unreadAlerts} color="error">
              <NotificationIcon />
            </Badge>
          </IconButton>
        </Box>
      </Box>

      {/* Risk Overview Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" variant="subtitle2">
                    Risk Score
                  </Typography>
                  <Typography variant="h4">
                    {riskMetrics.riskScore || 0}
                  </Typography>
                  <Chip
                    label={riskMetrics.riskLevel || 'LOW'}
                    color={getRiskColor(riskMetrics.riskLevel)}
                    size="small"
                    sx={{ mt: 1 }}
                  />
                </Box>
                <SecurityIcon sx={{ fontSize: 40, color: 'text.secondary' }} />
              </Box>
              <LinearProgress
                variant="determinate"
                value={riskMetrics.riskScore || 0}
                sx={{ mt: 2 }}
                color={getRiskColor(riskMetrics.riskLevel)}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" variant="subtitle2">
                    Daily P&L
                  </Typography>
                  <Typography variant="h4">
                    ${riskMetrics.dailyPnl || 0}
                  </Typography>
                  <Typography
                    variant="body2"
                    color={riskMetrics.dailyPnl >= 0 ? 'success.main' : 'error.main'}
                  >
                    {riskMetrics.dailyPnlPercent || 0}%
                  </Typography>
                </Box>
                {riskMetrics.dailyPnl >= 0 ? (
                  <TrendingUpIcon sx={{ fontSize: 40, color: 'success.main' }} />
                ) : (
                  <TrendingDownIcon sx={{ fontSize: 40, color: 'error.main' }} />
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" variant="subtitle2">
                    Exposure
                  </Typography>
                  <Typography variant="h4">
                    {riskMetrics.exposurePercent || 0}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    ${riskMetrics.totalExposure || 0}
                  </Typography>
                </Box>
                <BalanceIcon sx={{ fontSize: 40, color: 'text.secondary' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" variant="subtitle2">
                    Win Rate
                  </Typography>
                  <Typography variant="h4">
                    {performanceMetrics.winRate || 0}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {performanceMetrics.winningTrades || 0}W / {performanceMetrics.losingTrades || 0}L
                  </Typography>
                </Box>
                <AssessmentIcon sx={{ fontSize: 40, color: 'text.secondary' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Card>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab label="Overview" />
          <Tab label="Performance" />
          <Tab label="Alerts" />
          <Tab label="Analysis" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={3}>
            {/* Risk Gauge */}
            <Grid item xs={12} md={6}>
              <Card sx={{ bgcolor: 'background.default' }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Risk Assessment
                  </Typography>
                  <Box sx={{ mt: 2 }}>
                    <ResponsiveContainer width="100%" height={200}>
                      <PieChart>
                        <Pie
                          data={riskDistribution}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={80}
                          paddingAngle={5}
                          dataKey="value"
                        >
                          {riskDistribution.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </Box>
                  <List dense>
                    <ListItem>
                      <ListItemText 
                        primary="Positions" 
                        secondary={`${riskMetrics.positionsCount || 0} / ${riskMetrics.maxPositions || 3}`}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText 
                        primary="Consecutive Losses" 
                        secondary={riskMetrics.consecutiveLosses || 0}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText 
                        primary="Daily Trades" 
                        secondary={riskMetrics.dailyTrades || 0}
                      />
                    </ListItem>
                  </List>
                </CardContent>
              </Card>
            </Grid>

            {/* Key Metrics */}
            <Grid item xs={12} md={6}>
              <Card sx={{ bgcolor: 'background.default' }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Key Metrics
                  </Typography>
                  <List>
                    <ListItem>
                      <ListItemText 
                        primary="Sharpe Ratio" 
                        secondary={performanceMetrics.sharpeRatio || 0}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText 
                        primary="Max Drawdown" 
                        secondary={`$${performanceMetrics.maxDrawdown || 0}`}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText 
                        primary="Profit Factor" 
                        secondary={performanceMetrics.profitFactor || 0}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText 
                        primary="Expectancy" 
                        secondary={`$${performanceMetrics.expectancy || 0}`}
                      />
                    </ListItem>
                  </List>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          {/* Performance Charts */}
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                P&L Performance
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={pnlChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Area type="monotone" dataKey="pnl" stroke="#8884d8" fill="#8884d8" name="Daily P&L" />
                  <Area type="monotone" dataKey="cumulative" stroke="#82ca9d" fill="#82ca9d" name="Cumulative" />
                </AreaChart>
              </ResponsiveContainer>
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          {/* Alerts List */}
          <List>
            {alerts.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
                No active alerts
              </Typography>
            ) : (
              alerts.map((alert: any) => (
                <React.Fragment key={alert.id}>
                  <ListItem>
                    <ListItemIcon>
                      {alert.priority === 'critical' ? (
                        <ErrorIcon color="error" />
                      ) : alert.priority === 'high' ? (
                        <WarningIcon color="warning" />
                      ) : (
                        <CheckIcon color="success" />
                      )}
                    </ListItemIcon>
                    <ListItemText
                      primary={alert.title}
                      secondary={
                        <>
                          {alert.message}
                          <br />
                          <Typography variant="caption" color="text.secondary">
                            {new Date(alert.timestamp).toLocaleString()}
                          </Typography>
                        </>
                      }
                    />
                    <Chip
                      label={alert.priority}
                      size="small"
                      color={getPriorityColor(alert.priority)}
                    />
                  </ListItem>
                  <Divider />
                </React.Fragment>
              ))
            )}
          </List>
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          {/* Trading Analysis */}
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card sx={{ bgcolor: 'background.default' }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Trade Statistics
                  </Typography>
                  <TableContainer>
                    <Table size="small">
                      <TableBody>
                        <TableRow>
                          <TableCell>Total Trades</TableCell>
                          <TableCell align="right">{performanceMetrics.totalTrades || 0}</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>Average Win</TableCell>
                          <TableCell align="right">${performanceMetrics.avgWin || 0}</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>Average Loss</TableCell>
                          <TableCell align="right">${performanceMetrics.avgLoss || 0}</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>Best Trade</TableCell>
                          <TableCell align="right">${performanceMetrics.bestTrade || 0}</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>Worst Trade</TableCell>
                          <TableCell align="right">${performanceMetrics.worstTrade || 0}</TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>
      </Card>

      {/* Position Size Calculator Dialog */}
      <Dialog open={calculatorDialog} onClose={() => setCalculatorDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Position Size Calculator</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Account Balance"
              type="number"
              value={positionCalc.balance}
              onChange={(e) => setPositionCalc({ ...positionCalc, balance: parseFloat(e.target.value) })}
              fullWidth
            />
            <TextField
              label="Entry Price"
              type="number"
              value={positionCalc.entryPrice}
              onChange={(e) => setPositionCalc({ ...positionCalc, entryPrice: parseFloat(e.target.value) })}
              fullWidth
            />
            <TextField
              label="Stop Loss Price"
              type="number"
              value={positionCalc.stopLoss}
              onChange={(e) => setPositionCalc({ ...positionCalc, stopLoss: parseFloat(e.target.value) })}
              fullWidth
            />
            <TextField
              label="Leverage"
              type="number"
              value={positionCalc.leverage}
              onChange={(e) => setPositionCalc({ ...positionCalc, leverage: parseInt(e.target.value) })}
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCalculatorDialog(false)}>Cancel</Button>
          <Button variant="contained">Calculate</Button>
        </DialogActions>
      </Dialog>

      {/* Risk Settings Dialog */}
      <Dialog open={settingsDialog} onClose={() => setSettingsDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Risk Management Settings</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Max Risk Per Trade (%)"
              type="number"
              value={riskSettings.maxRiskPerTrade}
              onChange={(e) => setRiskSettings({ ...riskSettings, maxRiskPerTrade: parseFloat(e.target.value) })}
              fullWidth
            />
            <TextField
              label="Max Total Risk (%)"
              type="number"
              value={riskSettings.maxRiskTotal}
              onChange={(e) => setRiskSettings({ ...riskSettings, maxRiskTotal: parseFloat(e.target.value) })}
              fullWidth
            />
            <TextField
              label="Max Leverage"
              type="number"
              value={riskSettings.maxLeverage}
              onChange={(e) => setRiskSettings({ ...riskSettings, maxLeverage: parseInt(e.target.value) })}
              fullWidth
            />
            <TextField
              label="Min Risk/Reward Ratio"
              type="number"
              value={riskSettings.minRiskRewardRatio}
              onChange={(e) => setRiskSettings({ ...riskSettings, minRiskRewardRatio: parseFloat(e.target.value) })}
              fullWidth
            />
            <TextField
              label="Max Daily Loss (%)"
              type="number"
              value={riskSettings.maxDailyLoss}
              onChange={(e) => setRiskSettings({ ...riskSettings, maxDailyLoss: parseFloat(e.target.value) })}
              fullWidth
            />
            <TextField
              label="Max Positions"
              type="number"
              value={riskSettings.maxPositions}
              onChange={(e) => setRiskSettings({ ...riskSettings, maxPositions: parseInt(e.target.value) })}
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSettingsDialog(false)}>Cancel</Button>
          <Button 
            variant="contained"
            onClick={() => updateSettings({ variables: { input: riskSettings } })}
          >
            Save Settings
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default RiskManagement;