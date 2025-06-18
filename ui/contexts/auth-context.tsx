'use client'

import React, { createContext, useContext, useState } from 'react'

interface SimpleUser {
    id: string
    email: string
}

interface AuthContextType {
    user: SimpleUser | null
    session: { api_key: string } | null
    loading: boolean
    signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function useAuth() {
    const context = useContext(AuthContext)
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}

interface AuthProviderProps {
    children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
    // For now, we'll use a hardcoded user since we're using API key auth
    const [user] = useState<SimpleUser>({
        id: 'api-user-1',
        email: 'api@namastex.ai'
    })
    const [session] = useState({ api_key: 'namastex888' })
    const [loading] = useState(false)

    const signOut = async () => {
        // In a real app, you might clear local storage or redirect
        window.location.href = '/'
    }

    const value = {
        user,
        session,
        loading,
        signOut,
    }

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}