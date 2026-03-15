import { create } from 'zustand'
import { loginUser } from '../api'

interface AuthState {
  token: string | null
  refreshToken: string | null
  username: string | null
  login: (credentials: { username: string; password: string }) => Promise<void>
  logout: () => void
  setTokens: (access: string, refresh: string) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: sessionStorage.getItem('access_token'),
  refreshToken: sessionStorage.getItem('refresh_token'),
  username: sessionStorage.getItem('username'),

  login: async (credentials) => {
    const data = await loginUser(credentials)
    sessionStorage.setItem('access_token', data.access)
    sessionStorage.setItem('refresh_token', data.refresh)
    sessionStorage.setItem('username', credentials.username)
    set({ token: data.access, refreshToken: data.refresh, username: credentials.username })
  },

  logout: () => {
    sessionStorage.removeItem('access_token')
    sessionStorage.removeItem('refresh_token')
    sessionStorage.removeItem('username')
    set({ token: null, refreshToken: null, username: null })
  },

  setTokens: (access, refresh) => {
    sessionStorage.setItem('access_token', access)
    sessionStorage.setItem('refresh_token', refresh)
    set({ token: access, refreshToken: refresh })
  },
}))
