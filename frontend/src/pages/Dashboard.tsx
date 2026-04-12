import { useState } from 'react'
import type { TaskStatus, TaskCreate } from '../types'
import { useTasks } from '../hooks/useTasks'
import TaskCard from '../components/tasks/TaskCard'
import TaskForm from '../components/tasks/TaskForm'
import Modal from '../components/ui/Modal'
import Button from '../components/ui/Button'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import LoadingSpinner from '../components/ui/LoadingSpinner'

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
  const { tasks, isLoading, error, fetchTasks, addTask, editTask, removeTask } = useTasks()
  const [filter, setFilter] = useState<FilterStatus>('all')
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [creating, setCreating] = useState(false)

  const counts: Record<TaskStatus, number> = {
    pending: tasks.filter((t) => t.status === 'pending').length,
    in_progress: tasks.filter((t) => t.status === 'in_progress').length,
    completed: tasks.filter((t) => t.status === 'completed').length,
  }

  const filtered = filter === 'all' ? tasks : tasks.filter((t) => t.status === filter)

  async function handleCreate(data: TaskCreate) {
    setCreating(true)
    try {
      await addTask(data)
      setIsCreateOpen(false)
    } finally {
      setCreating(false)
    }
  }

  async function handleStatusChange(id: number, status: TaskStatus) {
    await editTask(id, { status })
  }

  async function handleDelete(id: number) {
    await removeTask(id)
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
        <Button onClick={() => setIsCreateOpen(true)}>+ New task</Button>
      </div>

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
          action={<Button onClick={() => setIsCreateOpen(true)}>+ New task</Button>}
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
            />
          ))}
        </div>
      )}

      {/* Create modal */}
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="New task">
        <TaskForm
          onSubmit={handleCreate}
          onCancel={() => setIsCreateOpen(false)}
          isLoading={creating}
          mode="create"
        />
      </Modal>
    </>
  )
}
