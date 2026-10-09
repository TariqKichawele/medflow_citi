import { Navigate, Outlet, useLocation } from 'react-router-dom'
import Box from '@mui/material/Box'
import CircularProgress from '@mui/material/CircularProgress'

import { useAuth } from './AuthContext'

export function ProtectedRoute({ permission, anyOf }: { permission?: string; anyOf?: string[] }) {
  const { user, loading, can } = useAuth()
  const location = useLocation()
  const required = anyOf ?? (permission ? [permission] : [])

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 12 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (required.length > 0 && !required.some((item) => can(item))) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
