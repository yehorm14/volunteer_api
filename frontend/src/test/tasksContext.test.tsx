import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { TasksProvider } from '../context/TasksContext'
import { useTasks } from '../hooks/useTasks'
import { HttpResponse, db, delay, http, seed, server } from './server'

function Probe() {
  const { tasks, fetchTasks, editTask } = useTasks()
  return (
    <div>
      <ul>
        {tasks.map((t) => (
          <li key={t.id}>{`${t.id}:${t.title}:${t.status}`}</li>
        ))}
      </ul>
      <button onClick={() => void fetchTasks()}>reload</button>
      <button onClick={() => void editTask(1, { title: 'Renamed' }).catch(() => undefined)}>rename</button>
      <button onClick={() => void editTask(1, { status: 'completed' }).catch(() => undefined)}>complete</button>
    </div>
  )
}

function renderProbe() {
  return render(
    <TasksProvider>
      <Probe />
    </TasksProvider>
  )
}

describe('TasksProvider', () => {
  it('keeps the newest list when an older request answers last', async () => {
    seed([{ title: 'Old' }])
    let calls = 0
    server.use(
      http.get('/api/tasks', async () => {
        const n = ++calls
        if (n === 2) {
          await delay(150) // the second request is slow and returns what was true at the time
          return HttpResponse.json([{ id: 1, title: 'Older answer', description: null, status: 'pending', owner_id: 1 }])
        }
        if (n === 3) return HttpResponse.json([{ id: 1, title: 'Newest answer', description: null, status: 'pending', owner_id: 1 }])
        return HttpResponse.json(db.tasks)
      })
    )
    const user = userEvent.setup()
    renderProbe()
    await screen.findByText('1:Old:pending')

    await user.click(screen.getByText('reload')) // slow
    await user.click(screen.getByText('reload')) // fast, newer
    expect(await screen.findByText('1:Newest answer:pending')).toBeInTheDocument()
    await delay(250)
    expect(screen.queryByText('1:Older answer:pending')).not.toBeInTheDocument()
    expect(screen.getByText('1:Newest answer:pending')).toBeInTheDocument()
  })

  it('rolls back only the failed edit, not a concurrent successful one', async () => {
    seed([{ title: 'Original', status: 'pending' }])
    server.use(
      http.patch('/api/tasks/:id', async ({ request }) => {
        const body = (await request.json()) as Record<string, string>
        if ('title' in body) {
          await delay(100)
          return HttpResponse.json({ detail: 'nope' }, { status: 500 })
        }
        Object.assign(db.tasks[0], body)
        return HttpResponse.json(db.tasks[0])
      })
    )
    const user = userEvent.setup()
    renderProbe()
    await screen.findByText('1:Original:pending')

    await user.click(screen.getByText('rename')) // fails after 100ms
    await user.click(screen.getByText('complete')) // succeeds immediately

    // After the rename fails (100ms) the title is restored but the completed status is kept.
    // (A snapshot-based rollback would put the task back to pending and undo the successful edit.)
    await delay(250)
    expect(screen.getByText('1:Original:completed')).toBeInTheDocument()
  })
})
