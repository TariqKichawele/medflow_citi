import Chip from '@mui/material/Chip'
import type { ChipProps } from '@mui/material/Chip'

const COLORS: Record<string, ChipProps['color']> = {
  available: 'success',
  in_use: 'info',
  maintenance: 'warning',
  offline: 'default',
  pending: 'warning',
  in_progress: 'info',
  completed: 'success',
  failed: 'error',
  low: 'default',
  medium: 'warning',
  critical: 'error',
}

export function StatusChip({ value }: { value: string }) {
  return <Chip size="small" label={value.replaceAll('_', ' ')} color={COLORS[value] ?? 'default'} />
}
