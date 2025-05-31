"""CLI Node for Claude subprocess execution with streaming output and session management.

This module provides robust wrapper for executing `claude` CLI commands with 
streaming output, process monitoring, and session management for LangGraph orchestration.
"""

import asyncio
import json
import logging
import os
import subprocess
import uuid
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class CLIExecutionError(Exception):
    """Exception raised when CLI execution fails."""
    pass

class CLINode:
    """Claude CLI wrapper with async execution and streaming output."""
    
    def __init__(self):
        """Initialize CLI node."""
        self.active_processes: Dict[str, subprocess.Popen] = {}
        
    async def run_claude_agent(
        self,
        agent_name: str,
        task_message: str,
        workspace_path: str,
        resume_session: Optional[str] = None,
        max_turns: int = 30,
        mcp_config_path: str = "/root/workspace/.mcp.json",
        timeout: Optional[int] = None
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
            
            # Build claude command
            cmd = self._build_claude_command(
                agent_name=agent_name,
                task_message=task_message,
                workspace_path=str(workspace_path),
                resume_session=resume_session,
                max_turns=max_turns,
                mcp_config_path=mcp_config_path
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
        mcp_config_path: str = "/root/workspace/.mcp.json"
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
        cmd = [
            "claude",
            "--max-turns", str(max_turns),
            "--output-format", "json"
        ]
        
        # Add MCP config if exists
        if os.path.exists(mcp_config_path):
            cmd.extend(["--mcp-config", mcp_config_path])
        
        # Add resume session if provided
        if resume_session:
            cmd.extend(["--resume", resume_session])
        
        # Add task message
        cmd.append(task_message)
        
        return cmd
    
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
                async with asyncio.timeout(timeout) if timeout else asyncio.nullcontext():
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