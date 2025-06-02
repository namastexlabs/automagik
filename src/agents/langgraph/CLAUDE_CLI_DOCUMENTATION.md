# Claude CLI Command Execution Documentation

This document provides an in-depth analysis of the Claude CLI command execution process, preparing for refactoring into a separate `claude-code` agent type folder.

## Table of Contents
1. [Overview](#overview)
2. [Claude CLI Parameters](#claude-cli-parameters)
3. [Command Building Process](#command-building-process)
4. [Session Management](#session-management)
5. [Streaming Output Mechanism](#streaming-output-mechanism)
6. [Process Monitoring](#process-monitoring)
7. [Error Handling](#error-handling)
8. [Integration Points](#integration-points)
9. [Refactoring Considerations](#refactoring-considerations)

## Overview

The Claude CLI execution is managed through the `EnhancedCLINode` class in `shared/cli_node.py`. This wrapper provides:
- Asynchronous subprocess execution
- Real-time output streaming
- Session persistence and resumption
- Process monitoring and kill switches
- Git snapshot integration
- MCP configuration management

## Claude CLI Parameters

### Core Command Structure
```bash
claude [options] [command] [prompt]
```

### Available Options

#### 1. **Basic Options**
- `-d, --debug` - Enable debug mode
- `--verbose` - Override verbose mode from config
- `-v, --version` - Output version number
- `-h, --help` - Display help

#### 2. **Output Control**
- `-p, --print` - Print response and exit (non-interactive mode)
- `--output-format <format>` - Output format options:
  - `text` (default)
  - `json` (single result with session_id)
  - `stream-json` (realtime streaming)

#### 3. **Session Management**
- `-c, --continue` - Continue the most recent conversation
- `-r, --resume [sessionId]` - Resume specific session or select interactively
- `--max-turns <turns>` - Maximum conversation turns (default: 30)

#### 4. **Tool Control**
- `--allowedTools <tools...>` - Comma/space-separated list of allowed tools
  - Example: `"Bash(git:*) Edit Read"`
- `--disallowedTools <tools...>` - Tools to deny access to
- `--dangerously-skip-permissions` - Bypass permission checks (Docker only)

#### 5. **MCP Configuration**
- `--mcp-config <file or string>` - Load MCP servers from JSON
- `--mcp-debug` - [Deprecated] Use --debug instead

#### 6. **Model Selection**
- `--model <model>` - Specify model for session
  - Aliases: `sonnet`, `opus`
  - Full names: `claude-sonnet-4-20250514`

#### 7. **System Prompt (Undocumented)**
- `--append-system-prompt <content>` - Append to system prompt
- Used internally for agent-specific prompts

## Command Building Process

### 1. Basic Command Construction
```python
def _build_claude_command(self, ...):
    cmd = ["claude"]
    
    # Handle resume vs new session
    if resume_session:
        cmd.extend(["--resume", resume_session])
        cmd.extend(["-p", task_message])
    else:
        cmd.extend(["-p", task_message])
        
        # Add agent-specific prompt
        prompt_file = f".claude/agents-prompts/{agent_name}_prompt.md"
        if os.path.exists(prompt_file):
            with open(prompt_file, 'r') as f:
                prompt_content = f.read()
            cmd.extend(["--append-system-prompt", prompt_content])
```

### 2. Test Mode Handling

#### Ping Pong Test Mode
```python
if "ping pong" in task_message.lower():
    task_message = f"[PING PONG TEST MODE] {task_message}\n\n"
    task_message += f"Auto-respond with: '{agent_name} received ping pong, passing to next agent.'"
    max_turns = 1  # Immediate response
```

#### Epic Simulation Mode
```python
if "epic simulation" in task_message.lower():
    agent_tasks = {
        "genie": "Create Linear project/epic and post to Slack",
        "alpha": "Break down epic into Linear issues",
        "beta": "Create implementation tasks with git branches",
        # ...
    }
    task_message = f"[EPIC SIMULATION MODE] {task_message}\n\n"
    task_message += f"Your role: {agent_tasks.get(agent_name)}"
```

### 3. MCP Configuration Discovery
```python
# Search order for MCP config:
# 1. Explicit mcp_config_path parameter
# 2. Workspace root: {workspace}/.mcp.json
# 3. Parent directory: {workspace}/../.mcp.json
# 4. Default fallback: /root/workspace/.mcp.json

if os.path.exists(mcp_config_path):
    cmd.extend(["--mcp-config", mcp_config_path])
```

### 4. Tool Allowlist Loading
```python
# Search order for allowed_tools.json:
# 1. Custom file from orchestration_config["allowed_tools_file"]
# 2. Workspace root: {workspace}/allowed_tools.json
# 3. Parent directory: {workspace}/../allowed_tools.json

allowed_tools = self._load_allowed_tools(workspace_path)
if allowed_tools:
    cmd.extend(["--allowedTools", ",".join(allowed_tools)])
```

### 5. Final Parameters
```python
cmd.extend(["--max-turns", str(max_turns)])
cmd.extend(["--output-format", "json"])  # Always use JSON for parsing
```

## Session Management

### Session ID Extraction
```python
def _extract_session_id(self, output: str) -> Optional[str]:
    # Try JSON parsing first
    for line in reversed(output.strip().split('\n')):
        if line.startswith('{') and line.endswith('}'):
            data = json.loads(line)
            if 'session_id' in data:
                return data['session_id']
    
    # Fallback to regex pattern matching
    session_pattern = r'session[_-]?id["\']?\s*[:=]\s*["\']?([a-f0-9-]{36})["\']?'
    match = re.search(session_pattern, output, re.IGNORECASE)
    if match:
        return match.group(1)
```

### Session Persistence
- Sessions are tracked via `claude_session_id` in orchestration state
- Resume capability allows continuing conversations across rounds
- Session IDs are UUID format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

## Streaming Output Mechanism

### Async Process Execution
```python
async def _execute_with_streaming(self, cmd, workspace_path, timeout):
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=workspace_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,  # Combine stderr with stdout
        env=os.environ.copy()
    )
    
    # Real-time streaming
    async for line in process.stdout:
        line_str = line.decode('utf-8', errors='replace').rstrip()
        output_lines.append(line_str)
        logger.info(f"[{process.pid}] {line_str}")
```

### Timeout Handling
```python
async with async_timeout(timeout):
    # Stream output
    ...
    
# On timeout:
# 1. Send SIGTERM for graceful shutdown
# 2. Wait 5 seconds
# 3. Send SIGKILL if still running
```

## Process Monitoring

### Active Process Tracking
```python
class EnhancedCLINode:
    def __init__(self):
        self.active_processes: Dict[str, subprocess.Popen] = {}
    
    # Track process during execution
    process_id = str(uuid.uuid4())
    self.active_processes[process_id] = process
```

### Kill Switch Implementation
```python
async def kill_active_process(self, pid: int, force: bool = False):
    # Graceful termination (SIGTERM)
    os.kill(pid, signal.SIGTERM)
    
    # Wait up to 5 seconds
    for _ in range(5):
        await asyncio.sleep(1)
        try:
            os.kill(pid, 0)  # Check if alive
        except ProcessLookupError:
            return True  # Successfully terminated
    
    # Force kill if requested (SIGKILL)
    if force:
        os.kill(pid, signal.SIGKILL)
```

### Process Information
```python
async def get_process_info(self, pid: int):
    # Use ps command for detailed info
    cmd = ["ps", "-p", str(pid), "-o", "pid,ppid,state,cmd"]
    # Returns: pid, parent pid, state, command
```

## Error Handling

### Exception Hierarchy
```python
class CLIExecutionError(Exception):
    """Base exception for CLI execution failures"""
    pass
```

### Error Scenarios
1. **Workspace Not Found** - Creates directory if missing
2. **Process Timeout** - Graceful termination, then force kill
3. **Git Operation Failure** - Returns "unknown" SHA
4. **Session ID Not Found** - Falls back to regex parsing
5. **MCP Config Missing** - Uses default configuration

## Integration Points

### 1. Git Integration
```python
# Before execution
git_sha_start = await self._get_git_sha(workspace_path)

# After execution  
git_sha_end = await self._get_git_sha(workspace_path)
```

### 2. Orchestration State
```python
# State updates after execution
state["claude_session_id"] = result.get("claude_session_id")
state["process_pid"] = result.get("pid")
state["active_process_pid"] = result.get("pid")
state["execution_result"] = result
state["git_sha_end"] = result.get("git_sha_end")
```

### 3. Group Chat Context
```python
# Inject group chat history into task message
group_context = await self.messenger.prepare_chat_context(state["group_chat_id"])
enhanced_message = f"{state['task_message']}\n\n{group_context}"
```

### 4. Agent Prompts
- Location: `.claude/agents-prompts/{agent_name}_prompt.md`
- Fallback: `/root/workspace/.claude/agents-prompts/`
- Applied via `--append-system-prompt`

## Refactoring Considerations

### 1. Modular Architecture
```
claude-code/
├── __init__.py
├── agent.py           # Main ClaudeCodeAgent class
├── cli/
│   ├── __init__.py
│   ├── command.py     # Command builder
│   ├── executor.py    # Process executor
│   └── parser.py      # Output parser
├── session/
│   ├── __init__.py
│   ├── manager.py     # Session management
│   └── store.py       # Session persistence
├── process/
│   ├── __init__.py
│   ├── monitor.py     # Process monitoring
│   └── control.py     # Kill switches
├── prompts/
│   ├── __init__.py
│   └── loader.py      # Prompt loading
└── models.py          # Data models
```

### 2. Key Interfaces
```python
class ClaudeCodeAgent(AutomagikAgent):
    """Claude Code agent for subprocess execution"""
    
    async def execute(
        self,
        message: str,
        session_id: Optional[str] = None,
        max_turns: int = 30,
        workspace: Optional[str] = None
    ) -> ClaudeExecutionResult:
        """Execute Claude CLI with given parameters"""
        pass

class ClaudeCommandBuilder:
    """Builds Claude CLI commands"""
    
    def build(self, config: ClaudeConfig) -> List[str]:
        pass

class ClaudeSessionManager:
    """Manages Claude session lifecycle"""
    
    async def create_session(self) -> str:
        pass
    
    async def resume_session(self, session_id: str) -> bool:
        pass

class ClaudeProcessMonitor:
    """Monitors and controls Claude processes"""
    
    async def start_monitoring(self, pid: int) -> None:
        pass
    
    async def kill_process(self, pid: int, force: bool = False) -> bool:
        pass
```

### 3. Configuration Model
```python
@dataclass
class ClaudeConfig:
    agent_name: str
    task_message: str
    workspace_path: str
    resume_session: Optional[str] = None
    max_turns: int = 30
    mcp_config_path: Optional[str] = None
    allowed_tools: List[str] = field(default_factory=list)
    output_format: str = "json"
    debug: bool = False
    test_mode: Optional[str] = None  # ping_pong, epic_simulation
```

### 4. Migration Strategy
1. Create new `claude-code` agent type folder
2. Extract CLI-related code from `cli_node.py`
3. Implement `ClaudeCodeAgent` extending `AutomagikAgent`
4. Add proper tool registration for orchestration
5. Update orchestrator to use new agent type
6. Maintain backward compatibility during transition

### 5. Testing Approach
- Unit tests for command building
- Mock subprocess for execution tests
- Integration tests with real Claude CLI
- Session persistence tests
- Process monitoring tests
- Error handling scenarios

This documentation provides a complete understanding of the Claude CLI execution process and serves as a blueprint for refactoring into a dedicated `claude-code` agent type.