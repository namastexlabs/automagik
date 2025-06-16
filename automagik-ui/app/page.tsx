'use client';

import { useState, useEffect } from 'react';
import QuickActions from '@/components/QuickActions';
import SystemHealth from '@/components/SystemHealth';
import WorkflowCard from '@/components/WorkflowCard';
import { AutomagikAPI, WorkflowType, WorkflowStatus } from '@/lib/api';

export default function Dashboard() {
  const [workflows, setWorkflows] = useState<WorkflowType[]>([]);
  const [recentRuns, setRecentRuns] = useState<WorkflowStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  const fetchData = async () => {
    try {
      setError('');
      const [workflowTypes, runs] = await Promise.all([
        AutomagikAPI.listWorkflows().catch(() => [
          // Fallback workflows if API is not available
          { name: 'test', description: 'Run tests and validate code quality', capabilities: ['testing', 'validation'] },
          { name: 'pr', description: 'Create and manage pull requests', capabilities: ['git', 'review'] },
          { name: 'fix', description: 'Identify and fix bugs in code', capabilities: ['debugging', 'repair'] },
          { name: 'refactor', description: 'Improve code structure and quality', capabilities: ['optimization', 'cleanup'] },
          { name: 'implement', description: 'Build new features and functionality', capabilities: ['development', 'creation'] },
          { name: 'review', description: 'Code review and quality assessment', capabilities: ['analysis', 'feedback'] },
          { name: 'document', description: 'Generate and update documentation', capabilities: ['writing', 'explanation'] },
          { name: 'architect', description: 'Design system architecture', capabilities: ['planning', 'design'] },
        ]),
        AutomagikAPI.listRecentRuns({ limit: 10 }).catch(() => [])
      ]);
      
      setWorkflows(workflowTypes);
      setRecentRuns(runs);
    } catch (err) {
      setError('Failed to load dashboard data: ' + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const handleWorkflowStart = (runId: string) => {
    // Add the new workflow to recent runs with pending status
    const newWorkflow: WorkflowStatus = {
      run_id: runId,
      workflow_name: 'pending',
      status: 'pending',
      started_at: new Date().toISOString(),
      message: 'Workflow starting...'
    };
    
    setRecentRuns(prev => [newWorkflow, ...prev.slice(0, 9)]);
    
    // Refresh data to get the actual workflow details
    setTimeout(fetchData, 2000);
  };

  const handleWorkflowStatusChange = (updatedWorkflow: WorkflowStatus) => {
    setRecentRuns(prev => 
      prev.map(workflow => 
        workflow.run_id === updatedWorkflow.run_id ? updatedWorkflow : workflow
      )
    );
  };

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-6">
              <div className="h-96 bg-gray-200 rounded-lg"></div>
              <div className="h-64 bg-gray-200 rounded-lg"></div>
            </div>
            <div className="h-96 bg-gray-200 rounded-lg"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">Manage workflows and monitor system health</p>
        </div>
        <button
          onClick={fetchData}
          className="bg-automagik-600 text-white px-4 py-2 rounded-md hover:bg-automagik-700 transition-colors"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-300 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column - Quick Actions and Recent Workflows */}
        <div className="lg:col-span-2 space-y-8">
          {/* Quick Actions */}
          <QuickActions 
            workflows={workflows} 
            onWorkflowStart={handleWorkflowStart}
          />

          {/* Recent Workflows */}
          <div>
            <h2 className="text-xl font-semibold mb-4 text-gray-800">Recent Workflows</h2>
            {recentRuns.length === 0 ? (
              <div className="bg-white rounded-lg shadow-md p-8 text-center">
                <div className="text-gray-400 text-6xl mb-4">🤖</div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">No workflows yet</h3>
                <p className="text-gray-600">Start your first workflow to see it here!</p>
              </div>
            ) : (
              <div className="space-y-4">
                {recentRuns.map((workflow) => (
                  <WorkflowCard
                    key={workflow.run_id}
                    initialWorkflow={workflow}
                    onStatusChange={handleWorkflowStatusChange}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column - System Health */}
        <div>
          <SystemHealth />
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow-md p-6 text-center">
          <div className="text-3xl font-bold text-green-600">
            {recentRuns.filter(w => w.status === 'completed').length}
          </div>
          <div className="text-sm text-gray-600 mt-1">Completed</div>
        </div>
        <div className="bg-white rounded-lg shadow-md p-6 text-center">
          <div className="text-3xl font-bold text-blue-600">
            {recentRuns.filter(w => w.status === 'running').length}
          </div>
          <div className="text-sm text-gray-600 mt-1">Running</div>
        </div>
        <div className="bg-white rounded-lg shadow-md p-6 text-center">
          <div className="text-3xl font-bold text-yellow-600">
            {recentRuns.filter(w => w.status === 'pending').length}
          </div>
          <div className="text-sm text-gray-600 mt-1">Pending</div>
        </div>
        <div className="bg-white rounded-lg shadow-md p-6 text-center">
          <div className="text-3xl font-bold text-red-600">
            {recentRuns.filter(w => w.status === 'failed').length}
          </div>
          <div className="text-sm text-gray-600 mt-1">Failed</div>
        </div>
      </div>

      {/* Footer */}
      <div className="text-center text-gray-500 text-sm pt-8 border-t border-gray-200">
        <p>Automagik Dashboard - Workflow automation made simple</p>
        <p className="mt-1">Connected to API at localhost:28881</p>
      </div>
    </div>
  );
}