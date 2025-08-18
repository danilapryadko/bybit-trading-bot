import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';
import { useAppDispatch } from './store/hooks';
import { connectWebSocket } from './services/websocket';

// Layout
import Layout from './components/Layout';

// Pages
import Dashboard from './pages/Dashboard';
import Trading from './pages/Trading';
import Positions from './pages/Positions';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';
import Backtest from './pages/Backtest';
import Strategies from './pages/Strategies';
import RiskManagement from './pages/RiskManagement';
import Portfolio from './pages/Portfolio';

const App: React.FC = () => {
  const dispatch = useAppDispatch();

  useEffect(() => {
    // Connect to WebSocket on app start
    connectWebSocket(dispatch);

    return () => {
      // Cleanup WebSocket connection
      // WebSocket disconnect handled in service
    };
  }, [dispatch]);

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/trading" element={<Trading />} />
          <Route path="/positions" element={<Positions />} />
          <Route path="/strategies" element={<Strategies />} />
          <Route path="/risk" element={<RiskManagement />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </Box>
  );
};

export default App;