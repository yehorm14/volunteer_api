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

export const DEMO_SESSION_KEY = 'demo_session'

export const API_CONFIG_ERROR: string | null =
  !envApiUrl && import.meta.env.PROD
    ? 'VITE_API_URL is not set. Set it to the backend URL and rebuild the frontend.'
    : null

if (API_CONFIG_ERROR) {
  console.error(`[config] ${API_CONFIG_ERROR}`)
}

// Set VITE_DEMO_ENABLED=true at build time when the API has DEMO_PUBLIC=1, to show the sample-workspace button.
export const DEMO_ENABLED = (import.meta.env.VITE_DEMO_ENABLED as string | undefined) === 'true'

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

// Wrapped so tests can observe the full-page redirect that jsdom cannot perform.
export const navigation = {
  toLogin: () => {
    window.location.href = '/login'
  },
}

// ── Response interceptor: handle 401 ────────────────────────

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // A 401 from the auth endpoints (wrong password) is feedback for the form, not an expired session.
    // Only a rejected request that carried a stored token ends the session and redirects.
    const url = error.config?.url ?? ''
    const isAuthRequest = url.startsWith('/auth/')
    if (error.response?.status === 401 && !isAuthRequest) {
      const hadSession = localStorage.getItem('access_token') !== null
      localStorage.removeItem('access_token')
      localStorage.removeItem(DEMO_SESSION_KEY)
      if (hadSession && window.location.pathname !== '/login') {
        navigation.toLogin()
      }
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

// Passwordless sign-in to the shared read-only sample workspace
export async function loginDemo(): Promise<TokenResponse> {
  const res = await api.post<TokenResponse>('/auth/demo')
  return res.data
}

// ── Tasks ────────────────────────────────────────────────────

// The API pages GET /tasks (default 100, max 500); fetch every page so the UI still shows all tasks.
export const TASK_PAGE_SIZE = 100

export async function getTasks(): Promise<Task[]> {
  const all: Task[] = []
  for (;;) {
    const res = await api.get<Task[]>('/tasks', {
      params: { limit: TASK_PAGE_SIZE, offset: all.length },
    })
    all.push(...res.data)
    if (res.data.length < TASK_PAGE_SIZE) return all
  }
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
