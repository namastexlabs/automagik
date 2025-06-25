# Conversation Branching - Visual Diagrams

## Complete Branching Flow Diagram

```mermaid
graph TD
    A[Original Conversation] --> B[User Edits Message]
    B --> C{Create Branch?}
    C -->|Yes| D[POST /messages/id/branch]
    C -->|Inline| E[PUT /messages/id with create_branch=true]
    
    D --> F[Create New Session]
    E --> F
    
    F --> G[Copy Message History to Branch Point]
    G --> H[Create Edited Message in Branch]
    H --> I{run_agent = true?}
    
    I -->|Yes| J[Identify Agent from Parent Session]
    I -->|No| K[Branch Creation Complete]
    
    J --> L[Execute Agent with Branch Context]
    L --> M[Save Agent Response to Branch]
    M --> N[Branch Creation Complete with Agent Response]
    
    K --> O[Return Branch Session ID]
    N --> O
```

## Session Tree Structure

```mermaid
graph TD
    Root[Main Session: Customer Support Chat]
    
    Root --> B1[Branch 1: Billing Issue]
    Root --> B2[Branch 2: Technical Problem]
    Root --> B3[Branch 3: Feature Request]
    
    B1 --> B1A[Sub-branch: Refund Process]
    B1 --> B1B[Sub-branch: Payment Update]
    
    B2 --> B2A[Sub-branch: Account Access]
    B2 --> B2B[Sub-branch: App Crashes]
    
    B3 --> B3A[Sub-branch: Mobile Features]
    B3 --> B3B[Sub-branch: Web Features]
    
    style Root fill:#e1f5fe
    style B1 fill:#fff3e0
    style B2 fill:#fff3e0
    style B3 fill:#fff3e0
    style B1A fill:#f3e5f5
    style B1B fill:#f3e5f5
    style B2A fill:#f3e5f5
    style B2B fill:#f3e5f5
    style B3A fill:#f3e5f5
    style B3B fill:#f3e5f5
```

## API Interaction Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Database
    participant Agent
    
    User->>API: POST /messages/{id}/branch
    Note over User,API: {edited_content, branch_name, run_agent: true}
    
    API->>Database: Get original message & session
    Database-->>API: Message & session data
    
    API->>Database: Create new branch session
    Database-->>API: New session ID
    
    API->>Database: Copy messages to branch point
    Database-->>API: Messages copied
    
    API->>Database: Create edited message
    Database-->>API: Edited message created
    
    alt run_agent = true
        API->>Database: Get agent from parent session
        Database-->>API: Agent information
        
        API->>Agent: Execute with branch context
        Agent-->>API: Agent response
        
        API->>Database: Save agent response
        Database-->>API: Response saved
    end
    
    API-->>User: Branch creation response
    Note over User,API: {branch_session_id, status: success}
```

## Database Relationship Diagram

```mermaid
erDiagram
    SESSIONS {
        uuid id PK
        uuid parent_session_id FK
        uuid branch_point_message_id FK
        enum branch_type
        boolean is_main_branch
        string name
        timestamp created_at
    }
    
    MESSAGES {
        uuid id PK
        uuid session_id FK
        string role
        text text_content
        timestamp created_at
    }
    
    AGENTS {
        int id PK
        string name
        boolean active
    }
    
    SESSIONS ||--o{ SESSIONS : "parent-child"
    SESSIONS ||--o{ MESSAGES : "contains"
    SESSIONS }o--|| AGENTS : "uses"
    MESSAGES ||--o| SESSIONS : "branch_point"
```

## Message Flow Timeline

```mermaid
timeline
    title Conversation Evolution with Branching
    
    section Original Conversation
        T1 : User: "I need help with deployment"
        T2 : Agent: "What platform are you deploying to?"
        T3 : User: "Cloud platform"
        T4 : Agent: "Which cloud provider?"
    
    section Branch Creation (T3 Edit)
        T3-Branch : User: "On-premise servers"
               : Copy T1, T2 to branch
               : Create edited T3 in branch
    
    section Continued Conversations
        T5-Main : Agent: "AWS, Google Cloud, or Azure?"
               : (continues from original T3)
        
        T5-Branch : Agent: "What's your server setup?"
                 : (continues from edited T3)
    
    section Independent Evolution
        T6-Main : User: "AWS with EKS"
        T6-Branch : User: "Ubuntu servers with Docker"
```

## Agent Execution Decision Tree

```mermaid
flowchart TD
    Start[Branch Creation Request] --> Check{run_agent parameter?}
    
    Check -->|false| NoAgent[Skip Agent Execution]
    Check -->|true| GetParent[Get Parent Session]
    
    GetParent --> HasAgent{Parent has agent_id?}
    
    HasAgent -->|No| LogWarning[Log: No agent found]
    HasAgent -->|Yes| GetAgent[Fetch Agent Details]
    
    GetAgent --> AgentExists{Agent exists & active?}
    
    AgentExists -->|No| LogError[Log: Agent not found/inactive]
    AgentExists -->|Yes| CreateRequest[Create AgentRunRequest]
    
    CreateRequest --> ExecuteAgent[Call handle_agent_run]
    
    ExecuteAgent --> Success{Execution successful?}
    
    Success -->|Yes| SaveResponse[Save Agent Response to Branch]
    Success -->|No| LogIssue[Log: Agent execution issues]
    
    NoAgent --> Complete[Branch Creation Complete]
    LogWarning --> Complete
    LogError --> Complete
    SaveResponse --> Complete
    LogIssue --> Complete
    
    style Complete fill:#c8e6c9
    style SaveResponse fill:#e8f5e8
    style LogWarning fill:#fff3e0
    style LogError fill:#ffebee
    style LogIssue fill:#ffebee
```

## Branching Use Case Examples

### Example 1: Customer Support Escalation

```mermaid
graph LR
    A["Customer: 'My order is wrong'"] --> B["Agent: 'Let me check your order'"]
    B --> C["Customer: 'It was supposed to be blue'"]
    
    C --> D1["Branch 1: Return Process"]
    C --> D2["Branch 2: Exchange Process"] 
    C --> D3["Branch 3: Discount Offer"]
    
    D1 --> E1["Agent: 'I'll create a return label'"]
    D2 --> E2["Agent: 'Let's arrange an exchange'"]
    D3 --> E3["Agent: 'I can offer 20% off your next order'"]
    
    style A fill:#e3f2fd
    style B fill:#e8f5e8
    style C fill:#e3f2fd
    style D1 fill:#fff3e0
    style D2 fill:#fff3e0
    style D3 fill:#fff3e0
    style E1 fill:#e8f5e8
    style E2 fill:#e8f5e8
    style E3 fill:#e8f5e8
```

### Example 2: Technical Troubleshooting

```mermaid
graph TD
    A["User: 'App keeps crashing'"] --> B["Agent: 'What device are you using?'"]
    B --> C["User: 'iPhone'"]
    
    C -.->|Edit| C1["User: 'Android phone'"]
    C -.->|Edit| C2["User: 'Web browser'"]
    
    C --> D["iOS-specific troubleshooting"]
    C1 --> D1["Android-specific troubleshooting"]
    C2 --> D2["Web-specific troubleshooting"]
    
    D --> E["Check iOS version compatibility"]
    D1 --> E1["Check Android permissions"]
    D2 --> E2["Check browser compatibility"]
    
    style A fill:#e3f2fd
    style B fill:#e8f5e8
    style C fill:#e3f2fd
    style C1 fill:#e1f5fe
    style C2 fill:#e1f5fe
    style D fill:#e8f5e8
    style D1 fill:#e8f5e8
    style D2 fill:#e8f5e8
```

## Branch Management Dashboard Concept

```mermaid
graph TB
    Dashboard[Branch Management Dashboard]
    
    Dashboard --> TreeView[Tree View]
    Dashboard --> ListView[List View]
    Dashboard --> Analytics[Analytics]
    
    TreeView --> Visual[Visual Tree Representation]
    TreeView --> Navigation[Click-to-Navigate]
    
    ListView --> BranchList[Chronological Branch List]
    ListView --> Search[Search & Filter]
    
    Analytics --> Metrics[Usage Metrics]
    Analytics --> Performance[Performance Stats]
    
    Visual --> Nodes[Session Nodes]
    Visual --> Connections[Parent-Child Connections]
    
    Nodes --> NodeInfo[Session Info: Name, Created, Messages]
    Connections --> BranchInfo[Branch Info: Type, Point, Agent Status]
    
    style Dashboard fill:#e8eaf6
    style TreeView fill:#f3e5f5
    style ListView fill:#e8f5e8
    style Analytics fill:#fff3e0
```

## Performance Optimization Strategies

```mermaid
flowchart LR
    Optimize[Performance Optimization] --> DB[Database Level]
    Optimize --> API[API Level]
    Optimize --> Caching[Caching Layer]
    
    DB --> Indexes[Strategic Indexes]
    DB --> Partitioning[Table Partitioning]
    DB --> Queries[Optimized Queries]
    
    API --> Pagination[Paginated Responses]
    API --> Async[Async Operations]
    API --> Batch[Batch Processing]
    
    Caching --> Session[Session Cache]
    Caching --> Message[Message Cache]
    Caching --> Tree[Tree Structure Cache]
    
    Indexes --> ParentIdx[parent_session_id index]
    Indexes --> BranchIdx[branch_point_message_id index]
    Indexes --> MainIdx[is_main_branch index]
```

These diagrams provide comprehensive visual documentation for the conversation branching feature, covering everything from high-level flows to detailed technical implementation and use cases.