import { defineConfig } from '@hey-api/openapi-ts'

export default defineConfig({
  input: './openapi.json',
  output: { path: 'src/api/generated', clean: true },
  plugins: [
    '@hey-api/typescript',
    { name: '@hey-api/sdk', operations: { strategy: 'flat' } },
    '@hey-api/client-fetch',
    '@tanstack/react-query',
  ],
})
