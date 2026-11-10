import { render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { StrictMode } from 'react'
import { MemoryRouter } from 'react-router'
import { App } from '../src/App'
import { createQueryClient } from '../src/api/queryClient'

/** Mount the whole app at a route, backed by the MSW fake API. `strict` mounts it in
 * StrictMode, as `main.tsx` does, so effects run twice. */
export function renderApp(
  route: string | { pathname: string; state: unknown } = '/',
  { strict = false }: { strict?: boolean } = {},
) {
  const queryClient = createQueryClient()
  queryClient.setDefaultOptions({
    queries: { ...queryClient.getDefaultOptions().queries, retry: false },
  })
  const user = userEvent.setup()
  const app = (
    <MemoryRouter initialEntries={[route]}>
      <App queryClient={queryClient} />
    </MemoryRouter>
  )
  render(strict ? <StrictMode>{app}</StrictMode> : app)
  return { user }
}
