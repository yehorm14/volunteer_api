import { defineConfig } from '@playwright/test'

const baseURL = 'http://127.0.0.1:5189'

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.e2e.ts',
  use: {
    baseURL,
    channel: process.env.PLAYWRIGHT_CHANNEL,
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5189 --strictPort',
    env: { VITE_API_URL: '/api' },
    url: baseURL,
  },
})
