import React, { useEffect, useRef, useState } from 'react';
import {
  createChart,
  IChartApi,
  ISeriesApi,
  ColorType,
  CrosshairMode,
  UTCTimestamp,
} from 'lightweight-charts';
import { Box, Card, CardContent, Typography, ToggleButton, ToggleButtonGroup } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import useWebSocket from 'react-use-websocket';
import { useRealKlines } from '../hooks/useRealKlines';

interface TradingChartProps {
  symbol: string;
  height?: number;
}

interface KlineData {
  time: UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

const TradingChart: React.FC<TradingChartProps> = ({ symbol, height = 500 }) => {
  const theme = useTheme();
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  
  const [timeframe, setTimeframe] = useState('15');
  const [chartType, setChartType] = useState<'candles' | 'line'>('candles');
  
  // Fetch real klines data
  const { klines, loading } = useRealKlines(symbol, timeframe);
  
  // WebSocket connection for real-time data
  const { lastMessage } = useWebSocket(
    `wss://stream.bybit.com/v5/public/linear`,
    {
      onOpen: () => {
        console.log('WebSocket connected for chart');
        // Subscribe to kline stream
        // const subscribeMsg = {
        //   op: 'subscribe',
        //   args: [`kline.${timeframe}.${symbol}`],
        // };
        // Note: In production, send subscription message
      },
      shouldReconnect: () => true,
      reconnectInterval: 3000,
    }
  );

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: {
          type: ColorType.Solid,
          color: theme.palette.mode === 'dark' ? '#1e1e1e' : '#ffffff',
        },
        textColor: theme.palette.text.primary,
      },
      grid: {
        vertLines: {
          color: theme.palette.divider,
          style: 1,
        },
        horzLines: {
          color: theme.palette.divider,
          style: 1,
        },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: theme.palette.divider,
        scaleMargins: {
          top: 0.1,
          bottom: 0.2,
        },
      },
      timeScale: {
        borderColor: theme.palette.divider,
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: theme.palette.success.main,
      downColor: theme.palette.error.main,
      borderUpColor: theme.palette.success.dark,
      borderDownColor: theme.palette.error.dark,
      wickUpColor: theme.palette.success.light,
      wickDownColor: theme.palette.error.light,
    });
    candlestickSeriesRef.current = candlestickSeries;

    // Add volume series
    const volumeSeries = chart.addHistogramSeries({
      color: theme.palette.primary.main,
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: 'volume',
    });
    volumeSeriesRef.current = volumeSeries;

    // Set volume price scale
    chart.priceScale('volume').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    // Initial data will be loaded via useRealKlines hook

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [theme, height]);

  // Update chart with real klines data
  useEffect(() => {
    if (!klines || klines.length === 0 || !candlestickSeriesRef.current || !volumeSeriesRef.current) return;
    
    // Convert klines to chart format
    const chartData: KlineData[] = [];
    const volumeData: { time: UTCTimestamp; value: number; color?: string }[] = [];
    
    // Sort klines by timestamp
    const sortedKlines = [...klines].sort((a, b) => a.timestamp - b.timestamp);
    
    sortedKlines.forEach(kline => {
      const time = (kline.timestamp / 1000) as UTCTimestamp; // Convert to seconds
      
      chartData.push({
        time,
        open: kline.open,
        high: kline.high,
        low: kline.low,
        close: kline.close,
        volume: kline.volume,
      });
      
      volumeData.push({
        time,
        value: kline.volume,
        color: kline.close >= kline.open 
          ? theme.palette.success.main + '80'
          : theme.palette.error.main + '80',
      });
    });
    
    // Update chart series
    if (chartData.length > 0) {
      candlestickSeriesRef.current.setData(chartData);
      volumeSeriesRef.current.setData(volumeData);
      
      // Fit content
      if (chartRef.current) {
        chartRef.current.timeScale().fitContent();
      }
    }
  }, [klines, theme]);

  // Handle real-time updates
  useEffect(() => {
    if (!lastMessage) return;
    
    try {
      const message = JSON.parse(lastMessage.data);
      if (message.topic && message.topic.startsWith('kline')) {
        const kline = message.data[0];
        if (candlestickSeriesRef.current) {
          candlestickSeriesRef.current.update({
            time: (kline.timestamp / 1000) as UTCTimestamp,
            open: parseFloat(kline.open),
            high: parseFloat(kline.high),
            low: parseFloat(kline.low),
            close: parseFloat(kline.close),
          });
        }
        
        if (volumeSeriesRef.current) {
          volumeSeriesRef.current.update({
            time: (kline.timestamp / 1000) as UTCTimestamp,
            value: parseFloat(kline.volume),
            color: parseFloat(kline.close) >= parseFloat(kline.open)
              ? theme.palette.success.main + '80'
              : theme.palette.error.main + '80',
          });
        }
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }, [lastMessage, theme]);

  // Handle timeframe change
  const handleTimeframeChange = (_event: React.MouseEvent<HTMLElement>, newTimeframe: string) => {
    if (newTimeframe) {
      setTimeframe(newTimeframe);
      // Data will be reloaded automatically by useRealKlines hook
    }
  };

  // Handle chart type change
  const handleChartTypeChange = (_event: React.MouseEvent<HTMLElement>, newType: 'candles' | 'line') => {
    if (newType) {
      setChartType(newType);
      // TODO: Switch between candlestick and line series
    }
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            {symbol} Chart
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2 }}>
            <ToggleButtonGroup
              value={chartType}
              exclusive
              onChange={handleChartTypeChange}
              size="small"
            >
              <ToggleButton value="candles">Candles</ToggleButton>
              <ToggleButton value="line">Line</ToggleButton>
            </ToggleButtonGroup>
            
            <ToggleButtonGroup
              value={timeframe}
              exclusive
              onChange={handleTimeframeChange}
              size="small"
            >
              <ToggleButton value="1">1M</ToggleButton>
              <ToggleButton value="5">5M</ToggleButton>
              <ToggleButton value="15">15M</ToggleButton>
              <ToggleButton value="60">1H</ToggleButton>
              <ToggleButton value="240">4H</ToggleButton>
              <ToggleButton value="D">1D</ToggleButton>
            </ToggleButtonGroup>
          </Box>
        </Box>
        
        <Box ref={chartContainerRef} sx={{ position: 'relative' }} />
      </CardContent>
    </Card>
  );
};

export default TradingChart;