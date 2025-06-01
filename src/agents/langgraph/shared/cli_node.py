"""CLI Node for Claude subprocess execution with streaming output and session management.

This module provides robust wrapper for executing `claude` CLI commands with 
streaming output, process monitoring, and session management for LangGraph orchestration.
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import uuid
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import sys
from contextlib import asynccontextmanager

# Python 3.11+ compatibility
if sys.version_info >= (3, 11):
    from asyncio import timeout as async_timeout
else:
    # For Python < 3.11, use async_timeout package or a simple wrapper
    @asynccontextmanager
    async def async_timeout(seconds):
        """Simple timeout context manager for older Python versions."""
        if seconds is None:
            yield
            return
            
        task = asyncio.current_task()
        if task is None:
            yield
            return
            
        async def _timeout():
            await asyncio.sleep(seconds)
            task.cancel()
            
        timeout_task = asyncio.create_task(_timeout())
        try:
            yield
        finally:
            timeout_task.cancel()
            try:
                await timeout_task
            except asyncio.CancelledError:
                pass

logger = logging.getLogger(__name__)

class CLIExecutionError(Exception):
    """Exception raised when CLI execution fails."""
    pass

class CLINode:
    """Claude CLI wrapper with async execution and streaming output."""
    
    def __init__(self):
        """Initialize CLI node."""
        self.active_processes: Dict[str, subprocess.Popen] = {}


class EnhancedCLINode(CLINode):
    """Extended CLI node with process management capabilities."""
    
    async def kill_active_process(self, pid: int, force: bool = False) -> bool:
        """Kill a running Claude process.
        
        Args:
            pid: Process ID to kill
            force: Use SIGKILL instead of SIGTERM
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if process exists first
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                logger.warning(f"Process {pid} does not exist")
                return True  # Already dead
            
            # First try graceful termination
            logger.info(f"Sending SIGTERM to process {pid}")
            os.kill(pid, signal.SIGTERM)
            
            # Wait up to 5 seconds for graceful shutdown
            for _ in range(5):
                await asyncio.sleep(1)
                try:
                    os.kill(pid, 0)  # Check if still alive
                except ProcessLookupError:
                    logger.info(f"Process {pid} terminated gracefully")
                    return True
            
            # Still running, force kill if requested
            if force:
                logger.warning(f"Force killing process {pid} with SIGKILL")
                os.kill(pid, signal.SIGKILL)
                await asyncio.sleep(1)
                
                # Verify it's dead
                try:
                    os.kill(pid, 0)
                    logger.error(f"Process {pid} survived SIGKILL!")
                    return False
                except ProcessLookupError:
                    logger.info(f"Process {pid} force killed successfully")
                    return True
            else:
                logger.warning(f"Process {pid} did not terminate gracefully, use force=True to kill")
                return False
                
        except Exception as e:
            logger.error(f"Failed to kill process {pid}: {str(e)}")
            return False
    
    async def get_process_info(self, pid: int) -> Optional[Dict[str, Any]]:
        """Get information about a process.
        
        Args:
            pid: Process ID
            
        Returns:
            Process info dict or None if not found
        """
        try:
            # Check if process exists
            os.kill(pid, 0)
            
            # Get process info using ps command
            cmd = ["ps", "-p", str(pid), "-o", "pid,ppid,state,cmd", "--no-headers"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout:
                parts = result.stdout.strip().split(None, 3)
                if len(parts) >= 4:
                    return {
                        "pid": int(parts[0]),
                        "ppid": int(parts[1]),
                        "state": parts[2],
                        "command": parts[3],
                        "exists": True
                    }
            
            return {"pid": pid, "exists": True, "info": "Limited info available"}
            
        except ProcessLookupError:
            return {"pid": pid, "exists": False}
        except Exception as e:
            logger.error(f"Error getting process info for {pid}: {e}")
            return None
        
    async def run_claude_agent(
        self,
        agent_name: str,
        task_message: str,
        workspace_path: str,
        resume_session: Optional[str] = None,
        max_turns: int = 1,  # Default to 1 for tests
        mcp_config_path: Optional[str] = None,
        timeout: Optional[int] = None,
        orchestration_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute claude CLI agent with streaming output and session management.
        
        Args:
            agent_name: Name of the agent to run
            task_message: Task message for the agent
            workspace_path: Working directory for execution
            resume_session: Optional session UUID to resume
            max_turns: Maximum conversation turns
            mcp_config_path: Path to MCP configuration file
            timeout: Optional timeout in seconds
            
        Returns:
            Dict containing execution results:
            {
                "claude_session_id": str,
                "result": str,
                "exit_code": int,
                "git_sha_start": str,
                "git_sha_end": str,
                "pid": int,
                "output": str
            }
            
        Raises:
            CLIExecutionError: If execution fails
        """
        try:
            # Ensure workspace directory exists
            workspace_path = Path(workspace_path)
            workspace_path.mkdir(parents=True, exist_ok=True)
            
            # Capture git SHA before execution
            git_sha_start = await self._get_git_sha(workspace_path)
            
            # Override parameters from orchestration config
            config = orchestration_config or {}
            
            # Use orchestration config values if provided
            if config.get("resume_session"):
                resume_session = config["resume_session"]
            if config.get("max_turns") is not None:
                max_turns = config["max_turns"]
            if config.get("mcp_config_path"):
                mcp_config_path = config["mcp_config_path"]
            
            # Build claude command
            cmd = self._build_claude_command(
                agent_name=agent_name,
                task_message=task_message,
                workspace_path=str(workspace_path),
                resume_session=resume_session,
                max_turns=max_turns,
                mcp_config_path=mcp_config_path,
                orchestration_config=config
            )
            
            logger.info(f"Executing claude command: {' '.join(cmd)}")
            
            # Execute process with streaming
            result = await self._execute_with_streaming(
                cmd=cmd,
                workspace_path=str(workspace_path),
                timeout=timeout
            )
            
            # Capture git SHA after execution
            git_sha_end = await self._get_git_sha(workspace_path)
            
            # Parse claude session ID from output
            claude_session_id = self._extract_session_id(result["output"])
            
            return {
                "claude_session_id": claude_session_id,
                "result": result["output"],
                "exit_code": result["exit_code"],
                "git_sha_start": git_sha_start,
                "git_sha_end": git_sha_end,
                "pid": result["pid"],
                "output": result["output"]
            }
            
        except Exception as e:
            logger.error(f"CLI execution failed: {str(e)}")
            raise CLIExecutionError(f"Failed to execute claude agent: {str(e)}")
    
    def _build_claude_command(
        self,
        agent_name: str,
        task_message: str,
        workspace_path: str,
        resume_session: Optional[str] = None,
        max_turns: int = 30,
        mcp_config_path: Optional[str] = None,
        orchestration_config: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Build claude CLI command with proper arguments.
        
        Args:
            agent_name: Name of the agent
            task_message: Task message
            workspace_path: Working directory
            resume_session: Optional session to resume
            max_turns: Maximum turns
            mcp_config_path: MCP config path
            
        Returns:
            List of command arguments
        """
        cmd = ["claude"]
        
        # Add resume session if provided
        if resume_session:
            cmd.extend(["--resume", resume_session])
            # For resume, add the continuation message with -p
            cmd.extend(["-p", task_message])
        else:
            # For new session, add the task message with -p
            cmd.extend(["-p", task_message])
            
            # Add system prompt based on agent name
            prompt_file = f"/root/prod/am-agents-labs/.claude/agents-prompts/{agent_name}_prompt.md"
            if os.path.exists(prompt_file):
                cmd.extend(["--append-system-prompt", prompt_file])
            else:
                # Try alternative location
                alt_prompt_file = f"/root/workspace/.claude/agents-prompts/{agent_name}_prompt.md" 
                if os.path.exists(alt_prompt_file):
                    cmd.extend(["--append-system-prompt", alt_prompt_file])
        
        # Find MCP config - check workspace root first, then parent
        if not mcp_config_path:
            # Try workspace root first
            workspace_mcp = os.path.join(workspace_path, ".mcp.json")
            if os.path.exists(workspace_mcp):
                mcp_config_path = workspace_mcp
            else:
                # Try parent directory
                parent_mcp = os.path.join(os.path.dirname(workspace_path), ".mcp.json")
                if os.path.exists(parent_mcp):
                    mcp_config_path = parent_mcp
                else:
                    # Fallback to default
                    mcp_config_path = "/root/workspace/.mcp.json"
        
        if os.path.exists(mcp_config_path):
            cmd.extend(["--mcp-config", mcp_config_path])
            logger.info(f"Using MCP config: {mcp_config_path}")
        
        # Load allowed tools from JSON file or use custom path
        config = orchestration_config or {}
        if config.get("allowed_tools_file"):
            # Use custom allowed tools file
            allowed_tools_file = config["allowed_tools_file"]
        else:
            # Use default search
            allowed_tools_file = None
        
        allowed_tools = self._load_allowed_tools(workspace_path, allowed_tools_file)
        if allowed_tools:
            cmd.extend(["--allowedTools", ",".join(allowed_tools)])
        
        # Add max turns and output format
        cmd.extend(["--max-turns", str(max_turns)])
        cmd.extend(["--output-format", "json"])
        
        return cmd
    
    def _load_allowed_tools(self, workspace_path: str, custom_file: Optional[str] = None) -> List[str]:
        """Load allowed tools from JSON file.
        
        Args:
            workspace_path: Working directory
            
        Returns:
            List of allowed tool names
        """
        # Use custom file if provided
        if custom_file and os.path.exists(custom_file):
            tools_file = custom_file
        else:
            # Try workspace root first
            tools_file = os.path.join(workspace_path, "allowed_tools.json")
            if not os.path.exists(tools_file):
                # Try parent directory
                tools_file = os.path.join(os.path.dirname(workspace_path), "allowed_tools.json")
        
        if os.path.exists(tools_file):
            try:
                with open(tools_file, 'r') as f:
                    tools = json.load(f)
                    logger.info(f"Loaded {len(tools)} allowed tools from {tools_file}")
                    return tools
            except Exception as e:
                logger.warning(f"Failed to load allowed tools from {tools_file}: {e}")
        
        # Return minimal default set if file not found
        logger.warning("Using default allowed tools")
        return [
            "mcp__postgres_automagik_agents__query",
            "mcp__agent-memory__search_memory_nodes",
            "mcp__agent-memory__search_memory_facts",
            "mcp__agent-memory__add_memory"
        ]
    
    async def _execute_with_streaming(
        self,
        cmd: List[str],
        workspace_path: str,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute command with streaming output capture.
        
        Args:
            cmd: Command to execute
            workspace_path: Working directory
            timeout: Optional timeout
            
        Returns:
            Dict with output, exit_code, and pid
        """
        try:
            # Start process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=workspace_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=os.environ.copy()
            )
            
            # Store process for monitoring
            process_id = str(uuid.uuid4())
            self.active_processes[process_id] = process
            
            output_lines = []
            
            try:
                # Stream output with timeout
                async with async_timeout(timeout):
                    async for line in process.stdout:
                        line_str = line.decode('utf-8', errors='replace').rstrip()
                        output_lines.append(line_str)
                        logger.info(f"[{process.pid}] {line_str}")
                
                # Wait for completion
                exit_code = await process.wait()
                
            except asyncio.TimeoutError:
                logger.warning(f"Process {process.pid} timed out, terminating")
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                raise CLIExecutionError("Process timed out")
            
            finally:
                # Clean up process tracking
                if process_id in self.active_processes:
                    del self.active_processes[process_id]
            
            output = '\n'.join(output_lines)
            
            return {
                "output": output,
                "exit_code": exit_code,
                "pid": process.pid
            }
            
        except Exception as e:
            logger.error(f"Process execution failed: {str(e)}")
            raise
    
    async def _get_git_sha(self, workspace_path: Path) -> str:
        """Get current git SHA for workspace.
        
        Args:
            workspace_path: Path to workspace
            
        Returns:
            Git SHA string or 'unknown' if not a git repo
        """
        try:
            process = await asyncio.create_subprocess_exec(
                "git", "rev-parse", "HEAD",
                cwd=str(workspace_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode().strip()
            else:
                logger.warning(f"Git SHA lookup failed: {stderr.decode()}")
                return "unknown"
                
        except Exception as e:
            logger.warning(f"Could not get git SHA: {str(e)}")
            return "unknown"
    
    def _extract_session_id(self, output: str) -> Optional[str]:
        """Extract claude session ID from output.
        
        Args:
            output: Command output
            
        Returns:
            Session ID if found, None otherwise
        """
        try:
            # Look for JSON output at the end
            lines = output.strip().split('\n')
            for line in reversed(lines):
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    try:
                        data = json.loads(line)
                        if 'session_id' in data:
                            return data['session_id']
                    except json.JSONDecodeError:
                        continue
            
            # Fallback: look for session patterns
            import re
            session_pattern = r'session[_-]?id["\']?\s*[:=]\s*["\']?([a-f0-9-]{36})["\']?'
            match = re.search(session_pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)
            
            logger.warning("Could not extract session ID from output")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting session ID: {str(e)}")
            return None
    
    async def kill_process(self, pid: int, force: bool = False) -> bool:
        """Kill a running process.
        
        Args:
            pid: Process ID to kill
            force: Use SIGKILL instead of SIGTERM
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import signal
            
            # Find process in our tracking
            process = None
            for proc in self.active_processes.values():
                if proc.pid == pid:
                    process = proc
                    break
            
            if process:
                if force:
                    process.kill()
                else:
                    process.terminate()
                    
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    if not force:
                        process.kill()
                        await process.wait()
                
                return True
            else:
                # Direct OS kill
                os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
                return True
                
        except Exception as e:
            logger.error(f"Failed to kill process {pid}: {str(e)}")
            return False
    
    def get_active_processes(self) -> Dict[str, Dict[str, Any]]:
        """Get information about active processes.
        
        Returns:
            Dict mapping process IDs to process info
        """
        result = {}
        for proc_id, process in self.active_processes.items():
            result[proc_id] = {
                "pid": process.pid,
                "poll": process.poll(),
                "returncode": process.returncode
            }
        return result 