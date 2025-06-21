'use client';

import { useState, useEffect } from 'react';
import { getSystemHealth } from '@/lib/api';

interface SystemStatus {
  status: 'healthy' | 'warning' | 'error';
  timestamp: string;
  version: string;
  environment: string;
  workflows?: {
    [key: string]: boolean;
  };
  agent_available?: boolean;
  container_manager?: boolean;
  feature_enabled?: boolean;
  claude_cli_path?: string;
}

export default function SystemHealth() {
  const [health, setHealth] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchHealth = async () => {
    try {
      const healthData = await getSystemHealth();
      setHealth(healthData);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to fetch system health:', error);
      setHealth({
        status: 'error',
        timestamp: new Date().toISOString(),
        version: 'unknown',
        environment: 'unknown'
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 60000); // Update every 60 seconds (reduced from 30)
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600 bg-green-100';
      case 'warning': return 'text-yellow-600 bg-yellow-100';
      case 'error': return 'text-red-600 bg-red-100';
      case 'degraded': return 'text-yellow-600 bg-yellow-100';
      case 'down': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return (
          <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        );
      case 'warning':
        return (
          <svg className="w-4 h-4 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        );
      case 'error':
      case 'down':
        return (
          <svg className="w-4 h-4 text-red-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
        );
      default:
        return (
          <svg className="w-4 h-4 text-gray-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
        );
    }
  };

  const formatUptime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    return `${Math.floor(seconds / 86400)}d`;
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">System Health</h2>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
          <div className="space-y-2">
            <div className="h-8 bg-gray-200 rounded"></div>
            <div className="h-8 bg-gray-200 rounded"></div>
            <div className="h-8 bg-gray-200 rounded"></div>
            <div className="h-8 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!health) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">System Health</h2>
        <div className="text-red-600">Failed to load system health</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-800">System Health</h2>
        <button
          onClick={fetchHealth}
          className="text-sm text-automagik-600 hover:text-automagik-700 font-medium"
        >
          Refresh
        </button>
      </div>

      <div className="mb-6">
        <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(health.status)}`}>
          {getStatusIcon(health.status)}
          <span className="ml-2 capitalize">{health.status}</span>
        </div>
      </div>

      <div className="space-y-3 mb-6">
        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center">
            {getStatusIcon(health.status)}
            <span className="ml-3 font-medium text-gray-700">API Server</span>
          </div>
          <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(health.status)}`}>
            {health.status}
          </span>
        </div>
        
        {health.agent_available !== undefined && (
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center">
              {getStatusIcon(health.agent_available ? 'healthy' : 'error')}
              <span className="ml-3 font-medium text-gray-700">Agent System</span>
            </div>
            <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(health.agent_available ? 'healthy' : 'error')}`}>
              {health.agent_available ? 'available' : 'unavailable'}
            </span>
          </div>
        )}
        
        {health.container_manager !== undefined && (
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center">
              {getStatusIcon(health.container_manager ? 'healthy' : 'warning')}
              <span className="ml-3 font-medium text-gray-700">Container Manager</span>
            </div>
            <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(health.container_manager ? 'healthy' : 'warning')}`}>
              {health.container_manager ? 'enabled' : 'disabled'}
            </span>
          </div>
        )}
        
        {health.workflows && (
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="font-medium text-gray-700 mb-2">Available Workflows</div>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(health.workflows).map(([workflow, available]) => (
                <div key={workflow} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 capitalize">{workflow}</span>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(available ? 'healthy' : 'error')}`}>
                    {available ? '✓' : '✗'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200">
        <div>
          <div className="text-sm text-gray-600">Environment</div>
          <div className="text-lg font-semibold text-gray-900 capitalize">{health.environment}</div>
        </div>
        <div>
          <div className="text-sm text-gray-600">Version</div>
          <div className="text-lg font-semibold text-gray-900">{health.version}</div>
        </div>
      </div>

      <div className="text-xs text-gray-500 mt-4">
        Last updated: {lastUpdate.toLocaleTimeString()}
      </div>
    </div>
  );
}