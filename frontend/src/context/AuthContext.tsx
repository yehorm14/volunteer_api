import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import * as api from '../services/api'
import type { User } from '../types'

interface AuthContextValue {
  user: { email: string } | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
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

  // Restore session from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('access_token')
    if (stored) {
      const email = decodeJwtEmail(stored)
      setToken(stored)
      if (email) setUser({ email })
    }
    setIsLoading(false)
  }, [])

  async function login(email: string, password: string) {
    const { access_token } = await api.login(email, password)
    localStorage.setItem('access_token', access_token)
    setToken(access_token)
    setUser({ email })
  }

  async function register(email: string, password: string): Promise<User> {
    const newUser = await api.register({ email, password })
    // Auto-login after registration
    await login(email, password)
    return newUser
  }

  function logout() {
    localStorage.removeItem('access_token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
