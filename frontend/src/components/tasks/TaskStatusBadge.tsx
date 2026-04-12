import type { TaskStatus } from '../../types'

interface TaskStatusBadgeProps {
  status: TaskStatus
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
  const config = statusConfig[status]
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${config.className} ${className}`}
    >
      {config.label}
    </span>
  )
}
