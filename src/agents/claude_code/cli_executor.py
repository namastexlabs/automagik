"""Claude CLI Executor with session management and streaming.

This module executes Claude CLI commands with session persistence,
streaming JSON output, and proper resource management.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, List, Any, Callable, AsyncIterator
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


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
            'streaming_messages': self.streaming_messages or []
        }


@dataclass 
class ClaudeSession:
    """Manages Claude CLI sessions."""
    
    session_id: Optional[str] = None
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
        """
        cmd = ["claude"]
        
        # Resume session if provided
        if self.session_id:
            cmd.extend(["-r", self.session_id])
        
        # Add standard flags
        cmd.extend([
            "-p",  # Pretty output
            "--output-format", "stream-json",
            "--max-turns", str(self.max_turns),
            "--dangerously-skip-permissions"
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
    
    def __init__(self, on_message: Optional[Callable] = None):
        """Initialize stream processor.
        
        Args:
            on_message: Optional callback for each message
        """
        self.session_id: Optional[str] = None
        self.messages: List[Dict[str, Any]] = []
        self.on_message = on_message
        self.result_text = ""
        self.completed = False
        
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
            
        try:
            data = json.loads(line)
            
            # Extract session ID from init message
            if data.get("type") == "system" and data.get("subtype") == "init":
                # Session ID is directly in the init message
                self.session_id = data.get("session_id")
                logger.info(f"Extracted session ID: {self.session_id}")
            
            # Accumulate result text
            if data.get("type") == "text" and data.get("content"):
                self.result_text += data["content"]
            
            # Detect completion
            if data.get("type") == "result":
                self.completed = True
                if data.get("result"):
                    self.result_text = data["result"]
            
            # Store message
            self.messages.append(data)
            
            # Call callback if provided
            if self.on_message:
                await self.on_message(data)
            
            return data
            
        except json.JSONDecodeError as e:
            # Log non-JSON lines (might be errors or warnings)
            if line and not line.startswith("{"):
                logger.debug(f"Non-JSON output: {line}")
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
        
        # Setup workflow directory
        workflow_dir = workspace / "workflow"
        if not workflow_dir.exists():
            workflow_src = Path(__file__).parent / "workflows" / workflow
            if workflow_src.exists():
                import shutil
                shutil.copytree(workflow_src, workflow_dir)
        
        # Build command
        cmd = session.build_command(message, workspace, workflow_dir)
        
        # Log command (without full message for brevity)
        logger.info(f"Executing Claude CLI: {' '.join(cmd[:10])}...")
        
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
            
            # Execute process
            result = await self._run_process(
                cmd, workspace, session, stream_callback, timeout
            )
            
            # Get git commits
            git_commits = await self._get_git_commits(workspace / "am-agents-labs")
            
            # Update result with commits
            result.git_commits = git_commits
            result.execution_time = time.time() - start_time
            
            # Store session if successful
            if result.success and result.session_id:
                self.sessions[result.session_id] = session
                
            return result
            
        except Exception as e:
            logger.error(f"CLI execution failed: {e}")
            return CLIResult(
                success=False,
                session_id=session.session_id,
                result="",
                exit_code=-1,
                execution_time=time.time() - start_time,
                logs=str(e),
                error=str(e)
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
        # Create process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(workspace / "am-agents-labs"),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "CLAUDE_SESSION_ID": session.run_id}
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
        
        # Update session ID if extracted
        if processor.session_id:
            session.session_id = processor.session_id
        
        return CLIResult(
            success=process.returncode == 0,
            session_id=session.session_id,
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