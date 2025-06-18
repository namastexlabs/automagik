# Epic D - Flag Fidelity & File-based Convenience

## Owner: @builder-workflow
## Branch: feature/sdk-migration (after Epic B)
## Priority: FOURTH - Depends on Epic B

## Objective
Ensure all CLI flags and file-based conveniences work correctly with the SDK, using `system_prompt` instead of `append_system_prompt`.

## Detailed Implementation Steps

### D1. Max Thinking Tokens Support
Based on SDK analysis, this is already supported! No monkey-patching needed:

```python
# In sdk_executor.py - already handled in _build_options
if max_thinking_tokens:
    options.max_thinking_tokens = max_thinking_tokens
```

✅ **No additional work needed** - SDK handles this correctly

### D2. System Prompt Loading (NOT append)
Implement the new `prompt.md` → `system_prompt` behavior:

```python
# In sdk_executor.py, update _build_options method

def _build_options(self, workspace: Path, **kwargs) -> ClaudeCodeOptions:
    """Build options with new system_prompt behavior."""
    options = ClaudeCodeOptions()
    
    # ... other options ...
    
    # NEW BEHAVIOR: prompt.md → system_prompt (not append)
    prompt_file = workspace / "prompt.md"
    if prompt_file.exists():
        # Use system_prompt to REPLACE default, not append
        prompt_content = prompt_file.read_text().strip()
        if prompt_content:  # Only set if non-empty
            options.system_prompt = prompt_content
            logger.info(f"Loaded system prompt from {prompt_file} ({len(prompt_content)} chars)")
    else:
        # No prompt.md = vanilla Claude Code behavior
        logger.debug("No prompt.md found, using vanilla Claude Code")
    
    return options
```

### D3. Allowed/Disallowed Tools File Loading
Implement automatic loading of tool configurations:

```python
# In sdk_executor.py, enhance _build_options

def _build_options(self, workspace: Path, **kwargs) -> ClaudeCodeOptions:
    options = ClaudeCodeOptions()
    
    # ... other options ...
    
    # Load allowed tools if file exists and not explicitly provided
    if 'allowed_tools' not in kwargs:
        allowed_tools_file = workspace / "allowed_tools.json"
        if allowed_tools_file.exists():
            try:
                with open(allowed_tools_file) as f:
                    tools_list = json.load(f)
                    if isinstance(tools_list, list):
                        options.allowed_tools = tools_list
                        logger.info(f"Loaded {len(tools_list)} allowed tools from file")
                    else:
                        logger.warning("allowed_tools.json must contain a JSON array")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid allowed_tools.json: {e}")
    
    # Load disallowed tools if file exists
    if 'disallowed_tools' not in kwargs:
        disallowed_tools_file = workspace / "disallowed_tools.json"
        if disallowed_tools_file.exists():
            try:
                with open(disallowed_tools_file) as f:
                    tools_list = json.load(f)
                    if isinstance(tools_list, list):
                        options.disallowed_tools = tools_list
                        logger.info(f"Loaded {len(tools_list)} disallowed tools from file")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid disallowed_tools.json: {e}")
    
    return options
```

### D4. MCP Configuration Loading
Load MCP servers from `.mcp.json`:

```python
# In sdk_executor.py, add to _build_options

# Load MCP configuration
mcp_config_file = workspace / ".mcp.json"
if mcp_config_file.exists():
    try:
        with open(mcp_config_file) as f:
            mcp_data = json.load(f)
            
        # SDK expects mcp_servers dict
        if 'servers' in mcp_data and isinstance(mcp_data['servers'], dict):
            options.mcp_servers = mcp_data['servers']
            logger.info(f"Loaded {len(mcp_data['servers'])} MCP servers from config")
        else:
            logger.warning(".mcp.json must contain 'servers' object")
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid .mcp.json: {e}")
```

### D5. Configuration Priority System
Implement proper priority for configuration sources:

```python
class ConfigPriority:
    """Configuration loading priority system."""
    
    @staticmethod
    def load_with_priority(
        workspace: Path,
        explicit_value: Optional[Any],
        file_name: str,
        default: Any = None
    ) -> Any:
        """
        Load configuration with priority:
        1. Explicit parameter (if provided)
        2. File in workspace (if exists)
        3. Default value
        """
        if explicit_value is not None:
            return explicit_value
            
        file_path = workspace / file_name
        if file_path.exists():
            try:
                if file_name.endswith('.json'):
                    with open(file_path) as f:
                        return json.load(f)
                else:
                    return file_path.read_text().strip()
            except Exception as e:
                logger.error(f"Failed to load {file_name}: {e}")
                
        return default
```

### D6. Testing File-based Loading

```python
# tests/test_file_loading.py

@pytest.mark.asyncio
async def test_system_prompt_loading(tmp_path):
    """Test prompt.md loads as system_prompt (not append)."""
    prompt_content = "You are a Python expert. Be concise."
    (tmp_path / "prompt.md").write_text(prompt_content)
    
    executor = ClaudeSDKExecutor(mock_env_mgr)
    options = executor._build_options(tmp_path)
    
    assert options.system_prompt == prompt_content
    assert not hasattr(options, 'append_system_prompt')

@pytest.mark.asyncio
async def test_no_prompt_file(tmp_path):
    """Test vanilla Claude Code when no prompt.md exists."""
    executor = ClaudeSDKExecutor(mock_env_mgr)
    options = executor._build_options(tmp_path)
    
    assert options.system_prompt is None

@pytest.mark.asyncio
async def test_tools_loading(tmp_path):
    """Test allowed/disallowed tools loading."""
    allowed = ["Read", "Write", "Edit"]
    disallowed = ["Bash", "WebSearch"]
    
    (tmp_path / "allowed_tools.json").write_text(json.dumps(allowed))
    (tmp_path / "disallowed_tools.json").write_text(json.dumps(disallowed))
    
    executor = ClaudeSDKExecutor(mock_env_mgr)
    options = executor._build_options(tmp_path)
    
    assert options.allowed_tools == allowed
    assert options.disallowed_tools == disallowed
```

## Migration Documentation

Create clear documentation for the behavior change:

```markdown
# prompt.md Behavior Change

## Old Behavior (CLI)
- prompt.md content was APPENDED to Claude's base prompt
- Used `--append-system-prompt` flag

## New Behavior (SDK)
- prompt.md content REPLACES the system prompt entirely
- Uses `system_prompt` parameter
- If no prompt.md exists, Claude Code runs with default behavior

## Migration Guide
1. Review your prompt.md files
2. Ensure they're complete system prompts, not fragments
3. Test behavior with new SDK executor
```

## Success Criteria
- [ ] ✅ max_thinking_tokens works without modification
- [ ] prompt.md loads as system_prompt (not append)
- [ ] allowed_tools.json auto-loads when present
- [ ] disallowed_tools.json auto-loads when present
- [ ] .mcp.json servers configuration loads correctly
- [ ] Explicit parameters override file-based configs
- [ ] Clear documentation of behavior changes
- [ ] All file loading has error handling

## Files to Modify
- `/src/agents/claude_code/sdk_executor.py` (enhance _build_options)
- `/tests/test_file_loading.py` (new)
- `/docs/prompt_behavior_change.md` (new)

## Communication Plan
1. Document the prompt.md behavior change prominently
2. Update all workflow prompt.md files if needed
3. Notify team about semantic change
4. Update workflow documentation