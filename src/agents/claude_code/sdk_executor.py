"""SDK-based executor for Claude Code agent.

This module implements the ClaudeSDKExecutor that uses the official claude-code-sdk
instead of the legacy CLI approach. It provides file-based configuration loading
with proper priority handling.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from uuid import uuid4

from claude_code_sdk import query, ClaudeCodeOptions

from .executor_base import ExecutorBase
from .models import ClaudeCodeRunRequest

logger = logging.getLogger(__name__)


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


class ClaudeSDKExecutor(ExecutorBase):
    """Executor that uses the official claude-code-sdk."""
    
    def __init__(self, environment_manager=None):
        """Initialize the SDK executor.
        
        Args:
            environment_manager: Optional environment manager for workspace handling
        """
        self.environment_manager = environment_manager
        self.active_sessions: Dict[str, Any] = {}
        
    def _build_options(self, workspace: Path, **kwargs) -> ClaudeCodeOptions:
        """Build options with file-based configuration loading.
        
        Args:
            workspace: The workspace directory path
            **kwargs: Additional options that override file-based configs
            
        Returns:
            Configured ClaudeCodeOptions instance
        """
        options = ClaudeCodeOptions()
        
        # Set workspace
        options.workspace = str(workspace)
        
        # Load system prompt from prompt.md (NOT append_system_prompt)
        prompt_file = workspace / "prompt.md"
        if prompt_file.exists():
            try:
                prompt_content = prompt_file.read_text().strip()
                if prompt_content:
                    options.system_prompt = prompt_content
                    logger.info(f"Loaded system prompt from {prompt_file} ({len(prompt_content)} chars)")
                else:
                    logger.debug("prompt.md is empty, using default Claude Code behavior")
            except Exception as e:
                logger.error(f"Failed to load prompt.md: {e}")
        else:
            logger.debug("No prompt.md found, using vanilla Claude Code")
        
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
                except Exception as e:
                    logger.error(f"Failed to load allowed_tools.json: {e}")
        
        # Load disallowed tools if file exists and not explicitly provided
        if 'disallowed_tools' not in kwargs:
            disallowed_tools_file = workspace / "disallowed_tools.json"
            if disallowed_tools_file.exists():
                try:
                    with open(disallowed_tools_file) as f:
                        tools_list = json.load(f)
                        if isinstance(tools_list, list):
                            options.disallowed_tools = tools_list
                            logger.info(f"Loaded {len(tools_list)} disallowed tools from file")
                        else:
                            logger.warning("disallowed_tools.json must contain a JSON array")
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid disallowed_tools.json: {e}")
                except Exception as e:
                    logger.error(f"Failed to load disallowed_tools.json: {e}")
        
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
            except Exception as e:
                logger.error(f"Failed to load .mcp.json: {e}")
        
        # Apply explicit kwargs (highest priority)
        for key, value in kwargs.items():
            if hasattr(options, key) and value is not None:
                setattr(options, key, value)
        
        # Handle max_thinking_tokens if provided
        if 'max_thinking_tokens' in kwargs and kwargs['max_thinking_tokens'] is not None:
            options.max_thinking_tokens = kwargs['max_thinking_tokens']
            logger.info(f"Set max_thinking_tokens to {kwargs['max_thinking_tokens']}")
        
        return options
    
    async def execute_claude_task(
        self, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a Claude Code task using the SDK.
        
        Args:
            request: Execution request with task details
            agent_context: Agent context including session info
            
        Returns:
            Dictionary with execution results
        """
        start_time = time.time()
        session_id = request.session_id or str(uuid4())
        
        try:
            # Get workspace from environment manager
            workspace_path = None
            if self.environment_manager:
                workspace_info = await self.environment_manager.prepare_workspace(
                    repository_url=request.repository_url,
                    git_branch=request.git_branch,
                    session_id=session_id
                )
                workspace_path = Path(workspace_info['workspace_path'])
            else:
                workspace_path = Path.cwd()
            
            # Build options with file-based configs
            options = self._build_options(
                workspace_path,
                max_turns=request.max_turns,
                environment=request.environment
            )
            
            # Store session info
            self.active_sessions[session_id] = {
                'client': self.client,
                'options': options,
                'start_time': start_time,
                'workspace': workspace_path
            }
            
            # Execute the task
            result = await self.client.execute(
                message=request.message,
                options=options
            )
            
            execution_time = time.time() - start_time
            
            # Extract git commits if any
            git_commits = []
            if hasattr(result, 'git_commits'):
                git_commits = result.git_commits
            
            return {
                'success': True,
                'session_id': session_id,
                'result': str(result),
                'exit_code': 0,
                'execution_time': execution_time,
                'logs': '',  # SDK doesn't provide separate logs
                'git_commits': git_commits,
                'workspace_path': str(workspace_path)
            }
            
        except Exception as e:
            logger.error(f"SDK execution failed: {e}")
            
            return {
                'success': False,
                'session_id': session_id,
                'result': '',
                'exit_code': 1,
                'execution_time': time.time() - start_time,
                'logs': str(e),
                'error': str(e),
                'workspace_path': str(workspace_path) if workspace_path else None
            }
        finally:
            # Cleanup session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
    
    async def execute_until_first_response(
        self, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Claude Code and return after first response.
        
        This method starts execution and returns as soon as Claude provides
        the first substantial response.
        
        Args:
            request: Execution request with task details
            agent_context: Agent context including session info
            
        Returns:
            Dictionary with first response data
        """
        session_id = request.session_id or str(uuid4())
        
        try:
            # Get workspace
            workspace_path = None
            if self.environment_manager:
                workspace_info = await self.environment_manager.prepare_workspace(
                    repository_url=request.repository_url,
                    git_branch=request.git_branch,
                    session_id=session_id
                )
                workspace_path = Path(workspace_info['workspace_path'])
            else:
                workspace_path = Path.cwd()
            
            # Build options
            options = self._build_options(
                workspace_path,
                max_turns=request.max_turns,
                environment=request.environment
            )
            
            # Store session info
            self.active_sessions[session_id] = {
                'client': self.client,
                'options': options,
                'start_time': time.time(),
                'workspace': workspace_path
            }
            
            # Start streaming execution
            first_response = None
            async for chunk in self.client.stream(
                message=request.message,
                options=options
            ):
                if chunk and chunk.strip():
                    first_response = chunk
                    break
            
            return {
                'session_id': session_id,
                'first_response': first_response or "Claude Code is processing...",
                'streaming_started': True
            }
            
        except Exception as e:
            logger.error(f"Failed to start streaming: {e}")
            return {
                'session_id': session_id,
                'first_response': f"Error: {str(e)}",
                'streaming_started': False
            }
    
    async def get_execution_logs(self, execution_id: str) -> str:
        """Get execution logs.
        
        Args:
            execution_id: Session ID
            
        Returns:
            Execution logs as string
        """
        # SDK doesn't provide separate log access
        return f"Session {execution_id} logs not available in SDK mode"
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution.
        
        Args:
            execution_id: Session ID
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        if execution_id in self.active_sessions:
            try:
                session = self.active_sessions[execution_id]
                # SDK should provide a cancel method
                if hasattr(session['client'], 'cancel'):
                    await session['client'].cancel()
                del self.active_sessions[execution_id]
                return True
            except Exception as e:
                logger.error(f"Failed to cancel execution: {e}")
                return False
        return False
    
    async def cleanup(self) -> None:
        """Clean up all resources."""
        # Cancel all active sessions
        for session_id in list(self.active_sessions.keys()):
            await self.cancel_execution(session_id)
        
        # Clean up SDK client if needed
        if hasattr(self.client, 'cleanup'):
            await self.client.cleanup()