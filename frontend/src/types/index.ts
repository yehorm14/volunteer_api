// ── Task ────────────────────────────────────────────────────

export type TaskStatus = 'pending' | 'in_progress' | 'completed'

export interface Task {
  id: number
  title: string
  description: string | null
  status: TaskStatus
  owner_id: number
}

export interface TaskCreate {
  title: string
  description?: string
  status?: TaskStatus
}

export interface TaskUpdate {
  title?: string
  description?: string
  status?: TaskStatus
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
