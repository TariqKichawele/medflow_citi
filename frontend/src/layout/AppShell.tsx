import DashboardIcon from '@mui/icons-material/SpaceDashboard'
import DevicesIcon from '@mui/icons-material/MedicalServices'
import AssignmentIcon from '@mui/icons-material/Assignment'
import DomainIcon from '@mui/icons-material/Domain'
import PeopleIcon from '@mui/icons-material/People'
import LogoutIcon from '@mui/icons-material/Logout'
import AppBar from '@mui/material/AppBar'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Chip from '@mui/material/Chip'
import Container from '@mui/material/Container'
import Drawer from '@mui/material/Drawer'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemIcon from '@mui/material/ListItemIcon'
import ListItemText from '@mui/material/ListItemText'
import Toolbar from '@mui/material/Toolbar'
import Typography from '@mui/material/Typography'
import { NavLink, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'
import { ROLE_AUDITOR, ROLE_CLINICAL_ADMIN } from '../constants'

const DRAWER_WIDTH = 240

const NAV = [
  { to: '/', label: 'Dashboard', icon: <DashboardIcon />, end: true },
  { to: '/equipment', label: 'Equipment', icon: <DevicesIcon /> },
  { to: '/work-orders', label: 'Work orders', icon: <AssignmentIcon /> },
  { to: '/hospitals', label: 'Hospitals', icon: <DomainIcon /> },
  {
    to: '/users',
    label: 'Users',
    icon: <PeopleIcon />,
    roles: [ROLE_CLINICAL_ADMIN, ROLE_AUDITOR],
  },
]

function roleLabel(role: string) {
  if (role === 'clinical_admin') return 'Clinical admin'
  if (role === 'field_technician') return 'Field technician'
  if (role === 'auditor') return 'Auditor'
  return role
}

export function AppShell() {
  const { user, logout } = useAuth()
  const location = useLocation()

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            MedFlow
          </Typography>
          {user ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Typography variant="body2">{user.full_name}</Typography>
              <Chip size="small" color="secondary" label={roleLabel(user.role)} />
              <Button color="inherit" startIcon={<LogoutIcon />} onClick={logout}>
                Sign out
              </Button>
            </Box>
          ) : null}
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          [`& .MuiDrawer-paper`]: { width: DRAWER_WIDTH, boxSizing: 'border-box' },
        }}
      >
        <Toolbar />
        <List>
          {NAV.filter((item) => !item.roles || (user && item.roles.includes(user.role))).map(
            (item) => (
              <ListItemButton
                key={item.to}
                component={NavLink}
                to={item.to}
                selected={item.end ? location.pathname === item.to : location.pathname.startsWith(item.to)}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItemButton>
            ),
          )}
        </List>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Toolbar />
        <Container maxWidth="xl" disableGutters>
          <Outlet />
        </Container>
      </Box>
    </Box>
  )
}
