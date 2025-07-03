# Example Agent Template

This is a template for creating custom agents that work with the Automagik framework.

## Structure

- `agent.py` - The main agent implementation
- `README.md` - This file

## How to Use

1. Copy this entire directory to your agents folder (default: `~/.automagik/agents/`)
2. Rename the directory to match your agent name (e.g., `my_custom_agent`)
3. Modify the `agent.py` file:
   - Update the `AGENT_PROMPT` to define your agent's behavior
   - Rename the `ExampleAgent` class to match your agent
   - Add custom tools if needed
   - Configure the model and other settings

## Example Customization

```python
# Define a custom prompt for a code review agent
AGENT_PROMPT = """You are an expert code reviewer.
You analyze code for:
- Security vulnerabilities
- Performance issues
- Code style and best practices
- Potential bugs

Provide constructive feedback with specific suggestions."""

# Rename the class
class CodeReviewAgent(AutomagikAgent):
    # ... rest of the implementation
```

## Adding Tools

To add custom tools to your agent:

```python
from src.tools import MyCustomTool

class MyAgent(AutomagikAgent):
    def __init__(self, config):
        super().__init__(config)
        # ... other initialization
        
        # Register a custom tool
        self.tool_registry.register_tool(MyCustomTool())
```

## Testing Your Agent

After creating your agent, test it using the Automagik CLI:

```bash
# List available agents (your agent should appear)
automagik agents list

# Test your agent
automagik agents run -a your_agent_name -m "Test message"

# Or use the API
curl -X POST http://localhost:8000/api/v1/agents/your_agent_name/invoke \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"message": "Test message"}'
```

## Configuration

Agents can be configured through:
1. The `config` parameter passed to `create_agent()`
2. Environment variables
3. The Automagik configuration file

Common configuration options:
- `model` - The LLM model to use (e.g., "openai:gpt-4", "anthropic:claude-3")
- `temperature` - Model temperature (0.0 - 2.0)
- `max_tokens` - Maximum response length
- Custom parameters specific to your agent