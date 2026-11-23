import { fireEvent, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { HttpResponse, http, seed, server } from './server'
import { renderApp } from './renderApp'

const PLACEHOLDER = /need to call the shelter/

function setup() {
  const [task] = seed([{ title: 'Call the shelter' }])
  server.use(http.get('/api/tasks/:id', () => HttpResponse.json(task)))
  renderApp(`/tasks/${task.id}`)
  return { task, user: userEvent.setup() }
}

describe('AI panel error handling', () => {
  it('shows a counter and blocks overlong notes without calling the API', async () => {
    let calls = 0
    server.use(http.post('/api/tasks/extract', () => { calls++; return HttpResponse.json({}, { status: 500 }) }))
    const { user } = setup()
    const box = await screen.findByPlaceholderText(PLACEHOLDER)
    expect(screen.getByText('0 / 10,000 characters')).toBeInTheDocument()

    fireEvent.change(box, { target: { value: 'a'.repeat(10_001) } })
    expect(screen.getByText('10,001 / 10,000 characters')).toBeInTheDocument()
    expect(screen.getByText(/Notes are too long/)).toBeInTheDocument()
    const button = screen.getByRole('button', { name: 'Extract task' })
    expect(button).toBeDisabled()
    await user.click(button)
    expect(calls).toBe(0)

    fireEvent.change(box, { target: { value: 'a'.repeat(10_000) } })
    expect(button).toBeEnabled()
  })

  it('renders a structured 422 as text and stays usable, then retries', async () => {
    let n = 0
    server.use(
      http.post('/api/tasks/extract', () => {
        n++
        if (n === 1) {
          return HttpResponse.json(
            { detail: [{ type: 'string_too_long', loc: ['body', 'notes'], msg: 'String should have at most 10000 characters', input: 'x', ctx: { max_length: 10000 } }] },
            { status: 422 }
          )
        }
        return HttpResponse.json({ id: 99, title: 'Call shelter', description: 'About food', status: 'todo' })
      })
    )
    const { user } = setup()
    await user.type(await screen.findByPlaceholderText(PLACEHOLDER), 'some notes')
    await user.click(screen.getByRole('button', { name: 'Extract task' }))
    expect(await screen.findByText('String should have at most 10000 characters')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'AI Tools' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Extract task' }))
    expect(await screen.findByText('Task created')).toBeInTheDocument()
    expect(screen.queryByText('String should have at most 10000 characters')).not.toBeInTheDocument()
  })

  it('shows provider errors for extract and categorize and allows retry', async () => {
    let n = 0
    server.use(
      http.post('/api/tasks/extract', () => {
        n++
        return n === 1
          ? HttpResponse.json({ detail: 'AI provider error. Try again.' }, { status: 502 })
          : HttpResponse.json({ id: 98, title: 'Ok', description: '', status: 'todo' })
      }),
      http.post('/api/tasks/:id/ai-categorize', () => HttpResponse.json({}, { status: 500 }))
    )
    const { user } = setup()
    await user.click(await screen.findByRole('button', { name: 'Categorize' }))
    expect(await screen.findByText('The server returned an error (500).')).toBeInTheDocument()

    await user.type(screen.getByPlaceholderText(PLACEHOLDER), 'notes')
    await user.click(screen.getByRole('button', { name: 'Extract task' }))
    expect(await screen.findByText('AI provider error. Try again.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Extract task' }))
    expect(await screen.findByText('Task created')).toBeInTheDocument()
  })

  it('shows the 503 notice from a string detail', async () => {
    server.use(http.post('/api/tasks/extract', () => HttpResponse.json({ detail: 'AI is not configured' }, { status: 503 })))
    const { user } = setup()
    await user.type(await screen.findByPlaceholderText(PLACEHOLDER), 'notes')
    await user.click(screen.getByRole('button', { name: 'Extract task' }))
    expect(await screen.findByRole('status')).toHaveTextContent('AI is not configured')
  })
})
