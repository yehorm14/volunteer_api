import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import type { Task, TaskFormValues } from '../types'
import * as api from '../services/api'
import { useTasks } from '../hooks/useTasks'
import { useAuth } from '../hooks/useAuth'
import TaskStatusBadge from '../components/tasks/TaskStatusBadge'
import TaskForm from '../components/tasks/TaskForm'
import AIPanel from '../components/tasks/AIPanel'
import Button from '../components/ui/Button'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import ErrorState from '../components/ui/ErrorState'
import { describeError } from '../utils/errors'

export default function TaskDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { editTask, removeTask } = useTasks()
  const { isDemo } = useAuth()

  const [task, setTask] = useState<Task | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setIsLoading(true)
    setError(null)
    api
      .getTask(Number(id))
      .then(setTask)
      .catch(() => setError('Task not found or you do not have access.'))
      .finally(() => setIsLoading(false))
  }, [id])

  async function handleSave(data: TaskFormValues) {
    if (!task) return
    setIsSaving(true)
    setSaveError(null)
    try {
      const updated = await editTask(task.id, data)
      setTask(updated)
      setIsEditing(false)
    } catch (err) {
      // Stay in the form so the user's changes are not lost.
      setSaveError(`Your changes were not saved. ${describeError(err)}`)
    } finally {
      setIsSaving(false)
    }
  }

  async function handleDelete() {
    if (!task) return
    setIsDeleting(true)
    setDeleteError(null)
    try {
      await removeTask(task.id)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      // Keep the confirmation controls so the user can retry.
      setDeleteError(`The task was not deleted. ${describeError(err)}`)
      setIsDeleting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error || !task) {
    return (
      <ErrorState
        message={error ?? 'Task not found'}
        onRetry={() => navigate(0)}
      />
    )
  }

  return (
    <div className="max-w-2xl">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-slate-400 mb-6">
        <Link to="/dashboard" className="hover:text-slate-100 transition-colors">
          Dashboard
        </Link>
        <span>/</span>
        <span className="text-slate-500 truncate max-w-[200px]">{task.title}</span>
      </div>

      {/* Task card */}
      {isEditing ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-slate-100 mb-5">Edit task</h2>
          {saveError && (
            <div role="alert" className="mb-4 px-4 py-3 bg-red-950 border border-red-800 rounded-lg text-sm text-red-300">
              {saveError}
            </div>
          )}
          <TaskForm
            initialValues={{
              title: task.title,
              description: task.description ?? undefined,
              status: task.status,
            }}
            onSubmit={handleSave}
            onCancel={() => setIsEditing(false)}
            isLoading={isSaving}
            mode="edit"
          />
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <div className="flex items-start justify-between gap-4 mb-4">
            <h1 className="text-xl font-bold text-slate-100 leading-snug">{task.title}</h1>
            <TaskStatusBadge status={task.status} />
          </div>

          {task.description ? (
            <p className="text-slate-300 text-sm leading-relaxed mb-6">{task.description}</p>
          ) : (
            <p className="text-slate-500 text-sm italic mb-6">No description</p>
          )}

          {deleteError && (
            <div role="alert" className="mb-4 px-4 py-3 bg-red-950 border border-red-800 rounded-lg text-sm text-red-300">
              {deleteError}
            </div>
          )}

          {!isDemo && (
            <div className="flex items-center gap-3 pt-4 border-t border-slate-800">
              <Button onClick={() => { setSaveError(null); setIsEditing(true) }} variant="secondary" size="sm">
                Edit
              </Button>

              {deleteConfirm ? (
                <div className="flex items-center gap-2 ml-auto">
                  <span className="text-sm text-slate-400">Delete this task?</span>
                  <Button
                    variant="danger"
                    size="sm"
                    isLoading={isDeleting}
                    onClick={handleDelete}
                  >
                    Confirm
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => { setDeleteConfirm(false); setDeleteError(null) }}
                  >
                    Cancel
                  </Button>
                </div>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setDeleteConfirm(true)}
                  className="ml-auto text-red-400 hover:text-red-300"
                >
                  Delete
                </Button>
              )}
            </div>
          )}
        </div>
      )}

      {/* AI Panel */}
      <div className="mt-6">
        {isDemo ? (
          <p role="status" className="text-sm text-slate-500">
            AI tools and editing are turned off in the read-only sample workspace.
          </p>
        ) : (
          <AIPanel taskId={task.id} taskTitle={task.title} />
        )}
      </div>
    </div>
  )
}
