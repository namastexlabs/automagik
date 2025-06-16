"""Claude CLI Executor with session management and streaming.

This module executes Claude CLI commands with session persistence,
streaming JSON output, and proper resource management.
"""

import asyncio
import json
import logging
import os
import subprocess
import time
import aiofiles
import aiofiles.os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, List, Any, Callable
from datetime import datetime
import uuid
import shutil

from .log_manager import get_log_manager

logger = logging.getLogger(__name__)


def find_claude_executable() -> Optional[str]:
    """Find Claude CLI executable in system.
    
    Returns:
        Path to claude executable or None if not found
    """
    # First check if claude is in PATH
    claude_path = shutil.which("claude")
    if claude_path:
        logger.info(f"Found claude in PATH: {claude_path}")
        return claude_path
    
    # Check common Node.js installation paths
    home = os.path.expanduser("~")
    possible_paths = [
        # NVM installations
        f"{home}/.nvm/versions/node/*/bin/claude",
        # Node Version Manager patterns
        f"{home}/.volta/bin/claude",
        f"{home}/.fnm/node-versions/*/bin/claude",
        # System-wide installations
        "/usr/local/bin/claude",
        "/usr/bin/claude",
        "/opt/homebrew/bin/claude",
        # Direct npm global installations
        f"{home}/.npm-global/bin/claude",
        f"{home}/node_modules/.bin/claude",
    ]
    
    # Expand glob patterns and check each path
    import glob
    for pattern in possible_paths:
        for path in glob.glob(pattern):
            if os.path.exists(path) and os.access(path, os.X_OK):
                logger.info(f"Found claude at: {path}")
                return path
    
    logger.warning("Claude CLI not found in any common location")
    return None


# Cache the Claude executable path
_CLAUDE_EXECUTABLE_PATH = None


def is_claude_available() -> bool:
    """Check if Claude CLI is available.
    
    Returns:
        True if Claude CLI is found, False otherwise
    """
    global _CLAUDE_EXECUTABLE_PATH
    if _CLAUDE_EXECUTABLE_PATH is None:
        _CLAUDE_EXECUTABLE_PATH = find_claude_executable()
    return _CLAUDE_EXECUTABLE_PATH is not None


def get_claude_path() -> Optional[str]:
    """Get the path to Claude CLI executable.
    
    Returns:
        Path to claude executable or None if not found
    """
    global _CLAUDE_EXECUTABLE_PATH
    if _CLAUDE_EXECUTABLE_PATH is None:
        _CLAUDE_EXECUTABLE_PATH = find_claude_executable()
    return _CLAUDE_EXECUTABLE_PATH


@dataclass
class CLIResult:
    """Result from Claude CLI execution."""
    success: bool
    session_id: Optional[str]
    result: str
    exit_code: int
    execution_time: float
    logs: str
    error: Optional[str] = None
    git_commits: List[str] = None
    streaming_messages: List[Dict[str, Any]] = None
    log_file_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'success': self.success,
            'session_id': self.session_id,
            'result': self.result,
            'exit_code': self.exit_code,
            'execution_time': self.execution_time,
            'logs': self.logs,
            'error': self.error,
            'git_commits': self.git_commits or [],
            'streaming_messages': self.streaming_messages or [],
            'log_file_path': self.log_file_path
        }


@dataclass 
class ClaudeSession:
    """Manages Claude CLI sessions."""
    
    session_id: Optional[str] = None  # Database session ID
    claude_session_id: Optional[str] = None  # Claude's actual session ID
    run_id: str = None
    workflow_name: str = None
    max_turns: int = 2
    created_at: datetime = None
    
    def __post_init__(self):
        if not self.run_id:
            self.run_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.utcnow()
    
    def build_command(
        self, 
        message: str, 
        workspace: Path,
        workflow_dir: Optional[Path] = None
    ) -> List[str]:
        """Build Claude CLI command with session support.
        
        Args:
            message: User message for Claude
            workspace: Workspace directory path
            workflow_dir: Optional workflow directory with configs
            
        Returns:
            List of command arguments
        
        Raises:
            FileNotFoundError: If Claude CLI is not found
        """
        global _CLAUDE_EXECUTABLE_PATH
        
        # Use cached path or find it
        if _CLAUDE_EXECUTABLE_PATH is None:
            _CLAUDE_EXECUTABLE_PATH = find_claude_executable()
            
        if not _CLAUDE_EXECUTABLE_PATH:
            raise FileNotFoundError(
                "Claude CLI not found. Please install it with: npm install -g @anthropic-ai/claude-cli\n"
                "Make sure Node.js is installed and the claude command is in your PATH."
            )
            
        cmd = [_CLAUDE_EXECUTABLE_PATH]
        
        # Resume session if Claude session ID is provided
        if self.claude_session_id:
            cmd.extend(["-r", self.claude_session_id])
        
        # Add standard flags
        cmd.extend([
            "-p",  # Pretty output
            "--output-format", "stream-json",
            "--max-turns", str(self.max_turns),
            "--model", "sonnet"  # Use Sonnet by default to avoid expensive models
        ])
        
        # Add MCP configuration if available
        mcp_paths = [
            workspace / ".mcp.json",
            workflow_dir / ".mcp.json" if workflow_dir else None
        ]
        for mcp_path in filter(None, mcp_paths):
            if mcp_path and mcp_path.exists():
                cmd.extend(["--mcp-config", str(mcp_path)])
                break
        
        # Add allowed tools if available - using SDK format
        tools_paths = [
            workspace / "allowed_tools.json",
            workflow_dir / "allowed_tools.json" if workflow_dir else None
        ]
        tools_loaded = False
        for tools_path in filter(None, tools_paths):
            if tools_path and tools_path.exists():
                try:
                    with open(tools_path, 'r') as f:
                        tools = json.load(f)
                        if tools:
                            # Use space-separated format from SDK docs
                            cmd.extend(["--allowedTools"] + tools)
                            tools_loaded = True
                            logger.info(f"Loaded {len(tools)} allowed tools from {tools_path}")
                            break
                except Exception as e:
                    logger.warning(f"Failed to load allowed tools from {tools_path}: {e}")
        
        # If no tools file found, grant basic permissions for workflows
        if not tools_loaded:
            basic_tools = ["Bash", "LS", "Read", "Write", "Edit", "Glob", "Grep", "Task"]
            cmd.extend(["--allowedTools"] + basic_tools)
            logger.info(f"No tools file found, using basic tools: {basic_tools}")
        
        # Add permission mode to avoid interactive prompts in workflows
        cmd.extend(["--permission-mode", "acceptEdits"])
        logger.debug("Added acceptEdits permission mode to avoid interactive prompts")
        
        # Add system prompt if available
        prompt_paths = [
            workflow_dir / "prompt.md" if workflow_dir else None,
            workspace / "prompt.md"
        ]
        for prompt_path in filter(None, prompt_paths):
            if prompt_path and prompt_path.exists():
                with open(prompt_path, 'r') as f:
                    prompt_content = f.read()
                cmd.extend(["--append-system-prompt", prompt_content])
                break
        
        # Add user message
        cmd.append(message)
        
        # Add verbose flag for better debugging
        cmd.append("--verbose")
        
        return cmd


class StreamProcessor:
    """Processes Claude CLI JSON stream output."""
    
    def __init__(self, on_message: Optional[Callable] = None, log_writer: Optional[Callable] = None, session_event: Optional[asyncio.Event] = None, workspace: Optional[Path] = None, run_id: Optional[str] = None):
        """Initialize stream processor.
        
        Args:
            on_message: Optional callback for each message
            log_writer: Optional log writer function for file logging
            session_event: Optional event to set when session is confirmed
            workspace: Optional workspace path for auto-commits
            run_id: Optional run ID for auto-commits
        """
        self.session_id: Optional[str] = None
        self.messages: List[Dict[str, Any]] = []
        self.on_message = on_message
        self.log_writer = log_writer
        self.workspace = workspace
        self.run_id = run_id
        self.session_event = session_event
        self.result_text = ""
        self.completed = False
        self.session_confirmed = False  # Track when session ID is extracted
        
    async def process_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Process a line from Claude CLI output.
        
        Args:
            line: Raw line from stdout
            
        Returns:
            Parsed JSON data or None
        """
        line = line.strip()
        if not line:
            return None
        
        # Store raw line for later processing by RawStreamProcessor
        if self.log_writer:
            await self.log_writer(
                line.strip(),
                "claude_stream_raw",
                {"message": line.strip()}  # Use "message" field consistently
            )
        
        try:
            data = json.loads(line)
            
            # Log each parsed JSON event as individual log entry for metric extraction
            if self.log_writer:
                event_type = data.get("type", "unknown")
                subtype = data.get("subtype", "")
                event_name = f"claude_stream_{event_type}"
                if subtype:
                    event_name += f"_{subtype}"
                
                await self.log_writer(
                    f"Claude stream event: {event_type}" + (f".{subtype}" if subtype else ""),
                    event_name,
                    data  # Log the complete parsed JSON data
                )
            
            # Extract session ID from init message and log session establishment
            if data.get("type") == "system" and data.get("subtype") == "init":
                # Session ID is directly in the init message
                self.session_id = data.get("session_id")
                self.session_confirmed = True
                logger.info(f"Extracted session ID: {self.session_id}")
                
                # Set session event for early API response
                if self.session_event:
                    self.session_event.set()
                
                # Log consolidated session establishment (replaces session_confirmed + claude_output for init)
                if self.log_writer:
                    await self.log_writer(
                        f"Session established: {self.session_id}",
                        "session_established",
                        {
                            "claude_session_id": self.session_id,
                            "tools_available": len(data.get("tools", [])),
                            "mcp_servers": [server.get("name") for server in data.get("mcp_servers", [])],
                            "model": data.get("model"),
                            "working_directory": data.get("cwd")
                        }
                    )
            
            # Skip redundant claude_response logging - we already have claude_stream_assistant events
            
            # Log result events
            elif data.get("type") == "result" and self.log_writer:
                await self.log_writer(
                    f"Claude result: {data.get('subtype', 'unknown')}",
                    "claude_result",
                    {
                        "type": "result", 
                        "subtype": data.get("subtype"),
                        "result_length": len(str(data.get("result", ""))),
                        "cost_usd": data.get("cost_usd"),
                        "duration_ms": data.get("duration_ms"),
                        "num_turns": data.get("num_turns"),
                        "is_error": data.get("is_error", False)
                    }
                )
            
            # Accumulate result text
            if data.get("type") == "text" and data.get("content"):
                self.result_text += data["content"]
            
            # Detect completion and log execution summary
            if data.get("type") == "result":
                self.completed = True
                if data.get("result"):
                    self.result_text = data["result"]
                
                # Log enhanced execution completion (replaces generic completion event)
                if self.log_writer:
                    await self.log_writer(
                        f"Execution completed: {data.get('subtype', 'unknown')}",
                        "execution_complete",
                        {
                            "status": "completed" if not data.get("is_error") else "failed",
                            "exit_code": 0 if not data.get("is_error") else 1,
                            "duration_ms": data.get("duration_ms"),
                            "total_cost_usd": data.get("cost_usd"),
                            "turns_used": data.get("num_turns"),
                            "final_result": f"{self.result_text[:200]}..." if len(self.result_text) > 200 else self.result_text,
                            "session_id": self.session_id
                        }
                    )
            
            # Store message
            self.messages.append(data)
            
            # Call callback if provided
            if self.on_message:
                await self.on_message(data)
            
            return data
            
        except json.JSONDecodeError:
            # Log significant non-JSON lines only (errors, warnings)
            if line and not line.startswith("{") and any(keyword in line.lower() for keyword in ["error", "warning", "failed", "exception"]):
                logger.debug(f"Non-JSON output: {line}")
                
                # Log only significant non-JSON output
                if self.log_writer:
                    await self.log_writer(line.strip(), "stderr_event", {"stream": "stderr", "significant": True})
            return None
    
    def get_final_result(self) -> str:
        """Get the final result text."""
        return self.result_text or "No result generated"


class ClaudeCLIExecutor:
    """Executes Claude CLI commands with session management."""
    
    def __init__(
        self,
        timeout: int = 7200,
        max_concurrent: int = 5
    ):
        """Initialize CLI executor.
        
        Args:
            timeout: Default timeout in seconds
            max_concurrent: Maximum concurrent executions
        """
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.sessions: Dict[str, ClaudeSession] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        logger.info(f"ClaudeCLIExecutor initialized with timeout={timeout}s")
    
    async def execute(
        self,
        workflow: str,
        message: str,
        workspace: Path,
        session_id: Optional[str] = None,
        max_turns: int = 2,
        stream_callback: Optional[Callable] = None,
        timeout: Optional[int] = None,
        run_id: Optional[str] = None
    ) -> CLIResult:
        """Execute Claude CLI with streaming output.
        
        Args:
            workflow: Workflow name
            message: User message
            workspace: Workspace directory
            session_id: Optional session ID to resume
            max_turns: Maximum conversation turns
            stream_callback: Optional callback for streaming messages
            timeout: Optional custom timeout
            
        Returns:
            CLIResult with execution details
        """
        async with self._semaphore:
            return await self._execute_internal(
                workflow, message, workspace, 
                session_id, max_turns, stream_callback, timeout, run_id
            )
    
    async def _execute_internal(
        self,
        workflow: str,
        message: str,
        workspace: Path,
        session_id: Optional[str],
        max_turns: int,
        stream_callback: Optional[Callable],
        timeout: Optional[int],
        run_id: Optional[str]
    ) -> CLIResult:
        """Internal execution method."""
        start_time = time.time()
        timeout = timeout or self.timeout
        
        # Create or get session
        session = self._get_or_create_session(workflow, session_id, max_turns)
        
        # Setup log manager for this run
        log_manager = get_log_manager()
        actual_run_id = run_id or session.run_id
        
        # Setup workflow directory
        workflow_dir = workspace / "workflow"
        if not workflow_dir.exists():
            workflow_src = Path(__file__).parent / "workflows" / workflow
            if workflow_src.exists():
                import shutil
                shutil.copytree(workflow_src, workflow_dir, dirs_exist_ok=True)
        
        # Build command
        cmd = session.build_command(message, workspace, workflow_dir)
        
        # Log enhanced command debug structure (replace bloated raw_command event)
        async with log_manager.get_log_writer(actual_run_id) as log_writer:
            # Build config file info
            mcp_config_file = None
            system_prompt_file = None
            allowed_tools_file = None
            
            # Extract config files from command
            for i, arg in enumerate(cmd):
                if arg == "--mcp-config" and i + 1 < len(cmd):
                    mcp_config_file = cmd[i + 1]
                elif arg == "--append-system-prompt" and i + 1 < len(cmd):
                    # Check if it's a file path or inline content
                    next_arg = cmd[i + 1]
                    if len(next_arg) < 500 and "\n" not in next_arg:
                        system_prompt_file = next_arg
                    else:
                        system_prompt_file = "<inline_content>"  # Indicate inline content
                elif arg == "--allowedTools" and i + 1 < len(cmd):
                    allowed_tools_file = "<inline_tools_list>"
            
            # Build command reconstruction (for debugging)
            reconstruction_parts = [cmd[0]]  # Executable
            i = 1
            while i < len(cmd):
                arg = cmd[i]
                if arg in ["-p", "--output-format", "--max-turns", "--verbose"]:
                    if i + 1 < len(cmd) and not cmd[i + 1].startswith("-"):
                        reconstruction_parts.extend([arg, cmd[i + 1]])
                        i += 2
                    else:
                        reconstruction_parts.append(arg)
                        i += 1
                elif arg == "--mcp-config":
                    reconstruction_parts.extend([arg, "workflow/.mcp.json"])
                    i += 2
                elif arg == "--allowedTools":
                    reconstruction_parts.extend([arg, "<tools_list>"])
                    i += 2
                elif arg == "--append-system-prompt":
                    if system_prompt_file == "<inline_content>":
                        reconstruction_parts.extend([arg, "@workflow/prompt.md"])
                    else:
                        reconstruction_parts.extend([arg, f"@{system_prompt_file}"])
                    i += 2
                elif arg in ["-r"] and i + 1 < len(cmd):
                    reconstruction_parts.extend([arg, cmd[i + 1]])
                    i += 2
                else:
                    # This is likely the user message (last arg)
                    reconstruction_parts.append('"<user_message>"')
                    break
            
            await log_writer(
                "Command debug information with clean structure",
                "command_debug",
                {
                    "executable": cmd[0] if cmd else None,
                    "args": [arg for arg in cmd[1:] if not (len(str(arg)) > 1000)],  # Exclude large content
                    "config_files": {
                        "mcp_config": mcp_config_file,
                        "system_prompt": system_prompt_file,
                        "allowed_tools": allowed_tools_file
                    },
                    "command_reconstruction": " ".join(reconstruction_parts),
                    "working_directory": self._determine_working_directory(workspace),
                    "user_message_length": len(message),
                    "max_turns": max_turns,
                    "workflow": workflow,
                    "session_id": session.session_id,
                    "run_id": session.run_id
                }
            )
        
        # Log command (for regular logging)
        logger.info(f"Executing Claude CLI: {' '.join(cmd[:3])}... (full command logged to file)")
        
        try:
            # Create stream callback for WebSocket if run_id provided
            ws_callback = None
            if run_id and stream_callback is None:
                # Try to import WebSocket streaming function
                try:
                    from src.api.routes.claude_code_websocket import stream_claude_output
                    async def ws_callback(msg):
                        await stream_claude_output(run_id, msg)
                    stream_callback = ws_callback
                except ImportError:
                    logger.warning("WebSocket streaming not available")
            
            # Execute process with log streaming
            result = await self._run_process_with_logging(
                cmd, workspace, session, stream_callback, timeout, actual_run_id, log_manager
            )
            
            # Get git commits
            git_repo_path = Path(self._determine_working_directory(workspace))
            git_commits = await self._get_git_commits(git_repo_path)
            
            # Update result with commits and log file path
            result.git_commits = git_commits
            result.execution_time = time.time() - start_time
            result.log_file_path = str(log_manager.get_log_path(actual_run_id))
            
            # Store session if successful
            if result.success and session.session_id:
                self.sessions[session.session_id] = session
                
            return result
            
        except Exception as e:
            logger.error(f"CLI execution failed: {e}")
            
            # Log error to file if we have a run_id
            if actual_run_id:
                try:
                    async with log_manager.get_log_writer(actual_run_id) as log_writer:
                        await log_writer(
                            f"Execution failed: {str(e)}",
                            "error",
                            {"error_type": type(e).__name__, "traceback": str(e)}
                        )
                except Exception:
                    pass  # Don't fail on logging errors
            
            return CLIResult(
                success=False,
                session_id=session.session_id,
                result="",
                exit_code=-1,
                execution_time=time.time() - start_time,
                logs=str(e),
                error=str(e),
                log_file_path=str(log_manager.get_log_path(actual_run_id)) if actual_run_id else None
            )
    
    async def _run_process_with_logging(
        self,
        cmd: List[str],
        workspace: Path,
        session: ClaudeSession,
        stream_callback: Optional[Callable],
        timeout: int,
        run_id: str,
        log_manager
    ) -> CLIResult:
        """Run the Claude CLI process with integrated log streaming."""
        async with log_manager.get_log_writer(run_id) as log_writer:
            await self._log_execution_init(log_writer, session, workspace, cmd, run_id)
            
            env = self._prepare_environment(session)
            await self._log_environment_setup(log_writer, env)
            
            working_dir = self._determine_working_directory(workspace)
            process = await self._create_process(cmd, working_dir, env)
            
            await self._log_process_start(log_writer, process, timeout)
            self.active_processes[session.run_id] = process
            
            processor, session_task = await self._setup_stream_processing(
                stream_callback, log_writer, session, workspace
            )
            
            try:
                stdout_lines, stderr_lines = await self._execute_process_streams(
                    process, processor, log_writer, timeout
                )
                
            except asyncio.TimeoutError:
                await self._handle_process_timeout(log_writer, process, timeout)
                raise
                
            finally:
                await self._cleanup_process_execution(
                    session_task, stderr_lines, log_writer, session
                )
            
            return await self._build_execution_result(
                process, processor, stdout_lines, stderr_lines, 
                session, run_id, log_manager, log_writer
            )
    
    
    def _get_or_create_session(
        self,
        workflow: str,
        session_id: Optional[str],
        max_turns: int
    ) -> ClaudeSession:
        """Get existing session or create new one."""
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            session.max_turns = max_turns  # Update max turns
            return session
        
        return ClaudeSession(
            session_id=session_id,
            workflow_name=workflow,
            max_turns=max_turns
        )
    
    async def _get_git_commits(self, repo_path: Path) -> List[str]:
        """Get list of git commits made during execution."""
        if not repo_path.exists():
            return []
            
        try:
            # Get commits (newest first)
            cmd = ["git", "log", "--format=%H", "--reverse", "-10"]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            
            if process.returncode == 0:
                commits = stdout.decode('utf-8').strip().split('\n')
                return [c for c in commits if c]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get git commits: {e}")
            return []
    
    async def execute_until_first_response(
        self,
        workflow: str,
        message: str,
        workspace: Path,
        session_id: Optional[str] = None,
        max_turns: int = 2,
        timeout: Optional[int] = None,
        run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute Claude CLI and return after first substantial response.
        
        This method starts Claude CLI execution, waits for session confirmation
        and first response, then returns immediately while allowing execution
        to continue in background.
        
        Args:
            workflow: Workflow name
            message: User message
            workspace: Workspace directory
            session_id: Optional session ID to resume
            max_turns: Maximum conversation turns
            timeout: Optional custom timeout
            run_id: Optional run ID for logging
            
        Returns:
            Dictionary with first response data
        """
        async with self._semaphore:
            return await self._execute_until_first_response_internal(
                workflow, message, workspace, session_id, max_turns, timeout, run_id
            )
    
    async def _execute_until_first_response_internal(
        self,
        workflow: str,
        message: str,
        workspace: Path,
        session_id: Optional[str],
        max_turns: int,
        timeout: Optional[int],
        run_id: Optional[str]
    ) -> Dict[str, Any]:
        """Internal implementation for execute_until_first_response."""
        timeout = timeout or self.timeout
        
        # Create or get session
        session = self._get_or_create_session(workflow, session_id, max_turns)
        
        # Setup log manager for this run
        log_manager = get_log_manager()
        actual_run_id = run_id or session.run_id
        
        # Setup workflow directory
        workflow_dir = workspace / "workflow"
        if not workflow_dir.exists():
            workflow_src = Path(__file__).parent / "workflows" / workflow
            if workflow_src.exists():
                import shutil
                shutil.copytree(workflow_src, workflow_dir, dirs_exist_ok=True)
        
        # Build command
        cmd = session.build_command(message, workspace, workflow_dir)
        
        try:
            # Setup environment
            env = self._prepare_environment(session)
            
            if _CLAUDE_EXECUTABLE_PATH:
                claude_dir = os.path.dirname(_CLAUDE_EXECUTABLE_PATH)
                current_path = env.get("PATH", "")
                if claude_dir not in current_path:
                    env["PATH"] = f"{claude_dir}:{current_path}"
            
            # Start the Claude CLI process
            working_dir = self._determine_working_directory(workspace)
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Track active process
            self.active_processes[session.run_id] = process
            
            # Create events for tracking progress
            session_confirmed_event = asyncio.Event()
            first_response_event = asyncio.Event()
            first_response_text = None
            claude_session_id = None
            
            # Log early start
            async with log_manager.get_log_writer(actual_run_id) as log_writer:
                await log_writer(
                    f"Started execute_until_first_response for workflow '{workflow}'",
                    "early_execution_start",
                    {
                        "workflow": workflow,
                        "session_id": session_id,
                        "run_id": actual_run_id,
                        "pid": process.pid
                    }
                )
            
            # Create stream processor with events for early detection
            async def early_callback(data):
                nonlocal first_response_text, claude_session_id
                
                # Track session establishment
                if data.get("type") == "system" and data.get("subtype") == "init":
                    claude_session_id = data.get("session_id")
                    session_confirmed_event.set()
                
                # Track first substantial response from Claude
                elif data.get("type") == "assistant" and data.get("message"):
                    if not first_response_event.is_set():
                        # Extract content from Claude's message structure: message.content[0].text
                        message = data.get("message", {})
                        content = message.get("content", [])
                        if content and len(content) > 0 and content[0].get("type") == "text":
                            first_response_text = content[0].get("text", "")
                            if first_response_text:  # Only set if we have actual content
                                first_response_event.set()
                
                # Also check for result messages with substantial content
                elif data.get("type") == "result" and data.get("result"):
                    if not first_response_event.is_set():
                        first_response_text = data.get("result", "")
                        first_response_event.set()
            
            # Shared flag to coordinate stream reading between early and background tasks
            stdout_handoff_event = asyncio.Event()
            
            # Start background task to continue full execution
            async def continue_full_execution():
                try:
                    # Wait for the early reading to complete before starting background reading
                    await stdout_handoff_event.wait()
                    
                    # Create a separate stream processor for background execution with log writer
                    async with log_manager.get_log_writer(actual_run_id) as background_log_writer:
                        background_processor = StreamProcessor(log_writer=background_log_writer)
                        
                        # Continue reading any remaining output to prevent stream backup
                        remaining_lines = []
                        try:
                            # Read remaining output with timeout to prevent hanging
                            async def drain_remaining_output():
                                async for line in process.stdout:
                                    decoded = line.decode('utf-8', errors='replace')
                                    remaining_lines.append(decoded)
                                    await background_processor.process_line(decoded)
                        
                            # Give it time to complete, but don't wait forever
                            await asyncio.wait_for(
                                asyncio.gather(process.wait(), drain_remaining_output()),
                                timeout=timeout
                            )
                        except asyncio.TimeoutError:
                            logger.warning("Background execution timed out, terminating process")
                            process.terminate()
                            try:
                                await asyncio.wait_for(process.wait(), timeout=5)
                            except asyncio.TimeoutError:
                                process.kill()
                        
                        # Clean up process tracking
                        if session.run_id in self.active_processes:
                            del self.active_processes[session.run_id]
                        
                except Exception as e:
                    logger.error(f"Background execution error: {e}")
                    # Clean up on error
                    if session.run_id in self.active_processes:
                        try:
                            if not process.returncode:
                                process.terminate()
                                await asyncio.wait_for(process.wait(), timeout=5)
                        except Exception:
                            pass
                        del self.active_processes[session.run_id]
            
            # Start background continuation task
            # It will wait for stdout_handoff_event before reading stdout
            asyncio.create_task(continue_full_execution())
            
            # Create simple stream processor for early detection
            class EarlyStreamProcessor:
                def __init__(self):
                    self.session_id = None
                    self.first_response = None
                
                async def process_line(self, line: str):
                    line = line.strip()
                    if not line:
                        return
                    
                    try:
                        data = json.loads(line)
                        await early_callback(data)
                        
                        # Update our tracking
                        if data.get("type") == "system" and data.get("subtype") == "init":
                            self.session_id = data.get("session_id")
                        elif data.get("type") == "assistant" and data.get("message"):
                            if not self.first_response:
                                # Extract content from Claude's message structure: message.content[0].text
                                message = data.get("message", {})
                                content = message.get("content", [])
                                if content and len(content) > 0 and content[0].get("type") == "text":
                                    self.first_response = content[0].get("text", "")
                        elif data.get("type") == "result" and data.get("result"):
                            if not self.first_response:
                                self.first_response = data.get("result", "")
                                
                    except json.JSONDecodeError:
                        pass  # Ignore non-JSON lines
            
            early_processor = EarlyStreamProcessor()
            
            # Read stdout until we get first response or timeout
            # Use a bounded buffer approach to avoid stream contamination
            try:
                # Set a reasonable timeout for first response (30 seconds)
                first_response_timeout = 30
                early_lines_buffer = []
                max_early_lines = 100  # Limit early reading to prevent memory issues
                
                async def read_until_first_response():
                    line_count = 0
                    async for line in process.stdout:
                        if line_count >= max_early_lines:
                            # Stop early reading to prevent infinite buffering
                            logger.debug(f"Reached max early lines ({max_early_lines}), stopping early read")
                            break
                            
                        decoded = line.decode('utf-8', errors='replace')
                        early_lines_buffer.append(decoded)  # Store for potential debugging
                        await early_processor.process_line(decoded)
                        line_count += 1
                        
                        # Stop reading once we have first response
                        if first_response_event.is_set():
                            logger.debug("First response captured, stopping early read")
                            break
                
                # Wait for either session + first response or timeout
                await asyncio.wait_for(
                    asyncio.gather(
                        session_confirmed_event.wait(),
                        read_until_first_response()
                    ),
                    timeout=first_response_timeout
                )
                
                # Wait a bit more for first response if we only have session
                if not first_response_event.is_set():
                    try:
                        await asyncio.wait_for(first_response_event.wait(), timeout=10)
                    except asyncio.TimeoutError:
                        logger.debug("Timeout waiting for first response, continuing with session confirmation")
                        pass  # Continue with what we have
                
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for first response after {first_response_timeout}s")
            
            # Signal that early reading is complete and background can take over stdout
            stdout_handoff_event.set()
            
            # Extract results
            session_id_result = claude_session_id or early_processor.session_id
            response_text = first_response_text or early_processor.first_response
            
            # Default response if nothing substantial found
            if not response_text:
                response_text = "Claude Code execution started. Processing your request..."
            
            # Log what we captured
            async with log_manager.get_log_writer(actual_run_id) as log_writer:
                await log_writer(
                    f"Early response captured: {response_text[:100]}...",
                    "early_response_captured",
                    {
                        "response_length": len(response_text),
                        "claude_session_id": session_id_result,
                        "session_confirmed": session_confirmed_event.is_set(),
                        "first_response_found": first_response_event.is_set(),
                        "early_lines_processed": len(early_lines_buffer)
                    }
                )
            
            # CRITICAL: Ensure we return immediately without any further stdout interference
            # The background task will handle the rest of the execution
            # No print statements, no stdout operations after this point
            return {
                "session_id": session_id_result,
                "first_response": response_text,
                "streaming_started": True
            }
            
        except Exception as e:
            logger.error(f"Error in execute_until_first_response: {e}")
            
            # Clean up process if needed
            if session.run_id in self.active_processes:
                try:
                    process = self.active_processes[session.run_id]
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=5)
                except Exception:
                    pass
                finally:
                    del self.active_processes[session.run_id]
            
            return {
                "session_id": session.session_id,
                "first_response": f"Error starting execution: {str(e)}",
                "streaming_started": False
            }
    
    async def cancel_execution(self, run_id: str) -> bool:
        """Cancel a running execution with GUARDIAN safety validation.
        
        Args:
            run_id: Run ID to cancel
            
        Returns:
            True if cancelled, False otherwise
        """
        # GUARDIAN Safety Validation - Pre-kill checks
        kill_start_time = time.time()
        
        # Validate run_id before proceeding
        if not run_id or not isinstance(run_id, str):
            logger.error(f"🛡️ GUARDIAN: Invalid run_id for cancellation: {run_id}")
            return False
        
        # Check if process exists in active processes
        if run_id not in self.active_processes:
            logger.warning(f"🛡️ GUARDIAN: Process {run_id} not found in active processes")
            # Try to clean up stale database records
            await self._cleanup_workflow_process(run_id, "not_found")
            return False
        
        process = self.active_processes[run_id]
        
        # GUARDIAN Safety Validation - Process health check
        try:
            # Verify process is still running
            if process.returncode is not None:
                logger.info(f"🛡️ GUARDIAN: Process {run_id} already terminated (code: {process.returncode})")
                await self._cleanup_workflow_process(run_id, "already_terminated")
                del self.active_processes[run_id]
                return True
            
            # Log kill attempt for audit trail
            log_manager = get_log_manager()
            async with log_manager.get_log_writer(run_id) as log_writer:
                await log_writer(
                    f"🛡️ GUARDIAN initiating process cancellation",
                    "guardian_kill_start",
                    {
                        "run_id": run_id,
                        "process_pid": process.pid,
                        "kill_reason": "manual_cancellation",
                        "safety_validated": True,
                        "guardian_timestamp": datetime.utcnow().isoformat()
                    }
                )
        except Exception as e:
            logger.error(f"🛡️ GUARDIAN: Pre-kill validation failed for {run_id}: {e}")
            # Continue with kill attempt despite validation error
        
        # GUARDIAN Progressive Kill Strategy - Graceful → Force → Cleanup
        kill_success = False
        kill_method = "unknown"
        
        try:
            # Phase 1: Graceful shutdown (SIGTERM with 5s timeout)
            logger.info(f"🛡️ GUARDIAN: Attempting graceful termination of {run_id}")
            process.terminate()
            
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
                kill_success = True
                kill_method = "graceful"
                logger.info(f"🛡️ GUARDIAN: Successfully terminated {run_id} gracefully")
                
            except asyncio.TimeoutError:
                # Phase 2: Force kill (SIGKILL)
                logger.warning(f"🛡️ GUARDIAN: Graceful termination failed, force killing {run_id}")
                process.kill()
                
                try:
                    await asyncio.wait_for(process.wait(), timeout=10)
                    kill_success = True
                    kill_method = "force"
                    logger.info(f"🛡️ GUARDIAN: Successfully force killed {run_id}")
                    
                except asyncio.TimeoutError:
                    logger.error(f"🛡️ GUARDIAN: Force kill failed for {run_id} - process may be stuck")
                    kill_method = "failed"
                    kill_success = False
        
        except Exception as e:
            logger.error(f"🛡️ GUARDIAN: Kill operation failed for {run_id}: {e}")
            kill_method = "error"
            kill_success = False
        
        # Phase 3: Cleanup and audit logging
        kill_duration = time.time() - kill_start_time
        
        try:
            # Clean up workflow process record in database
            status = f"{kill_method}_killed" if kill_success else "kill_failed"
            await self._cleanup_workflow_process(run_id, status)
            
            # Remove from active processes
            if run_id in self.active_processes:
                del self.active_processes[run_id]
            
            # GUARDIAN Audit Logging
            log_manager = get_log_manager()
            async with log_manager.get_log_writer(run_id) as log_writer:
                await log_writer(
                    f"🛡️ GUARDIAN process cancellation completed",
                    "guardian_kill_complete",
                    {
                        "run_id": run_id,
                        "kill_success": kill_success,
                        "kill_method": kill_method,
                        "kill_duration_seconds": round(kill_duration, 3),
                        "cleanup_completed": True,
                        "guardian_timestamp": datetime.utcnow().isoformat(),
                        "safety_validated": True
                    }
                )
                
            if kill_success:
                logger.info(f"🛡️ GUARDIAN: Successfully cancelled execution {run_id} ({kill_method}) in {kill_duration:.3f}s")
            else:
                logger.error(f"🛡️ GUARDIAN: Failed to cancel execution {run_id} after {kill_duration:.3f}s")
            
        except Exception as cleanup_error:
            logger.error(f"🛡️ GUARDIAN: Cleanup failed for {run_id}: {cleanup_error}")
            # Even if cleanup fails, return the kill result
        
        return kill_success
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session information or None
        """
        session = self.sessions.get(session_id)
        if not session:
            return None
            
        return {
            "session_id": session.session_id,
            "run_id": session.run_id,
            "workflow_name": session.workflow_name,
            "max_turns": session.max_turns,
            "created_at": session.created_at.isoformat()
        }
    
    def list_sessions(self) -> List[str]:
        """List all active session IDs."""
        return list(self.sessions.keys())
    
    # --- Extracted methods from _run_process_with_logging ---
    
    async def _log_execution_init(self, log_writer, session, workspace, cmd, run_id):
        """Log execution initialization."""
        await log_writer(
            f"Workflow execution initialized: {session.workflow_name}",
            "execution_init",
            {
                "run_id": run_id,
                "workflow": session.workflow_name,
                "max_turns": session.max_turns,
                "workspace": str(workspace),
                "claude_executable": _CLAUDE_EXECUTABLE_PATH,
                "session_id": session.session_id,
                "claude_session_id": session.claude_session_id,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "command_args_count": len(cmd)
            }
        )
    
    def _prepare_environment(self, session):
        """Prepare environment variables for process execution."""
        env = os.environ.copy()
        env["CLAUDE_SESSION_ID"] = session.run_id
        
        # Add virtual environment to Python path for uv-managed dependencies
        # Find .venv in current working directory or parent directories
        current_dir = Path.cwd()
        venv_path = None
        
        # Look for .venv in current directory and up to 3 parent levels
        for check_dir in [current_dir] + list(current_dir.parents)[:3]:
            candidate = check_dir / ".venv"
            if candidate.exists() and candidate.is_dir():
                venv_path = candidate
                break
        
        if venv_path and venv_path.exists():
            # Add .venv/bin to PATH so Python finds the right packages
            venv_bin = str(venv_path / "bin")
            current_path = env.get("PATH", "")
            if venv_bin not in current_path:
                env["PATH"] = f"{venv_bin}:{current_path}"
            
            # Set VIRTUAL_ENV for tools that check it
            env["VIRTUAL_ENV"] = str(venv_path)
            
            # Set PYTHONPATH to include venv site-packages
            venv_site = str(venv_path / "lib" / "python3.12" / "site-packages")
            if (venv_path / "lib" / "python3.12" / "site-packages").exists():
                env["PYTHONPATH"] = venv_site + ":" + env.get("PYTHONPATH", "")
        
        return env
    
    async def _log_environment_setup(self, log_writer, env):
        """Log environment setup if Claude CLI directory was added to PATH."""
        if _CLAUDE_EXECUTABLE_PATH:
            claude_dir = os.path.dirname(_CLAUDE_EXECUTABLE_PATH)
            current_path = env.get("PATH", "")
            if claude_dir not in current_path:
                env["PATH"] = f"{claude_dir}:{current_path}"
                await log_writer(
                    f"Added Claude CLI directory to PATH: {claude_dir}",
                    "environment",
                    {"claude_dir": claude_dir, "path_modified": True}
                )
    
    def _determine_working_directory(self, workspace):
        """Determine the correct working directory for process execution."""
        # For worktrees, the workspace IS the repository
        if "builder_run_" in str(workspace):
            return str(workspace)
        elif workspace.name == "am-agents-labs":
            return str(workspace)
        else:
            return str(workspace / "am-agents-labs")
    
    async def _create_process(self, cmd, working_dir, env):
        """Create the Claude CLI subprocess."""
        return await asyncio.create_subprocess_exec(
            *cmd,
            cwd=working_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
    
    async def _log_process_start(self, log_writer, process, timeout):
        """Log process start information."""
        await log_writer(
            f"Process started with PID {process.pid}",
            "process_start",
            {
                "pid": process.pid, 
                "timeout": timeout
            }
        )
        
        # Register process in database for tracking and emergency kill
        await self._register_workflow_process(process, log_writer)
    
    async def _setup_stream_processing(self, stream_callback, log_writer, session, workspace=None):
        """Setup stream processing and session confirmation tracking."""
        session_confirmed_event = asyncio.Event()
        processor = StreamProcessor(stream_callback, log_writer, session_confirmed_event, workspace, session.run_id)
        
        async def wait_for_session_confirmation():
            try:
                await asyncio.wait_for(session_confirmed_event.wait(), timeout=30)
                await log_writer(
                    "Session confirmation received and logged",
                    "session_confirmation",
                    {"confirmed_early": True, "session_id": getattr(processor, 'session_id', None)}
                )
            except asyncio.TimeoutError:
                await log_writer(
                    "Session confirmation timeout (30s) - continuing execution",
                    "session_confirmation",
                    {"confirmed_early": False, "timeout": 30}
                )
        
        session_task = asyncio.create_task(wait_for_session_confirmation())
        return processor, session_task
    
    async def _execute_process_streams(self, process, processor, log_writer, timeout):
        """Execute and monitor process streams."""
        stdout_lines = []
        stderr_lines = []
        
        async def read_stream(stream, lines_list, is_stdout=True):
            async for line in stream:
                decoded = line.decode('utf-8', errors='replace')
                lines_list.append(decoded)
                
                if is_stdout:
                    await processor.process_line(decoded)
                else:
                    if decoded.strip():
                        await log_writer(
                            f"STDERR: {decoded.strip()}",
                            "stderr",
                            {"stream": "stderr", "content": decoded.strip()}
                        )
        
        async def auto_commit_worker(workspace, run_id, interval=60):
            """Background task for periodic auto-commits."""
            from .cli_environment import CLIEnvironmentManager
            env_manager = CLIEnvironmentManager()
            snapshot_count = 0
            
            while not process.stdout.at_eof() and not process.stderr.at_eof():
                try:
                    await asyncio.sleep(interval)
                    snapshot_count += 1
                    commit_msg = f"auto-snapshot: workflow progress #{snapshot_count}"
                    await env_manager.auto_commit_snapshot(workspace, run_id, commit_msg)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.debug(f"Auto-commit worker error: {e}")
            
        # Start auto-commit worker if workspace is available
        auto_commit_task = None
        if hasattr(processor, 'workspace') and hasattr(processor, 'run_id'):
            auto_commit_task = asyncio.create_task(
                auto_commit_worker(processor.workspace, processor.run_id)
            )
        
        stdout_task = asyncio.create_task(
            read_stream(process.stdout, stdout_lines, True)
        )
        stderr_task = asyncio.create_task(
            read_stream(process.stderr, stderr_lines, False)
        )
        
        try:
            await asyncio.wait_for(
                asyncio.gather(process.wait(), stdout_task, stderr_task),
                timeout=timeout
            )
        finally:
            # Clean up auto-commit task
            if auto_commit_task and not auto_commit_task.done():
                auto_commit_task.cancel()
                try:
                    await auto_commit_task
                except asyncio.CancelledError:
                    pass
        
        return stdout_lines, stderr_lines
    
    async def _handle_process_timeout(self, log_writer, process, timeout):
        """Handle process timeout with graceful shutdown."""
        await log_writer(
            f"Process timed out after {timeout}s, attempting graceful shutdown",
            "timeout",
            {"timeout_seconds": timeout, "pid": process.pid}
        )
        logger.warning(f"Process timed out after {timeout}s")
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
            await log_writer(
                "Process terminated gracefully after timeout",
                "process",
                {"termination": "graceful"}
            )
        except asyncio.TimeoutError:
            process.kill()
            await log_writer(
                "Process killed forcefully after timeout",
                "process",
                {"termination": "force_kill"}
            )
    
    async def _cleanup_process_execution(self, session_task, stderr_lines, log_writer, session):
        """Clean up process execution resources."""
        if not session_task.done():
            session_task.cancel()
            try:
                await session_task
            except asyncio.CancelledError:
                pass
        
        if stderr_lines and any(line.strip() for line in stderr_lines):
            await log_writer(
                "Stderr content detected",
                "stderr_summary",
                {"stderr_lines": len(stderr_lines), "content_preview": ''.join(stderr_lines)[:200]}
            )
        
        # Clean up workflow process record in database
        await self._cleanup_workflow_process(session.run_id, "completed")
        
        del self.active_processes[session.run_id]
    
    async def _build_execution_result(self, process, processor, stdout_lines, stderr_lines, 
                                     session, run_id, log_manager, log_writer):
        """Build the final execution result."""
        stdout_text = ''.join(stdout_lines)
        stderr_text = ''.join(stderr_lines)
        
        await log_writer(
            f"Process completed with exit code {process.returncode}",
            "process_complete",
            {
                "exit_code": process.returncode,
                "success": process.returncode == 0,
                "claude_session_id": processor.session_id,
                "session_confirmed": processor.session_confirmed,
                "result_length": len(processor.get_final_result()),
                "streaming_messages_count": len(processor.messages),
                "has_stderr": len(stderr_lines) > 0
            }
        )
        
        if processor.session_id:
            session.claude_session_id = processor.session_id
        
        return CLIResult(
            success=process.returncode == 0,
            session_id=processor.session_id or session.session_id,
            result=processor.get_final_result(),
            exit_code=process.returncode,
            execution_time=0,  # Will be set by caller
            logs=f"{stdout_text}\n{stderr_text}" if stderr_text else stdout_text,
            error=stderr_text if process.returncode != 0 else None,
            streaming_messages=processor.messages,
            log_file_path=str(log_manager.get_log_path(run_id))
        )
    
    async def _register_workflow_process(self, process, log_writer):
        """Register workflow process in database for tracking and emergency kill."""
        try:
            # Import here to avoid circular imports
            from src.db.repository import create_workflow_process
            from src.db.models import WorkflowProcessCreate
            from datetime import datetime
            
            # Find the session info from active processes
            run_id = None
            session = None
            for rid, proc in self.active_processes.items():
                if proc == process:
                    run_id = rid
                    session = self.sessions.get(rid)
                    break
            
            if not run_id:
                # Try to extract from process environment if available
                run_id = f"unknown_{process.pid}"
                logger.warning(f"Could not find run_id for process {process.pid}, using {run_id}")
            
            # Create workflow process record
            workflow_process = WorkflowProcessCreate(
                run_id=run_id,
                pid=process.pid,
                status="running",
                workflow_name=session.workflow_name if session else "unknown",
                session_id=session.session_id if session else None,
                user_id=None,  # Will be populated from session metadata if available
                workspace_path=None,  # Will be set from environment if available
                process_info={
                    "command": "claude",
                    "timeout": self.timeout,
                    "registered_at": datetime.utcnow().isoformat(),
                    "claude_session_id": session.claude_session_id if session else None
                }
            )
            
            success = create_workflow_process(workflow_process)
            
            if success:
                await log_writer(
                    f"Registered workflow process in database: {run_id}",
                    "process_registered",
                    {
                        "run_id": run_id,
                        "pid": process.pid,
                        "workflow_name": session.workflow_name if session else "unknown",
                        "tracking_enabled": True
                    }
                )
            else:
                await log_writer(
                    f"Failed to register workflow process in database: {run_id}",
                    "process_registration_failed",
                    {
                        "run_id": run_id,
                        "pid": process.pid,
                        "error": "Database registration failed"
                    }
                )
                
        except Exception as e:
            logger.warning(f"Failed to register workflow process {process.pid}: {e}")
            try:
                await log_writer(
                    f"Process registration error: {str(e)}",
                    "process_registration_error",
                    {
                        "pid": process.pid,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
            except Exception:
                pass  # Don't fail on logging errors
    
    async def _cleanup_workflow_process(self, run_id, status="completed"):
        """Clean up workflow process record in database."""
        try:
            from src.db.repository import mark_process_terminated
            
            success = mark_process_terminated(run_id, status)
            if success:
                logger.info(f"Marked workflow process as {status}: {run_id}")
            else:
                logger.warning(f"Failed to mark workflow process as {status}: {run_id}")
                
        except Exception as e:
            logger.warning(f"Failed to cleanup workflow process {run_id}: {e}")

    async def cleanup(self):
        """Clean up all active processes."""
        for run_id in list(self.active_processes.keys()):
            await self.cancel_execution(run_id)
        
        self.sessions.clear()
        logger.info("ClaudeCLIExecutor cleanup complete")