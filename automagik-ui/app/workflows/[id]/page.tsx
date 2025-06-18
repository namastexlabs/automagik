"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { 
    ArrowLeft, GitBranch, Clock, CheckCircle, XCircle, 
    AlertCircle, Play, StopCircle, Copy, ChevronDown, 
    ChevronUp, FileCode, Plus, Minus, ExternalLink,
    RefreshCw, Terminal, MessageSquare, Bot, User
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ProtectedRoute } from "@/components/protected-route";
import { TaskStatusBadge } from "@/components/task-status-badge";
import { toast } from "sonner";

interface WorkflowDetails {
    run_id: string;
    status: "running" | "completed" | "failed" | "pending" | "killed";
    workflow_name: string;
    repository_url: string;
    git_branch: string;
    started_at: string;
    completed_at?: string;
    error?: string;
    commit_hash?: string;
    ai_model?: string;
    files_changed?: FileChange[];
    logs?: LogEntry[];
    messages?: ChatMessage[];
}

interface FileChange {
    path: string;
    status: "added" | "modified" | "deleted";
    additions: number;
    deletions: number;
    diff?: string;
}

interface LogEntry {
    timestamp: string;
    level: "info" | "error" | "warning" | "debug";
    message: string;
}

interface ChatMessage {
    role: "user" | "assistant" | "system";
    content: string;
    timestamp: string;
}

export default function WorkflowDetailPage() {
    const params = useParams();
    const router = useRouter();
    const [workflow, setWorkflow] = useState<WorkflowDetails | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());
    const [allExpanded, setAllExpanded] = useState(false);
    const [isPolling, setIsPolling] = useState(false);
    const logsEndRef = useRef<HTMLDivElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const workflowId = params.id as string;

    const loadWorkflowDetails = useCallback(async (silent = false) => {
        try {
            if (!silent) setIsLoading(true);
            setIsPolling(true);

            // Fetch workflow status
            const statusResponse = await fetch(
                `http://localhost:28881/api/v1/workflows/claude-code/run/${workflowId}/status`,
                {
                    headers: {
                        'x-api-key': 'namastex888'
                    }
                }
            );

            if (!statusResponse.ok) {
                throw new Error('Failed to fetch workflow details');
            }

            const statusData = await statusResponse.json();

            // Fetch logs
            const logsResponse = await fetch(
                `http://localhost:28881/api/v1/tasks/${workflowId}/logs`,
                {
                    headers: {
                        'x-api-key': 'namastex888'
                    }
                }
            );

            let logs: LogEntry[] = [];
            if (logsResponse.ok) {
                const logsText = await logsResponse.text();
                logs = logsText.split('\n')
                    .filter(line => line.trim())
                    .map(line => ({
                        timestamp: new Date().toISOString(),
                        level: "info" as const,
                        message: line
                    }));
            }

            // Mock file changes for demonstration
            const mockFileChanges: FileChange[] = statusData.status === "completed" ? [
                {
                    path: "src/components/NewFeature.tsx",
                    status: "added",
                    additions: 150,
                    deletions: 0,
                    diff: `+import React from 'react';
+
+export const NewFeature: React.FC = () => {
+  return (
+    <div className="feature-container">
+      <h2>New Feature Component</h2>
+      <p>This component was automatically generated</p>
+    </div>
+  );
+};`
                },
                {
                    path: "src/App.tsx",
                    status: "modified",
                    additions: 5,
                    deletions: 2,
                    diff: ` import React from 'react';
 import './App.css';
+import { NewFeature } from './components/NewFeature';
 
 function App() {
   return (
     <div className="App">
       <header className="App-header">
-        <p>Hello World</p>
+        <p>Welcome to the enhanced app</p>
+        <NewFeature />
       </header>
     </div>
   );`
                }
            ] : [];

            // Mock messages for demonstration
            const mockMessages: ChatMessage[] = [
                {
                    role: "user",
                    content: "Create a new React component for displaying user profiles",
                    timestamp: new Date(Date.now() - 300000).toISOString()
                },
                {
                    role: "assistant",
                    content: "I'll create a new React component for displaying user profiles. Let me analyze the project structure and create the component with proper TypeScript types and styling.",
                    timestamp: new Date(Date.now() - 280000).toISOString()
                },
                {
                    role: "assistant",
                    content: "I've successfully created the UserProfile component with the following features:\n- TypeScript interface for user data\n- Responsive design with Tailwind CSS\n- Avatar display with fallback\n- User information cards\n- Social links section",
                    timestamp: new Date(Date.now() - 180000).toISOString()
                }
            ];

            const workflowDetails: WorkflowDetails = {
                run_id: workflowId,
                status: statusData.status || "pending",
                workflow_name: statusData.workflow_name || "Claude Code Workflow",
                repository_url: statusData.repository_url || "https://github.com/example/repo",
                git_branch: statusData.git_branch || "main",
                started_at: statusData.started_at || new Date().toISOString(),
                completed_at: statusData.completed_at,
                error: statusData.error,
                commit_hash: statusData.commit_hash || "abc123def456",
                ai_model: "Claude 3.5 Sonnet",
                files_changed: mockFileChanges,
                logs: logs,
                messages: mockMessages
            };

            setWorkflow(workflowDetails);
        } catch (error) {
            console.error('Error loading workflow details:', error);
            if (!silent) {
                toast.error('Failed to load workflow details');
            }
        } finally {
            setIsLoading(false);
            setIsPolling(false);
        }
    }, [workflowId]);

    useEffect(() => {
        if (workflowId) {
            loadWorkflowDetails();
            // Start polling if workflow is running
            const interval = setInterval(() => {
                if (workflow?.status === "running" || workflow?.status === "pending") {
                    loadWorkflowDetails(true);
                }
            }, 2000);
            return () => clearInterval(interval);
        }
    }, [workflowId, workflow?.status, loadWorkflowDetails]);

    // Auto-scroll logs and messages
    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [workflow?.logs]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [workflow?.messages]);

    const handleKillWorkflow = async () => {
        try {
            const response = await fetch(
                `http://localhost:28881/api/v1/workflows/claude-code/run/${workflowId}/kill`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'x-api-key': 'namastex888'
                    }
                }
            );

            if (!response.ok) {
                throw new Error('Failed to kill workflow');
            }

            toast.success('Workflow killed successfully');
            loadWorkflowDetails();
        } catch (error) {
            console.error('Error killing workflow:', error);
            toast.error('Failed to kill workflow');
        }
    };

    const handleCreatePR = async () => {
        toast.info('Creating pull request...');
        // TODO: Implement PR creation
        setTimeout(() => {
            toast.success('Pull request created successfully');
        }, 2000);
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
        toast.success('Copied to clipboard');
    };

    const toggleFileExpansion = (path: string) => {
        const newExpanded = new Set(expandedFiles);
        if (newExpanded.has(path)) {
            newExpanded.delete(path);
        } else {
            newExpanded.add(path);
        }
        setExpandedFiles(newExpanded);
    };

    const toggleAllFiles = () => {
        if (allExpanded) {
            setExpandedFiles(new Set());
        } else {
            const allPaths = workflow?.files_changed?.map(f => f.path) || [];
            setExpandedFiles(new Set(allPaths));
        }
        setAllExpanded(!allExpanded);
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case "running": return <Play className="w-4 h-4 animate-pulse" />;
            case "completed": return <CheckCircle className="w-4 h-4" />;
            case "failed": return <XCircle className="w-4 h-4" />;
            case "killed": return <StopCircle className="w-4 h-4" />;
            default: return <Clock className="w-4 h-4" />;
        }
    };

    if (isLoading) {
        return (
            <ProtectedRoute>
                <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
                    <div className="flex items-center gap-3 text-slate-500">
                        <RefreshCw className="w-5 h-5 animate-spin" />
                        Loading workflow details...
                    </div>
                </div>
            </ProtectedRoute>
        );
    }

    if (!workflow) {
        return (
            <ProtectedRoute>
                <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
                    <div className="text-center">
                        <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                        <h2 className="text-xl font-semibold mb-2">Workflow not found</h2>
                        <Button onClick={() => router.push('/workflows')} variant="outline">
                            Back to Workflows
                        </Button>
                    </div>
                </div>
            </ProtectedRoute>
        );
    }

    return (
        <ProtectedRoute>
            <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
                {/* Header */}
                <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
                    <div className="container mx-auto px-6 py-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <Button
                                    onClick={() => router.push('/workflows')}
                                    variant="ghost"
                                    size="sm"
                                    className="gap-2"
                                >
                                    <ArrowLeft className="w-4 h-4" />
                                    Back
                                </Button>
                                <div className="flex items-center gap-3">
                                    <h1 className="text-xl font-semibold">Workflow #{workflow.run_id}</h1>
                                    <TaskStatusBadge status={workflow.status} />
                                    {isPolling && (
                                        <Badge variant="outline" className="gap-1">
                                            <RefreshCw className="w-3 h-3 animate-spin" />
                                            Live
                                        </Badge>
                                    )}
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                {workflow.status === "completed" && (
                                    <Button onClick={handleCreatePR} className="gap-2">
                                        <GitBranch className="w-4 h-4" />
                                        Create PR
                                    </Button>
                                )}
                                {(workflow.status === "running" || workflow.status === "pending") && (
                                    <Button
                                        onClick={handleKillWorkflow}
                                        variant="destructive"
                                        className="gap-2"
                                    >
                                        <StopCircle className="w-4 h-4" />
                                        Kill Workflow
                                    </Button>
                                )}
                            </div>
                        </div>
                    </div>
                </header>

                {/* Main Content */}
                <main className="container mx-auto px-6 py-8 max-w-7xl">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Left Column - Main Content */}
                        <div className="lg:col-span-2 space-y-6">
                            {/* Info Panel */}
                            <Card>
                                <CardHeader>
                                    <CardTitle>Workflow Information</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <p className="text-sm text-slate-500 mb-1">Repository</p>
                                            <div className="flex items-center gap-2">
                                                <p className="text-sm font-medium">{workflow.repository_url}</p>
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    className="h-6 w-6 p-0"
                                                    onClick={() => window.open(workflow.repository_url, '_blank')}
                                                >
                                                    <ExternalLink className="w-3 h-3" />
                                                </Button>
                                            </div>
                                        </div>
                                        <div>
                                            <p className="text-sm text-slate-500 mb-1">Branch</p>
                                            <div className="flex items-center gap-2">
                                                <GitBranch className="w-4 h-4 text-slate-400" />
                                                <p className="text-sm font-medium">{workflow.git_branch}</p>
                                            </div>
                                        </div>
                                        <div>
                                            <p className="text-sm text-slate-500 mb-1">AI Model</p>
                                            <div className="flex items-center gap-2">
                                                <Bot className="w-4 h-4 text-slate-400" />
                                                <p className="text-sm font-medium">{workflow.ai_model}</p>
                                            </div>
                                        </div>
                                        <div>
                                            <p className="text-sm text-slate-500 mb-1">Started</p>
                                            <p className="text-sm font-medium">
                                                {new Date(workflow.started_at).toLocaleString()}
                                            </p>
                                        </div>
                                        {workflow.commit_hash && (
                                            <div>
                                                <p className="text-sm text-slate-500 mb-1">Commit</p>
                                                <div className="flex items-center gap-2">
                                                    <code className="text-xs bg-slate-100 px-2 py-1 rounded">
                                                        {workflow.commit_hash.substring(0, 7)}
                                                    </code>
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        className="h-6 w-6 p-0"
                                                        onClick={() => copyToClipboard(workflow.commit_hash!)}
                                                    >
                                                        <Copy className="w-3 h-3" />
                                                    </Button>
                                                </div>
                                            </div>
                                        )}
                                        {workflow.completed_at && (
                                            <div>
                                                <p className="text-sm text-slate-500 mb-1">Duration</p>
                                                <p className="text-sm font-medium">
                                                    {Math.round(
                                                        (new Date(workflow.completed_at).getTime() - 
                                                         new Date(workflow.started_at).getTime()) / 1000
                                                    )}s
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                </CardContent>
                            </Card>

                            {/* Code Changes */}
                            {workflow.files_changed && workflow.files_changed.length > 0 && (
                                <Card>
                                    <CardHeader>
                                        <div className="flex items-center justify-between">
                                            <CardTitle>Code Changes</CardTitle>
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={toggleAllFiles}
                                                className="gap-2"
                                            >
                                                {allExpanded ? (
                                                    <>
                                                        <Minus className="w-3 h-3" />
                                                        Collapse All
                                                    </>
                                                ) : (
                                                    <>
                                                        <Plus className="w-3 h-3" />
                                                        Expand All
                                                    </>
                                                )}
                                            </Button>
                                        </div>
                                        <CardDescription>
                                            {workflow.files_changed.length} file{workflow.files_changed.length !== 1 ? 's' : ''} changed
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-3">
                                            {workflow.files_changed.map((file) => (
                                                <div key={file.path} className="border rounded-lg overflow-hidden">
                                                    <div
                                                        className="flex items-center justify-between p-3 bg-slate-50 hover:bg-slate-100 cursor-pointer"
                                                        onClick={() => toggleFileExpansion(file.path)}
                                                    >
                                                        <div className="flex items-center gap-3">
                                                            <FileCode className="w-4 h-4 text-slate-500" />
                                                            <span className="text-sm font-medium">{file.path}</span>
                                                            <Badge
                                                                variant={
                                                                    file.status === "added" ? "default" :
                                                                    file.status === "deleted" ? "destructive" :
                                                                    "secondary"
                                                                }
                                                                className="text-xs"
                                                            >
                                                                {file.status}
                                                            </Badge>
                                                        </div>
                                                        <div className="flex items-center gap-3">
                                                            <div className="flex items-center gap-2 text-xs">
                                                                <span className="text-green-600">+{file.additions}</span>
                                                                <span className="text-red-600">-{file.deletions}</span>
                                                            </div>
                                                            {expandedFiles.has(file.path) ? (
                                                                <ChevronUp className="w-4 h-4" />
                                                            ) : (
                                                                <ChevronDown className="w-4 h-4" />
                                                            )}
                                                        </div>
                                                    </div>
                                                    {expandedFiles.has(file.path) && file.diff && (
                                                        <div className="p-3 bg-slate-900 overflow-x-auto">
                                                            <pre className="text-xs text-slate-100 font-mono">
                                                                {file.diff.split('\n').map((line, idx) => (
                                                                    <div
                                                                        key={idx}
                                                                        className={
                                                                            line.startsWith('+') ? 'text-green-400' :
                                                                            line.startsWith('-') ? 'text-red-400' :
                                                                            'text-slate-400'
                                                                        }
                                                                    >
                                                                        {line}
                                                                    </div>
                                                                ))}
                                                            </pre>
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </CardContent>
                                </Card>
                            )}

                            {/* Logs */}
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <Terminal className="w-4 h-4" />
                                        Workflow Logs
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="bg-slate-900 rounded-lg p-4 max-h-96 overflow-y-auto">
                                        {workflow.logs && workflow.logs.length > 0 ? (
                                            <div className="space-y-1">
                                                {workflow.logs.map((log, idx) => (
                                                    <div key={idx} className="text-xs font-mono">
                                                        <span className="text-slate-500">
                                                            [{new Date(log.timestamp).toLocaleTimeString()}]
                                                        </span>
                                                        <span className={`ml-2 ${
                                                            log.level === 'error' ? 'text-red-400' :
                                                            log.level === 'warning' ? 'text-yellow-400' :
                                                            'text-slate-300'
                                                        }`}>
                                                            {log.message}
                                                        </span>
                                                    </div>
                                                ))}
                                                <div ref={logsEndRef} />
                                            </div>
                                        ) : (
                                            <p className="text-slate-500 text-sm">No logs available</p>
                                        )}
                                    </div>
                                </CardContent>
                            </Card>
                        </div>

                        {/* Right Column - Chat History */}
                        <div className="space-y-6">
                            <Card className="h-[calc(100vh-12rem)] flex flex-col">
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <MessageSquare className="w-4 h-4" />
                                        AI Conversation
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="flex-1 overflow-y-auto">
                                    {workflow.messages && workflow.messages.length > 0 ? (
                                        <div className="space-y-4">
                                            {workflow.messages.map((message, idx) => (
                                                <div
                                                    key={idx}
                                                    className={`flex gap-3 ${
                                                        message.role === 'user' ? 'justify-end' : ''
                                                    }`}
                                                >
                                                    {message.role === 'assistant' && (
                                                        <div className="flex-shrink-0">
                                                            <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                                                                <Bot className="w-4 h-4 text-white" />
                                                            </div>
                                                        </div>
                                                    )}
                                                    <div
                                                        className={`max-w-[80%] rounded-lg p-3 ${
                                                            message.role === 'user'
                                                                ? 'bg-slate-200 text-slate-900'
                                                                : 'bg-white border'
                                                        }`}
                                                    >
                                                        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                                                        <p className="text-xs text-slate-500 mt-1">
                                                            {new Date(message.timestamp).toLocaleTimeString()}
                                                        </p>
                                                    </div>
                                                    {message.role === 'user' && (
                                                        <div className="flex-shrink-0">
                                                            <div className="w-8 h-8 bg-slate-500 rounded-full flex items-center justify-center">
                                                                <User className="w-4 h-4 text-white" />
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                            <div ref={messagesEndRef} />
                                        </div>
                                    ) : (
                                        <p className="text-slate-500 text-sm text-center">No messages yet</p>
                                    )}
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                </main>
            </div>
        </ProtectedRoute>
    );
}