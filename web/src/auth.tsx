import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { api, getToken, setToken, setUnauthorizedHandler, type TokenResponse, type User } from './api'
import { AuthContext, type AuthState } from './useAuth'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(() => getToken() !== null)

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(logout)
    if (!getToken()) return
    api
      .me()
      .then(setUser)
      .catch(logout)
      .finally(() => setLoading(false))
  }, [logout])

  const accept = (res: TokenResponse) => {
    setToken(res.access_token)
    setUser(res.user)
  }

  const value: AuthState = {
    user,
    loading,
    login: async (email, password) => accept(await api.login(email, password)),
    register: async (name, email, password) => accept(await api.register(name, email, password)),
    logout,
    markProfileComplete: () => setUser((u) => (u ? { ...u, has_profile: true } : u)),
    acceptSession: accept,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
