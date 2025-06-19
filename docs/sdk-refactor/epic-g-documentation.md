# Epic G - Documentation Updates

## Owner: @lina-workflow
## Branch: feature/sdk-migration (final epic)
## Priority: SEVENTH - After migration complete

## Objective
Update all documentation to reflect the SDK migration, including user guides, API docs, and migration notes.

## Detailed Implementation Steps

### G1. Update Main README

Update `/README.md`:

```markdown
# Agents Platform

## Claude Code Execution

The platform now uses the official `claude-code-sdk` for all Claude interactions.

### Installation
```bash
pip install -e .[dev]
# Includes claude-code-sdk>=0.0.10
```

### Configuration

#### System Prompts (Breaking Change)
- Place `prompt.md` in your workspace to set the system prompt
- **NEW**: Content now REPLACES the system prompt (previously appended)
- No prompt.md = vanilla Claude Code behavior

#### Supported Configuration Files
- `prompt.md` - System prompt (if present)
- `.mcp.json` - MCP server configuration
- `allowed_tools.json` - Allowed tool list
- `disallowed_tools.json` - Disallowed tool list

### Example Usage
```python
from agents.claude_code import ClaudeSDKExecutor, CLIEnvironmentManager

env_mgr = CLIEnvironmentManager()
executor = ClaudeSDKExecutor(env_mgr)

result = await executor.execute(
    "Your prompt here",
    workspace=Path("/path/to/workspace"),
    max_tokens=1000,
    max_thinking_tokens=50000
)
```
```

### G2. Create Migration Guide

Create `/docs/sdk_migration_guide.md`:

```markdown
# Claude Code SDK Migration Guide

## Overview
We've migrated from our custom CLI wrapper to the official `claude-code-sdk`.

## Breaking Changes

### 1. System Prompt Behavior
**Old**: `prompt.md` content was APPENDED to Claude's base prompt
**New**: `prompt.md` content REPLACES the system prompt entirely

**Migration Steps**:
1. Review all `prompt.md` files in your workflows
2. Ensure they contain complete system prompts
3. Test behavior with sample prompts

### 2. Environment Variables
The SDK handles environment differently. Custom env vars are now injected at the subprocess level.

### 3. Removed Features
- `--append-system-prompt` flag (use `system_prompt` instead)
- Custom CLI executable detection
- Direct CLI flag manipulation

## New Features

### 1. Improved Streaming
The SDK provides better streaming control and error handling.

### 2. Native MCP Support
MCP servers are now configured directly through the SDK.

### 3. Better Type Safety
Full Pydantic models for all options and responses.

## Configuration Examples

### Basic Workspace Setup
```
workspace/
├── prompt.md           # System prompt (optional)
├── .mcp.json          # MCP servers (optional)
├── allowed_tools.json # Tool whitelist (optional)
└── your_code_here.py
```

### prompt.md Example
```markdown
You are an expert Python developer with deep knowledge of async programming.
Focus on clean, maintainable code with comprehensive error handling.
Use type hints and follow PEP 8 conventions.
```

### .mcp.json Example
```json
{
  "servers": {
    "memory-server": {
      "command": "mcp-server-memory",
      "args": ["--port", "8080"]
    }
  }
}
```

## Troubleshooting

### Issue: Old append behavior expected
**Solution**: Update prompt.md to be a complete system prompt

### Issue: Environment variables not passed
**Solution**: Verify CLIEnvironmentManager.as_dict() includes your vars

### Issue: Performance regression
**Solution**: Check SDK version, report benchmarks

## Support
- GitHub Issues: [Link to repo]
- Migration questions: [Team channel]
```

### G3. Update API Documentation

Create `/docs/api/sdk_executor.md`:

```markdown
# ClaudeSDKExecutor API Reference

## Class: ClaudeSDKExecutor

Drop-in replacement for ClaudeCLIExecutor using the official claude-code-sdk.

### Constructor
```python
ClaudeSDKExecutor(environment_manager: CLIEnvironmentManager)
```

### Methods

#### execute()
Execute a prompt and return the complete result.

```python
async def execute(
    prompt: str,
    *,
    workspace: Path,
    max_tokens: Optional[int] = None,
    max_thinking_tokens: Optional[int] = None,
    model: Optional[str] = None,
    resume_session_id: Optional[str] = None,
    timeout: Optional[float] = None,
    **kwargs
) -> CLIResult
```

**Parameters**:
- `prompt`: The prompt to send to Claude
- `workspace`: Working directory path
- `max_tokens`: Maximum response tokens
- `max_thinking_tokens`: Maximum thinking tokens
- `model`: Model identifier (e.g., "claude-3-opus")
- `resume_session_id`: Resume previous session
- `timeout`: Execution timeout in seconds

**Returns**: `CLIResult` with messages, success status, and execution time

#### execute_until_first_response()
Execute until first assistant response for UI streaming optimization.

```python
async def execute_until_first_response(
    prompt: str,
    *,
    workspace: Path,
    **kwargs
) -> tuple[list[dict], asyncio.Task]
```

**Returns**: Tuple of (consumed_messages, continuation_task)

### Configuration Files

The executor automatically loads these files from the workspace:

| File | Purpose | Format |
|------|---------|--------|
| `prompt.md` | System prompt | Markdown text |
| `.mcp.json` | MCP servers | JSON object |
| `allowed_tools.json` | Tool whitelist | JSON array |
| `disallowed_tools.json` | Tool blacklist | JSON array |

### Example Usage

```python
# Basic execution
executor = ClaudeSDKExecutor(env_manager)
result = await executor.execute(
    "Explain the code in main.py",
    workspace=Path("/my/project")
)

# With options
result = await executor.execute(
    "Refactor for performance",
    workspace=Path("/my/project"),
    max_tokens=2000,
    max_thinking_tokens=100000,
    model="claude-3-opus-20240229"
)

# UI streaming
consumed, task = await executor.execute_until_first_response(
    "Generate a React component",
    workspace=Path("/my/app")
)
# Show consumed messages immediately
# Await task for complete response
```
```

### G4. Update Workflow Documentation

Update `/docs/workflows/README.md`:

```markdown
# Workflow System Documentation

## Claude Code Integration

All workflows now use the official Claude Code SDK.

### Workflow Configuration

Each workflow can include:
- `prompt.md` - Workflow-specific system prompt
- `.mcp.json` - Workflow-specific MCP configuration  
- `allowed_tools.json` - Workflow-specific tool restrictions

### Priority Order
1. Workflow-specific configuration (if exists)
2. Workspace configuration
3. Default SDK behavior

### Example Workflow Structure
```
workflows/
└── code-review/
    ├── prompt.md          # "You are a code reviewer focused on security..."
    ├── allowed_tools.json # ["Read", "Write", "Edit"]
    └── config.yaml        # Workflow metadata
```

### System Prompt Best Practices

Since `prompt.md` now REPLACES the system prompt:

✅ **Good** - Complete system prompt:
```markdown
You are an expert code reviewer with deep knowledge of security best practices.
Focus on identifying potential vulnerabilities, code smells, and performance issues.
Provide actionable feedback with specific examples.
```

❌ **Bad** - Fragment expecting append:
```markdown
Also check for SQL injection vulnerabilities.
```
```

### G5. Update Changelog

Add to `/CHANGELOG.md`:

```markdown
# Changelog

## [2.0.0] - 2024-12-19

### Changed
- **BREAKING**: Migrated to official `claude-code-sdk`
- **BREAKING**: `prompt.md` now sets `system_prompt` (replaces) instead of appending
- Improved streaming performance and reliability
- Better error handling and timeout support

### Added
- Native MCP server support via SDK
- Full type safety with Pydantic models
- Automatic configuration file loading
- Performance benchmarking suite

### Removed
- Custom CLI executor implementation
- CLI executable detection logic
- `--append-system-prompt` flag support
- Direct CLI flag manipulation

### Migration
See [SDK Migration Guide](docs/sdk_migration_guide.md) for detailed instructions.
```

## Success Criteria
- [ ] README.md updated with SDK information
- [ ] Migration guide created and comprehensive
- [ ] API documentation complete
- [ ] Workflow documentation updated
- [ ] Changelog reflects all changes
- [ ] All example code tested and working
- [ ] Documentation reviewed by team

## Documentation Deployment
1. Merge documentation updates to main
2. Trigger documentation site rebuild
3. Announce availability to team
4. Monitor for questions/confusion
5. Update based on feedback

## Files to Create/Modify
- MODIFY: `/README.md`
- CREATE: `/docs/sdk_migration_guide.md`
- CREATE: `/docs/api/sdk_executor.md`
- MODIFY: `/docs/workflows/README.md`
- MODIFY: `/CHANGELOG.md`
- MODIFY: Any workflow-specific docs

## Post-Launch Tasks
- [ ] Blog post about migration benefits
- [ ] Team training session
- [ ] Update external documentation
- [ ] Customer communication (if needed)