import { useCallback, useRef, useState, type MouseEvent } from 'react'
import type { TaskStatus, TaskFormValues } from '../types'
import { useTasks } from '../hooks/useTasks'
import { useAuth } from '../hooks/useAuth'
import TaskCard from '../components/tasks/TaskCard'
import TaskForm from '../components/tasks/TaskForm'
import Modal from '../components/ui/Modal'
import Button from '../components/ui/Button'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { describeError } from '../utils/errors'

type FilterStatus = TaskStatus | 'all'

const FILTER_TABS: { value: FilterStatus; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed', label: 'Completed' },
]

const statsConfig = [
  { key: 'pending' as const, label: 'Pending', colorClass: 'text-amber-400' },
  { key: 'in_progress' as const, label: 'In Progress', colorClass: 'text-blue-400' },
  { key: 'completed' as const, label: 'Completed', colorClass: 'text-emerald-400' },
]

export default function Dashboard() {
  const { isDemo } = useAuth()
  const { tasks, isLoading, error, fetchTasks, addTask, editTask, removeTask } = useTasks()
  const [filter, setFilter] = useState<FilterStatus>('all')
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const createTrigger = useRef<HTMLButtonElement | null>(null)
  const headerCreateButton = useRef<HTMLButtonElement | null>(null)
  // Failure of a status change or delete; the list has already been restored when this shows.
  const [actionError, setActionError] = useState<string | null>(null)

  const counts: Record<TaskStatus, number> = {
    pending: tasks.filter((t) => t.status === 'pending').length,
    in_progress: tasks.filter((t) => t.status === 'in_progress').length,
    completed: tasks.filter((t) => t.status === 'completed').length,
  }

  const filtered = filter === 'all' ? tasks : tasks.filter((t) => t.status === filter)

  function openCreate(event: MouseEvent<HTMLButtonElement>) {
    createTrigger.current = event.currentTarget
    setCreateError(null)
    setIsCreateOpen(true)
  }

  const restoreCreateFocus = useCallback(() => {
    const trigger = createTrigger.current
    const target = trigger?.isConnected ? trigger : headerCreateButton.current
    target?.focus({ preventScroll: true })
  }, [])

  async function handleCreate(data: TaskFormValues) {
    setCreating(true)
    setCreateError(null)
    try {
      await addTask({ ...data, description: data.description ?? undefined })
      setIsCreateOpen(false)
    } catch (err) {
      // Keep the dialog open with what the user typed, and say why it failed.
      setCreateError(`The task was not created. ${describeError(err)}`)
    } finally {
      setCreating(false)
    }
  }

  function titleOf(id: number) {
    return tasks.find((t) => t.id === id)?.title ?? 'the task'
  }

  async function handleStatusChange(id: number, status: TaskStatus) {
    setActionError(null)
    const title = titleOf(id)
    try {
      await editTask(id, { status })
    } catch (err) {
      setActionError(`Could not update "${title}". It was restored to its previous status. ${describeError(err)}`)
    }
  }

  async function handleDelete(id: number) {
    setActionError(null)
    const title = titleOf(id)
    try {
      await removeTask(id)
    } catch (err) {
      setActionError(`Could not delete "${title}". It is back in your list. ${describeError(err)}`)
    }
  }

  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">My Tasks</h1>
          <p className="text-slate-400 text-sm mt-1">
            {tasks.length} task{tasks.length !== 1 ? 's' : ''} total
          </p>
        </div>
        {!isDemo && <Button ref={headerCreateButton} onClick={openCreate}>+ New task</Button>}
      </div>

      {isDemo && (
        <div
          role="status"
          className="mb-6 px-4 py-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-sm text-amber-300"
        >
          You are viewing a read-only sample workspace with made-up tasks. Changes and AI tools are
          turned off. Sign out and create an account to manage your own tasks.
        </div>
      )}

      {actionError && (
        <div
          role="alert"
          className="mb-6 flex items-start justify-between gap-4 px-4 py-3 bg-red-950 border border-red-800 rounded-lg text-sm text-red-300"
        >
          <span>{actionError}</span>
          <button
            type="button"
            onClick={() => setActionError(null)}
            className="text-red-300 hover:text-white"
            aria-label="Dismiss error"
          >
            &times;
          </button>
        </div>
      )}

      {/* Stats row */}
      {tasks.length > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-8">
          {statsConfig.map(({ key, label, colorClass }) => (
            <div key={key} className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <p className="text-sm text-slate-400">{label}</p>
              <p className={`text-2xl font-bold mt-1 ${colorClass}`}>{counts[key]}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filter tabs */}
      {tasks.length > 0 && (
        <div className="flex gap-2 flex-wrap mb-6">
          {FILTER_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setFilter(tab.value)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                filter === tab.value
                  ? 'bg-brand-600 text-white'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <LoadingSpinner size="lg" />
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={fetchTasks} />
      ) : tasks.length === 0 ? (
        <EmptyState
          title="No tasks yet"
          description="Create your first task to get started tracking your volunteer work."
          action={isDemo ? undefined : <Button onClick={openCreate}>+ New task</Button>}
          icon={
            <svg
              width="48"
              height="48"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 0 2-2h2a2 2 0 0 0 2 2" />
            </svg>
          }
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          title={`No ${filter.replace('_', ' ')} tasks`}
          description="Try a different filter or create a new task."
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onStatusChange={handleStatusChange}
              onDelete={handleDelete}
              readOnly={isDemo}
            />
          ))}
        </div>
      )}

      {isCreateOpen && (
        <Modal onClose={() => setIsCreateOpen(false)} restoreFocus={restoreCreateFocus} title="New task">
          {createError && (
            <div role="alert" className="mb-4 px-4 py-3 bg-red-950 border border-red-800 rounded-lg text-sm text-red-300">
              {createError}
            </div>
          )}
          <TaskForm
            onSubmit={handleCreate}
            onCancel={() => setIsCreateOpen(false)}
            isLoading={creating}
            mode="create"
          />
        </Modal>
      )}
    </>
  )
}
