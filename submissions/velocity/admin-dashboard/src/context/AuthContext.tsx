/**
 * Auth context: holds the current user + JWT, exposes login/register/logout,
 * and hydrates from /api/auth/me on load if a token is already stored.
 */
import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { api, getStoredToken, setStoredToken } from "@/lib/api"
import type { AuthResponse, User } from "@/types/auth"

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = getStoredToken()
    if (!token) {
      setIsLoading(false)
      return
    }
    api
      .get<User>("/api/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => setStoredToken(null))
      .finally(() => setIsLoading(false))
  }, [])

  async function login(email: string, password: string) {
    const res = await api.post<AuthResponse>("/api/auth/login", { email, password })
    setStoredToken(res.data.access_token)
    setUser(res.data.user)
  }

  function logout() {
    setStoredToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, isAuthenticated: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider")
  return ctx
}
