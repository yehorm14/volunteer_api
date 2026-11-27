import { createContext, useContext, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import * as api from '../services/api'
import type { Task, TaskCreate, TaskUpdate } from '../types'

interface TasksContextValue {
  tasks: Task[]
  isLoading: boolean
  error: string | null
  fetchTasks: () => Promise<void>
  addTask: (data: TaskCreate) => Promise<Task>
  /** Add or replace a task that was already saved on the server (e.g. by AI extraction). */
  insertTask: (task: Task) => void
  editTask: (id: number, data: TaskUpdate) => Promise<Task>
  removeTask: (id: number) => Promise<void>
}

const TasksContext = createContext<TasksContextValue | null>(null)

export function TasksProvider({ children }: { children: ReactNode }) {
  const [tasks, setTasksState] = useState<Task[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // The ref is the source of truth for the current list so that rollbacks and
  // overlapping requests never work from a stale render closure.
  const tasksRef = useRef<Task[]>([])
  const latestFetch = useRef(0)
  const mutations = useRef(0)

  function commit(updater: (prev: Task[]) => Task[]) {
    tasksRef.current = updater(tasksRef.current)
    setTasksState(tasksRef.current)
  }

  async function fetchTasks() {
    const requestId = ++latestFetch.current
    setIsLoading(true)
    setError(null)
    const maxAttempts = 3
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      const mutationsAtStart = mutations.current
      try {
        const data = await api.getTasks()
        // A newer fetch has started: this response is stale, drop it.
        if (requestId !== latestFetch.current) return
        // The list was read before a create/edit/delete finished, so it may
        // not include that change: read it again instead of showing old data.
        if (mutations.current !== mutationsAtStart && attempt < maxAttempts) continue
        commit(() => data)
        break
      } catch {
        if (requestId !== latestFetch.current) return
        setError('Failed to load tasks')
        break
      }
    }
    setIsLoading(false)
  }

  useEffect(() => {
    void fetchTasks()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function addTask(data: TaskCreate): Promise<Task> {
    mutations.current++
    try {
      const task = await api.createTask(data)
      commit((prev) => [task, ...prev])
      return task
    } finally {
      mutations.current++
    }
  }

  function insertTask(task: Task) {
    // A fetch that started before this task was saved may not include it: make it re-read.
    mutations.current += 2
    commit((prev) =>
      prev.some((t) => t.id === task.id)
        ? prev.map((t) => (t.id === task.id ? task : t))
        : [task, ...prev]
    )
  }

  async function editTask(id: number, data: TaskUpdate): Promise<Task> {
    mutations.current++
    const before = tasksRef.current.find((t) => t.id === id)
    // Optimistic update
    commit((prev) => prev.map((t) => (t.id === id ? { ...t, ...data } : t)))
    try {
      const updated = await api.updateTask(id, data)
      commit((prev) => prev.map((t) => (t.id === id ? updated : t)))
      return updated
    } catch (err) {
      // Roll back only the fields this edit changed, and only if nothing else has
      // changed them since, so a concurrent successful edit is not undone.
      if (before) {
        commit((prev) =>
          prev.map((t) => {
            if (t.id !== id) return t
            const restored: Task = { ...t }
            for (const key of Object.keys(data) as (keyof TaskUpdate)[]) {
              if (t[key] === data[key]) {
                ;(restored as unknown as Record<string, unknown>)[key] = before[key]
              }
            }
            return restored
          })
        )
      }
      throw err
    } finally {
      mutations.current++
    }
  }

  async function removeTask(id: number): Promise<void> {
    mutations.current++
    const before = tasksRef.current.find((t) => t.id === id)
    // Optimistic removal
    commit((prev) => prev.filter((t) => t.id !== id))
    try {
      await api.deleteTask(id)
    } catch (err) {
      // Put the task back (unless a refetch already did)
      if (before) {
        commit((prev) =>
          prev.some((t) => t.id === id) ? prev : [...prev, before].sort((a, b) => a.id - b.id)
        )
      }
      throw err
    } finally {
      mutations.current++
    }
  }

  return (
    <TasksContext.Provider
      value={{ tasks, isLoading, error, fetchTasks, addTask, insertTask, editTask, removeTask }}
    >
      {children}
    </TasksContext.Provider>
  )
}

export function useTasks(): TasksContextValue {
  const ctx = useContext(TasksContext)
  if (!ctx) throw new Error('useTasks must be used within TasksProvider')
  return ctx
}
