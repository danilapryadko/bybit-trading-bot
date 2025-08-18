import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Badge,
  Avatar,
  Chip,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  TrendingUp as TradingIcon,
  AccountBalance as PositionsIcon,
  Analytics as AnalyticsIcon,
  Science as BacktestIcon,
  Settings as SettingsIcon,
  Notifications as NotificationsIcon,
  Circle as CircleIcon,
  Security as RiskIcon,
  Psychology as StrategyIcon,
  PieChart as PortfolioIcon,
} from '@mui/icons-material';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { toggleNotificationsPanel } from '../store/slices/notificationsSlice';
import NotificationsPanel from './NotificationsPanel';
import { useRealBalance } from '../hooks/useRealBalance';

const drawerWidth = 240;

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  
  // Поддерживаем соединение с API на всех страницах
  const { isConnected: apiConnected } = useRealBalance();
  
  const isConnected = useAppSelector(state => state.market.isConnected);
  const unreadCount = useAppSelector(state => state.notifications.unreadCount);
  const isTradingEnabled = useAppSelector(state => state.trading.isTradingEnabled);
  const isPaperTrading = useAppSelector(state => state.trading.isPaperTrading);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
    { text: 'Trading', icon: <TradingIcon />, path: '/trading' },
    { text: 'Positions', icon: <PositionsIcon />, path: '/positions' },
    { text: 'Portfolio', icon: <PortfolioIcon />, path: '/portfolio' },
    { text: 'Strategies', icon: <StrategyIcon />, path: '/strategies' },
    { text: 'Risk Management', icon: <RiskIcon />, path: '/risk' },
    { text: 'Analytics', icon: <AnalyticsIcon />, path: '/analytics' },
    { text: 'Backtest', icon: <BacktestIcon />, path: '/backtest' },
    { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
  ];

  const drawer = (
    <div>
      <Toolbar>
        <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
          <Avatar sx={{ bgcolor: 'primary.main', mr: 2 }}>B</Avatar>
          <Typography variant="h6" noWrap>
            Bybit Bot
          </Typography>
        </Box>
      </Toolbar>
      <Divider />
      <List>
        {menuItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => navigate(item.path)}
              sx={{
                '&.Mui-selected': {
                  backgroundColor: 'rgba(247, 166, 0, 0.08)',
                  '&:hover': {
                    backgroundColor: 'rgba(247, 166, 0, 0.12)',
                  },
                },
              }}
            >
              <ListItemIcon
                sx={{
                  color: location.pathname === item.path ? 'primary.main' : 'inherit',
                }}
              >
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      <Divider />
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <CircleIcon
            sx={{
              fontSize: 12,
              color: isConnected ? 'success.main' : 'error.main',
              mr: 1,
            }}
          />
          <Typography variant="body2" color="text.secondary">
            {isConnected ? 'Connected' : 'Disconnected'}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {isTradingEnabled && (
            <Chip
              label={isPaperTrading ? 'Paper' : 'Live'}
              size="small"
              color={isPaperTrading ? 'warning' : 'success'}
              variant="outlined"
            />
          )}
        </Box>
      </Box>
    </div>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
          bgcolor: 'background.paper',
          borderBottom: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {menuItems.find(item => item.path === location.pathname)?.text || 'Bybit Trading Bot'}
          </Typography>
          <IconButton
            color="inherit"
            onClick={() => dispatch(toggleNotificationsPanel())}
          >
            <Badge badgeContent={unreadCount} color="error">
              <NotificationsIcon />
            </Badge>
          </IconButton>
        </Toolbar>
      </AppBar>
      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true,
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
              bgcolor: 'background.paper',
            },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
              bgcolor: 'background.paper',
              borderRight: '1px solid',
              borderColor: 'divider',
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          mt: 8,
        }}
      >
        {children}
      </Box>
      <NotificationsPanel />
    </Box>
  );
};

export default Layout;