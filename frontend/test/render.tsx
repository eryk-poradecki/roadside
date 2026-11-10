import { render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { App } from '../src/App'
import { createQueryClient } from '../src/api/queryClient'

/** Mount the whole app at a route, backed by the MSW fake API. */
export function renderApp(route = '/') {
  const queryClient = createQueryClient()
  queryClient.setDefaultOptions({
    queries: { ...queryClient.getDefaultOptions().queries, retry: false },
  })
  const user = userEvent.setup()
  render(
    <MemoryRouter initialEntries={[route]}>
      <App queryClient={queryClient} />
    </MemoryRouter>,
  )
  return { user }
}
