import type { TaskStatus } from '../types'

export const TASK_STATUSES: readonly TaskStatus[] = ['pending', 'in_progress', 'completed']

/** True for the three statuses the API accepts. Rows from before the contract may hold anything else. */
export function isTaskStatus(value: string): value is TaskStatus {
  return (TASK_STATUSES as readonly string[]).includes(value)
}
