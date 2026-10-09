import DashboardIcon from '@mui/icons-material/SpaceDashboard'
import DevicesIcon from '@mui/icons-material/MedicalServices'
import AssignmentIcon from '@mui/icons-material/Assignment'
import DomainIcon from '@mui/icons-material/Domain'
import PeopleIcon from '@mui/icons-material/People'
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings'
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
import { ThemeToggle } from '../components/ThemeToggle'
import { Permission } from '../permissions'

const DRAWER_WIDTH = 240

const NAV = [
  { to: '/', label: 'Dashboard', icon: <DashboardIcon />, end: true, permissions: [Permission.analyticsRead] },
  {
    to: '/equipment',
    label: 'Equipment',
    icon: <DevicesIcon />,
    permissions: [Permission.equipmentRead, Permission.equipmentReadAssigned],
  },
  {
    to: '/work-orders',
    label: 'Work orders',
    icon: <AssignmentIcon />,
    permissions: [Permission.workOrderRead, Permission.workOrderReadAssigned],
  },
  { to: '/hospitals', label: 'Hospitals', icon: <DomainIcon />, permissions: [Permission.hospitalRead] },
  { to: '/users', label: 'Users', icon: <PeopleIcon />, permissions: [Permission.userRead] },
  { to: '/roles', label: 'Roles', icon: <AdminPanelSettingsIcon />, permissions: [Permission.roleRead] },
]

function roleLabel(role: string) {
  if (role === 'clinical_admin') return 'Clinical admin'
  if (role === 'field_technician') return 'Field technician'
  if (role === 'auditor') return 'Auditor'
  return role
}

export function AppShell() {
  const { user, logout, can } = useAuth()
  const location = useLocation()

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            MedFlow
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <ThemeToggle />
            {user ? (
              <>
                <Typography variant="body2">{user.full_name}</Typography>
                <Chip size="small" color="secondary" label={roleLabel(user.role)} />
                <Button color="inherit" startIcon={<LogoutIcon />} onClick={logout}>
                  Sign out
                </Button>
              </>
            ) : null}
          </Box>
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
          {NAV.filter((item) => item.permissions.some((permission) => can(permission))).map(
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
