'use client';

import { useState } from 'react';
import { startWorkflow, WorkflowType } from '@/lib/api';

interface QuickActionsProps {
  workflows: WorkflowType[];
  onWorkflowStart: (runId: string) => void;
}

export default function QuickActions({ workflows, onWorkflowStart }: QuickActionsProps) {
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>('');
  const [message, setMessage] = useState<string>('');
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  const handleRunWorkflow = async () => {
    if (!selectedWorkflow || !message.trim()) {
      setError('Please select a workflow and enter a message');
      return;
    }

    setIsRunning(true);
    setError('');

    try {
      const result = await startWorkflow(selectedWorkflow, { message });
      onWorkflowStart(result.run_id || Date.now().toString());
      setMessage('');
      setSelectedWorkflow('');
    } catch (err) {
      setError('Failed to start workflow: ' + (err as Error).message);
    } finally {
      setIsRunning(false);
    }
  };

  const getWorkflowColor = (workflowName: string) => {
    const colors: Record<string, string> = {
      'test': 'bg-green-100 border-green-300 text-green-800',
      'pr': 'bg-blue-100 border-blue-300 text-blue-800',
      'fix': 'bg-red-100 border-red-300 text-red-800',
      'refactor': 'bg-purple-100 border-purple-300 text-purple-800',
      'implement': 'bg-yellow-100 border-yellow-300 text-yellow-800',
      'review': 'bg-orange-100 border-orange-300 text-orange-800',
      'document': 'bg-gray-100 border-gray-300 text-gray-800',
      'architect': 'bg-indigo-100 border-indigo-300 text-indigo-800',
    };
    return colors[workflowName] || 'bg-gray-100 border-gray-300 text-gray-800';
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-800">Quick Actions</h2>
      
      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-300 text-red-700 rounded">
          {error}
        </div>
      )}

      <div className="space-y-4">
        <div>
          <label htmlFor="workflow-select" className="block text-sm font-medium text-gray-700 mb-2">
            Select Workflow
          </label>
          <select
            id="workflow-select"
            value={selectedWorkflow}
            onChange={(e) => setSelectedWorkflow(e.target.value)}
            className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-automagik-500 focus:border-transparent"
            disabled={isRunning}
          >
            <option value="">Choose a workflow...</option>
            {workflows.map((workflow) => (
              <option key={workflow.name} value={workflow.name}>
                {workflow.name} - {workflow.description}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="message" className="block text-sm font-medium text-gray-700 mb-2">
            Task Description
          </label>
          <textarea
            id="message"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Describe what you want to accomplish..."
            rows={4}
            className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-automagik-500 focus:border-transparent"
            disabled={isRunning}
          />
        </div>

        <button
          onClick={handleRunWorkflow}
          disabled={isRunning || !selectedWorkflow || !message.trim()}
          className="w-full bg-automagik-600 text-white py-3 px-4 rounded-md hover:bg-automagik-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
        >
          {isRunning ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Starting Workflow...
            </span>
          ) : (
            'Run Workflow'
          )}
        </button>
      </div>

      {workflows.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Available Workflows</h3>
          <div className="grid grid-cols-2 gap-2">
            {workflows.map((workflow) => (
              <div
                key={workflow.name}
                className={`p-2 rounded border text-xs ${getWorkflowColor(workflow.name)}`}
              >
                <div className="font-medium">{workflow.name}</div>
                <div className="text-xs opacity-75">{workflow.description}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}