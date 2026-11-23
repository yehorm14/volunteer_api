import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { HttpResponse, http, seed, server } from './server'
import { renderApp } from './renderApp'

describe('429 responses show the server message', () => {
  it('on sign in', async () => {
    server.use(
      http.post('/api/auth/login', () =>
        HttpResponse.json({ detail: 'Too many attempts. Please wait 42 seconds and try again.' }, { status: 429 })
      )
    )
    const user = userEvent.setup()
    renderApp('/login', { signedIn: false })
    await user.type(screen.getByLabelText('Email'), 'vol@example.com')
    await user.type(screen.getByLabelText('Password'), 'whatever')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Too many attempts. Please wait 42 seconds and try again.')).toBeInTheDocument()
  })

  it('on the AI actions', async () => {
    const [task] = seed([{ title: 'Call the shelter' }])
    const detail = 'Daily AI limit reached (20 per day). It resets at midnight UTC.'
    server.use(
      http.get('/api/tasks/:id', () => HttpResponse.json(task)),
      http.post('/api/tasks/:id/ai-categorize', () => HttpResponse.json({ detail }, { status: 429 })),
      http.post('/api/tasks/extract', () => HttpResponse.json({ detail }, { status: 429 }))
    )
    const user = userEvent.setup()
    renderApp(`/tasks/${task.id}`)

    await user.click(await screen.findByRole('button', { name: 'Categorize' }))
    expect(await screen.findByText(detail)).toBeInTheDocument()

    await user.type(screen.getByPlaceholderText(/need to call the shelter/), 'some notes')
    await user.click(screen.getByRole('button', { name: 'Extract task' }))
    expect(await screen.findAllByText(detail)).toHaveLength(2)
  })
})
