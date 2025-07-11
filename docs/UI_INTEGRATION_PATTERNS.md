# UI Integration Patterns for Agent Management

Quick reference patterns for common UI scenarios when integrating with the agent management API.

## 🎨 **Common UI Components & API Patterns**

### 1. Agent Selector Component

```typescript
interface Agent {
  id: number;
  name: string;
  description: string;
}

const AgentSelector = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  
  useEffect(() => {
    const fetchAgents = async () => {
      const response = await fetch('/api/v1/agents', {
        headers: { 'X-API-Key': API_KEY }
      });
      const agentList = await response.json();
      setAgents(agentList);
    };
    fetchAgents();
  }, []);

  return (
    <select>
      {agents.map(agent => (
        <option key={agent.id} value={agent.name}>
          {agent.name} - {agent.description}
        </option>
      ))}
    </select>
  );
};
```

### 2. Agent Chat Interface

```typescript
const AgentChat = ({ agentIdentifier }: { agentIdentifier: string }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (content: string) => {
    setIsLoading(true);
    
    try {
      const response = await fetch(`/api/v1/agent/${agentIdentifier}/run`, {
        method: 'POST',
        headers: {
          'X-API-Key': API_KEY,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message_content: content,
          session_name: `chat_${Date.now()}`
        })
      });

      const result = await response.json();
      
      if (result.success) {
        setMessages(prev => [...prev, 
          { role: 'user', content },
          { role: 'assistant', content: result.message }
        ]);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-interface">
      <MessageList messages={messages} />
      <MessageInput onSend={sendMessage} disabled={isLoading} />
    </div>
  );
};
```

### 3. Agent Configuration Panel

```typescript
const AgentConfigPanel = ({ agentId }: { agentId: number }) => {
  const [config, setConfig] = useState({
    model: '',
    description: '',
    active: true
  });

  const updateAgent = async () => {
    const response = await fetch(`/api/v1/agent/${agentId}`, {
      method: 'PUT',
      headers: {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(config)
    });

    if (response.ok) {
      toast.success('Agent updated successfully!');
    }
  };

  return (
    <form onSubmit={updateAgent}>
      <ModelSelector 
        value={config.model} 
        onChange={(model) => setConfig({...config, model})}
      />
      <TextArea 
        value={config.description}
        onChange={(description) => setConfig({...config, description})}
      />
      <Switch 
        checked={config.active}
        onChange={(active) => setConfig({...config, active})}
      />
      <button type="submit">Update Agent</button>
    </form>
  );
};
```

### 4. Prompt Management Interface

```typescript
const PromptManager = ({ agentIdentifier }: { agentIdentifier: string }) => {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<Prompt | null>(null);

  const createPrompt = async (promptData: PromptCreateRequest) => {
    const response = await fetch(`/api/v1/agent/${agentIdentifier}/prompt`, {
      method: 'POST',
      headers: {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(promptData)
    });

    if (response.ok) {
      const newPrompt = await response.json();
      setPrompts(prev => [...prev, newPrompt]);
    }
  };

  const activatePrompt = async (promptId: number) => {
    const response = await fetch(
      `/api/v1/agent/${agentIdentifier}/prompt/${promptId}/activate`,
      {
        method: 'POST',
        headers: { 'X-API-Key': API_KEY }
      }
    );

    if (response.ok) {
      // Refresh prompts list
      fetchPrompts();
    }
  };

  return (
    <div className="prompt-manager">
      <PromptList 
        prompts={prompts} 
        onSelect={setSelectedPrompt}
        onActivate={activatePrompt}
      />
      <PromptEditor 
        prompt={selectedPrompt}
        onSave={createPrompt}
      />
    </div>
  );
};
```

### 5. Async Operation Handler

```typescript
const useAsyncAgentRun = () => {
  const [runStatus, setRunStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
  const [result, setResult] = useState<string>('');

  const runAgentAsync = async (agentId: string, message: string) => {
    setRunStatus('running');
    
    // Start async run
    const startResponse = await fetch(`/api/v1/agent/${agentId}/run/async`, {
      method: 'POST',
      headers: {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ message_content: message })
    });

    const { run_id } = await startResponse.json();

    // Poll for completion
    const pollStatus = async () => {
      const statusResponse = await fetch(`/api/v1/run/${run_id}/status`, {
        headers: { 'X-API-Key': API_KEY }
      });
      
      const status = await statusResponse.json();
      
      if (status.status === 'completed') {
        setRunStatus('completed');
        setResult(status.result);
      } else if (status.status === 'failed') {
        setRunStatus('failed');
        setResult(status.error || 'Unknown error');
      } else {
        // Still running, poll again
        setTimeout(pollStatus, 1000);
      }
    };

    pollStatus();
  };

  return { runAgentAsync, runStatus, result };
};
```

## 🎯 **Form Validation Patterns**

### Agent Creation Form

```typescript
const AgentCreationForm = () => {
  const [formData, setFormData] = useState({
    sourceAgent: '',
    newName: '',
    description: '',
    model: 'openai:gpt-4'
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.newName.trim()) {
      newErrors.newName = 'Agent name is required';
    } else if (!/^[a-zA-Z0-9_-]+$/.test(formData.newName)) {
      newErrors.newName = 'Agent name can only contain letters, numbers, underscores, and hyphens';
    }

    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    try {
      const response = await fetch(`/api/v1/agent/${formData.sourceAgent}/copy`, {
        method: 'POST',
        headers: {
          'X-API-Key': API_KEY,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          new_name: formData.newName,
          description: formData.description,
          model: formData.model
        })
      });

      if (response.ok) {
        const result = await response.json();
        toast.success(`Agent '${result.new_agent}' created successfully!`);
        // Reset form or redirect
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to create agent');
      }
    } catch (error) {
      toast.error('Network error occurred');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <SourceAgentSelector 
        value={formData.sourceAgent}
        onChange={(sourceAgent) => setFormData({...formData, sourceAgent})}
        error={errors.sourceAgent}
      />
      <Input
        label="Agent Name"
        value={formData.newName}
        onChange={(newName) => setFormData({...formData, newName})}
        error={errors.newName}
      />
      <TextArea
        label="Description"
        value={formData.description}
        onChange={(description) => setFormData({...formData, description})}
        error={errors.description}
      />
      <ModelSelector
        value={formData.model}
        onChange={(model) => setFormData({...formData, model})}
      />
      <button type="submit">Create Agent</button>
    </form>
  );
};
```

## 🔄 **State Management Patterns**

### React Query Integration

```typescript
// Custom hooks for agent management
export const useAgents = () => {
  return useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      const response = await fetch('/api/v1/agents', {
        headers: { 'X-API-Key': API_KEY }
      });
      return response.json();
    }
  });
};

export const useAgentPrompts = (agentId: string) => {
  return useQuery({
    queryKey: ['agent-prompts', agentId],
    queryFn: async () => {
      const response = await fetch(`/api/v1/agent/${agentId}/prompt`, {
        headers: { 'X-API-Key': API_KEY }
      });
      return response.json();
    },
    enabled: !!agentId
  });
};

export const useUpdateAgent = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ agentId, data }: { agentId: string, data: any }) => {
      const response = await fetch(`/api/v1/agent/${agentId}`, {
        method: 'PUT',
        headers: {
          'X-API-Key': API_KEY,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      });
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
    }
  });
};
```

## 🚨 **Error Handling Patterns**

```typescript
const handleApiError = (error: any) => {
  if (error.status === 404) {
    toast.error('Agent not found. Please check the agent name or ID.');
  } else if (error.status === 401) {
    toast.error('Authentication failed. Please check your API key.');
  } else if (error.status === 422) {
    const validationErrors = error.detail;
    validationErrors.forEach((err: any) => {
      toast.error(`${err.loc.join('.')}: ${err.msg}`);
    });
  } else {
    toast.error('An unexpected error occurred. Please try again.');
  }
};

const apiCall = async (url: string, options: RequestInit) => {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json',
        ...options.headers
      }
    });

    if (!response.ok) {
      const error = await response.json();
      throw { status: response.status, ...error };
    }

    return response.json();
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};
```

## 🎛️ **Model Selector Component**

```typescript
const ModelSelector = ({ value, onChange }: { value: string, onChange: (model: string) => void }) => {
  const models = [
    { 
      provider: 'OpenAI',
      models: [
        { id: 'openai:gpt-4', name: 'GPT-4', description: 'Most capable model' },
        { id: 'openai:gpt-4-turbo', name: 'GPT-4 Turbo', description: 'Faster responses' },
        { id: 'openai:gpt-3.5-turbo', name: 'GPT-3.5 Turbo', description: 'Fast and efficient' }
      ]
    },
    {
      provider: 'Anthropic',
      models: [
        { id: 'anthropic:claude-3-sonnet-20240229', name: 'Claude 3 Sonnet', description: 'Balanced performance' },
        { id: 'anthropic:claude-3-haiku-20240307', name: 'Claude 3 Haiku', description: 'Fast responses' }
      ]
    }
  ];

  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      {models.map(provider => (
        <optgroup key={provider.provider} label={provider.provider}>
          {provider.models.map(model => (
            <option key={model.id} value={model.id}>
              {model.name} - {model.description}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
};
```

These patterns should provide a solid foundation for building UI components that integrate seamlessly with the agent management API!