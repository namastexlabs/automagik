# Frontend Integration Guide for Automagik Workflows

## Overview

This guide provides comprehensive instructions for frontend applications to integrate with the Automagik workflow system. The API provides full workflow lifecycle management including starting, monitoring, message injection, and status tracking.

## How to Use Workflows

### Understanding Workflow Types

Automagik provides specialized workflows for different development tasks:

- **`architect`**: Design system architecture and technical specifications
- **`implement`**: Build features based on architectural designs
- **`test`**: Create comprehensive test suites and validation
- **`review`**: Perform code review and quality assessment
- **`fix`**: Apply surgical fixes for specific issues (recommended for bug fixes)
- **`refactor`**: Improve code structure and maintainability
- **`document`**: Generate comprehensive documentation

### Workflow Execution Modes

#### 1. Default Mode (Working in Current Repository)
Best for development in the Automagik agents repository:
```javascript
const result = await startWorkflow('fix', {
  message: 'Fix the authentication timeout bug in login controller',
  maxTurns: 30,
  sessionName: 'auth-timeout-fix'
});
```

#### 2. External Repository Mode
For working with external Git repositories:
```javascript
const result = await startWorkflow('implement', {
  message: 'Add user profile feature',
  repositoryUrl: 'https://github.com/yourorg/yourapp.git',
  gitBranch: 'feature/user-profile',
  maxTurns: 50
});
```

#### 3. Temporary Workspace Mode
For isolated tasks without git integration:
```javascript
const queryParams = new URLSearchParams({ temp_workspace: true });
const response = await fetch(
  `${API_BASE_URL}/workflows/claude-code/run/architect?${queryParams}`,
  {
    method: 'POST',
    headers,
    body: JSON.stringify({
      message: 'Design a microservices architecture for e-commerce platform'
    })
  }
);
```

### Step-by-Step Workflow Usage

#### Step 1: Choose the Right Workflow
```javascript
// For bug fixes - use 'fix' workflow
const bugFix = await startWorkflow('fix', {
  message: 'Fix null pointer exception in OrderService.processPayment()'
});

// For new features - use 'implement' workflow
const feature = await startWorkflow('implement', {
  message: 'Implement OAuth2 login with Google and GitHub providers'
});

// For code improvements - use 'refactor' workflow
const refactor = await startWorkflow('refactor', {
  message: 'Refactor UserController to use dependency injection pattern'
});
```

#### Step 2: Monitor Progress
```javascript
// Poll for status updates
const checkProgress = async (runId) => {
  const status = await getWorkflowStatus(runId);
  
  console.log(`Status: ${status.status}`);
  console.log(`Progress: ${status.progress.turns}/${status.progress.max_turns || '∞'}`);
  console.log(`Current Phase: ${status.progress.current_phase}`);
  console.log(`Cost: $${status.metrics.cost_usd.toFixed(4)}`);
  
  if (status.status === 'completed') {
    console.log('Result:', status.result.message);
    console.log('Files changed:', status.result.files_changed);
  }
  
  return status;
};

// Poll every 5 seconds
const pollInterval = setInterval(async () => {
  const status = await checkProgress(runId);
  if (['completed', 'failed', 'killed'].includes(status.status)) {
    clearInterval(pollInterval);
  }
}, 5000);
```

#### Step 3: Inject Additional Instructions (Optional)
```javascript
// Wait for workflow to be running
await new Promise(resolve => setTimeout(resolve, 5000));

// Inject additional instructions
try {
  await injectMessage(runId, 'Please also add comprehensive unit tests with 90% coverage');
  console.log('Additional instructions sent');
} catch (error) {
  if (error.status === 408) {
    console.log('Workflow still initializing, retry in a few seconds');
  }
}
```

#### Step 4: Handle Completion
```javascript
const handleWorkflowCompletion = async (runId) => {
  const finalStatus = await getWorkflowStatus(runId);
  
  if (finalStatus.status === 'completed') {
    console.log('✅ Workflow completed successfully');
    console.log('Files created:', finalStatus.result.files_created);
    console.log('Git commits:', finalStatus.result.git_commits);
    
    // If auto_merge was not enabled, remind about PR
    if (finalStatus.result.git_commits.length > 0) {
      console.log('Remember to create a pull request for the changes');
    }
  } else if (finalStatus.status === 'failed') {
    console.error('❌ Workflow failed:', finalStatus.result.message);
  }
};
```

### Common Workflow Patterns

#### Pattern 1: Bug Fix with Validation
```javascript
async function fixBugWithValidation(bugDescription) {
  // Start fix workflow
  const { run_id } = await startWorkflow('fix', {
    message: bugDescription,
    sessionName: `bug-fix-${Date.now()}`
  });
  
  // Wait for initial analysis
  await new Promise(resolve => setTimeout(resolve, 10000));
  
  // Request test creation
  await injectMessage(run_id, 'Create a test that reproduces this bug before fixing');
  
  // Monitor until completion
  return monitorWorkflow(run_id);
}
```

#### Pattern 2: Feature Implementation with Architecture
```javascript
async function implementFeatureWithDesign(featureRequest) {
  // First, create architecture
  const architectResult = await startWorkflow('architect', {
    message: `Design architecture for: ${featureRequest}`,
    sessionName: 'feature-design'
  });
  
  // Wait for architecture completion
  await waitForCompletion(architectResult.run_id);
  
  // Then implement based on design
  const implementResult = await startWorkflow('implement', {
    message: `Implement the feature based on the architecture design: ${featureRequest}`,
    sessionId: architectResult.session_id // Continue same session
  });
  
  return implementResult;
}
```

#### Pattern 3: Code Review and Refactor
```javascript
async function reviewAndRefactor(codeSection) {
  // Review first
  const reviewResult = await startWorkflow('review', {
    message: `Review ${codeSection} for code quality and best practices`
  });
  
  await waitForCompletion(reviewResult.run_id);
  
  // If issues found, refactor
  const refactorResult = await startWorkflow('refactor', {
    message: `Refactor ${codeSection} based on the review feedback`,
    sessionId: reviewResult.session_id
  });
  
  return { reviewResult, refactorResult };
}
```

### Workflow Parameters Guide

#### Required Parameters
- **`message`**: Clear, specific description of the task

#### Optional Parameters
- **`max_turns`**: Limit conversation turns (1-200, unlimited if not set)
- **`session_id`**: Continue a previous session (UUID format)
- **`session_name`**: Human-readable name for the session
- **`user_id`**: Track workflows by user
- **`timeout`**: Max execution time in seconds (60-14400, default: 7200)
- **`git_branch`**: Specific branch to work on
- **`repository_url`**: External repository URL

#### Query Parameters
- **`persistent`**: Keep workspace after completion (default: true)
- **`auto_merge`**: Auto-merge to main branch (default: false)
- **`temp_workspace`**: Use temporary workspace (default: false)

### Error Handling Guide

#### Common Errors and Solutions

```javascript
try {
  const result = await startWorkflow('implement', config);
} catch (error) {
  switch (error.status) {
    case 400:
      // Invalid parameters
      if (error.response.detail.includes('temp_workspace')) {
        console.error('Cannot use temp_workspace with git parameters');
      }
      break;
      
    case 404:
      // Workflow not found
      console.error('Invalid workflow name');
      break;
      
    case 408:
      // Timeout - workspace not ready
      console.log('Workspace initializing, retry in a few seconds');
      break;
      
    case 500:
      // Server error
      console.error('Server error, please try again');
      break;
  }
}
```

### Production Setup Checklist

1. **API Endpoint Configuration**
   - Update `API_BASE_URL` to your production URL
   - Ensure HTTPS is enabled for production
   - Configure CORS settings on the server

2. **Authentication**
   - Use environment variables for API keys
   - Never expose API keys in frontend code
   - Consider implementing token refresh logic

3. **Rate Limiting**
   - Implement client-side rate limiting
   - Handle 429 (Too Many Requests) responses
   - Add exponential backoff for retries

4. **Monitoring**
   - Log workflow starts and completions
   - Track error rates and response times
   - Set up alerts for failed workflows

## API Configuration

### Base URL and Authentication

```javascript
const API_BASE_URL = 'http://localhost:8000/api/v1';
const API_KEY = 'your-api-key-here';

const headers = {
  'accept': 'application/json',
  'x-api-key': API_KEY,
  'Content-Type': 'application/json'
};
```

### Error Handling

```javascript
class WorkflowAPIError extends Error {
  constructor(message, status, response) {
    super(message);
    this.status = status;
    this.response = response;
  }
}

async function handleAPIResponse(response) {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new WorkflowAPIError(
      errorData.detail || `HTTP ${response.status}`,
      response.status,
      errorData
    );
  }
  return response.json();
}
```

## Core Workflow Operations

### 1. List Available Workflows

```javascript
async function listWorkflows() {
  const response = await fetch(`${API_BASE_URL}/workflows/claude-code/workflows`, {
    headers
  });
  return handleAPIResponse(response);
}

// Usage
const workflows = await listWorkflows();
console.log('Available workflows:', workflows);
```

### 2. Start a Workflow

```javascript
async function startWorkflow(workflowName, config) {
  const payload = {
    message: config.message,
    max_turns: config.maxTurns || 50,
    session_id: config.sessionId || null,
    session_name: config.sessionName || null,
    user_id: config.userId || null,
    git_branch: config.gitBranch || null,
    repository_url: config.repositoryUrl || null,
    timeout: config.timeout || 7200
  };

  const response = await fetch(
    `${API_BASE_URL}/workflows/claude-code/run/${workflowName}`,
    {
      method: 'POST',
      headers,
      body: JSON.stringify(payload)
    }
  );

  return handleAPIResponse(response);
}

// Usage
const result = await startWorkflow('surgeon', {
  message: 'Fix the authentication bug in user controller',
  maxTurns: 30,
  sessionName: 'auth-bug-fix',
  userId: 'user-123'
});
console.log('Workflow started:', result.run_id);
```

### 3. Check Workflow Status

```javascript
async function getWorkflowStatus(runId, debug = false) {
  const endpoint = debug ? 
    `${API_BASE_URL}/workflows/claude-code/run/${runId}/status/debug` :
    `${API_BASE_URL}/workflows/claude-code/run/${runId}/status`;

  const response = await fetch(endpoint, { headers });
  return handleAPIResponse(response);
}

// Usage
const status = await getWorkflowStatus('run_abc123');
console.log('Status:', status.status);
console.log('Progress:', status.progress);
console.log('Cost:', status.metrics.cost_usd);
```

### 4. List Running Workflows

```javascript
async function listRunningWorkflows() {
  const response = await fetch(`${API_BASE_URL}/workflows/claude-code/runs`, {
    headers
  });
  return handleAPIResponse(response);
}

// Usage
const runs = await listRunningWorkflows();
console.log('Active workflows:', runs.filter(r => r.status === 'running'));
```

### 5. Kill a Workflow

```javascript
async function killWorkflow(runId) {
  const response = await fetch(
    `${API_BASE_URL}/workflows/claude-code/run/${runId}/kill`,
    {
      method: 'POST',
      headers
    }
  );
  return handleAPIResponse(response);
}

// Usage
await killWorkflow('run_abc123');
console.log('Workflow killed');
```

## Message Injection

### Inject Messages into Running Workflows

```javascript
async function injectMessage(runId, message, retries = 3) {
  const payload = { message };
  
  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/workflows/claude-code/run/${runId}/inject-message`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify(payload)
        }
      );
      
      if (response.status === 408) {
        // Timeout - workspace not ready, wait and retry
        await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
        continue;
      }
      
      return handleAPIResponse(response);
    } catch (error) {
      if (attempt === retries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
    }
  }
}

// Usage
try {
  const result = await injectMessage('run_abc123', 'Please also add unit tests');
  console.log('Message injected:', result.message_id);
} catch (error) {
  if (error.status === 400) {
    console.log('Workflow not in valid state for injection');
  } else {
    console.error('Injection failed:', error.message);
  }
}
```

## React Integration Example

```jsx
import React, { useState, useEffect } from 'react';

const WorkflowManager = () => {
  const [workflows, setWorkflows] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadWorkflows();
    loadRuns();
  }, []);

  const loadWorkflows = async () => {
    try {
      const data = await listWorkflows();
      setWorkflows(data);
    } catch (error) {
      console.error('Failed to load workflows:', error);
    }
  };

  const loadRuns = async () => {
    try {
      const data = await listRunningWorkflows();
      setRuns(data);
    } catch (error) {
      console.error('Failed to load runs:', error);
    }
  };

  const startNewWorkflow = async (workflowName, message) => {
    setLoading(true);
    try {
      const result = await startWorkflow(workflowName, {
        message,
        maxTurns: 50,
        sessionName: `workflow-${Date.now()}`
      });
      await loadRuns(); // Refresh the list
      return result;
    } catch (error) {
      console.error('Failed to start workflow:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const injectMessageToWorkflow = async (runId, message) => {
    try {
      await injectMessage(runId, message);
      // Optionally refresh status
      await loadRuns();
    } catch (error) {
      console.error('Failed to inject message:', error);
      throw error;
    }
  };

  return (
    <div className="workflow-manager">
      <h2>Workflow Manager</h2>
      
      {/* Available Workflows */}
      <div className="section">
        <h3>Available Workflows</h3>
        {workflows.map(workflow => (
          <div key={workflow.name} className="workflow-card">
            <h4>{workflow.name}</h4>
            <p>{workflow.description}</p>
            <button 
              onClick={() => startNewWorkflow(workflow.name, 'Sample task')}
              disabled={loading}
            >
              Start Workflow
            </button>
          </div>
        ))}
      </div>

      {/* Running Workflows */}
      <div className="section">
        <h3>Running Workflows</h3>
        {runs.map(run => (
          <WorkflowStatus 
            key={run.run_id} 
            run={run} 
            onInjectMessage={injectMessageToWorkflow}
          />
        ))}
      </div>
    </div>
  );
};

const WorkflowStatus = ({ run, onInjectMessage }) => {
  const [status, setStatus] = useState(run);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const updatedStatus = await getWorkflowStatus(run.run_id);
        setStatus(updatedStatus);
      } catch (error) {
        console.error('Failed to update status:', error);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [run.run_id]);

  const handleInjectMessage = async () => {
    if (!message.trim()) return;
    
    try {
      await onInjectMessage(run.run_id, message);
      setMessage('');
    } catch (error) {
      alert('Failed to inject message: ' + error.message);
    }
  };

  return (
    <div className="workflow-status">
      <h4>Run: {run.run_id}</h4>
      <div className="status-badge" data-status={status.status}>
        {status.status}
      </div>
      <p>Progress: {status.progress?.turns}/{status.progress?.max_turns || '∞'}</p>
      <p>Cost: ${status.metrics?.cost_usd?.toFixed(4) || '0.0000'}</p>
      
      {status.status === 'running' && (
        <div className="message-injection">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Inject message..."
            onKeyPress={(e) => e.key === 'Enter' && handleInjectMessage()}
          />
          <button onClick={handleInjectMessage}>Inject</button>
        </div>
      )}
    </div>
  );
};

export default WorkflowManager;
```

## Vue.js Integration Example

```vue
<template>
  <div class="workflow-manager">
    <h2>Workflow Manager</h2>
    
    <div class="section">
      <h3>Available Workflows</h3>
      <div v-for="workflow in workflows" :key="workflow.name" class="workflow-card">
        <h4>{{ workflow.name }}</h4>
        <p>{{ workflow.description }}</p>
        <button @click="startWorkflow(workflow.name)" :disabled="loading">
          Start Workflow
        </button>
      </div>
    </div>

    <div class="section">
      <h3>Running Workflows</h3>
      <div v-for="run in runs" :key="run.run_id" class="workflow-status">
        <h4>Run: {{ run.run_id }}</h4>
        <div class="status-badge" :data-status="run.status">
          {{ run.status }}
        </div>
        <p>Progress: {{ run.progress?.turns }}/{{ run.progress?.max_turns || '∞' }}</p>
        <p>Cost: ${{ run.metrics?.cost_usd?.toFixed(4) || '0.0000' }}</p>
        
        <div v-if="run.status === 'running'" class="message-injection">
          <input
            v-model="injectionMessages[run.run_id]"
            @keyup.enter="injectMessage(run.run_id)"
            placeholder="Inject message..."
          />
          <button @click="injectMessage(run.run_id)">Inject</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue';

export default {
  name: 'WorkflowManager',
  setup() {
    const workflows = ref([]);
    const runs = ref([]);
    const loading = ref(false);
    const injectionMessages = ref({});
    let statusInterval;

    const loadWorkflows = async () => {
      try {
        const data = await listWorkflows();
        workflows.value = data;
      } catch (error) {
        console.error('Failed to load workflows:', error);
      }
    };

    const loadRuns = async () => {
      try {
        const data = await listRunningWorkflows();
        runs.value = data;
      } catch (error) {
        console.error('Failed to load runs:', error);
      }
    };

    const startWorkflow = async (workflowName) => {
      loading.value = true;
      try {
        await startWorkflow(workflowName, {
          message: 'Sample task',
          maxTurns: 50,
          sessionName: `workflow-${Date.now()}`
        });
        await loadRuns();
      } catch (error) {
        console.error('Failed to start workflow:', error);
      } finally {
        loading.value = false;
      }
    };

    const injectMessage = async (runId) => {
      const message = injectionMessages.value[runId];
      if (!message?.trim()) return;
      
      try {
        await injectMessage(runId, message);
        injectionMessages.value[runId] = '';
        await loadRuns();
      } catch (error) {
        alert('Failed to inject message: ' + error.message);
      }
    };

    onMounted(() => {
      loadWorkflows();
      loadRuns();
      
      // Poll for status updates
      statusInterval = setInterval(loadRuns, 5000);
    });

    onUnmounted(() => {
      if (statusInterval) {
        clearInterval(statusInterval);
      }
    });

    return {
      workflows,
      runs,
      loading,
      injectionMessages,
      startWorkflow,
      injectMessage
    };
  }
};
</script>
```

## TypeScript Interfaces

```typescript
interface WorkflowInfo {
  name: string;
  description: string;
  path: string;
  valid: boolean;
}

interface WorkflowStartRequest {
  message: string;
  max_turns?: number;
  session_id?: string;
  session_name?: string;
  user_id?: string;
  git_branch?: string;
  repository_url?: string;
  timeout?: number;
}

interface WorkflowStartResponse {
  run_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'killed';
  message: string;
  session_id: string;
  started_at: string;
}

interface WorkflowProgress {
  turns: number;
  max_turns?: number;
  current_phase: string;
  phases_completed: string[];
  is_running: boolean;
}

interface WorkflowMetrics {
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
  api_duration_ms?: number;
  performance_score?: number;
}

interface WorkflowResult {
  success: boolean;
  completion_type: string;
  message: string;
  final_output?: string;
  files_created: string[];
  git_commits: string[];
  files_changed: Array<{[key: string]: any}>;
}

interface WorkflowStatusResponse {
  run_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'killed';
  workflow_name: string;
  started_at: string;
  completed_at?: string;
  execution_time_seconds?: number;
  progress: WorkflowProgress;
  metrics: WorkflowMetrics;
  result: WorkflowResult;
}

interface MessageInjectionRequest {
  message: string;
}

interface MessageInjectionResponse {
  message_id: string;
  status: string;
  message: string;
  injected_at: string;
}
```

## Best Practices

### 1. Status Polling
- Poll every 5-10 seconds for active workflows
- Stop polling when workflow completes
- Handle network failures gracefully

### 2. Message Injection Timing
- Wait 5-10 seconds after workflow start before injection
- Implement retry logic for timing issues
- Handle 408 timeout responses appropriately

### 3. Error Handling
- Display user-friendly error messages
- Provide retry options for failed operations
- Log detailed errors for debugging

### 4. Performance
- Batch status updates when possible
- Use WebSockets for real-time updates if needed
- Implement proper loading states

### 5. User Experience
- Show progress indicators
- Provide clear status messages
- Allow users to cancel long-running workflows

This guide provides everything needed to integrate the Automagik workflow system into any frontend application. The examples show both React and Vue.js implementations, but the core API patterns can be adapted to any frontend framework.