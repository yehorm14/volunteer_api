import type { MouseEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Task, TaskStatus } from '../../types'
import TaskStatusBadge from './TaskStatusBadge'
import Button from '../ui/Button'

interface TaskCardProps {
  task: Task
  onStatusChange: (id: number, status: TaskStatus) => void
  onDelete: (id: number) => void
}

const STATUS_CYCLE: Record<TaskStatus, TaskStatus> = {
  pending: 'in_progress',
  in_progress: 'completed',
  completed: 'pending',
}

const STATUS_LABEL: Record<TaskStatus, string> = {
  pending: 'Mark in progress',
  in_progress: 'Mark complete',
  completed: 'Reset to pending',
}

export default function TaskCard({ task, onStatusChange, onDelete }: TaskCardProps) {
  const navigate = useNavigate()

  function handleCardClick(e: MouseEvent<HTMLDivElement>) {
    if ((e.target as HTMLElement).closest('button')) return
    navigate(`/tasks/${task.id}`)
  }

  return (
    <div
      onClick={handleCardClick}
      className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors cursor-pointer flex flex-col gap-3 group"
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-slate-100 leading-snug line-clamp-2 group-hover:text-white transition-colors">
          {task.title}
        </h3>
        <TaskStatusBadge status={task.status} />
      </div>

      {task.description && (
        <p className="text-sm text-slate-400 line-clamp-2">{task.description}</p>
      )}

      <div className="flex items-center gap-2 mt-auto pt-3 border-t border-slate-800">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onStatusChange(task.id, STATUS_CYCLE[task.status])}
          className="text-xs"
        >
          {STATUS_LABEL[task.status]}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onDelete(task.id)}
          className="text-xs text-red-400 hover:text-red-300 ml-auto"
        >
          Delete
        </Button>
      </div>
    </div>
  )
}
