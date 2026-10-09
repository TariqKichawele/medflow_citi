import { createTheme, type PaletteMode } from '@mui/material/styles'

/**
 * Page background colours. The blocking script in index.html mirrors these
 * so the first paint matches the theme before React loads.
 */
export const PAGE_BACKGROUND = {
  light: '#f3f6f7',
  dark: '#0e1517',
} as const

export function createAppTheme(mode: PaletteMode) {
  const dark = mode === 'dark'

  return createTheme({
    palette: {
      mode,
      primary: dark
        ? { main: '#5dccc0', contrastText: '#042421' }
        : { main: '#0f4c5c', contrastText: '#ffffff' },
      secondary: dark
        ? { main: '#8fd9a8', contrastText: '#042421' }
        : { main: '#14695f', contrastText: '#ffffff' },
      background: dark
        ? { default: PAGE_BACKGROUND.dark, paper: '#172226' }
        : { default: PAGE_BACKGROUND.light, paper: '#ffffff' },
      text: dark
        ? { primary: '#e8f2f2', secondary: '#a9c4c6' }
        : { primary: '#1a2b30', secondary: '#4a6568' },
      error: { main: '#c62828', contrastText: '#ffffff' },
      warning: { main: '#e9c46a', contrastText: '#1a1400' },
      success: dark
        ? { main: '#81c784', contrastText: '#042421' }
        : { main: '#2e7d32', contrastText: '#ffffff' },
      info: dark
        ? { main: '#4fc3f7', contrastText: '#042421' }
        : { main: '#01579b', contrastText: '#ffffff' },
      divider: dark ? 'rgba(232, 242, 242, 0.16)' : 'rgba(15, 76, 92, 0.12)',
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
      MuiAppBar: {
        styleOverrides: {
          root: { boxShadow: 'none' },
          colorPrimary: {
            backgroundColor: '#0f4c5c',
            color: '#ffffff',
          },
        },
      },
    },
  })
}
