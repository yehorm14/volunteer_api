import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest'
import { resetDb, server } from './server'

// Anything the test has not mocked must fail loudly: no live provider, no real network.
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
beforeEach(() => {
  resetDb()
  localStorage.clear()
  window.history.pushState({}, '', '/')
})
afterEach(() => {
  cleanup()
  server.resetHandlers()
})
afterAll(() => server.close())
