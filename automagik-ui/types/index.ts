// File change interface for merge view
export interface FileChange {
    filename: string;
    before: string;
    after: string;
    path: string;
    status: "added" | "modified" | "deleted";
    additions: number;
    deletions: number;
    diff?: string;
}

// Chat message interface for workflows
export interface ChatMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: string;
}

// API response types
export interface ApiResponse<T = any> {
    status: 'success' | 'error';
    data?: T;
    error?: string;
    message?: string;
}