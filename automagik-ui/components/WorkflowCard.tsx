'use client';

import { useState, useEffect } from 'react';
import { getWorkflowStatus, WorkflowStatus } from '@/lib/api';
import { WorkflowStatusBadge } from '@/components/WorkflowStatusBadge';
import { toast } from 'sonner';

interface WorkflowCardProps {
  initialWorkflow: WorkflowStatus;
  onStatusChange?: (status: WorkflowStatus) => void;
}

export default function WorkflowCard({ initialWorkflow, onStatusChange }: WorkflowCardProps) {
  const [workflow, setWorkflow] = useState<WorkflowStatus>(initialWorkflow);
  const [isPolling, setIsPolling] = useState(false);

  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    if (workflow.status === 'running' || workflow.status === 'pending') {
      setIsPolling(true);
      
      const pollStatus = async () => {
        try {
          const updatedStatus = await getWorkflowStatus(workflow.run_id);
          setWorkflow(updatedStatus);
          onStatusChange?.(updatedStatus);
          
          if (updatedStatus.status === 'completed') {
            toast.success(`Workflow "${updatedStatus.workflow_name}" completed successfully!`, {
              description: updatedStatus.message,
              duration: 5000,
            });
            setIsPolling(false);
            clearInterval(intervalId);
          } else if (updatedStatus.status === 'failed' || updatedStatus.status === 'timeout') {
            toast.error(`Workflow "${updatedStatus.workflow_name}" ${updatedStatus.status}`, {
              description: updatedStatus.error || 'Check logs for details',
              duration: 8000,
            });
            setIsPolling(false);
            clearInterval(intervalId);
          }
        } catch (error) {
          console.error('Failed to poll workflow status:', error);
          // Don't stop polling on transient errors
        }
      };

      // Poll every 2 seconds (matching async-code-web)
      intervalId = setInterval(pollStatus, 2000);
      
      // Initial poll immediately
      pollStatus();
    } else {
      setIsPolling(false);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
        setIsPolling(false);
      }
    };
  }, [workflow.run_id, workflow.status, onStatusChange]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800 border-green-200';
      case 'running': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'pending': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'failed': return 'bg-red-100 text-red-800 border-red-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        );
      case 'running':
        return (
          <svg className="w-5 h-5 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        );
      case 'pending':
        return (
          <svg className="w-5 h-5 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
          </svg>
        );
      case 'failed':
        return (
          <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5 text-gray-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
        );
    }
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const calculateDuration = () => {
    const start = new Date(workflow.started_at);
    const end = workflow.completed_at ? new Date(workflow.completed_at) : new Date();
    const diffMs = end.getTime() - start.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);
    
    if (diffSeconds < 60) return `${diffSeconds}s`;
    if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ${diffSeconds % 60}s`;
    return `${Math.floor(diffSeconds / 3600)}h ${Math.floor((diffSeconds % 3600) / 60)}m`;
  };

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 hover:shadow-lg transition-shadow duration-200">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          {getStatusIcon(workflow.status)}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 capitalize">
              {workflow.workflow_name}
            </h3>
            <p className="text-sm text-gray-600">ID: {workflow.run_id}</p>
          </div>
        </div>
        <div className={`px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(workflow.status)}`}>
          {workflow.status.toUpperCase()}
          {isPolling && workflow.status === 'running' && (
            <span className="ml-1 inline-block">
              <span className="status-indicator status-healthy"></span>
            </span>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      {workflow.progress !== undefined && (
        <div className="mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Progress</span>
            <span>{workflow.progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-automagik-600 h-2 rounded-full transition-all duration-300 ease-in-out"
              style={{ width: `${workflow.progress}%` }}
            ></div>
          </div>
        </div>
      )}

      {/* Message */}
      <div className="mb-4">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Task</h4>
        <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded border">
          {workflow.message}
        </p>
      </div>

      {/* Error Message */}
      {workflow.error && (
        <div className="mb-4">
          <h4 className="text-sm font-medium text-red-700 mb-2">Error</h4>
          <p className="text-sm text-red-600 bg-red-50 p-3 rounded border border-red-200">
            {workflow.error}
          </p>
        </div>
      )}

      {/* Timing Information */}
      <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200 text-sm">
        <div>
          <span className="text-gray-600">Started:</span>
          <div className="font-medium text-gray-900">{formatTime(workflow.started_at)}</div>
        </div>
        <div>
          <span className="text-gray-600">Duration:</span>
          <div className="font-medium text-gray-900">{calculateDuration()}</div>
        </div>
        {workflow.completed_at && (
          <>
            <div className="col-span-2">
              <span className="text-gray-600">Completed:</span>
              <div className="font-medium text-gray-900">{formatTime(workflow.completed_at)}</div>
            </div>
          </>
        )}
      </div>

      {/* Actions */}
      {workflow.status === 'running' && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <button
            className="text-sm text-red-600 hover:text-red-700 font-medium"
            onClick={() => {
              // TODO: Implement workflow cancellation
              console.log('Cancel workflow:', workflow.run_id);
            }}
          >
            Cancel Workflow
          </button>
        </div>
      )}
    </div>
  );
}