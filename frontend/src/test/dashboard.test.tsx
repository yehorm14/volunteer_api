import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { HttpResponse, db, delay, http, seed, server } from './server'
import { renderApp } from './renderApp'

const THREE = [
  { title: 'Call the food bank', status: 'pending' },
  { title: 'Print sign-in sheets', status: 'in_progress' },
  { title: 'Send thank-you emails', status: 'completed' },
]

/** The stat tile for a status, e.g. statCount('Pending') -> 1 */
function statCount(label: string): number {
  const tile = screen.getAllByText(label).map((el) => el.closest('div.bg-slate-900'))
  const found = tile.find((t) => t?.querySelector('p.text-2xl'))
  return Number(found?.querySelector('p.text-2xl')?.textContent)
}

function card(title: string): HTMLElement {
  return screen.getByRole('heading', { name: title }).closest('div.group') as HTMLElement
}

describe('sign in', () => {
  it('signs in and lands on the dashboard with the three statuses', async () => {
    seed(THREE)
    const user = userEvent.setup()
    renderApp('/login', { signedIn: false })

    await user.type(screen.getByLabelText('Email'), 'vol@example.com')
    await user.type(screen.getByLabelText('Password'), 'correct-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { name: 'My Tasks' })).toBeInTheDocument()
    expect(await screen.findByText('Call the food bank')).toBeInTheDocument()
    expect(statCount('Pending')).toBe(1)
    expect(statCount('In Progress')).toBe(1)
    expect(statCount('Completed')).toBe(1)
    expect(localStorage.getItem('access_token')).toBeTruthy()
  })

  it('shows the server message for bad credentials and stays on the form', async () => {
    const user = userEvent.setup()
    renderApp('/login', { signedIn: false })
    await user.type(screen.getByLabelText('Email'), 'vol@example.com')
    await user.type(screen.getByLabelText('Password'), 'wrong')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Incorrect email or password')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'My Tasks' })).not.toBeInTheDocument()
  })

  it('sends a signed-out visitor from the dashboard to sign in', async () => {
    renderApp('/dashboard', { signedIn: false })
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
  })
})

describe('task workflows', () => {
  it('creates a task', async () => {
    const user = userEvent.setup()
    renderApp('/dashboard')
    expect(await screen.findByText('No tasks yet')).toBeInTheDocument()

    await user.click(screen.getAllByRole('button', { name: '+ New task' })[0])
    await user.type(screen.getByLabelText('Title'), 'Pack food boxes')
    await user.type(screen.getByLabelText('Description'), 'Saturday 10am')
    await user.click(screen.getByRole('button', { name: 'Create task' }))

    expect(await screen.findByText('Pack food boxes')).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(db.tasks).toHaveLength(1)
    expect(db.tasks[0]).toMatchObject({ title: 'Pack food boxes', status: 'pending' })
    expect(statCount('Pending')).toBe(1)
  })

  it('validates a blank title without calling the API', async () => {
    const user = userEvent.setup()
    renderApp('/dashboard')
    await screen.findByText('No tasks yet')
    await user.click(screen.getAllByRole('button', { name: '+ New task' })[0])
    await user.click(screen.getByRole('button', { name: 'Create task' }))
    expect(screen.getByText('Title is required')).toBeInTheDocument()
    expect(db.tasks).toHaveLength(0)
  })

  it('moves a task through all three statuses', async () => {
    seed([{ title: 'Walk the dogs', status: 'pending' }])
    const user = userEvent.setup()
    renderApp('/dashboard')
    await screen.findByText('Walk the dogs')

    await user.click(within(card('Walk the dogs')).getByRole('button', { name: 'Mark in progress' }))
    await waitFor(() => expect(within(card('Walk the dogs')).getByText('In Progress')).toBeInTheDocument())
    expect(db.tasks[0].status).toBe('in_progress')
    expect(statCount('In Progress')).toBe(1)

    await user.click(within(card('Walk the dogs')).getByRole('button', { name: 'Mark complete' }))
    await waitFor(() => expect(within(card('Walk the dogs')).getByText('Completed')).toBeInTheDocument())
    expect(db.tasks[0].status).toBe('completed')

    await user.click(within(card('Walk the dogs')).getByRole('button', { name: 'Reset to pending' }))
    await waitFor(() => expect(within(card('Walk the dogs')).getByText('Pending')).toBeInTheDocument())
    expect(db.tasks[0].status).toBe('pending')
  })

  it('filters by status and explains an empty filter', async () => {
    seed([...THREE])
    const user = userEvent.setup()
    renderApp('/dashboard')
    await screen.findByText('Call the food bank')

    await user.click(screen.getByRole('button', { name: 'In Progress' }))
    expect(screen.getByText('Print sign-in sheets')).toBeInTheDocument()
    expect(screen.queryByText('Call the food bank')).not.toBeInTheDocument()
    expect(screen.queryByText('Send thank-you emails')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Completed' }))
    await user.click(within(card('Send thank-you emails')).getByRole('button', { name: 'Reset to pending' }))
    expect(await screen.findByText('No completed tasks')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'All' }))
    expect(screen.getAllByRole('heading', { level: 3 })).toHaveLength(3)
  })

  it('deletes a task', async () => {
    seed([...THREE])
    const user = userEvent.setup()
    renderApp('/dashboard')
    await screen.findByText('Call the food bank')

    await user.click(within(card('Call the food bank')).getByRole('button', { name: 'Delete' }))
    await waitFor(() => expect(screen.queryByText('Call the food bank')).not.toBeInTheDocument())
    expect(db.tasks.map((t) => t.title)).not.toContain('Call the food bank')
    expect(screen.getByText('2 tasks total')).toBeInTheDocument()
  })

  it('shows a legacy status as unknown and lets the user repair it', async () => {
    seed([{ title: 'Old row', status: 'In Progress' }])
    const user = userEvent.setup()
    renderApp('/dashboard')
    expect(await screen.findByText('Unknown status')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Reset to pending' }))
    await waitFor(() => expect(screen.queryByText('Unknown status')).not.toBeInTheDocument())
    expect(db.tasks[0].status).toBe('pending')
  })
})

describe('error recovery', () => {
  it('restores the task and explains a failed status change', async () => {
    seed([{ title: 'Walk the dogs', status: 'pending' }])
    server.use(http.patch('/api/tasks/:id', () => HttpResponse.json({ detail: 'Database unavailable' }, { status: 500 })))
    const user = userEvent.setup()
    renderApp('/dashboard')
    await screen.findByText('Walk the dogs')

    await user.click(within(card('Walk the dogs')).getByRole('button', { name: 'Mark in progress' }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Could not update "Walk the dogs"')
    expect(alert).toHaveTextContent('restored to its previous status')
    expect(alert).toHaveTextContent('Database unavailable')
    // Card, badge, button and counts all agree on the original state again.
    expect(within(card('Walk the dogs')).getByText('Pending')).toBeInTheDocument()
    expect(within(card('Walk the dogs')).getByRole('button', { name: 'Mark in progress' })).toBeInTheDocument()
    expect(statCount('Pending')).toBe(1)
    expect(statCount('In Progress')).toBe(0)
    // The user can dismiss the message and try again once the server recovers.
    await user.click(screen.getByRole('button', { name: 'Dismiss error' }))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    server.resetHandlers()
    await user.click(within(card('Walk the dogs')).getByRole('button', { name: 'Mark in progress' }))
    await waitFor(() => expect(within(card('Walk the dogs')).getByText('In Progress')).toBeInTheDocument())
  })

  it('explains a status change when the server cannot be reached', async () => {
    seed([{ title: 'Walk the dogs' }])
    server.use(http.patch('/api/tasks/:id', () => HttpResponse.error()))
    const user = userEvent.setup()
    renderApp('/dashboard')
    await screen.findByText('Walk the dogs')
    await user.click(within(card('Walk the dogs')).getByRole('button', { name: 'Mark in progress' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be reached')
    expect(within(card('Walk the dogs')).getByText('Pending')).toBeInTheDocument()
  })

  it('puts a task back when deleting it fails', async () => {
    seed([{ title: 'Walk the dogs' }, { title: 'Water the garden' }])
    server.use(http.delete('/api/tasks/:id', () => HttpResponse.json({ detail: 'Nope' }, { status: 500 })))
    const user = userEvent.setup()
    renderApp('/dashboard')
    await screen.findByText('Walk the dogs')

    await user.click(within(card('Walk the dogs')).getByRole('button', { name: 'Delete' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not delete "Walk the dogs"')
    expect(screen.getByText('Walk the dogs')).toBeInTheDocument()
    expect(screen.getByText('2 tasks total')).toBeInTheDocument()
  })

  it('keeps the create dialog and its text when creating fails', async () => {
    server.use(http.post('/api/tasks', () => HttpResponse.json({ detail: 'Try later' }, { status: 503 })))
    const user = userEvent.setup()
    renderApp('/dashboard')
    await screen.findByText('No tasks yet')
    await user.click(screen.getAllByRole('button', { name: '+ New task' })[0])
    await user.type(screen.getByLabelText('Title'), 'Pack food boxes')
    await user.click(screen.getByRole('button', { name: 'Create task' }))

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByRole('alert')).toHaveTextContent('The task was not created. Try later')
    expect(within(dialog).getByLabelText('Title')).toHaveValue('Pack food boxes')
    expect(screen.queryByText('1 task total')).not.toBeInTheDocument()
  })

  it('recovers from a failed load with Try again', async () => {
    seed([{ title: 'Walk the dogs' }])
    server.use(http.get('/api/tasks', () => HttpResponse.json({ detail: 'down' }, { status: 500 }), { once: true }))
    const user = userEvent.setup()
    renderApp('/dashboard')

    expect(await screen.findByText('Failed to load tasks')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('Walk the dogs')).toBeInTheDocument()
    expect(screen.queryByText('Failed to load tasks')).not.toBeInTheDocument()
  })

  it('does not lose a task created while the first list request is still in flight', async () => {
    let calls = 0
    server.use(
      http.get('/api/tasks', async () => {
        calls += 1
        if (calls === 1) {
          const snapshot = [...db.tasks] // what the server knew when the request arrived: nothing
          await delay(150)
          return HttpResponse.json(snapshot)
        }
        return HttpResponse.json(db.tasks)
      })
    )
    const user = userEvent.setup()
    renderApp('/dashboard')
    // The header button is available while the list is still loading.
    await user.click(screen.getAllByRole('button', { name: '+ New task' })[0])
    await user.type(screen.getByLabelText('Title'), 'Created meanwhile')
    await user.click(screen.getByRole('button', { name: 'Create task' }))

    // The slow, out-of-date (empty) list arrives afterwards; the new task must still be shown.
    await waitFor(() => expect(calls).toBeGreaterThanOrEqual(2))
    expect(await screen.findByText('Created meanwhile')).toBeInTheDocument()
    expect(screen.queryByText('No tasks yet')).not.toBeInTheDocument()
  })
})
