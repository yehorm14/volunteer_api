import { useState, type FormEvent } from 'react'
import type { TaskCreate, TaskStatus } from '../../types'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Textarea from '../ui/Textarea'

interface TaskFormProps {
  initialValues?: Partial<TaskCreate>
  onSubmit: (data: TaskCreate) => Promise<void>
  onCancel?: () => void
  isLoading?: boolean
  mode?: 'create' | 'edit'
}

const STATUS_OPTIONS: { value: TaskStatus; label: string }[] = [
  { value: 'pending', label: 'Pending' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed', label: 'Completed' },
]

export default function TaskForm({
  initialValues = {},
  onSubmit,
  onCancel,
  isLoading = false,
  mode = 'create',
}: TaskFormProps) {
  const [title, setTitle] = useState(initialValues.title ?? '')
  const [description, setDescription] = useState(initialValues.description ?? '')
  const [status, setStatus] = useState<TaskStatus>(initialValues.status ?? 'pending')
  const [titleError, setTitleError] = useState('')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!title.trim()) {
      setTitleError('Title is required')
      return
    }
    setTitleError('')
    await onSubmit({
      title: title.trim(),
      description: description.trim() || undefined,
      status,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <Input
        label="Title"
        value={title}
        onChange={(e) => {
          setTitle(e.target.value)
          if (e.target.value.trim()) setTitleError('')
        }}
        placeholder="What needs to be done?"
        error={titleError}
        autoFocus
      />
      <Textarea
        label="Description"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Optional details..."
        rows={3}
      />
      {mode === 'edit' && (
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-slate-300">Status</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as TaskStatus)}
            className="bg-slate-800 border border-slate-700 text-slate-100 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      )}
      <div className="flex gap-3 pt-2">
        <Button type="submit" isLoading={isLoading} className="flex-1">
          {mode === 'create' ? 'Create task' : 'Save changes'}
        </Button>
        {onCancel && (
          <Button type="button" variant="secondary" onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  )
}
