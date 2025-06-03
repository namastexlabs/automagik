# ADR-002: Executor Abstraction Pattern

## Status
Proposed

## Context
To support multiple execution modes (Docker and Local), we need a clean abstraction that allows the ClaudeCodeAgent to work with different execution strategies without coupling to implementation details.

## Decision
Implement an abstract base class `ExecutorBase` that defines the contract for all executors, with the following key methods:

```python
class ExecutorBase(ABC):
    @abstractmethod
    async def execute_claude_task(request, agent_context) -> Dict
    
    @abstractmethod
    async def cleanup() -> None
    
    @abstractmethod
    async def get_execution_logs(execution_id: str) -> str
    
    @abstractmethod
    async def cancel_execution(execution_id: str) -> bool
```

### Implementation Structure:

```
executor_base.py      # Abstract base class
├── executor.py       # Docker implementation (renamed from current)
├── local_executor.py # Local process implementation
└── executor_factory.py # Factory for creating executors
```

## Consequences

### Positive
- **Clean Separation**: Docker and Local logic completely separated
- **Testability**: Can mock executors for testing
- **Extensibility**: Easy to add new execution modes
- **Type Safety**: Clear interface contract

### Negative
- **Refactoring Required**: Need to rename existing executor
- **Abstraction Overhead**: Additional layer of indirection

## Alternatives Considered

1. **Conditional Logic**: Using if/else in existing executor - rejected as messy
2. **Inheritance**: Having LocalExecutor inherit from DockerExecutor - rejected due to tight coupling
3. **Composition**: Rejected as executors share little common code

## Migration Impact
- Rename current `ClaudeExecutor` to `DockerExecutor`
- Update imports in `agent.py`
- No external API changes