import CssBaseline from '@mui/material/CssBaseline'
import { ThemeProvider } from '@mui/material/styles'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AuthProvider } from './auth/AuthContext'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { AppShell } from './layout/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { EquipmentPage } from './pages/EquipmentPage'
import { HospitalsPage } from './pages/HospitalsPage'
import { LoginPage } from './pages/LoginPage'
import { UsersPage } from './pages/UsersPage'
import { WorkOrdersPage } from './pages/WorkOrdersPage'
import { theme } from './theme'

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppShell />}>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/equipment" element={<EquipmentPage />} />
                <Route path="/work-orders" element={<WorkOrdersPage />} />
                <Route path="/hospitals" element={<HospitalsPage />} />
                <Route
                  element={<ProtectedRoute roles={['clinical_admin', 'auditor']} />}
                >
                  <Route path="/users" element={<UsersPage />} />
                </Route>
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
