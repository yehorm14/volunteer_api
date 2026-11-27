import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest'
import { resetDb, server } from './server'

// jsdom has no top layer. The real dialog interaction is covered by the browser spec.
if (!HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function () { this.open = true }
  HTMLDialogElement.prototype.close = function () { this.open = false }
}

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
