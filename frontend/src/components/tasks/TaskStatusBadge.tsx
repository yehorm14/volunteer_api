import type { TaskStatus } from '../../types'
import { isTaskStatus } from '../../utils/status'

interface TaskStatusBadgeProps {
  status: string
  className?: string
}

const statusConfig: Record<TaskStatus, { label: string; className: string }> = {
  pending: {
    label: 'Pending',
    className: 'bg-amber-500/15 text-amber-400 border border-amber-500/30',
  },
  in_progress: {
    label: 'In Progress',
    className: 'bg-blue-500/15 text-blue-400 border border-blue-500/30',
  },
  completed: {
    label: 'Completed',
    className: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
  },
}

export default function TaskStatusBadge({ status, className = '' }: TaskStatusBadgeProps) {
  // Legacy rows may carry a status outside the contract; show it instead of crashing.
  const config = isTaskStatus(status)
    ? statusConfig[status]
    : {
        label: 'Unknown status',
        className: 'bg-slate-500/15 text-slate-300 border border-slate-500/30',
      }
  return (
    <span
      title={isTaskStatus(status) ? undefined : `Unrecognised status: ${status || '(empty)'}. Change it to repair this task.`}
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${config.className} ${className}`}
    >
      {config.label}
    </span>
  )
}
