import useMediaQuery from '@mui/material/useMediaQuery'
import CssBaseline from '@mui/material/CssBaseline'
import { ThemeProvider, type PaletteMode } from '@mui/material/styles'
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

import { COLOR_MODE_KEY } from './constants'
import { createAppTheme } from './theme'

type ColorModeContextValue = {
  mode: PaletteMode
  toggleColorMode: () => void
}

const ColorModeContext = createContext<ColorModeContextValue | undefined>(undefined)

export function readStoredColorMode(): PaletteMode | null {
  try {
    const value = localStorage.getItem(COLOR_MODE_KEY)
    if (value === 'light' || value === 'dark') return value
    return null
  } catch {
    return null
  }
}

export function writeStoredColorMode(mode: PaletteMode): void {
  try {
    localStorage.setItem(COLOR_MODE_KEY, mode)
  } catch {
    // Storage can throw when it is blocked. The in-memory choice still applies.
  }
}

export function ColorModeProvider({ children }: { children: ReactNode }) {
  const [storedMode, setStoredMode] = useState<PaletteMode | null>(() => readStoredColorMode())
  const prefersDark = useMediaQuery('(prefers-color-scheme: dark)', { noSsr: true })
  const mode: PaletteMode = storedMode ?? (prefersDark ? 'dark' : 'light')
  const theme = useMemo(() => createAppTheme(mode), [mode])

  const toggleColorMode = useCallback(() => {
    const next: PaletteMode = mode === 'dark' ? 'light' : 'dark'
    setStoredMode(next)
    writeStoredColorMode(next)
  }, [mode])

  const value = useMemo(() => ({ mode, toggleColorMode }), [mode, toggleColorMode])

  return (
    <ColorModeContext.Provider value={value}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ColorModeContext.Provider>
  )
}

export function useColorMode() {
  const ctx = useContext(ColorModeContext)
  if (!ctx) throw new Error('useColorMode must be used inside ColorModeProvider')
  return ctx
}
