import axios, { type AxiosError } from 'axios'
import type {
  Task,
  TaskCreate,
  TaskUpdate,
  User,
  UserCreate,
  TokenResponse,
  AICategorizeResponse,
} from '../types'

// ── Instance ────────────────────────────────────────────────

// VITE_API_URL is required for production builds. In dev, /api is proxied to the backend by Vite.
// A production build without it would send API calls to the host's SPA rewrite, so it is reported as a config error.
const envApiUrl = (import.meta.env.VITE_API_URL as string | undefined)?.trim().replace(/\/+$/, '')

export const API_CONFIG_ERROR: string | null =
  !envApiUrl && import.meta.env.PROD
    ? 'VITE_API_URL is not set. Set it to the backend URL and rebuild the frontend.'
    : null

if (API_CONFIG_ERROR) {
  console.error(`[config] ${API_CONFIG_ERROR}`)
}

const API_BASE_URL = envApiUrl || '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// ── Request interceptor: inject token ───────────────────────

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor: handle 401 ────────────────────────

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ── Auth ────────────────────────────────────────────────────

export async function register(data: UserCreate): Promise<User> {
  const res = await api.post<User>('/auth/register', data)
  return res.data
}

// FastAPI's OAuth2PasswordRequestForm requires form-encoded data, not JSON
export async function login(email: string, password: string): Promise<TokenResponse> {
  const form = new URLSearchParams()
  form.append('username', email)
  form.append('password', password)
  const res = await api.post<TokenResponse>('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return res.data
}

// ── Tasks ────────────────────────────────────────────────────

export async function getTasks(): Promise<Task[]> {
  const res = await api.get<Task[]>('/tasks')
  return res.data
}

export async function getTask(id: number): Promise<Task> {
  const res = await api.get<Task>(`/tasks/${id}`)
  return res.data
}

export async function createTask(data: TaskCreate): Promise<Task> {
  const res = await api.post<Task>('/tasks', data)
  return res.data
}

export async function updateTask(id: number, data: TaskUpdate): Promise<Task> {
  const res = await api.patch<Task>(`/tasks/${id}`, data)
  return res.data
}

export async function deleteTask(id: number): Promise<void> {
  await api.delete(`/tasks/${id}`)
}

// ── AI ──────────────────────────────────────────────────────

export async function categorizeTask(id: number): Promise<AICategorizeResponse> {
  const res = await api.post<AICategorizeResponse>(`/tasks/${id}/ai-categorize`)
  return res.data
}

// Notes go in the JSON body so they never appear in URLs or server logs
export async function extractTaskFromNotes(notes: string): Promise<Task> {
  const res = await api.post<Task>('/tasks/extract', { notes })
  return res.data
}
