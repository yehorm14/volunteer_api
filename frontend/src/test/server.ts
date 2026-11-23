import { http, HttpResponse, delay } from 'msw'
import { setupServer } from 'msw/node'
import type { Task } from '../types'

/** A tiny in-memory stand-in for the API, reset before every test. */
export const db = {
  tasks: [] as Task[],
  nextId: 1,
}

export function seed(tasks: Partial<Task>[]): Task[] {
  db.tasks = tasks.map((t) => ({
    id: db.nextId++,
    title: 'Untitled',
    description: null,
    status: 'pending',
    owner_id: 1,
    ...t,
  }))
  return db.tasks
}

export function resetDb() {
  db.tasks = []
  db.nextId = 1
}

/** A fake, unsigned token whose payload carries the email the app displays. */
export function fakeToken(email = 'vol@example.com') {
  return `x.${btoa(JSON.stringify({ sub: email }))}.x`
}

const API = '/api'

export const handlers = [
  http.post(`${API}/auth/login`, async ({ request }) => {
    const form = new URLSearchParams(await request.text())
    if (form.get('password') !== 'correct-password') {
      return HttpResponse.json({ detail: 'Incorrect email or password' }, { status: 401 })
    }
    return HttpResponse.json({ access_token: fakeToken(form.get('username') ?? ''), token_type: 'bearer' })
  }),

  http.get(`${API}/tasks`, () => HttpResponse.json(db.tasks)),

  http.post(`${API}/tasks`, async ({ request }) => {
    const body = (await request.json()) as Partial<Task>
    const task: Task = {
      id: db.nextId++,
      title: body.title ?? '',
      description: body.description ?? null,
      status: body.status ?? 'pending',
      owner_id: 1,
    }
    db.tasks.push(task)
    return HttpResponse.json(task, { status: 201 })
  }),

  http.patch(`${API}/tasks/:id`, async ({ params, request }) => {
    const task = db.tasks.find((t) => t.id === Number(params.id))
    if (!task) return HttpResponse.json({ detail: 'Task not found' }, { status: 404 })
    Object.assign(task, await request.json())
    return HttpResponse.json(task)
  }),

  http.delete(`${API}/tasks/:id`, ({ params }) => {
    db.tasks = db.tasks.filter((t) => t.id !== Number(params.id))
    return new HttpResponse(null, { status: 204 })
  }),
]

export const server = setupServer(...handlers)
export { http, HttpResponse, delay }
