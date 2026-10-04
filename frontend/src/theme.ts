import { createTheme } from '@mui/material/styles'

export const theme = createTheme({
  palette: {
    primary: { main: '#0f4c5c', contrastText: '#ffffff' },
    secondary: { main: '#2a9d8f' },
    background: { default: '#f3f6f7', paper: '#ffffff' },
    error: { main: '#c62828' },
    warning: { main: '#e9c46a' },
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: '"IBM Plex Sans", "Segoe UI", Helvetica, Arial, sans-serif',
    h4: { fontWeight: 700 },
    h5: { fontWeight: 700 },
    h6: { fontWeight: 600 },
  },
  components: {
    MuiButton: { styleOverrides: { root: { textTransform: 'none', fontWeight: 600 } } },
    MuiAppBar: { styleOverrides: { root: { boxShadow: 'none' } } },
  },
})
