# Orchestration Run Count Feature

## Overview

The orchestration system now supports a `run_count` parameter that allows you to limit the number of agent iterations for cost control. This is especially useful when running expensive LLM operations through orchestrated agents.

## Key Features

1. **Default to 1 Run**: By default, orchestrated agents will only run 1 iteration to minimize costs
2. **Override Max Rounds**: The `run_count` parameter will limit `max_rounds` if it's lower
3. **Individual Agent Support**: You can run individual agents through orchestration with limited iterations
4. **Team Orchestration**: Full team orchestration also respects the run_count limit

## API Usage

### Request Parameters

- `run_count` (int, default=1): Number of agent iterations to run
- `max_rounds` (int, default=3): Maximum orchestration rounds (will be limited by run_count)

### Examples

#### Single Agent with Limited Runs
```json
POST /api/v1/agent/langgraph-beta/run
{
  "message_content": "Fix the authentication bug",
  "run_count": 1,
  "enable_rollback": false
}
```

#### Team Orchestration with Cost Control
```json
POST /api/v1/agent/langgraph-alpha/run
{
  "message_content": "Implement user authentication API",
  "target_agents": ["beta", "gamma", "delta"],
  "max_rounds": 5,
  "run_count": 2,
  "enable_rollback": true
}
```

## Implementation Details

### How It Works

1. When a request is made with `run_count`, the orchestrator calculates:
   ```python
   effective_max_rounds = min(max_rounds, run_count)
   ```

2. The orchestration workflow uses `effective_max_rounds` to limit iterations

3. This applies to both LangGraph and fallback orchestration modes

### Code Changes

1. **Added `run_count` field to `AgentRunRequest` model** (`src/api/models.py`)
   - Default value is 1 for cost control
   - Field is included in API documentation

2. **Updated `handle_orchestrated_agent_run`** (`src/api/controllers/agent_controller.py`)
   - Now actually executes orchestration instead of just initializing
   - Calculates effective max rounds based on run_count
   - Supports individual agent runs without full team

3. **Updated orchestrator execution** (`src/agents/langgraph/shared/orchestrator.py`)
   - Both LangGraph and fallback workflows respect run_count
   - Proper logging of effective rounds

## Benefits

1. **Cost Control**: Prevent runaway costs from unlimited agent iterations
2. **Flexibility**: Can still set higher limits when needed
3. **Safety**: Default of 1 run prevents accidental high costs
4. **Transparency**: Clear logging of effective rounds used

## Testing

The feature has been tested with:
- Various combinations of run_count and max_rounds
- Single agent orchestration
- Team orchestration
- Edge cases (run_count > max_rounds)

All tests verify that the effective max rounds are correctly calculated as the minimum of run_count and max_rounds.