"use client";

import { useState, useEffect } from "react";
import { Settings, GitBranch, StopCircle, RefreshCw, Clock, CheckCircle, XCircle, AlertCircle, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ProtectedRoute } from "@/components/protected-route";
import { TaskStatusBadge } from "@/components/task-status-badge";
import { useAuth } from "@/contexts/auth-context";
import { ApiService } from "@/lib/api-service";
import { toast } from "sonner";

interface Workflow {
    id: number;
    status: "running" | "completed" | "failed" | "pending";
    prompt?: string;
    repo_url: string;
    target_branch?: string;
    agent?: string;
    created_at: string;
    project_id?: number;
    chat_messages?: any[];
}

export default function WorkflowsPage() {
    const { user } = useAuth();
    const [workflows, setWorkflows] = useState<Workflow[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    useEffect(() => {
        if (user?.id) {
            loadWorkflows();
        }
    }, [user?.id]);

    // Auto-refresh every 5 seconds for running workflows
    useEffect(() => {
        if (!user?.id) return;

        const hasRunningWorkflows = workflows.some(w => w.status === "running" || w.status === "pending");
        if (!hasRunningWorkflows) return;

        const interval = setInterval(() => {
            loadWorkflows(true);
        }, 5000);

        return () => clearInterval(interval);
    }, [workflows, user?.id]);

    const loadWorkflows = async (silent = false) => {
        if (!user?.id) return;
        
        try {
            if (!silent) setIsLoading(true);
            
            // Use the correct Claude Code runs endpoint
            const response = await fetch(`http://localhost:28881/api/v1/workflows/claude-code/runs`, {
                headers: {
                    'x-api-key': 'namastex888'
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch workflows');
            }
            
            const data = await response.json();
            // Map runs to expected Workflow interface
            const workflowRuns = data.runs.map((run: any) => ({
                id: run.run_id, // Use run_id as id
                status: run.status,
                prompt: run.workflow_name,
                repo_url: run.repository_url || '',
                target_branch: run.git_branch || 'main',
                agent: run.workflow_name,
                created_at: run.started_at,
                project_id: null,
                chat_messages: []
            }));
            setWorkflows(workflowRuns);
        } catch (error) {
            console.error('Error loading workflows:', error);
            if (!silent) {
                toast.error('Failed to load workflows');
            }
        } finally {
            setIsLoading(false);
            setRefreshing(false);
        }
    };

    const handleKillWorkflow = async (workflowId: number) => {
        try {
            const response = await fetch(`http://localhost:28881/api/v1/workflows/claude-code/run/${workflowId}/kill`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': 'namastex888'
                }
            });

            if (!response.ok) {
                throw new Error('Failed to kill workflow');
            }

            toast.success(`Workflow #${workflowId} killed successfully`);
            loadWorkflows();
        } catch (error) {
            console.error('Error killing workflow:', error);
            toast.error(`Failed to kill workflow #${workflowId}`);
        }
    };

    const handleRefresh = () => {
        setRefreshing(true);
        loadWorkflows();
    };

    const getWorkflowPrompt = (workflow: Workflow): string => {
        if (workflow.prompt) return workflow.prompt;
        if (workflow.chat_messages && workflow.chat_messages.length > 0) {
            return workflow.chat_messages[0]?.content || 'No prompt available';
        }
        return 'No prompt available';
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case "running": return "text-blue-600";
            case "completed": return "text-green-600";
            case "failed": return "text-red-600";
            case "pending": return "text-amber-600";
            default: return "text-gray-600";
        }
    };

    return (
        <ProtectedRoute>
            <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
                {/* Header */}
                <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
                    <div className="container mx-auto px-6 py-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <h1 className="text-2xl font-semibold text-slate-900">Workflow Management</h1>
                                <p className="text-sm text-slate-500">Monitor and manage your AI code workflows</p>
                            </div>
                            <div className="flex items-center gap-3">
                                <Button
                                    onClick={handleRefresh}
                                    disabled={refreshing}
                                    variant="outline"
                                    className="gap-2"
                                >
                                    <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                                    Refresh
                                </Button>
                            </div>
                        </div>
                    </div>
                </header>

                {/* Main Content */}
                <main className="container mx-auto px-6 py-8 max-w-6xl">
                    <div className="space-y-6">
                        {/* Status Overview */}
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                            <Card>
                                <CardContent className="p-4">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-blue-100 rounded-lg">
                                            <Play className="w-4 h-4 text-blue-600" />
                                        </div>
                                        <div>
                                            <p className="text-sm text-slate-500">Running</p>
                                            <p className="text-xl font-semibold">
                                                {workflows.filter(w => w.status === "running").length}
                                            </p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>

                            <Card>
                                <CardContent className="p-4">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-amber-100 rounded-lg">
                                            <Clock className="w-4 h-4 text-amber-600" />
                                        </div>
                                        <div>
                                            <p className="text-sm text-slate-500">Pending</p>
                                            <p className="text-xl font-semibold">
                                                {workflows.filter(w => w.status === "pending").length}
                                            </p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>

                            <Card>
                                <CardContent className="p-4">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-green-100 rounded-lg">
                                            <CheckCircle className="w-4 h-4 text-green-600" />
                                        </div>
                                        <div>
                                            <p className="text-sm text-slate-500">Completed</p>
                                            <p className="text-xl font-semibold">
                                                {workflows.filter(w => w.status === "completed").length}
                                            </p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>

                            <Card>
                                <CardContent className="p-4">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-red-100 rounded-lg">
                                            <XCircle className="w-4 h-4 text-red-600" />
                                        </div>
                                        <div>
                                            <p className="text-sm text-slate-500">Failed</p>
                                            <p className="text-xl font-semibold">
                                                {workflows.filter(w => w.status === "failed").length}
                                            </p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>

                        {/* Workflows List */}
                        <Card>
                            <CardHeader>
                                <CardTitle>All Workflows</CardTitle>
                                <CardDescription>
                                    {workflows.length > 0 
                                        ? `${workflows.length} workflow${workflows.length === 1 ? '' : 's'} found`
                                        : 'No workflows found'
                                    }
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                {isLoading ? (
                                    <div className="flex items-center justify-center py-12">
                                        <div className="flex items-center gap-3 text-slate-500">
                                            <RefreshCw className="w-5 h-5 animate-spin" />
                                            Loading workflows...
                                        </div>
                                    </div>
                                ) : workflows.length === 0 ? (
                                    <div className="text-center py-12 text-slate-500">
                                        <Settings className="w-12 h-12 mx-auto mb-4 opacity-50" />
                                        <p className="text-lg font-medium">No workflows found</p>
                                        <p className="text-sm">Start your first workflow from the main dashboard</p>
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        {workflows.map((workflow) => (
                                            <div
                                                key={workflow.id}
                                                className="flex items-center justify-between p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
                                            >
                                                <div className="flex-1 min-w-0 space-y-2">
                                                    <div className="flex items-center gap-3">
                                                        <TaskStatusBadge status={workflow.status} />
                                                        <span className="text-sm font-medium text-slate-900">
                                                            Workflow #{workflow.id}
                                                        </span>
                                                        {workflow.agent && (
                                                            <Badge variant="outline" className="text-xs">
                                                                {workflow.agent.toUpperCase()}
                                                            </Badge>
                                                        )}
                                                    </div>
                                                    
                                                    <p className="text-sm text-slate-700 line-clamp-2">
                                                        {getWorkflowPrompt(workflow)}
                                                    </p>
                                                    
                                                    <div className="flex items-center gap-4 text-xs text-slate-500">
                                                        <div className="flex items-center gap-1">
                                                            <GitBranch className="w-3 h-3" />
                                                            {workflow.target_branch || 'main'}
                                                        </div>
                                                        <span>
                                                            Created {new Date(workflow.created_at).toLocaleDateString()}
                                                        </span>
                                                        <span>
                                                            {new Date(workflow.created_at).toLocaleTimeString()}
                                                        </span>
                                                    </div>
                                                </div>
                                                
                                                <div className="flex items-center gap-2 ml-4">
                                                    {(workflow.status === "running" || workflow.status === "pending") && (
                                                        <Button
                                                            onClick={() => handleKillWorkflow(workflow.id)}
                                                            variant="destructive"
                                                            size="sm"
                                                            className="gap-2"
                                                        >
                                                            <StopCircle className="w-3 h-3" />
                                                            Kill
                                                        </Button>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </main>
            </div>
        </ProtectedRoute>
    );
}