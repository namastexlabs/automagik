# Fix SimpleAgent Dynamic Variables in System Prompt

## Analysis

The current issue involves dynamic variables in prompt.py that should update with each run of the SimpleAgent. Based on my analysis of the codebase, there are several template variables in the system prompt:

```
{{run_id}}
{{personal_attributes}}
{{technical_knowledge}}
{{user_preferences}}
```

The `{{run_id}}` variable should be handled differently than the others - it should be retrieved and incremented from the `run_id` column in the agents table in the database. The other variables should be stored and retrieved from the memories system.

The core problem is that these variables are only set once during agent initialization in the `SimpleAgent.__init__` method:

```python
# Format the prompt with variables
system_prompt = SIMPLE_AGENT_PROMPT
for key, value in template_vars.items():
    system_prompt = system_prompt.replace(f"{{{{{key}}}}}", value)
```

This means:
1. The run_id isn't being incremented with each run
2. Memory variables aren't being refreshed before each message is processed
3. The system prompt remains static after initialization

Looking at the logs, we can see that the SimpleAgent is properly initialized but the system prompt variables aren't being dynamically updated.

Additionally, the variables should be created in the memories table during agent initialization if they don't already exist, with default placeholder values.

## Plan

1. Refactor to use PydanticAI's native dynamic system prompts with the `@agent.system_prompt` decorator
2. Create a method to initialize all memory variables during agent startup
3. Implement proper run_id handling via dynamic system prompts
4. Create memory entries for all template variables if they don't exist

## Execution

I'll update the SimpleAgent class in `src/agents/simple/simple_agent/agent.py` with the following changes:

1. Add an `_initialize_memory_variables` method that:
   - Gets all template variables from the prompt template
   - Creates memory entries for each variable if they don't exist
   - Uses sensible default values for new memory entries

2. Implement proper dynamic system prompts using PydanticAI's decorator:
   ```python
   @agent_instance.system_prompt
   def add_run_id(ctx: RunContext[SimpleAgentDependencies]) -> str:
       """Add the current run_id to the system prompt."""
       # Increment run_id in database
       run_id = ctx.deps.increment_run_id()
       return f"Current memory ID: {run_id}"
   ```

3. Add similar dynamic system prompt functions for other memory variables:
   ```python
   @agent_instance.system_prompt
   def add_memory_variables(ctx: RunContext[SimpleAgentDependencies]) -> str:
       """Add memory variables to the system prompt."""
       personal_attributes = await ctx.deps.get_memory("personal_attributes") or "None stored yet"
       technical_knowledge = await ctx.deps.get_memory("technical_knowledge") or "None stored yet"
       user_preferences = await ctx.deps.get_memory("user_preferences") or "None stored yet"
       
       return f"""
       ## Technical Knowledge
       - {personal_attributes}
       - {technical_knowledge}
       - {user_preferences}
       """
   ```

4. Update the initialization to detect template variables and ensure they exist in the memory system

5. Remove our custom implementation that manually reinitializes the agent on each run

## Testing

Testing should verify:

1. The run_id increments with each message sent to the agent
2. Memory variables update when their values change
3. Memory entries are created during initialization if they don't exist

To test:

```bash
# Ensure memories are created at initialization
automagik-agents agent discovery run

# Send a message and check logs for run_id increment
automagik-agents agent run message --agent simple_agent --message "Hello"

# Store a memory value
automagik-agents agent run message --agent simple_agent --message "Please remember my name is John"

# Verify memory is included in next run
automagik-agents agent run message --agent simple_agent --message "What is my name?"
```

Check the logs to verify that:
- Memory entries are created if they don't exist
- The run_id is incremented before each message
- The memory values are correctly retrieved
- The system prompt is updated via PydanticAI's dynamic system prompts

## Summary

Files modified:
- `src/agents/simple/simple_agent/agent.py` - Refactored to use PydanticAI's dynamic system prompts and added memory initialization

The solution ensures that:
1. Template variables are properly identified during initialization
2. Memory entries are created for all variables if they don't exist 
3. The system prompt is dynamically updated using PydanticAI's native mechanisms
4. The run_id is incremented with each run

This avoids reimplementing dynamic system prompts and properly uses the PydanticAI framework as intended. 