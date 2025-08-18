import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Fab,
  Chip,
  Box,
  Typography,
  Autocomplete,
  Alert,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { addToWatchlist, removeFromWatchlist } from '../store/slices/marketSlice';

// Popular trading pairs on Bybit
const POPULAR_PAIRS = [
  'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
  'ADAUSDT', 'AVAXUSDT', 'DOGEUSDT', 'DOTUSDT', 'MATICUSDT',
  'LINKUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT', 'ETCUSDT',
  'NEARUSDT', 'ICPUSDT', 'FILUSDT', 'APTUSDT', 'ARBUSDT',
  'OPUSDT', 'INJUSDT', 'SUIUSDT', 'SEIUSDT', 'TIAUSDT',
];

interface WatchlistManagerProps {
  onClose?: () => void;
}

const WatchlistManager: React.FC<WatchlistManagerProps> = ({ onClose }) => {
  const dispatch = useAppDispatch();
  const watchlist = useAppSelector((state) => state.market.watchlist);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedPair, setSelectedPair] = useState<string | null>(null);
  const [customPair, setCustomPair] = useState('');
  const [error, setError] = useState('');

  const handleOpen = () => {
    setIsOpen(true);
    setError('');
  };

  const handleClose = () => {
    setIsOpen(false);
    setSelectedPair(null);
    setCustomPair('');
    setError('');
    if (onClose) onClose();
  };

  const handleAddPair = () => {
    const pairToAdd = selectedPair || customPair.toUpperCase();
    
    if (!pairToAdd) {
      setError('Please select or enter a trading pair');
      return;
    }

    // Validate pair format (should end with USDT for Bybit perpetuals)
    if (!pairToAdd.endsWith('USDT')) {
      setError('Pair must end with USDT (e.g., BTCUSDT)');
      return;
    }

    if (watchlist.includes(pairToAdd)) {
      setError('This pair is already in your watchlist');
      return;
    }

    if (watchlist.length >= 20) {
      setError('Maximum 20 pairs allowed in watchlist');
      return;
    }

    dispatch(addToWatchlist(pairToAdd));
    
    // Save to localStorage
    const updatedWatchlist = [...watchlist, pairToAdd];
    localStorage.setItem('tradingWatchlist', JSON.stringify(updatedWatchlist));
    
    setSelectedPair(null);
    setCustomPair('');
    setError('');
  };

  const handleRemovePair = (pair: string) => {
    dispatch(removeFromWatchlist(pair));
    
    // Update localStorage
    const updatedWatchlist = watchlist.filter(p => p !== pair);
    localStorage.setItem('tradingWatchlist', JSON.stringify(updatedWatchlist));
  };

  // Get available pairs (not in watchlist)
  const availablePairs = POPULAR_PAIRS.filter(pair => !watchlist.includes(pair));

  return (
    <>
      {/* Floating Action Button */}
      <Fab
        color="primary"
        aria-label="edit watchlist"
        onClick={handleOpen}
        sx={{
          position: 'fixed',
          bottom: 16,
          right: 16,
          zIndex: 1000,
        }}
      >
        <EditIcon />
      </Fab>

      {/* Watchlist Manager Dialog */}
      <Dialog
        open={isOpen}
        onClose={handleClose}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">Manage Watchlist</Typography>
            <IconButton
              edge="end"
              color="inherit"
              onClick={handleClose}
              aria-label="close"
            >
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>

        <DialogContent>
          {/* Add New Pair Section */}
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>
              Add Trading Pair
            </Typography>
            
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <Autocomplete
                value={selectedPair}
                onChange={(event, newValue) => {
                  setSelectedPair(newValue);
                  setCustomPair('');
                  setError('');
                }}
                options={availablePairs}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Select popular pair"
                    variant="outlined"
                    size="small"
                  />
                )}
                sx={{ flex: 1 }}
              />
              
              <Typography variant="body2" sx={{ alignSelf: 'center' }}>
                OR
              </Typography>
              
              <TextField
                label="Enter custom pair"
                variant="outlined"
                size="small"
                value={customPair}
                onChange={(e) => {
                  setCustomPair(e.target.value.toUpperCase());
                  setSelectedPair(null);
                  setError('');
                }}
                placeholder="e.g., PEPEUSDT"
                sx={{ flex: 1 }}
              />
            </Box>

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleAddPair}
              fullWidth
            >
              Add to Watchlist
            </Button>
          </Box>

          {/* Current Watchlist */}
          <Box>
            <Typography variant="subtitle1" gutterBottom>
              Current Watchlist ({watchlist.length}/20)
            </Typography>
            
            <List>
              {watchlist.map((pair) => (
                <ListItem
                  key={pair}
                  sx={{
                    bgcolor: 'background.paper',
                    mb: 1,
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: 'divider',
                  }}
                >
                  <ListItemText
                    primary={pair}
                    secondary={
                      <Chip
                        label={pair === 'BTCUSDT' ? 'Bitcoin' : 
                               pair === 'ETHUSDT' ? 'Ethereum' :
                               pair === 'SOLUSDT' ? 'Solana' :
                               'Cryptocurrency'}
                        size="small"
                        variant="outlined"
                      />
                    }
                  />
                  <ListItemSecondaryAction>
                    <IconButton
                      edge="end"
                      aria-label="delete"
                      onClick={() => handleRemovePair(pair)}
                      color="error"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>

            {watchlist.length === 0 && (
              <Alert severity="info">
                Your watchlist is empty. Add some trading pairs to get started!
              </Alert>
            )}
          </Box>
        </DialogContent>

        <DialogActions>
          <Button onClick={handleClose}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default WatchlistManager;