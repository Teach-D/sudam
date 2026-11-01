'use client'

import { create } from 'zustand'
import { type AuthUser, clearAuth, loadAuth, saveAuth } from '@/lib/auth'

interface AuthState {
  user: AuthUser | null
  hydrated: boolean
  setUser: (user: AuthUser) => void
  logout: () => void
  hydrate: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  hydrated: false,

  setUser: (user) => {
    saveAuth(user)
    set({ user })
  },

  logout: () => {
    clearAuth()
    set({ user: null })
  },

  hydrate: () => {
    const user = loadAuth()
    set({ user, hydrated: true })
  },
}))
