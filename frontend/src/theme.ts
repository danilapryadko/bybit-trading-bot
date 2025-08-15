import { createTheme } from '@mui/material/styles';

export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#F7A600', // Bybit orange
      light: '#FFB824',
      dark: '#E09600',
    },
    secondary: {
      main: '#00D4E7',
      light: '#33DDEC',
      dark: '#00A8B8',
    },
    success: {
      main: '#00C853',
      light: '#5EFC82',
      dark: '#009624',
    },
    error: {
      main: '#FF3B30',
      light: '#FF6961',
      dark: '#C41E3A',
    },
    warning: {
      main: '#FF9500',
      light: '#FFAB40',
      dark: '#FF6D00',
    },
    background: {
      default: '#0B0E11',
      paper: '#141A1F',
    },
    text: {
      primary: '#E4E4E4',
      secondary: '#A0A0A0',
    },
  },
  typography: {
    fontFamily: '"Inter", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 600,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 600,
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 500,
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 500,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 500,
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: '#141A1F',
          border: '1px solid rgba(255, 255, 255, 0.05)',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
        },
      },
    },
  },
});