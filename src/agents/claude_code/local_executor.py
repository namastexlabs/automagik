"""Local execution implementation for Claude Code agent.

This module provides the LocalExecutor class that executes Claude CLI
directly on the host system without Docker containers.
"""

import asyncio
import subprocess
import os
import shutil
import tempfile
import json
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

from .executor_base import ExecutorBase
from .models import ClaudeCodeRunRequest

import logging
logger = logging.getLogger(__name__)


class LocalExecutor(ExecutorBase):
    """Executes Claude CLI directly on the host system."""
    
    def __init__(
        self, 
        workspace_base: str = "/tmp/claude-workspace",
        cleanup_on_complete: bool = True,
        git_cache_enabled: bool = False
    ):
        """Initialize the local executor.
        
        Args:
            workspace_base: Base directory for workspaces
            cleanup_on_complete: Whether to cleanup after execution
            git_cache_enabled: Whether to cache git repositories
        """
        self.workspace_base = workspace_base
        self.cleanup_on_complete = cleanup_on_complete
        self.git_cache_enabled = git_cache_enabled
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.workspace_paths: Dict[str, str] = {}
        
        # Ensure workspace base exists
        os.makedirs(self.workspace_base, exist_ok=True)
        
        logger.info(f"LocalExecutor initialized with workspace base: {workspace_base}")
    
    async def execute_claude_task(
        self, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a Claude CLI task locally.
        
        Args:
            request: Execution request with task details
            agent_context: Agent context including session info
            
        Returns:
            Dictionary with execution results
        """
        session_id = request.session_id or f"session_{int(time.time())}"
        start_time = time.time()
        
        try:
            # Create workspace
            workspace_dir = await self._create_workspace(session_id)
            self.workspace_paths[session_id] = workspace_dir
            
            # Setup repository
            await self._setup_repository(
                workspace_dir, 
                request.git_branch,
                repository_url="https://github.com/namastexlabs/am-agents-labs.git"
            )
            
            # Setup workflow configuration
            await self._setup_workflow(workspace_dir, request.workflow_name)
            
            # Build environment
            env = await self._build_environment(request, agent_context, workspace_dir)
            
            # Run Claude process
            result = await self._run_claude_process(
                workspace_dir,
                request.message,
                env,
                timeout=int(request.timeout or 7200)
            )
            
            # Get git commits
            git_commits = await self._get_git_commits(workspace_dir)
            
            # Cleanup if configured
            if self.cleanup_on_complete:
                await self._cleanup_workspace(workspace_dir)
                del self.workspace_paths[session_id]
            
            return {
                'success': result.get('success', True),
                'session_id': session_id,
                'result': result.get('output', ''),
                'exit_code': result.get('exit_code', 0),
                'execution_time': time.time() - start_time,
                'logs': result.get('logs', ''),
                'error': result.get('error'),
                'git_commits': git_commits,
                'workspace_path': workspace_dir if not self.cleanup_on_complete else None
            }
            
        except Exception as e:
            logger.error(f"Error executing local Claude task: {str(e)}")
            return {
                'success': False,
                'session_id': session_id,
                'result': '',
                'exit_code': -1,
                'execution_time': time.time() - start_time,
                'logs': '',
                'error': str(e),
                'git_commits': [],
                'workspace_path': None
            }
    
    async def get_execution_logs(self, execution_id: str) -> str:
        """Get execution logs.
        
        Args:
            execution_id: Session ID for local execution
            
        Returns:
            Execution logs as string
        """
        # For local execution, we would need to implement log persistence
        # For now, return a placeholder
        return f"Logs for session {execution_id} not available in local mode"
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution.
        
        Args:
            execution_id: Session ID for local execution
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            if execution_id in self.active_processes:
                process = self.active_processes[execution_id]
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                del self.active_processes[execution_id]
                logger.info(f"Cancelled local execution for session {execution_id}")
                return True
            else:
                logger.warning(f"No active process found for session {execution_id}")
                return False
        except Exception as e:
            logger.error(f"Error cancelling execution {execution_id}: {str(e)}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up all resources."""
        try:
            # Cancel all active processes
            for execution_id in list(self.active_processes.keys()):
                await self.cancel_execution(execution_id)
            
            # Clean up workspaces if configured
            if self.cleanup_on_complete:
                for session_id, workspace_path in list(self.workspace_paths.items()):
                    await self._cleanup_workspace(workspace_path)
                    
            logger.info("LocalExecutor cleanup completed")
        except Exception as e:
            logger.error(f"Error during LocalExecutor cleanup: {str(e)}")
    
    async def _create_workspace(self, session_id: str) -> str:
        """Create a workspace directory for the session.
        
        Returns:
            Full path to the created workspace
            
        Raises:
            OSError: If workspace creation fails
        """
        workspace_dir = os.path.join(self.workspace_base, f"claude-workspace-{session_id}")
        
        try:
            os.makedirs(workspace_dir, exist_ok=True)
            os.chmod(workspace_dir, 0o755)
            logger.info(f"Created workspace: {workspace_dir}")
            return workspace_dir
        except Exception as e:
            logger.error(f"Failed to create workspace: {str(e)}")
            raise OSError(f"Failed to create workspace: {str(e)}")
    
    async def _setup_repository(
        self, 
        workspace_dir: str, 
        git_branch: str,
        repository_url: str = "https://github.com/namastexlabs/am-agents-labs.git"
    ) -> None:
        """Clone and setup the repository in the workspace.
        
        Raises:
            subprocess.CalledProcessError: If git operations fail
        """
        repo_dir = os.path.join(workspace_dir, "am-agents-labs")
        
        try:
            # Clone repository
            clone_cmd = ["git", "clone", "--depth", "1", "--branch", git_branch, repository_url, repo_dir]
            
            process = await asyncio.create_subprocess_exec(
                *clone_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode, clone_cmd, stdout, stderr
                )
            
            # Configure git user
            git_config_cmds = [
                ["git", "config", "user.name", "Claude Code Agent"],
                ["git", "config", "user.email", "claude@automagik-agents.com"]
            ]
            
            for cmd in git_config_cmds:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=repo_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
            
            logger.info(f"Repository cloned and configured in: {repo_dir}")
            
        except Exception as e:
            logger.error(f"Failed to setup repository: {str(e)}")
            raise
    
    async def _setup_workflow(self, workspace_dir: str, workflow_name: str) -> None:
        """Copy workflow configuration to workspace."""
        try:
            # Source workflow directory
            workflow_src = os.path.join(
                os.path.dirname(__file__), 
                "workflows", 
                workflow_name
            )
            
            if not os.path.exists(workflow_src):
                raise FileNotFoundError(f"Workflow not found: {workflow_name}")
            
            # Destination workflow directory
            workflow_dst = os.path.join(workspace_dir, "workflow")
            
            # Copy workflow files
            shutil.copytree(workflow_src, workflow_dst)
            
            logger.info(f"Workflow {workflow_name} copied to workspace")
            
        except Exception as e:
            logger.error(f"Failed to setup workflow: {str(e)}")
            raise
    
    async def _build_environment(
        self, 
        request: ClaudeCodeRunRequest,
        agent_context: Dict[str, Any],
        workspace_dir: str
    ) -> Dict[str, str]:
        """Build environment variables for Claude execution."""
        env = os.environ.copy()
        
        # Add specific environment variables
        env.update({
            'SESSION_ID': request.session_id or '',
            'WORKFLOW_NAME': request.workflow_name,
            'GIT_BRANCH': request.git_branch,
            'CLAUDE_MESSAGE': request.message,
            'MAX_TURNS': str(request.max_turns),
            'WORKSPACE_DIR': os.path.join(workspace_dir, 'am-agents-labs'),
            'WORKFLOW_DIR': os.path.join(workspace_dir, 'workflow')
        })
        
        # Add agent context
        if agent_context:
            env.update({
                'AGENT_ID': str(agent_context.get('agent_id', '')),
                'USER_ID': str(agent_context.get('user_id', '')),
                'RUN_ID': str(agent_context.get('run_id', ''))
            })
        
        return env
    
    async def _run_claude_process(
        self,
        workspace_dir: str,
        message: str,
        env: Dict[str, str],
        timeout: int
    ) -> Dict[str, Any]:
        """Run Claude CLI as a subprocess.
        
        Returns:
            Execution result dictionary
            
        Raises:
            asyncio.TimeoutError: If execution exceeds timeout
        """
        # Build Claude command similar to entrypoint.sh
        claude_cmd = [
            "claude",
            "--dangerously-skip-permissions",
            "--output-format", "stream-json",
            "--max-turns", env.get('MAX_TURNS', '30')
        ]
        
        workflow_dir = env.get('WORKFLOW_DIR', os.path.join(workspace_dir, 'workflow'))
        
        # Add MCP configuration if available
        mcp_config = os.path.join(workflow_dir, '.mcp.json')
        if os.path.exists(mcp_config):
            claude_cmd.extend(["--mcp-config", mcp_config])
        
        # Add allowed tools if available
        tools_file = os.path.join(workflow_dir, 'allowed_tools.json')
        if os.path.exists(tools_file):
            try:
                with open(tools_file, 'r') as f:
                    tools = json.load(f)
                    if tools:
                        claude_cmd.extend(["--allowedTools", ",".join(tools)])
            except Exception as e:
                logger.warning(f"Failed to load allowed tools: {e}")
        
        # Add system prompt if available
        prompt_file = os.path.join(workflow_dir, 'prompt.md')
        if os.path.exists(prompt_file):
            with open(prompt_file, 'r') as f:
                prompt_content = f.read()
            claude_cmd.extend(["--append-system-prompt", prompt_content])
        
        # Add the user message
        claude_cmd.append(message)
        
        try:
            # Log the command for debugging
            logger.info(f"Running Claude command: {' '.join(claude_cmd[:5])}...")
            
            # Run Claude CLI
            process = await asyncio.create_subprocess_exec(
                *claude_cmd,
                cwd=os.path.join(workspace_dir, 'am-agents-labs'),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Store active process
            session_id = env.get('SESSION_ID', 'unknown')
            self.active_processes[session_id] = process
            
            # Monitor process with streaming output (useful for --output-format stream-json)
            output_lines = []
            error_lines = []
            
            async def read_stream(stream, lines_list, stream_name):
                """Read from a stream line by line."""
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded_line = line.decode('utf-8')
                    lines_list.append(decoded_line)
                    
                    # Log streaming output for monitoring
                    if stream_name == 'stdout' and decoded_line.strip():
                        try:
                            # Try to parse JSON line for stream-json format
                            json_data = json.loads(decoded_line.strip())
                            if 'content' in json_data:
                                logger.debug(f"Claude output: {json_data.get('content', '')[:100]}...")
                        except:
                            logger.debug(f"Claude output: {decoded_line.strip()[:100]}...")
            
            try:
                # Create tasks for reading both streams
                stdout_task = asyncio.create_task(read_stream(process.stdout, output_lines, 'stdout'))
                stderr_task = asyncio.create_task(read_stream(process.stderr, error_lines, 'stderr'))
                
                # Wait for process to complete with timeout
                await asyncio.wait_for(
                    asyncio.gather(process.wait(), stdout_task, stderr_task),
                    timeout=timeout
                )
                
            except asyncio.TimeoutError:
                logger.warning(f"Claude process timed out after {timeout} seconds")
                process.terminate()
                await asyncio.sleep(1)
                if process.returncode is None:
                    process.kill()
                raise
            finally:
                # Remove from active processes
                if session_id in self.active_processes:
                    del self.active_processes[session_id]
            
            # Join output lines
            stdout = ''.join(output_lines)
            stderr = ''.join(error_lines)
            
            # Parse output (already strings from read_stream)
            output = stdout
            error_output = stderr
            
            # Try to parse JSON output from Claude
            result_text = output
            try:
                # Claude outputs stream-json, so we need to parse the last complete JSON
                json_lines = [line for line in output.strip().split('\n') if line.strip()]
                if json_lines:
                    last_json = json.loads(json_lines[-1])
                    result_text = last_json.get('result', last_json.get('content', output))
            except Exception as e:
                logger.debug(f"Could not parse Claude JSON output: {e}")
            
            return {
                'success': process.returncode == 0,
                'output': result_text,
                'logs': output + '\n' + error_output if error_output else output,
                'exit_code': process.returncode,
                'error': error_output if process.returncode != 0 else None
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Claude process timed out after {timeout} seconds")
            return {
                'success': False,
                'output': '',
                'logs': f'Process timed out after {timeout} seconds',
                'exit_code': -1,
                'error': 'Execution timeout exceeded'
            }
        except Exception as e:
            logger.error(f"Error running Claude process: {str(e)}")
            return {
                'success': False,
                'output': '',
                'logs': str(e),
                'exit_code': -1,
                'error': str(e)
            }
    
    async def _get_git_commits(self, workspace_dir: str) -> List[str]:
        """Get list of git commits made during execution."""
        repo_dir = os.path.join(workspace_dir, "am-agents-labs")
        
        try:
            # Get commits since clone
            cmd = ["git", "log", "--format=%H", "--reverse", "HEAD@{1}..HEAD"]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=repo_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                commits = stdout.decode('utf-8').strip().split('\n')
                return [c for c in commits if c]  # Filter empty strings
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting git commits: {str(e)}")
            return []
    
    async def _cleanup_workspace(self, workspace_dir: str) -> None:
        """Clean up a workspace directory."""
        try:
            if os.path.exists(workspace_dir):
                shutil.rmtree(workspace_dir)
                logger.info(f"Cleaned up workspace: {workspace_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up workspace {workspace_dir}: {str(e)}")