'use client'
import React, { createContext, useContext, ReactNode } from 'react'

interface AuthContextType {
  user: any
  isAuthenticated: boolean
  login: (credentials: any) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const value = {
    user: { id: 'mock', name: 'Mock User' },
    isAuthenticated: true,
    login: async () => {},
    logout: () => {}
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
