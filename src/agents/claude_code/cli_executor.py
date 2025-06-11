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
            "--max-turns", str(self.max_turns)
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
        
        # Add allowed tools if available
        tools_paths = [
            workspace / "allowed_tools.json",
            workflow_dir / "allowed_tools.json" if workflow_dir else None
        ]
        for tools_path in filter(None, tools_paths):
            if tools_path and tools_path.exists():
                try:
                    with open(tools_path, 'r') as f:
                        tools = json.load(f)
                        if tools:
                            cmd.extend(["--allowedTools", ",".join(tools)])
                            break
                except Exception as e:
                    logger.warning(f"Failed to load allowed tools: {e}")
        
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
    
    def __init__(self, on_message: Optional[Callable] = None, log_writer: Optional[Callable] = None, session_event: Optional[asyncio.Event] = None):
        """Initialize stream processor.
        
        Args:
            on_message: Optional callback for each message
            log_writer: Optional log writer function for file logging
            session_event: Optional event to set when session is confirmed
        """
        self.session_id: Optional[str] = None
        self.messages: List[Dict[str, Any]] = []
        self.on_message = on_message
        self.log_writer = log_writer
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
        
        # Log raw output to file immediately
        if self.log_writer:
            await self.log_writer(line, "raw_output")
            
        try:
            data = json.loads(line)
            
            # Extract session ID from init message
            if data.get("type") == "system" and data.get("subtype") == "init":
                # Session ID is directly in the init message
                self.session_id = data.get("session_id")
                self.session_confirmed = True
                logger.info(f"Extracted session ID: {self.session_id}")
                
                # Set session event for early API response
                if self.session_event:
                    self.session_event.set()
                
                # Log session confirmation
                if self.log_writer:
                    await self.log_writer(
                        f"Claude session started: {self.session_id}",
                        "session_confirmed",
                        {"session_id": self.session_id, "confirmed": True}
                    )
            
            # Log structured data
            if self.log_writer:
                await self.log_writer(
                    json.dumps(data),
                    "claude_output",
                    {"parsed": True, "type": data.get("type"), "subtype": data.get("subtype")}
                )
            
            # Accumulate result text
            if data.get("type") == "text" and data.get("content"):
                self.result_text += data["content"]
            
            # Detect completion
            if data.get("type") == "result":
                self.completed = True
                if data.get("result"):
                    self.result_text = data["result"]
                
                # Log completion
                if self.log_writer:
                    await self.log_writer(
                        f"Workflow completed with result: {self.result_text[:200]}...",
                        "event",
                        {"completed": True, "result_length": len(self.result_text)}
                    )
            
            # Store message
            self.messages.append(data)
            
            # Call callback if provided
            if self.on_message:
                await self.on_message(data)
            
            return data
            
        except json.JSONDecodeError:
            # Log non-JSON lines (might be errors or warnings)
            if line and not line.startswith("{"):
                logger.debug(f"Non-JSON output: {line}")
                
                # Still log non-JSON output to file
                if self.log_writer:
                    await self.log_writer(line, "non_json_output")
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
                shutil.copytree(workflow_src, workflow_dir)
        
        # Build command
        cmd = session.build_command(message, workspace, workflow_dir)
        
        # Log complete raw command with all variables injected
        async with log_manager.get_log_writer(actual_run_id) as log_writer:
            await log_writer(
                "Complete Claude CLI command with all variables injected",
                "raw_command",
                {
                    "full_command": cmd,
                    "command_length": len(cmd),
                    "executable": cmd[0] if cmd else None,
                    "working_directory": str(workspace / "am-agents-labs"),
                    "user_message": message,
                    "user_message_length": len(message),
                    "max_turns": max_turns,
                    "workflow": workflow,
                    "session_details": {
                        "session_id": session.session_id,
                        "claude_session_id": session.claude_session_id,
                        "run_id": session.run_id
                    }
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
            git_commits = await self._get_git_commits(workspace / "am-agents-labs")
            
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
        # Use log manager for this execution
        async with log_manager.get_log_writer(run_id) as log_writer:
            
            # Log execution start with comprehensive details
            await log_writer(
                f"Starting Claude CLI execution for workflow '{session.workflow_name}'",
                "workflow_init",
                {
                    "run_id": run_id,
                    "workflow": session.workflow_name,
                    "max_turns": session.max_turns,
                    "command_preview": " ".join(cmd[:5]) + "..." if len(cmd) > 5 else " ".join(cmd),
                    "full_command_length": len(cmd),
                    "workspace": str(workspace),
                    "session_details": {
                        "session_id": session.session_id,
                        "claude_session_id": session.claude_session_id,
                        "created_at": session.created_at.isoformat() if session.created_at else None
                    }
                }
            )
            
            # Prepare environment with Node.js in PATH
            env = os.environ.copy()
            env["CLAUDE_SESSION_ID"] = session.run_id
            
            # If claude was found, ensure its directory is in PATH
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
            
            # Log environment setup
            await log_writer(
                "Environment prepared for Claude CLI execution",
                "environment",
                {
                    "claude_executable": _CLAUDE_EXECUTABLE_PATH,
                    "working_directory": str(workspace / "am-agents-labs"),
                    "claude_session_env": session.run_id
                }
            )
            
            # Create process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(workspace / "am-agents-labs"),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Log process creation
            await log_writer(
                f"Claude CLI process created with PID {process.pid}",
                "process",
                {"pid": process.pid, "command_args": len(cmd)}
            )
            
            # Track active process
            self.active_processes[session.run_id] = process
            
            # Add session confirmation tracking for early API response
            session_confirmed_event = asyncio.Event()
            
            # Create stream processor with log writer and session event
            processor = StreamProcessor(stream_callback, log_writer, session_confirmed_event)
            
            # Start background task to wait for session confirmation
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
            
            # Start confirmation task but don't await it
            session_task = asyncio.create_task(wait_for_session_confirmation())
            
            # Collect output
            stdout_lines = []
            stderr_lines = []
            
            try:
                # Create tasks for reading streams
                async def read_stream(stream, lines_list, is_stdout=True):
                    async for line in stream:
                        decoded = line.decode('utf-8', errors='replace')
                        lines_list.append(decoded)
                        
                        if is_stdout:
                            # Process JSON streaming output
                            await processor.process_line(decoded)
                        else:
                            # Log stderr directly
                            if decoded.strip():
                                await log_writer(
                                    f"STDERR: {decoded.strip()}",
                                    "stderr",
                                    {"stream": "stderr", "content": decoded.strip()}
                                )
                
                # Read both streams concurrently with timeout
                stdout_task = asyncio.create_task(
                    read_stream(process.stdout, stdout_lines, True)
                )
                stderr_task = asyncio.create_task(
                    read_stream(process.stderr, stderr_lines, False)
                )
                
                # Wait for completion with timeout
                await asyncio.wait_for(
                    asyncio.gather(process.wait(), stdout_task, stderr_task),
                    timeout=timeout
                )
                
            except asyncio.TimeoutError:
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
                raise
                
            finally:
                # Clean up session task
                if not session_task.done():
                    session_task.cancel()
                    try:
                        await session_task
                    except asyncio.CancelledError:
                        pass
                
                # Clean up
                del self.active_processes[session.run_id]
            
            # Prepare result
            stdout_text = ''.join(stdout_lines)
            stderr_text = ''.join(stderr_lines)
            
            # Log completion with comprehensive details
            await log_writer(
                f"Claude CLI execution completed with exit code {process.returncode}",
                "workflow_completion",
                {
                    "exit_code": process.returncode,
                    "success": process.returncode == 0,
                    "session_id": processor.session_id,
                    "session_confirmed": processor.session_confirmed,
                    "result_length": len(processor.get_final_result()),
                    "completed": processor.completed,
                    "streaming_messages_count": len(processor.messages),
                    "stdout_lines": len(stdout_lines),
                    "stderr_lines": len(stderr_lines),
                    "final_result_preview": processor.get_final_result()[:200] + "..." if len(processor.get_final_result()) > 200 else processor.get_final_result()
                }
            )
            
            # Log session confirmation status
            if processor.session_confirmed:
                await log_writer(
                    f"Session ID confirmed: {processor.session_id}",
                    "session_confirmation",
                    {"session_id": processor.session_id, "confirmed": True}
                )
            else:
                await log_writer(
                    "Session ID was not confirmed during execution",
                    "session_confirmation", 
                    {"confirmed": False, "reason": "not_received_or_process_ended"}
                )
            
            # Update Claude session ID if extracted
            if processor.session_id:
                session.claude_session_id = processor.session_id
            
            return CLIResult(
                success=process.returncode == 0,
                session_id=processor.session_id or session.session_id,
                result=processor.get_final_result(),
                exit_code=process.returncode,
                execution_time=0,  # Will be set by caller
                logs=stdout_text + "\n" + stderr_text if stderr_text else stdout_text,
                error=stderr_text if process.returncode != 0 else None,
                streaming_messages=processor.messages,
                log_file_path=str(log_manager.get_log_path(run_id))
            )
    
    async def _run_process(
        self,
        cmd: List[str],
        workspace: Path,
        session: ClaudeSession,
        stream_callback: Optional[Callable],
        timeout: int
    ) -> CLIResult:
        """Run the Claude CLI process with streaming."""
        # Prepare environment with Node.js in PATH
        env = os.environ.copy()
        env["CLAUDE_SESSION_ID"] = session.run_id
        
        # If claude was found, ensure its directory is in PATH
        if _CLAUDE_EXECUTABLE_PATH:
            claude_dir = os.path.dirname(_CLAUDE_EXECUTABLE_PATH)
            current_path = env.get("PATH", "")
            if claude_dir not in current_path:
                env["PATH"] = f"{claude_dir}:{current_path}"
                logger.debug(f"Added {claude_dir} to PATH for subprocess")
        
        # Create process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(workspace / "am-agents-labs"),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        # Track active process
        self.active_processes[session.run_id] = process
        
        # Create stream processor
        processor = StreamProcessor(stream_callback)
        
        # Collect output
        stdout_lines = []
        stderr_lines = []
        
        try:
            # Create tasks for reading streams
            async def read_stream(stream, lines_list, is_stdout=True):
                async for line in stream:
                    decoded = line.decode('utf-8', errors='replace')
                    lines_list.append(decoded)
                    
                    if is_stdout:
                        # Process JSON streaming output
                        await processor.process_line(decoded)
            
            # Read both streams concurrently with timeout
            stdout_task = asyncio.create_task(
                read_stream(process.stdout, stdout_lines, True)
            )
            stderr_task = asyncio.create_task(
                read_stream(process.stderr, stderr_lines, False)
            )
            
            # Wait for completion with timeout
            await asyncio.wait_for(
                asyncio.gather(process.wait(), stdout_task, stderr_task),
                timeout=timeout
            )
            
        except asyncio.TimeoutError:
            logger.warning(f"Process timed out after {timeout}s")
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
            raise
            
        finally:
            # Clean up
            del self.active_processes[session.run_id]
        
        # Prepare result
        stdout_text = ''.join(stdout_lines)
        stderr_text = ''.join(stderr_lines)
        
        # Update Claude session ID if extracted
        if processor.session_id:
            session.claude_session_id = processor.session_id
        
        return CLIResult(
            success=process.returncode == 0,
            session_id=session.claude_session_id or session.session_id,
            result=processor.get_final_result(),
            exit_code=process.returncode,
            execution_time=0,  # Will be set by caller
            logs=stdout_text + "\n" + stderr_text if stderr_text else stdout_text,
            error=stderr_text if process.returncode != 0 else None,
            streaming_messages=processor.messages
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
    
    async def cancel_execution(self, run_id: str) -> bool:
        """Cancel a running execution.
        
        Args:
            run_id: Run ID to cancel
            
        Returns:
            True if cancelled, False otherwise
        """
        if run_id in self.active_processes:
            process = self.active_processes[run_id]
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
            
            del self.active_processes[run_id]
            logger.info(f"Cancelled execution: {run_id}")
            return True
            
        return False
    
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
    
    async def cleanup(self):
        """Clean up all active processes."""
        for run_id in list(self.active_processes.keys()):
            await self.cancel_execution(run_id)
        
        self.sessions.clear()
        logger.info("ClaudeCLIExecutor cleanup complete")