# Claude-Code SDK Capabilities Analysis

## 🔍 SDK Location & Structure

**Found at**: `/home/namastex/workspace/am-agents-labs/dev/claude-code-sdk-python/`
- **Version**: 0.0.10
- **Type**: Official Python SDK wrapping the Claude Code CLI
- **Core Module**: `src/claude_code_sdk/`

## ✅ What the SDK DOES Support

### 1. **Core Query Functionality** ✅
```python
async def query(*, prompt: str, options: ClaudeCodeOptions | None = None) -> AsyncIterator[Message]
```
- Async streaming interface
- Message type handling (User, Assistant, System, Result)
- Content blocks (Text, ToolUse, ToolResult)

### 2. **MCP Server Configuration** ✅
```python
@dataclass
class ClaudeCodeOptions:
    mcp_servers: dict[str, McpServerConfig] = field(default_factory=dict)
```
- Full MCP server support via `mcp_servers` dict
- Transport and environment configuration
- **Note**: Uses inline config, not file path

### 3. **Tool Management** ✅
```python
@dataclass
class ClaudeCodeOptions:
    allowed_tools: list[str] = field(default_factory=list)
    disallowed_tools: list[str] = field(default_factory=list)
    mcp_tools: list[str] = field(default_factory=list)
```
- Supports tool allow/deny lists
- MCP tool specification

### 4. **System Prompts** ✅
```python
@dataclass
class ClaudeCodeOptions:
    system_prompt: str | None = None
    append_system_prompt: str | None = None  # Still supported!
```
- Both `system_prompt` and `append_system_prompt` are supported
- Can use either or both

### 5. **Working Directory** ✅
```python
@dataclass
class ClaudeCodeOptions:
    cwd: str | Path | None = None
```
- Full working directory support

### 6. **Permission Modes** ✅
```python
PermissionMode = Literal["default", "acceptEdits", "bypassPermissions"]
```
- All permission modes supported

### 7. **Model Selection** ✅
```python
@dataclass
class ClaudeCodeOptions:
    model: str | None = None
```
- Custom model selection supported

### 8. **Max Thinking Tokens** ✅
```python
@dataclass
class ClaudeCodeOptions:
    max_thinking_tokens: int = 8000
```
- Field exists with default value
- **Confirmed**: Passed to CLI via transport

### 9. **Session Management** ✅
```python
@dataclass
class ClaudeCodeOptions:
    continue_conversation: bool = False
    resume: str | None = None
```
- Session continuation and resumption supported

### 10. **Environment Variables** ⚠️
- SDK sets `CLAUDE_CODE_ENTRYPOINT=sdk-py`
- Process spawning allows custom env via `anyio.open_process`
- **Gap**: No direct `extra_env` parameter in options

## ❌ What the SDK DOES NOT Support

### 1. **execute_until_first_response** ❌
- No built-in helper for early termination
- Must be implemented as a wrapper

### 2. **File-based Config Loading** ❌
- No automatic loading of:
  - `prompt.md` → system_prompt
  - `allowed_tools.json` → allowed_tools
  - `.mcp.json` → mcp_servers (requires dict, not path)

### 3. **Timeout Management** ❌
- No built-in timeout parameter
- Must wrap with `asyncio.wait_for`

### 4. **Environment Injection Hook** ❌
- No `extra_env` parameter in ClaudeCodeOptions
- Must be handled at subprocess level

## 🔧 Implementation Strategy

### 1. **Wrapper Architecture**
```python
class ClaudeSDKExecutor:
    async def execute(self, prompt: str, **kwargs) -> CLIResult:
        # Load file-based configs
        options = self._build_options(**kwargs)
        
        # Stream messages
        messages = []
        async for msg in query(prompt=prompt, options=options):
            messages.append(msg)
            
        return self._build_result(messages)
```

### 2. **execute_until_first_response Implementation**
```python
async def execute_until_first_response(self, prompt: str, **kwargs):
    options = self._build_options(**kwargs)
    
    # Create cancellable task
    task = asyncio.create_task(self._query_generator(prompt, options))
    
    # Collect until first assistant message
    messages = []
    async for msg in self._wrap_task_generator(task):
        messages.append(msg)
        if isinstance(msg, AssistantMessage) and msg.content:
            # Cancel remaining
            task.cancel()
            break
            
    return messages, task
```

### 3. **File-based Config Loading**
```python
def _build_options(self, workspace: Path, **kwargs) -> ClaudeCodeOptions:
    options = ClaudeCodeOptions()
    
    # Load prompt.md
    prompt_file = workspace / "prompt.md"
    if prompt_file.exists():
        options.system_prompt = prompt_file.read_text()
    
    # Load allowed_tools.json
    tools_file = workspace / "allowed_tools.json"
    if tools_file.exists():
        options.allowed_tools = json.loads(tools_file.read_text())
    
    # Load .mcp.json
    mcp_file = workspace / ".mcp.json"
    if mcp_file.exists():
        mcp_config = json.loads(mcp_file.read_text())
        options.mcp_servers = mcp_config.get("mcpServers", {})
    
    return options
```

### 4. **Environment Injection**
Since the SDK uses `SubprocessCLITransport` internally, we need to monkey-patch or extend:
```python
# Option 1: Monkey-patch the transport
original_connect = SubprocessCLITransport.connect

async def patched_connect(self):
    # Inject custom env before spawning
    if hasattr(self, '_custom_env'):
        os.environ.update(self._custom_env)
    return await original_connect(self)

SubprocessCLITransport.connect = patched_connect
```

## 📊 Gap Summary

| Feature | SDK Support | Implementation Needed |
|---------|------------|---------------------|
| Basic execution | ✅ | None |
| MCP config | ✅ (dict) | File loader |
| System prompts | ✅ | File loader |
| Tool lists | ✅ | File loader |
| max_thinking_tokens | ✅ | None |
| execute_until_first | ❌ | Wrapper function |
| Timeouts | ❌ | asyncio.wait_for |
| Environment injection | ❌ | Monkey-patch or subprocess hook |
| prompt.md loading | ❌ | File reader |
| allowed_tools.json | ❌ | File reader |

## 🎯 Recommendations

1. **The SDK is production-ready** for our use case
2. **All gaps can be filled** with a thin wrapper layer
3. **No SDK modifications needed** - just convenience functions
4. **append_system_prompt is still supported** - no migration needed there
5. **Environment injection** requires the most careful implementation

## 🚀 Next Steps

1. Create `ClaudeSDKExecutor` wrapper class
2. Implement file-based config loaders
3. Add execute_until_first_response helper
4. Handle environment injection via subprocess hooks
5. Maintain API compatibility with existing ClaudeCLIExecutor