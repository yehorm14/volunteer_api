import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import * as api from '../services/api'
import type { Task, TaskCreate, TaskUpdate } from '../types'

interface TasksContextValue {
  tasks: Task[]
  isLoading: boolean
  error: string | null
  fetchTasks: () => Promise<void>
  addTask: (data: TaskCreate) => Promise<Task>
  editTask: (id: number, data: TaskUpdate) => Promise<Task>
  removeTask: (id: number) => Promise<void>
}

const TasksContext = createContext<TasksContextValue | null>(null)

export function TasksProvider({ children }: { children: ReactNode }) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function fetchTasks() {
    setIsLoading(true)
    setError(null)
    try {
      const data = await api.getTasks()
      setTasks(data)
    } catch {
      setError('Failed to load tasks')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void fetchTasks()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function addTask(data: TaskCreate): Promise<Task> {
    const task = await api.createTask(data)
    setTasks((prev) => [task, ...prev])
    return task
  }

  async function editTask(id: number, data: TaskUpdate): Promise<Task> {
    const previous = tasks.find((t) => t.id === id)
    // Optimistic update
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, ...data } : t))
    )
    try {
      const updated = await api.updateTask(id, data)
      setTasks((prev) => prev.map((t) => (t.id === id ? updated : t)))
      return updated
    } catch (err) {
      // Rollback on failure
      if (previous) {
        setTasks((prev) => prev.map((t) => (t.id === id ? previous : t)))
      }
      throw err
    }
  }

  async function removeTask(id: number): Promise<void> {
    const previous = tasks.find((t) => t.id === id)
    // Optimistic removal
    setTasks((prev) => prev.filter((t) => t.id !== id))
    try {
      await api.deleteTask(id)
    } catch (err) {
      // Rollback on failure
      if (previous) {
        setTasks((prev) => [...prev, previous].sort((a, b) => a.id - b.id))
      }
      throw err
    }
  }

  return (
    <TasksContext.Provider
      value={{ tasks, isLoading, error, fetchTasks, addTask, editTask, removeTask }}
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
