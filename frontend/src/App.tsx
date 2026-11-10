import { QueryClientProvider, type QueryClient } from '@tanstack/react-query'
import { useConfig } from './api/config'
import { useVehicles } from './api/vehicles'
import { AppRoutes } from './routes'

/** `GET /config` and `GET /vehicles` load at app start (ADR 0005). */
function Preload() {
  useConfig()
  useVehicles()
  return null
}

/** The app below the router, so tests can mount it in a MemoryRouter. */
export function App({ queryClient }: { queryClient: QueryClient }) {
  return (
    <QueryClientProvider client={queryClient}>
      <Preload />
      <AppRoutes />
    </QueryClientProvider>
  )
}
