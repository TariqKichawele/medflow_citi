import DarkModeOutlinedIcon from '@mui/icons-material/DarkModeOutlined'
import LightModeOutlinedIcon from '@mui/icons-material/LightModeOutlined'
import IconButton from '@mui/material/IconButton'
import Tooltip from '@mui/material/Tooltip'

import { useColorMode } from '../colorMode'

export function ThemeToggle({ color = 'inherit' }: { color?: 'inherit' | 'primary' }) {
  const { mode, toggleColorMode } = useColorMode()
  const label = mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'

  return (
    <Tooltip title={label}>
      <IconButton color={color} aria-label={label} aria-pressed={mode === 'dark'} onClick={toggleColorMode}>
        {mode === 'dark' ? <LightModeOutlinedIcon /> : <DarkModeOutlinedIcon />}
      </IconButton>
    </Tooltip>
  )
}
