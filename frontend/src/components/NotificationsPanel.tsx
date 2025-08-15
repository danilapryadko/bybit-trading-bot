import React from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Button,
  Divider,
  Chip,
} from '@mui/material';
import {
  Close as CloseIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Delete as DeleteIcon,
  DoneAll as DoneAllIcon,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import {
  setNotificationsPanelOpen,
  markAsRead,
  markAllAsRead,
  removeNotification,
  clearNotifications,
  NotificationType,
} from '../store/slices/notificationsSlice';

const NotificationsPanel: React.FC = () => {
  const dispatch = useAppDispatch();
  const { notifications, isOpen } = useAppSelector(state => state.notifications);

  const handleClose = () => {
    dispatch(setNotificationsPanelOpen(false));
  };

  const getNotificationIcon = (type: NotificationType) => {
    switch (type) {
      case 'success':
        return <SuccessIcon sx={{ color: 'success.main' }} />;
      case 'error':
        return <ErrorIcon sx={{ color: 'error.main' }} />;
      case 'warning':
        return <WarningIcon sx={{ color: 'warning.main' }} />;
      case 'info':
      default:
        return <InfoIcon sx={{ color: 'info.main' }} />;
    }
  };

  const getNotificationColor = (type: NotificationType) => {
    switch (type) {
      case 'success':
        return 'success';
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
      default:
        return 'info';
    }
  };

  return (
    <Drawer
      anchor="right"
      open={isOpen}
      onClose={handleClose}
      sx={{
        '& .MuiDrawer-paper': {
          width: 360,
          bgcolor: 'background.paper',
        },
      }}
    >
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6">Notifications</Typography>
          <IconButton onClick={handleClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {notifications.length > 0 && (
          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            <Button
              size="small"
              startIcon={<DoneAllIcon />}
              onClick={() => dispatch(markAllAsRead())}
            >
              Mark all read
            </Button>
            <Button
              size="small"
              color="error"
              startIcon={<DeleteIcon />}
              onClick={() => dispatch(clearNotifications())}
            >
              Clear all
            </Button>
          </Box>
        )}
      </Box>

      <Divider />

      {notifications.length === 0 ? (
        <Box sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            No notifications
          </Typography>
        </Box>
      ) : (
        <List sx={{ p: 0 }}>
          {notifications.map((notification) => (
            <ListItem
              key={notification.id}
              sx={{
                bgcolor: notification.read ? 'transparent' : 'action.hover',
                borderBottom: '1px solid',
                borderColor: 'divider',
                '&:hover': {
                  bgcolor: 'action.hover',
                },
              }}
              secondaryAction={
                <IconButton
                  edge="end"
                  size="small"
                  onClick={() => dispatch(removeNotification(notification.id))}
                >
                  <CloseIcon fontSize="small" />
                </IconButton>
              }
              onClick={() => !notification.read && dispatch(markAsRead(notification.id))}
            >
              <ListItemIcon>{getNotificationIcon(notification.type)}</ListItemIcon>
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="subtitle2">{notification.title}</Typography>
                    {!notification.read && (
                      <Chip
                        label="New"
                        size="small"
                        color={getNotificationColor(notification.type)}
                        sx={{ height: 16 }}
                      />
                    )}
                  </Box>
                }
                secondary={
                  <>
                    <Typography variant="body2" color="text.primary" sx={{ mb: 0.5 }}>
                      {notification.message}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {formatDistanceToNow(notification.timestamp, { addSuffix: true })}
                    </Typography>
                  </>
                }
              />
            </ListItem>
          ))}
        </List>
      )}
    </Drawer>
  );
};

export default NotificationsPanel;