import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { HttpResponse, db, http, seed, server } from './server'
import { renderApp } from './renderApp'

function useExtractAndGetTask(extract: () => Response | Promise<Response>) {
  server.use(
    http.get('/api/tasks/:id', ({ params }) => {
      const task = db.tasks.find((t) => t.id === Number(params.id))
      return task ? HttpResponse.json(task) : HttpResponse.json({ detail: 'Task not found' }, { status: 404 })
    }),
    http.post('/api/tasks/extract', () => extract())
  )
}

function pendingCount(): number {
  const tile = screen.getAllByText('Pending').map((el) => el.closest('div.bg-slate-900'))
  return Number(tile.find((t) => t?.querySelector('p.text-2xl'))?.querySelector('p.text-2xl')?.textContent)
}

describe('AI extraction keeps the dashboard in sync', () => {
  it('shows the extracted task and updated counts on the dashboard without a reload', async () => {
    seed([{ title: 'Existing task' }])
    useExtractAndGetTask(() => {
      const task = {
        id: db.nextId++,
        title: 'Call the shelter',
        description: 'About food donations',
        status: 'pending' as const,
        owner_id: 1,
      }
      db.tasks.push(task)
      return HttpResponse.json(task, { status: 201 })
    })
    const user = userEvent.setup()
    renderApp('/tasks/1')

    await user.type(await screen.findByPlaceholderText(/need to call the shelter/), 'call shelter about food')
    await user.click(screen.getByRole('button', { name: 'Extract task' }))
    expect(await screen.findByText('Task created')).toBeInTheDocument()

    // Navigate client-side (no reload) back to the dashboard.
    await user.click(screen.getAllByRole('link', { name: /dashboard/i })[0])
    expect(await screen.findByRole('heading', { name: 'My Tasks' })).toBeInTheDocument()
    expect(await screen.findByText('Call the shelter')).toBeInTheDocument()
    expect(screen.getAllByText('Call the shelter')).toHaveLength(1)
    expect(screen.getAllByText('Existing task')).toHaveLength(1)
    expect(pendingCount()).toBe(2)
  })

  it('leaves the dashboard unchanged when extraction fails', async () => {
    seed([{ title: 'Existing task' }])
    useExtractAndGetTask(() => HttpResponse.json({ detail: 'Could not extract a task' }, { status: 422 }))
    const user = userEvent.setup()
    renderApp('/tasks/1')

    await user.type(await screen.findByPlaceholderText(/need to call the shelter/), 'gibberish')
    await user.click(screen.getByRole('button', { name: 'Extract task' }))
    expect(await screen.findByText('Could not extract a task')).toBeInTheDocument()

    await user.click(screen.getAllByRole('link', { name: /dashboard/i })[0])
    expect(await screen.findByText('Existing task')).toBeInTheDocument()
    expect(pendingCount()).toBe(1)
    expect(within(document.body).queryByText('Task created')).not.toBeInTheDocument()
  })
})
