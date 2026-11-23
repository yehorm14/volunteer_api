import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import * as api from '../services/api'
import type { User } from '../types'

interface AuthContextValue {
  user: { email: string } | null
  token: string | null
  isLoading: boolean
  /** True in the shared read-only sample workspace: the API rejects every change. */
  isDemo: boolean
  login: (email: string, password: string) => Promise<void>
  loginAsDemo: () => Promise<void>
  register: (email: string, password: string) => Promise<User>
  logout: () => void
}

// Decode email from JWT payload without a library
function decodeJwtEmail(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1])) as { sub?: string }
    return payload.sub ?? null
  } catch {
    return null
  }
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<{ email: string } | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isDemo, setIsDemo] = useState(false)

  // Restore session from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('access_token')
    if (stored) {
      const email = decodeJwtEmail(stored)
      setToken(stored)
      setIsDemo(localStorage.getItem(api.DEMO_SESSION_KEY) === '1')
      if (email) setUser({ email })
    }
    setIsLoading(false)
  }, [])

  async function login(email: string, password: string) {
    const { access_token } = await api.login(email, password)
    localStorage.setItem('access_token', access_token)
    localStorage.removeItem(api.DEMO_SESSION_KEY)
    setToken(access_token)
    setUser({ email })
    setIsDemo(false)
  }

  async function loginAsDemo() {
    const { access_token } = await api.loginDemo()
    localStorage.setItem('access_token', access_token)
    localStorage.setItem(api.DEMO_SESSION_KEY, '1')
    setToken(access_token)
    setUser({ email: decodeJwtEmail(access_token) ?? 'Sample workspace' })
    setIsDemo(true)
  }

  async function register(email: string, password: string): Promise<User> {
    const newUser = await api.register({ email, password })
    // Auto-login after registration
    await login(email, password)
    return newUser
  }

  function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem(api.DEMO_SESSION_KEY)
    setToken(null)
    setUser(null)
    setIsDemo(false)
  }

  return (
    <AuthContext.Provider value={{ user, token, isLoading, isDemo, login, loginAsDemo, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
