import { Navigate, Route, Routes } from 'react-router'
import { AppShell } from './components/AppShell'
import { TabBar } from './components/TabBar'
import { DamageReportScreen } from './screens/DamageReportScreen'
import { History } from './screens/History'
import { IncidentEdit } from './screens/IncidentEdit'
import { IncidentScreen } from './screens/IncidentScreen'
import { Start } from './screens/Start'
import { VehicleForm } from './screens/VehicleForm'
import { Vehicles } from './screens/Vehicles'

/**
 * Mobile: top-level screens get the tab bar, flow screens use Back, and both keep the 112
 * control. Desktop: the sidebar on every route and no global 112 (ADR 0012).
 */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell dock={<TabBar />} />}>
        <Route index element={<Start />} />
        <Route path="incidents" element={<History />} />
        <Route path="vehicles" element={<Vehicles />} />
      </Route>
      <Route element={<AppShell />}>
        <Route path="incidents/:id" element={<IncidentScreen />} />
        <Route path="incidents/:id/edit" element={<IncidentEdit />} />
        <Route path="incidents/:id/report" element={<DamageReportScreen />} />
        <Route path="vehicles/new" element={<VehicleForm />} />
        <Route path="vehicles/:id" element={<VehicleForm />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
