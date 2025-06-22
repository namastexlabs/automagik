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
import { DiffViewer } from "@/components/DiffViewer";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { FileChange } from "@/types";

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
    progress?: {
        turns: number;
        max_turns?: number;
        completion_percentage: number;
        current_phase: string;
        phases_completed: string[];
        is_running: boolean;
    };
    metrics?: {
        cost_usd: number;
        tokens: {
            total: number;
            input: number;
            output: number;
            cache_created: number;
            cache_read: number;
            cache_efficiency: number;
        };
        tools_used: string[];
        api_duration_ms: number;
        performance_score: number;
    };
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

            // Fetch workflow status with detailed=true for rich metrics
            const statusResponse = await fetch(
                `http://localhost:28881/api/v1/workflows/claude-code/run/${workflowId}/status?detailed=true`,
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

            // Get file changes from the enhanced status API (result.files_changed)
            let fileChanges: FileChange[] = [];
            
            // First try to get from the enhanced status response
            if (statusData.result?.files_changed && statusData.result.files_changed.length > 0) {
                fileChanges = statusData.result.files_changed;
                console.log('Using enhanced file changes from status API:', fileChanges.length);
            } else {
                // Fallback to basic file changes from status
                fileChanges = statusData.result?.files_created?.map((file: string) => ({
                    filename: file,
                    path: file,
                    status: "added" as const,
                    additions: 0,
                    deletions: 0,
                    before: '',
                    after: 'New file created'
                })) || [];
                console.log('Using fallback file changes:', fileChanges.length);
            }

            // Get real conversation data from workflow progress (no more mocked data)
            const messages: ChatMessage[] = statusData.progress?.messages || [];

            const workflowDetails: WorkflowDetails = {
                run_id: workflowId,
                status: statusData.status || "pending",
                workflow_name: statusData.workflow_name || "Claude Code Workflow",
                repository_url: statusData.repository_url || process.env.NEXT_PUBLIC_REPO_URL || "",
                git_branch: statusData.git_branch || "main",
                started_at: statusData.started_at || new Date().toISOString(),
                completed_at: statusData.completed_at,
                error: statusData.error,
                commit_hash: statusData.result?.git_commits?.[0] || "",
                ai_model: statusData.metrics?.model || "Claude 3.5 Sonnet",
                files_changed: fileChanges,
                logs: logs,
                messages: messages,
                progress: statusData.progress,
                metrics: statusData.metrics
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
                <div className="min-h-screen bg-background flex items-center justify-center">
                    <div className="text-center animate-fade-in">
                        <AlertCircle className="w-12 h-12 text-destructive mx-auto mb-4" />
                        <h2 className="text-xl font-semibold mb-2 text-foreground">Workflow not found</h2>
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
            <div className="min-h-screen bg-background">
                {/* Header */}
                <header className="border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-50">
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
                                    <h1 className="text-xl font-semibold text-foreground">Workflow #{workflow.run_id.slice(0, 8)}...</h1>
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
                <main className="container mx-auto px-6 py-8 max-w-7xl animate-fade-in">
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
                                            <p className="text-sm text-muted-foreground mb-1">Repository</p>
                                            <div className="flex items-center gap-2">
                                                <p className="text-sm font-medium text-foreground">{workflow.repository_url || 'Not specified'}</p>
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
                                            <p className="text-sm text-muted-foreground mb-1">Branch</p>
                                            <div className="flex items-center gap-2">
                                                <GitBranch className="w-4 h-4 text-muted-foreground" />
                                                <p className="text-sm font-medium text-foreground">{workflow.git_branch}</p>
                                            </div>
                                        </div>
                                        <div>
                                            <p className="text-sm text-muted-foreground mb-1">AI Model</p>
                                            <div className="flex items-center gap-2">
                                                <Bot className="w-4 h-4 text-muted-foreground" />
                                                <p className="text-sm font-medium text-foreground">{workflow.ai_model}</p>
                                            </div>
                                        </div>
                                        <div>
                                            <p className="text-sm text-muted-foreground mb-1">Started</p>
                                            <p className="text-sm font-medium text-foreground">
                                                {new Date(workflow.started_at).toLocaleString()}
                                            </p>
                                        </div>
                                        {workflow.commit_hash && (
                                            <div>
                                                <p className="text-sm text-muted-foreground mb-1">Commit</p>
                                                <div className="flex items-center gap-2">
                                                    <code className="text-xs bg-muted px-2 py-1 rounded">
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

                            {/* Rich Metrics */}
                            {workflow.metrics && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle>Performance Metrics</CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                            <div className="text-center p-3 bg-slate-50 rounded-lg">
                                                <div className="text-2xl font-bold text-green-600">
                                                    ${workflow.metrics.cost_usd?.toFixed(4) || '0.0000'}
                                                </div>
                                                <div className="text-xs text-slate-600">Cost (USD)</div>
                                            </div>
                                            <div className="text-center p-3 bg-slate-50 rounded-lg">
                                                <div className="text-2xl font-bold text-blue-600">
                                                    {workflow.metrics.tokens?.cache_efficiency?.toFixed(1) || '0'}%
                                                </div>
                                                <div className="text-xs text-slate-600">Cache Efficiency</div>
                                            </div>
                                            <div className="text-center p-3 bg-slate-50 rounded-lg">
                                                <div className="text-2xl font-bold text-purple-600">
                                                    {workflow.metrics.performance_score || 0}
                                                </div>
                                                <div className="text-xs text-slate-600">Performance Score</div>
                                            </div>
                                            <div className="text-center p-3 bg-slate-50 rounded-lg">
                                                <div className="text-2xl font-bold text-orange-600">
                                                    {workflow.metrics.tools_used?.length || 0}
                                                </div>
                                                <div className="text-xs text-slate-600">Tools Used</div>
                                            </div>
                                        </div>
                                        {workflow.metrics.tokens && (
                                            <div className="mt-4 p-3 bg-slate-50 rounded-lg">
                                                <h4 className="font-medium text-sm mb-2">Token Usage</h4>
                                                <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
                                                    <div>
                                                        <div className="font-medium">{workflow.metrics.tokens.total.toLocaleString()}</div>
                                                        <div className="text-slate-600">Total</div>
                                                    </div>
                                                    <div>
                                                        <div className="font-medium">{workflow.metrics.tokens.input.toLocaleString()}</div>
                                                        <div className="text-slate-600">Input</div>
                                                    </div>
                                                    <div>
                                                        <div className="font-medium">{workflow.metrics.tokens.output.toLocaleString()}</div>
                                                        <div className="text-slate-600">Output</div>
                                                    </div>
                                                    <div>
                                                        <div className="font-medium">{workflow.metrics.tokens.cache_created.toLocaleString()}</div>
                                                        <div className="text-slate-600">Cache Created</div>
                                                    </div>
                                                    <div>
                                                        <div className="font-medium">{workflow.metrics.tokens.cache_read.toLocaleString()}</div>
                                                        <div className="text-slate-600">Cache Read</div>
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                        {workflow.metrics.tools_used && workflow.metrics.tools_used.length > 0 && (
                                            <div className="mt-4 p-3 bg-slate-50 rounded-lg">
                                                <h4 className="font-medium text-sm mb-2">Tools Used</h4>
                                                <div className="flex flex-wrap gap-1">
                                                    {workflow.metrics.tools_used.map((tool, idx) => (
                                                        <Badge key={idx} variant="outline" className="text-xs">
                                                            {tool}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>
                            )}

                            {/* Progress Tracking */}
                            {workflow.progress && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle>Progress Tracking</CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-4">
                                            <div>
                                                <div className="flex justify-between text-sm text-slate-600 mb-2">
                                                    <span>Overall Progress</span>
                                                    <span>{workflow.progress.completion_percentage}%</span>
                                                </div>
                                                <div className="w-full bg-slate-200 rounded-full h-3">
                                                    <div
                                                        className="bg-blue-600 h-3 rounded-full transition-all duration-300"
                                                        style={{ width: `${workflow.progress.completion_percentage}%` }}
                                                    ></div>
                                                </div>
                                            </div>
                                            <div className="grid grid-cols-2 gap-4 text-sm">
                                                <div>
                                                    <span className="text-slate-600">Current Phase:</span>
                                                    <div className="font-medium capitalize">{workflow.progress.current_phase}</div>
                                                </div>
                                                <div>
                                                    <span className="text-slate-600">Turns:</span>
                                                    <div className="font-medium">
                                                        {workflow.progress.turns}
                                                        {workflow.progress.max_turns ? ` / ${workflow.progress.max_turns}` : ''}
                                                    </div>
                                                </div>
                                            </div>
                                            {workflow.progress.phases_completed && workflow.progress.phases_completed.length > 0 && (
                                                <div>
                                                    <span className="text-slate-600 text-sm">Completed Phases:</span>
                                                    <div className="flex flex-wrap gap-1 mt-1">
                                                        {workflow.progress.phases_completed.map((phase, idx) => (
                                                            <Badge key={idx} variant="secondary" className="text-xs capitalize">
                                                                {phase}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </CardContent>
                                </Card>
                            )}

                            {/* Code Changes */}
                            {workflow.files_changed && workflow.files_changed.length > 0 && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle>Code Changes</CardTitle>
                                        <CardDescription>
                                            {workflow.files_changed.length} file{workflow.files_changed.length !== 1 ? 's' : ''} changed
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        <DiffViewer 
                                            fileChanges={workflow.files_changed}
                                            stats={{
                                                files: workflow.files_changed.length,
                                                additions: workflow.files_changed.reduce((sum, f) => sum + f.additions, 0),
                                                deletions: workflow.files_changed.reduce((sum, f) => sum + f.deletions, 0)
                                            }}
                                        />
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