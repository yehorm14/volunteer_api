// ── Task ────────────────────────────────────────────────────

export type TaskStatus = 'pending' | 'in_progress' | 'completed'

export interface Task {
  id: number
  title: string
  description: string | null
  // The API only accepts TaskStatus, but rows saved before the contract existed
  // may still hold another value, so reads are typed as string (see utils/status.ts).
  status: string
  owner_id: number
}

export interface TaskCreate {
  title: string
  description?: string | null
  status?: TaskStatus
}

export interface TaskUpdate {
  title?: string
  // null clears the description; leave the key out to keep it
  description?: string | null
  status?: TaskStatus
}

export interface TaskFormValues {
  title: string
  description?: string | null
  status: TaskStatus
}

// ── User ────────────────────────────────────────────────────

export interface User {
  id: number
  email: string
  is_active: boolean
  tasks: Task[]
}

export interface UserCreate {
  email: string
  password: string
}

// ── Auth ────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string
  token_type: string
}

// ── AI ──────────────────────────────────────────────────────

export interface AICategorizeResponse {
  task_id: number
  ai_suggestion: string
}

// ── API error shape ─────────────────────────────────────────

export interface ApiError {
  detail: string
}
