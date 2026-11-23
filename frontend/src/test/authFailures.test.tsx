import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest'
import { HttpResponse, http, seed, server } from './server'
import { renderApp } from './renderApp'
import { navigation } from '../services/api'

let toLogin: MockInstance

beforeEach(() => {
  toLogin = vi.spyOn(navigation, 'toLogin').mockImplementation(() => {})
})

describe('401 handling', () => {
  it('keeps a wrong-password error on the login form without navigating', async () => {
    const user = userEvent.setup()
    renderApp('/login', { signedIn: false })
    await user.type(screen.getByLabelText('Email'), 'vol@example.com')
    await user.type(screen.getByLabelText('Password'), 'wrong')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Incorrect email or password')).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toHaveValue('vol@example.com')
    expect(toLogin).not.toHaveBeenCalled()
  })

  it('still signs out and redirects when a stored session expires', async () => {
    server.use(http.get('/api/tasks', () => HttpResponse.json({ detail: 'Token expired' }, { status: 401 })))
    renderApp('/dashboard')

    await vi.waitFor(() => expect(toLogin).toHaveBeenCalledTimes(1))
    expect(localStorage.getItem('access_token')).toBeNull()
  })
})

describe('task detail deletion failure', () => {
  it('keeps the task and shows a retryable error', async () => {
    const [task] = seed([{ title: 'Call the shelter' }])
    let attempts = 0
    server.use(
      http.get('/api/tasks/:id', () => HttpResponse.json(task)),
      http.delete('/api/tasks/:id', () => {
        attempts++
        return attempts === 1
          ? HttpResponse.json({ detail: 'Database is busy' }, { status: 500 })
          : new HttpResponse(null, { status: 204 })
      })
    )
    const user = userEvent.setup()
    renderApp(`/tasks/${task.id}`)

    await user.click(await screen.findByRole('button', { name: 'Delete' }))
    await user.click(screen.getByRole('button', { name: 'Confirm' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('The task was not deleted. Database is busy')
    expect(screen.getByRole('heading', { name: 'Call the shelter' })).toBeInTheDocument()

    // Confirmation controls remain, so retry works.
    await user.click(screen.getByRole('button', { name: 'Confirm' }))
    await vi.waitFor(() => expect(attempts).toBe(2))
  })
})
