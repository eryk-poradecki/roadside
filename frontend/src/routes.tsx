import { Navigate, Route, Routes } from 'react-router'
import { AppShell } from './components/AppShell'
import { TabBar } from './components/TabBar'
import { History } from './screens/History'
import { IncidentScreen } from './screens/IncidentScreen'
import { Start } from './screens/Start'
import { VehicleForm } from './screens/VehicleForm'
import { Vehicles } from './screens/Vehicles'

/** Top-level screens get the tab bar. Flow screens use Back. Both keep the 112 control. */
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
        <Route path="vehicles/new" element={<VehicleForm />} />
        <Route path="vehicles/:id" element={<VehicleForm />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
