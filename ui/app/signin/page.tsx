'use client'

import { Auth } from '@supabase/auth-ui-react'
import { ThemeSupa } from '@supabase/auth-ui-shared'
import { getSupabase } from '@/lib/supabase'
import { useAuth } from '@/contexts/auth-context'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Code2 } from 'lucide-react'

export default function SignIn() {
    const { user, loading } = useAuth()
    const router = useRouter()

    useEffect(() => {
        if (user && !loading) {
            router.push('/')
        }
    }, [user, loading, router])

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900"></div>
            </div>
        )
    }

    if (user) {
        return null // Will redirect
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-6">
            <div className="w-full max-w-md">
                {/* Header */}
                <div className="text-center mb-8">
                    <div className="w-12 h-12 bg-black rounded-lg flex items-center justify-center mx-auto mb-4">
                        <Code2 className="w-6 h-6 text-white" />
                    </div>
                    <h1 className="text-2xl font-bold text-slate-900 mb-2">
                        Welcome to AI Code Automation
                    </h1>
                    <p className="text-slate-600">
                        Sign in to start automating your code with Claude Code & Codex CLI
                    </p>
                </div>

                {/* Auth Card */}
                <Card>
                    <CardHeader>
                        <CardTitle>Sign In</CardTitle>
                        <CardDescription>
                            Sign in to your account to continue
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Auth
                            supabaseClient={getSupabase()}
                            appearance={{
                                theme: ThemeSupa,
                                variables: {
                                    default: {
                                        colors: {
                                            brand: '#0f172a',
                                            brandAccent: '#1e293b',
                                        },
                                    },
                                },
                                className: {
                                    button: 'w-full px-4 py-2 rounded-md font-medium',
                                    input: 'w-full px-3 py-2 border border-slate-300 rounded-md',
                                }
                            }}
                            providers={['github']}
                            redirectTo={typeof window !== 'undefined' ? `${window.location.origin}/` : '/'}
                            onlyThirdPartyProviders={false}
                        />
                    </CardContent>
                </Card>

                {/* Footer */}
                <div className="text-center mt-6 text-sm text-slate-600">
                    <p>
                        By signing in, you agree to our terms of service and privacy policy.
                    </p>
                </div>
            </div>
        </div>
    )
} 