import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import '@fontsource-variable/atkinson-hyperlegible-next'
import './styles/tokens.css'
import './styles/base.css'
import { App } from './App'
import { configureApiClient } from './api/client'
import { createQueryClient } from './api/queryClient'
import { initI18n } from './i18n'

configureApiClient()
const root = document.getElementById('root')
if (!root) throw new Error('Missing #root')

void initI18n().then(() => {
  createRoot(root).render(
    <StrictMode>
      <BrowserRouter>
        <App queryClient={createQueryClient()} />
      </BrowserRouter>
    </StrictMode>,
  )
})
