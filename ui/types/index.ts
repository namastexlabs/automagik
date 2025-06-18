// Type definitions without Supabase dependencies

// Project type
export interface Project {
    id: number
    name: string
    description?: string
    repo_url: string
    created_at: string
    updated_at?: string
    user_id: string
}

// Task type
export interface Task {
    id: number
    status: string
    prompt: string
    repo_url: string
    branch?: string
    agent?: string
    model?: string
    created_at: string
    updated_at?: string
    project_id?: number
    user_id: string
    pr_url?: string
    pr_number?: number
    commit_hash?: string
    error?: string
    has_patch?: boolean
    chat_messages?: ChatMessage[]
}

// User type
export interface User {
    id: string
    email: string
    created_at?: string
}

// Chat message interface for tasks
export interface ChatMessage {
    role: 'user' | 'assistant'
    content: string
    timestamp: string
}

// File change interface for merge view
export interface FileChange {
    filename: string
    before: string
    after: string
}

// Frontend-specific interfaces
export interface TaskWithProject extends Task {
    project?: Project
    file_changes?: FileChange[]
}

export interface ProjectWithStats extends Project {
    task_count?: number
    completed_tasks?: number
    active_tasks?: number
}

// Legacy task interface for backward compatibility
export interface LegacyTask {
    id: string;
    status: string;
    prompt: string;
    repo_url: string;
    branch: string;
    model?: string;
    commit_hash?: string;
    error?: string;
    created_at: number;
}

// API response types
export interface ApiResponse<T = any> {
    status: 'success' | 'error'
    data?: T
    error?: string
    message?: string
}

export interface TaskListResponse {
    status: 'success'
    tasks: Record<string, {
        id: number
        status: string
        created_at: string
        prompt: string
        has_patch: boolean
        project_id?: number
        repo_url: string
        agent: string
    }>
    total_tasks: number
}

export interface ProjectListResponse {
    status: 'success'
    projects: Project[]
}