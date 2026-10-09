import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AuthProvider } from './auth/AuthContext'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { ColorModeProvider } from './colorMode'
import { AppShell } from './layout/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { EquipmentPage } from './pages/EquipmentPage'
import { HospitalsPage } from './pages/HospitalsPage'
import { LoginPage } from './pages/LoginPage'
import { UsersPage } from './pages/UsersPage'
import { RolesPage } from './pages/RolesPage'
import { WorkOrdersPage } from './pages/WorkOrdersPage'
import { Permission } from './permissions'

export default function App() {
  return (
    <ColorModeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppShell />}>
                <Route path="/" element={<DashboardPage />} />
                <Route
                  element={
                    <ProtectedRoute
                      anyOf={[Permission.equipmentRead, Permission.equipmentReadAssigned]}
                    />
                  }
                >
                  <Route path="/equipment" element={<EquipmentPage />} />
                </Route>
                <Route
                  element={
                    <ProtectedRoute
                      anyOf={[Permission.workOrderRead, Permission.workOrderReadAssigned]}
                    />
                  }
                >
                  <Route path="/work-orders" element={<WorkOrdersPage />} />
                </Route>
                <Route element={<ProtectedRoute permission={Permission.hospitalRead} />}>
                  <Route path="/hospitals" element={<HospitalsPage />} />
                </Route>
                <Route element={<ProtectedRoute permission={Permission.userRead} />}>
                  <Route path="/users" element={<UsersPage />} />
                </Route>
                <Route element={<ProtectedRoute permission={Permission.roleRead} />}>
                  <Route path="/roles" element={<RolesPage />} />
                </Route>
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ColorModeProvider>
  )
}
