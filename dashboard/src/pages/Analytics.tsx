import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  ToggleButton,
  ToggleButtonGroup,
  Button,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Line,
  Bar,
  Pie,
  Doughnut,
  Radar,
  Scatter
} from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  RadialLinearScale,
  Title,
  Tooltip as ChartTooltip,
  Legend,
  Filler
} from 'chart.js';
import {
  Download,
  Print,
  Share,
  CalendarMonth,
  TrendingUp,
  TrendingDown,
  Assessment,
  PieChart,
  BarChart,
  ShowChart
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  RadialLinearScale,
  Title,
  ChartTooltip,
  Legend,
  Filler
);

const Analytics: React.FC = () => {
  const [timeframe, setTimeframe] = useState('7d');
  const [selectedPair, setSelectedPair] = useState('all');
  const [chartType, setChartType] = useState<'line' | 'bar' | 'mixed'>('line');
  const [startDate, setStartDate] = useState<Date | null>(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000));
  const [endDate, setEndDate] = useState<Date | null>(new Date());

  // Sample data - in production, this would come from API
  const equityData = {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    datasets: [
      {
        label: 'Account Balance',
        data: [10000, 10250, 10180, 10420, 10650, 10580, 10743],
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        fill: true,
        tension: 0.4
      },
      {
        label: 'Equity',
        data: [10000, 10280, 10150, 10480, 10620, 10650, 10820],
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        fill: true,
        tension: 0.4
      }
    ]
  };

  const pnlData = {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    datasets: [
      {
        label: 'Daily P&L',
        data: [0, 250, -70, 240, 230, -70, 163],
        backgroundColor: (context: any) => {
          const value = context.parsed.y;
          return value > 0 ? 'rgba(75, 192, 192, 0.8)' : 'rgba(255, 99, 132, 0.8)';
        },
        borderColor: (context: any) => {
          const value = context.parsed.y;
          return value > 0 ? 'rgb(75, 192, 192)' : 'rgb(255, 99, 132)';
        },
        borderWidth: 1
      }
    ]
  };

  const pairPerformance = {
    labels: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'MATICUSDT'],
    datasets: [
      {
        label: 'P&L by Pair',
        data: [450, 320, 180, -50, 120],
        backgroundColor: [
          'rgba(255, 99, 132, 0.8)',
          'rgba(54, 162, 235, 0.8)',
          'rgba(255, 206, 86, 0.8)',
          'rgba(75, 192, 192, 0.8)',
          'rgba(153, 102, 255, 0.8)'
        ]
      }
    ]
  };

  const winRateData = {
    labels: ['Wins', 'Losses'],
    datasets: [
      {
        data: [68, 32],
        backgroundColor: [
          'rgba(75, 192, 192, 0.8)',
          'rgba(255, 99, 132, 0.8)'
        ],
        borderColor: [
          'rgb(75, 192, 192)',
          'rgb(255, 99, 132)'
        ],
        borderWidth: 1
      }
    ]
  };

  const strategyPerformance = {
    labels: ['ML Ensemble', 'Scalping', 'Trend Following', 'Mean Reversion', 'Arbitrage'],
    datasets: [
      {
        label: 'Win Rate %',
        data: [68, 62, 55, 58, 72],
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
        borderColor: 'rgb(75, 192, 192)',
        pointBackgroundColor: 'rgb(75, 192, 192)',
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: 'rgb(75, 192, 192)'
      }
    ]
  };

  const tradeDistribution = {
    labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
    datasets: [
      {
        label: 'Trade Count',
        data: [12, 8, 25, 35, 28, 15],
        backgroundColor: 'rgba(153, 102, 255, 0.5)',
        borderColor: 'rgb(153, 102, 255)',
        borderWidth: 2,
        fill: true,
        tension: 0.4
      }
    ]
  };

  const metrics = [
    { label: 'Total P&L', value: '$1,743.21', change: '+17.4%', positive: true },
    { label: 'Win Rate', value: '68%', change: '+3.2%', positive: true },
    { label: 'Sharpe Ratio', value: '1.85', change: '+0.15', positive: true },
    { label: 'Max Drawdown', value: '-4.8%', change: '-0.3%', positive: false },
    { label: 'Avg Trade', value: '$24.50', change: '+$2.30', positive: true },
    { label: 'Total Trades', value: '523', change: '+45', positive: true }
  ];

  const topTrades = [
    { id: 1, pair: 'BTCUSDT', type: 'LONG', entry: 43250, exit: 43850, pnl: 120.50, date: '2024-01-15' },
    { id: 2, pair: 'ETHUSDT', type: 'SHORT', entry: 2450, exit: 2380, pnl: 85.30, date: '2024-01-15' },
    { id: 3, pair: 'SOLUSDT', type: 'LONG', entry: 95.50, exit: 98.20, pnl: 67.80, date: '2024-01-14' },
    { id: 4, pair: 'DOGEUSDT', type: 'LONG', entry: 0.0850, exit: 0.0872, pnl: 45.20, date: '2024-01-14' },
    { id: 5, pair: 'MATICUSDT', type: 'SHORT', entry: 0.950, exit: 0.985, pnl: -35.50, date: '2024-01-13' }
  ];

  const handleExport = (format: 'pdf' | 'excel' | 'csv') => {
    // Implement export functionality
    console.log(`Exporting as ${format}`);
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
          <Typography variant="h4">Analytics & Reports</Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button startIcon={<Download />} onClick={() => handleExport('pdf')}>
              Export PDF
            </Button>
            <Button startIcon={<Download />} onClick={() => handleExport('excel')}>
              Export Excel
            </Button>
            <IconButton>
              <Print />
            </IconButton>
            <IconButton>
              <Share />
            </IconButton>
          </Box>
        </Box>

        {/* Filters */}
        <Paper sx={{ p: 2, mb: 3 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={3}>
              <ToggleButtonGroup
                value={timeframe}
                exclusive
                onChange={(e, v) => v && setTimeframe(v)}
                size="small"
              >
                <ToggleButton value="24h">24H</ToggleButton>
                <ToggleButton value="7d">7D</ToggleButton>
                <ToggleButton value="30d">30D</ToggleButton>
                <ToggleButton value="90d">90D</ToggleButton>
                <ToggleButton value="1y">1Y</ToggleButton>
              </ToggleButtonGroup>
            </Grid>
            <Grid item xs={12} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Trading Pair</InputLabel>
                <Select
                  value={selectedPair}
                  label="Trading Pair"
                  onChange={(e) => setSelectedPair(e.target.value)}
                >
                  <MenuItem value="all">All Pairs</MenuItem>
                  <MenuItem value="BTCUSDT">BTCUSDT</MenuItem>
                  <MenuItem value="ETHUSDT">ETHUSDT</MenuItem>
                  <MenuItem value="SOLUSDT">SOLUSDT</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={3}>
              <DatePicker
                label="Start Date"
                value={startDate}
                onChange={setStartDate}
                slotProps={{ textField: { size: 'small', fullWidth: true } }}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <DatePicker
                label="End Date"
                value={endDate}
                onChange={setEndDate}
                slotProps={{ textField: { size: 'small', fullWidth: true } }}
              />
            </Grid>
          </Grid>
        </Paper>

        {/* Metrics Cards */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {metrics.map((metric, index) => (
            <Grid item xs={6} sm={4} md={2} key={index}>
              <Card>
                <CardContent sx={{ p: 2 }}>
                  <Typography variant="body2" color="textSecondary" gutterBottom>
                    {metric.label}
                  </Typography>
                  <Typography variant="h6">
                    {metric.value}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    {metric.positive ? (
                      <TrendingUp color="success" fontSize="small" />
                    ) : (
                      <TrendingDown color="error" fontSize="small" />
                    )}
                    <Typography
                      variant="body2"
                      color={metric.positive ? 'success.main' : 'error.main'}
                    >
                      {metric.change}
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        {/* Charts Grid */}
        <Grid container spacing={3}>
          {/* Equity Curve */}
          <Grid item xs={12} lg={8}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Equity Curve
              </Typography>
              <Line
                data={equityData}
                options={{
                  responsive: true,
                  plugins: {
                    legend: {
                      position: 'top' as const,
                    }
                  },
                  scales: {
                    y: {
                      beginAtZero: false
                    }
                  }
                }}
                height={100}
              />
            </Paper>
          </Grid>

          {/* Win Rate */}
          <Grid item xs={12} lg={4}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Win Rate Distribution
              </Typography>
              <Doughnut
                data={winRateData}
                options={{
                  responsive: true,
                  plugins: {
                    legend: {
                      position: 'bottom' as const,
                    }
                  }
                }}
              />
            </Paper>
          </Grid>

          {/* Daily P&L */}
          <Grid item xs={12} lg={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Daily P&L
              </Typography>
              <Bar
                data={pnlData}
                options={{
                  responsive: true,
                  plugins: {
                    legend: {
                      display: false
                    }
                  },
                  scales: {
                    y: {
                      beginAtZero: true
                    }
                  }
                }}
              />
            </Paper>
          </Grid>

          {/* Pair Performance */}
          <Grid item xs={12} lg={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Performance by Pair
              </Typography>
              <Bar
                data={pairPerformance}
                options={{
                  responsive: true,
                  plugins: {
                    legend: {
                      display: false
                    }
                  },
                  scales: {
                    y: {
                      beginAtZero: true
                    }
                  }
                }}
              />
            </Paper>
          </Grid>

          {/* Strategy Performance */}
          <Grid item xs={12} lg={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Strategy Performance
              </Typography>
              <Radar
                data={strategyPerformance}
                options={{
                  responsive: true,
                  plugins: {
                    legend: {
                      display: false
                    }
                  },
                  scales: {
                    r: {
                      beginAtZero: true,
                      max: 100
                    }
                  }
                }}
              />
            </Paper>
          </Grid>

          {/* Trade Distribution */}
          <Grid item xs={12} lg={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Trade Distribution by Hour
              </Typography>
              <Line
                data={tradeDistribution}
                options={{
                  responsive: true,
                  plugins: {
                    legend: {
                      display: false
                    }
                  }
                }}
              />
            </Paper>
          </Grid>

          {/* Top Trades Table */}
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Top Trades
              </Typography>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Date</TableCell>
                      <TableCell>Pair</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell align="right">Entry</TableCell>
                      <TableCell align="right">Exit</TableCell>
                      <TableCell align="right">P&L</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {topTrades.map((trade) => (
                      <TableRow key={trade.id}>
                        <TableCell>{trade.date}</TableCell>
                        <TableCell>
                          <Chip label={trade.pair} size="small" />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={trade.type}
                            size="small"
                            color={trade.type === 'LONG' ? 'success' : 'error'}
                          />
                        </TableCell>
                        <TableCell align="right">${trade.entry.toLocaleString()}</TableCell>
                        <TableCell align="right">${trade.exit.toLocaleString()}</TableCell>
                        <TableCell align="right">
                          <Typography
                            color={trade.pnl > 0 ? 'success.main' : 'error.main'}
                            fontWeight="bold"
                          >
                            ${trade.pnl.toFixed(2)}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </LocalizationProvider>
  );
};

export default Analytics;