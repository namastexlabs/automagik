# Automagik Agents System Architecture

## Executive Summary

Automagik Agents is a production-ready AI agent framework built over Pydantic AI that provides a robust foundation for creating, deploying, and managing AI agents. The system consists of three main architectural layers:

1. **Core Agent Framework**: Production-ready agent runtime with memory, tools, and API endpoints
2. **Claude Code Agent System**: Containerized Claude CLI execution for autonomous workflows  
3. **Genie Orchestrator**: Multi-workflow orchestration system with time machine capabilities *(Future)*

## 🏗️ Overall System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        A[HTTP Clients]
        B[CLI Tool]
        C[Docker Containers]
    end
    
    subgraph "API Gateway"
        D[FastAPI Application]
        E[Authentication Middleware]
        F[CORS & Exception Handling]
    end
    
    subgraph "Agent Runtime"
        G[Agent Factory]
        H[AutomagikAgent Base Class]
        I[Tool Registry]
        J[Memory System]
    end
    
    subgraph "Agent Implementations"
        K[Simple Agents]
        L[Claude Code Agent]
        M[Custom Agents]
    end
    
    subgraph "Data Layer"
        N[PostgreSQL Database]
        O[Neo4j Knowledge Graph]
        P[File System]
    end
    
    subgraph "External Integrations"
        Q[LLM Providers]
        R[MCP Tools]
        S[Third-party APIs]
    end
    
    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
    H --> J
    I --> K
    I --> L
    I --> M
    
    H --> N
    J --> O
    I --> P
    
    H --> Q
    I --> R
    M --> S
    
    style L fill:#e1f5fe
    style O fill:#f3e5f5
    style Q fill:#fff3e0
```

## 🤖 Core Agent Framework

### Agent Base Architecture

```mermaid
classDiagram
    class AutomagikAgent {
        <<abstract>>
        +config: AgentConfig
        +context: Dict
        +dependencies: BaseDependencies
        +db_id: int
        +initialize_prompts()
        +run(input_text, options)
        +process_message()
        +cleanup()
    }
    
    class SimpleAgent {
        +run()
        +_code_prompt_text: str
    }
    
    class ClaudeCodeAgent {
        +executor: ExecutorBase
        +container_manager: ContainerManager
        +run()
        +create_async_run()
        +get_run_status()
    }
    
    class CustomAgent {
        +custom_tools: List
        +run()
    }
    
    AutomagikAgent <|-- SimpleAgent
    AutomagikAgent <|-- ClaudeCodeAgent
    AutomagikAgent <|-- CustomAgent
    
    class AgentFactory {
        +agents_registry: Dict
        +discover_agents()
        +get_agent(name)
        +list_available_agents()
    }
    
    AgentFactory --> AutomagikAgent
```

### Agent Lifecycle Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Factory
    participant Agent
    participant Memory
    participant LLM
    
    Client->>API: POST /api/v1/agent/{name}/run
    API->>Factory: get_agent(name)
    Factory->>Agent: initialize()
    
    Agent->>Memory: load_active_prompt_template()
    Agent->>Memory: fetch_memory_variables()
    
    Client->>Agent: run(input_text)
    Agent->>Memory: get_filled_system_prompt()
    Agent->>LLM: send_request(prompt + input)
    LLM-->>Agent: response
    Agent->>Memory: queue_graphiti_episode()
    Agent-->>Client: AgentResponse
```

## 🐳 Claude Code Agent System

The Claude Code Agent represents a sophisticated container-based execution system for running Claude CLI in isolated environments.

### Container Execution Architecture

```mermaid
graph TB
    subgraph "Claude Code Agent"
        A[ClaudeCodeAgent]
        B[ExecutorFactory]
        C[ContainerManager]
        D[LocalExecutor]
        E[DockerExecutor]
    end
    
    subgraph "Docker Infrastructure"
        F[Docker Container]
        G[Volume Mounts]
        H[Workspace Volume]
        I[Credentials Volume]
    end
    
    subgraph "Workflow System"
        J[Workflow Configs]
        K[prompt.md]
        L[.mcp.json]
        M[allowed_tools.json]
    end
    
    subgraph "Execution Context"
        N[Claude CLI]
        O[MCP Tools]
        P[Git Repository]
        Q[Environment]
    end
    
    A --> B
    B --> D
    B --> E
    E --> C
    C --> F
    F --> G
    G --> H
    G --> I
    
    F --> J
    J --> K
    J --> L
    J --> M
    
    F --> N
    N --> O
    N --> P
    N --> Q
    
    style F fill:#e3f2fd
    style J fill:#f1f8e9
```

### Workflow Execution Flow

```mermaid
sequenceDiagram
    participant Client
    participant Agent
    participant Executor
    participant Container
    participant Claude
    participant Tools
    
    Client->>Agent: run(task, workflow_name)
    Agent->>Executor: execute_claude_task()
    Executor->>Container: create_container()
    Container->>Claude: claude -p --max-turns 30 "task"
    
    loop Execution Turns
        Claude->>Tools: mcp__tool__action()
        Tools-->>Claude: result
        Claude->>Claude: process_and_continue()
    end
    
    Claude-->>Container: JSON completion result
    Container->>Executor: extract_git_commits()
    Executor->>Agent: execution_result
    Agent-->>Client: AgentResponse with metadata
```

### Current Workflow Types

```mermaid
graph LR
    subgraph "Implemented Workflows"
        A[architect] --> B[System Design & Planning]
        C[implement] --> D[Feature Implementation]
        E[test] --> F[Testing & QA]
        G[review] --> H[Code Review]
        I[fix] --> J[Bug Resolution]
        K[refactor] --> L[Code Improvement]
        M[document] --> N[Documentation]
        O[pr] --> P[Pull Request Prep]
    end
    
    style A fill:#ffecb3
    style C fill:#c8e6c9
    style E fill:#ffcdd2
    style G fill:#d1c4e9
    style I fill:#ffab91
    style K fill:#b39ddb
    style M fill:#81c784
    style O fill:#64b5f6
```

## 🧠 Memory & Knowledge System

### Memory Architecture

```mermaid
graph TB
    subgraph "Memory Layer"
        A[MessageHistory]
        B[Memory Variables]
        C[Prompt Templates]
    end
    
    subgraph "Knowledge Graph (Neo4j/Graphiti)"
        D[Nodes]
        E[Relationships] 
        F[Episodes]
        G[Facts]
    end
    
    subgraph "Storage Groups"
        H[genie_patterns]
        I[genie_decisions]
        J[genie_procedures]
        K[genie_learning]
        L[genie_context]
    end
    
    A --> D
    B --> C
    C --> F
    
    D --> H
    E --> I
    F --> J
    G --> K
    D --> L
    
    style G fill:#e8f5e8
    style H fill:#fff3e0
    style I fill:#e3f2fd
```

### Memory Integration Flow

```mermaid
sequenceDiagram
    participant Agent
    participant Memory
    participant Graphiti
    participant Database
    
    Agent->>Memory: fetch_memory_variables()
    Memory->>Database: SELECT memories WHERE agent_id
    Database-->>Memory: memory records
    
    Agent->>Memory: get_filled_system_prompt()
    Memory->>Memory: template.render(variables)
    Memory-->>Agent: filled_prompt
    
    Agent->>Graphiti: search_memory_nodes(query)
    Graphiti-->>Agent: relevant_nodes
    
    Agent->>Agent: execute_with_context()
    
    Agent->>Graphiti: add_memory(episode)
    Graphiti->>Graphiti: process_background()
```

## 🎭 Genie Orchestrator System *(Future Architecture)*

The Genie system represents the next evolution - a multi-workflow orchestration platform with time machine capabilities.

### Genie Architecture Overview

```mermaid
graph TB
    subgraph "Genie Orchestrator (LangGraph)"
        A[Epic State Machine]
        B[Workflow Coordinator]
        C[Container Lifecycle Manager]
        D[Time Machine System]
        E[Human Intervention Handler]
    end
    
    subgraph "Container Fleet"
        F[Architect Container]
        G[Implement Container]
        H[Test Container]
        I[Review Container]
        J[Fix Container]
    end
    
    subgraph "Shared Systems"
        K[Agent Memory MCP]
        L[Slack Communication]
        M[Linear Task Management]
        N[Git Time Machine]
    end
    
    subgraph "Production Safety"
        O[Breaking Change Detection]
        P[Human Approval Gates]
        Q[Rollback System]
        R[Cost Monitoring]
    end
    
    A --> B
    B --> C
    C --> F
    C --> G
    C --> H
    C --> I
    C --> J
    
    B --> K
    B --> L
    B --> M
    B --> N
    
    A --> O
    O --> P
    D --> Q
    C --> R
    
    style A fill:#e1f5fe
    style D fill:#fff3e0
    style O fill:#ffebee
```

### Epic Workflow Orchestration

```mermaid
stateDiagram-v2
    [*] --> Epic_Planning
    Epic_Planning --> Architecture
    Architecture --> Human_Review_1
    Human_Review_1 --> Implementation : Approved
    Human_Review_1 --> Architecture : Changes Needed
    
    Implementation --> Testing
    Testing --> Review
    Review --> Fix : Issues Found
    Fix --> Testing
    Review --> Documentation : Passed
    
    Documentation --> PR_Creation
    PR_Creation --> Human_Review_2
    Human_Review_2 --> Merge : Approved
    Human_Review_2 --> Fix : Issues Found
    
    Merge --> [*]
    
    Architecture --> Time_Machine : Failed
    Implementation --> Time_Machine : Failed
    Testing --> Time_Machine : Failed
    
    Time_Machine --> Architecture : Rollback
    Time_Machine --> Implementation : Rollback
    Time_Machine --> Testing : Rollback
```

### Container Time Machine System

```mermaid
sequenceDiagram
    participant Genie
    participant Container
    participant Git
    participant Memory
    participant Human
    
    Genie->>Container: execute_workflow(attempt_1)
    Container->>Git: create_branch(genie/epic/workflow/attempt_1)
    Container-->>Genie: FAILED (scope_creep)
    
    Genie->>Memory: store_failure_analysis()
    Genie->>Human: escalate_via_slack()
    Human->>Genie: provide_guidance()
    
    Genie->>Git: rollback_to_checkpoint()
    Genie->>Container: execute_workflow(attempt_2, enhanced_config)
    Container->>Git: create_branch(genie/epic/workflow/attempt_2)
    Container-->>Genie: SUCCESS
    
    Genie->>Memory: store_success_pattern()
```

## 🛠️ Tool Integration & MCP System

### Tool Architecture

```mermaid
graph TB
    subgraph "Tool Registry"
        A[Tool Discovery]
        B[Tool Registration]
        C[Tool Validation]
    end
    
    subgraph "MCP Integration"
        D[MCP Servers]
        E[Linear MCP]
        F[Slack MCP]
        G[Git MCP]
        H[Memory MCP]
        I[Custom MCPs]
    end
    
    subgraph "Tool Categories"
        J[File Operations]
        K[Communication]
        L[Version Control]
        M[Task Management]
        N[Memory Operations]
    end
    
    A --> B
    B --> C
    C --> D
    
    D --> E
    D --> F
    D --> G
    D --> H
    D --> I
    
    E --> M
    F --> K
    G --> L
    H --> N
    I --> J
    
    style D fill:#f3e5f5
    style E fill:#e8f5e8
```

## 🔐 Security & Production Safety

### Security Architecture

```mermaid
graph TB
    subgraph "Authentication Layer"
        A[API Key Middleware]
        B[Rate Limiting]
        C[Request Validation]
    end
    
    subgraph "Container Security"
        D[Docker Isolation]
        E[Volume Restrictions]
        F[Network Policies]
        G[Resource Limits]
    end
    
    subgraph "Production Safety"
        H[Breaking Change Detection]
        I[Human Approval Gates]
        J[Rollback Mechanisms]
        K[Audit Logging]
    end
    
    subgraph "Data Protection"
        L[Encrypted Storage]
        M[Secret Management]
        N[Access Controls]
    end
    
    A --> D
    B --> E
    C --> F
    H --> I
    I --> J
    J --> K
    
    L --> M
    M --> N
    
    style H fill:#ffebee
    style I fill:#fff3e0
```

## 📊 Data Flow & Storage

### Database Schema Overview

```mermaid
erDiagram
    AGENTS {
        int id PK
        string name
        string type
        boolean active
        json config
        timestamp created_at
    }
    
    SESSIONS {
        int id PK
        string session_id UK
        int agent_id FK
        string status
        json metadata
        timestamp created_at
    }
    
    MESSAGES {
        int id PK
        int session_id FK
        string role
        text content
        json raw_payload
        timestamp created_at
    }
    
    MEMORIES {
        int id PK
        int agent_id FK
        string name
        text content
        string memory_type
        boolean active
    }
    
    PROMPTS {
        int id PK
        int agent_id FK
        string status_key
        text template
        boolean is_active
    }
    
    AGENTS ||--o{ SESSIONS : has
    SESSIONS ||--o{ MESSAGES : contains
    AGENTS ||--o{ MEMORIES : owns
    AGENTS ||--o{ PROMPTS : uses
```

## 🚀 Deployment Architecture

### Production Deployment

```mermaid
graph TB
    subgraph "Load Balancer"
        A[nginx/traefik]
    end
    
    subgraph "Application Tier"
        B[FastAPI Instance 1]
        C[FastAPI Instance 2]
        D[FastAPI Instance N]
    end
    
    subgraph "Container Runtime"
        E[Docker Engine]
        F[Claude Code Containers]
        G[Volume Manager]
    end
    
    subgraph "Data Tier"
        H[PostgreSQL Primary]
        I[PostgreSQL Replica]
        J[Neo4j Cluster]
        K[Redis Cache]
    end
    
    subgraph "Monitoring"
        L[Prometheus]
        M[Grafana]
        N[Log Aggregation]
    end
    
    A --> B
    A --> C
    A --> D
    
    B --> E
    C --> E
    D --> E
    
    E --> F
    E --> G
    
    B --> H
    C --> H
    D --> H
    H --> I
    
    B --> J
    C --> J
    D --> J
    
    L --> M
    L --> N
    
    style A fill:#e3f2fd
    style H fill:#e8f5e8
    style E fill:#fff3e0
```

## 🔄 Development Workflow

### Local Development Setup

```mermaid
graph LR
    subgraph "Development Environment"
        A[Developer Machine]
        B[Local PostgreSQL]
        C[Local Neo4j]
        D[Docker Desktop]
    end
    
    subgraph "Development Process"
        E[Code Changes]
        F[make dev]
        G[Agent Testing]
        H[Integration Tests]
    end
    
    subgraph "Version Control"
        I[Git Repository]
        J[Feature Branches]
        K[Pull Requests]
    end
    
    A --> E
    E --> F
    F --> G
    G --> H
    H --> I
    I --> J
    J --> K
    
    B --> F
    C --> F
    D --> F
```

## 📈 Scalability Considerations

### Horizontal Scaling Strategy

```mermaid
graph TB
    subgraph "API Layer Scaling"
        A[Load Balancer]
        B[Auto Scaling Group]
        C[Health Checks]
    end
    
    subgraph "Container Scaling"
        D[Container Orchestrator]
        E[Resource Quotas]
        F[Queue Management]
    end
    
    subgraph "Database Scaling"
        G[Read Replicas]
        H[Connection Pooling]
        I[Caching Layer]
    end
    
    subgraph "Memory System Scaling"
        J[Neo4j Cluster]
        K[Graph Sharding]
        L[Query Optimization]
    end
    
    A --> B
    B --> C
    D --> E
    E --> F
    G --> H
    H --> I
    J --> K
    K --> L
```

## 🎯 Key Architectural Principles

### Design Philosophy

1. **Modularity**: Each component is independently replaceable and testable
2. **Extensibility**: New agent types and tools can be added without core changes
3. **Production Safety**: Built-in safeguards for production environments with hundreds of clients
4. **Memory-Driven**: Knowledge graph enables learning and context persistence
5. **Container Isolation**: Secure, reproducible execution environments
6. **Human-in-the-Loop**: Strategic decision points for human oversight
7. **Time Machine**: Complete rollback and learning capabilities for failed executions

### Technical Stack

- **Backend**: FastAPI + Pydantic AI + PostgreSQL + Neo4j
- **Container Runtime**: Docker + Claude CLI
- **Memory System**: Graphiti Knowledge Graph
- **Communication**: Slack + Linear + MCP Protocol
- **Orchestration**: LangGraph (Future Genie System)
- **Security**: API Keys + Docker Isolation + Rate Limiting

---

This architecture enables rapid development of production-ready AI agents while maintaining the flexibility to scale from simple chatbots to sophisticated multi-workflow orchestration systems. The Claude Code Agent represents the evolution toward autonomous container-based AI workflows, with the future Genie system providing enterprise-grade orchestration capabilities. 