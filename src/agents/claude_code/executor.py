"""Claude CLI execution logic for Claude-Code agent.

This module provides the ClaudeExecutor class that handles the execution
of Claude CLI commands within Docker containers.
"""
import logging
import asyncio
import json
import os
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from .container import ContainerManager
from .models import ClaudeCodeRunRequest

logger = logging.getLogger(__name__)

class ClaudeExecutor:
    """Handles execution of Claude CLI commands in containers."""
    
    def __init__(self, container_manager: ContainerManager):
        """Initialize the Claude executor.
        
        Args:
            container_manager: Container manager instance
        """
        self.container_manager = container_manager
        
        logger.info("ClaudeExecutor initialized")
    
    async def execute_claude_task(self, request: ClaudeCodeRunRequest, 
                                 agent_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Claude CLI task in a container.
        
        Args:
            request: Claude execution request
            agent_context: Agent context information
            
        Returns:
            Dictionary with execution results
        """
        try:
            # Prepare session ID - use UUID instead of unreliable __hash__
            session_id = request.session_id or f"session_{str(uuid.uuid4())[:8]}"
            
            logger.info(f"Starting Claude task execution for session {session_id}")
            
            # Initialize container manager if needed
            if not self.container_manager.docker_client:
                if not await self.container_manager.initialize():
                    return {
                        'success': False,
                        'error': 'Failed to initialize Docker client',
                        'exit_code': -1
                    }
            
            # Load workflow configuration
            workflow_config = await self._load_workflow_config(request.workflow_name)
            if not workflow_config:
                return {
                    'success': False,
                    'error': f'Failed to load workflow configuration for: {request.workflow_name}',
                    'exit_code': -1
                }
            
            # Prepare environment variables
            environment = await self._prepare_environment(request, workflow_config, agent_context)
            
            # Prepare volumes
            volumes = await self._prepare_volumes(request, workflow_config)
            
            # Create container
            container_id = await self.container_manager.create_container(
                session_id=session_id,
                workflow_name=request.workflow_name,
                environment=environment,
                volumes=volumes
            )
            
            # Build Claude command
            claude_command = await self._build_claude_command(request, workflow_config)
            
            # Start container with Claude command
            if not await self.container_manager.start_container(container_id, claude_command):
                return {
                    'success': False,
                    'error': f'Failed to start container {container_id}',
                    'exit_code': -1
                }
            
            # Wait for completion
            result = await self.container_manager.wait_for_completion(container_id)
            
            # Enhance result with request metadata
            result.update({
                'session_id': session_id,
                'workflow_name': request.workflow_name,
                'request_message': request.message,
                'git_branch': request.git_branch
            })
            
            logger.info(f"Claude task execution completed for session {session_id}: {result.get('success', False)}")
            return result
            
        except Exception as e:
            logger.error(f"Error executing Claude task: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'exit_code': -1
            }
    
    async def _load_workflow_config(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Load workflow configuration from filesystem.
        
        Args:
            workflow_name: Name of the workflow
            
        Returns:
            Workflow configuration dictionary or None if not found
        """
        try:
            workflow_path = os.path.join(
                os.path.dirname(__file__), 
                "workflows", 
                workflow_name
            )
            
            if not os.path.exists(workflow_path):
                logger.error(f"Workflow directory not found: {workflow_path}")
                return None
            
            config = {
                'name': workflow_name,
                'path': workflow_path
            }
            
            # Load prompt
            prompt_file = os.path.join(workflow_path, "prompt.md")
            if os.path.exists(prompt_file):
                with open(prompt_file, 'r') as f:
                    config['prompt'] = f.read()
            else:
                logger.warning(f"Prompt file not found: {prompt_file}")
                config['prompt'] = ""
            
            # Load MCP configuration
            mcp_file = os.path.join(workflow_path, ".mcp.json")
            if os.path.exists(mcp_file):
                with open(mcp_file, 'r') as f:
                    config['mcp_config'] = json.load(f)
            else:
                logger.warning(f"MCP config file not found: {mcp_file}")
                config['mcp_config'] = {}
            
            # Load allowed tools
            tools_file = os.path.join(workflow_path, "allowed_tools.json")
            if os.path.exists(tools_file):
                with open(tools_file, 'r') as f:
                    config['allowed_tools'] = json.load(f)
            else:
                logger.warning(f"Allowed tools file not found: {tools_file}")
                config['allowed_tools'] = []
            
            # Load environment variables
            env_file = os.path.join(workflow_path, ".env")
            if os.path.exists(env_file):
                config['env_file'] = env_file
            
            logger.debug(f"Loaded workflow configuration for: {workflow_name}")
            return config
            
        except Exception as e:
            logger.error(f"Error loading workflow config for {workflow_name}: {str(e)}")
            return None
    
    async def _prepare_environment(self, request: ClaudeCodeRunRequest, 
                                  workflow_config: Dict[str, Any],
                                  agent_context: Dict[str, Any]) -> Dict[str, str]:
        """Prepare environment variables for container execution.
        
        Args:
            request: Execution request
            workflow_config: Workflow configuration
            agent_context: Agent context
            
        Returns:
            Dictionary of environment variables
        """
        env = {
            'SESSION_ID': request.session_id or '',
            'WORKFLOW_NAME': request.workflow_name,
            'GIT_BRANCH': request.git_branch,
            'CLAUDE_MESSAGE': request.message,
            'MAX_TURNS': str(request.max_turns),
            'WORKSPACE_DIR': '/workspace/am-agents-labs',
            'WORKFLOW_DIR': '/workspace/workflow'
        }
        
        # Add agent context variables
        if agent_context:
            env.update({
                'AGENT_ID': str(agent_context.get('agent_id', '')),
                'USER_ID': str(agent_context.get('user_id', '')),
                'RUN_ID': str(agent_context.get('run_id', ''))
            })
        
        # Load environment from workflow .env file if available
        env_file = workflow_config.get('env_file')
        if env_file and os.path.exists(env_file):
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env[key.strip()] = value.strip()
            except Exception as e:
                logger.warning(f"Error loading environment file {env_file}: {str(e)}")
        
        logger.debug(f"Prepared {len(env)} environment variables")
        return env
    
    async def _prepare_volumes(self, request: ClaudeCodeRunRequest,
                              workflow_config: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        """Prepare volume mounts for container execution.
        
        Args:
            request: Execution request
            workflow_config: Workflow configuration
            
        Returns:
            Dictionary of volume mount specifications
        """
        volumes = {}
        
        # Workflow configuration volume (read-only)
        workflow_path = workflow_config['path']
        volumes[workflow_path] = {
            'bind': '/workspace/workflow',
            'mode': 'ro'
        }
        
        # Workspace volume (read-write)
        session_id = request.session_id or 'default'
        workspace_volume = f"claude-workspace-{session_id}"
        volumes[workspace_volume] = {
            'bind': '/workspace',
            'mode': 'rw'
        }
        
        # Docker socket for docker-in-docker (if needed)
        volumes['/var/run/docker.sock'] = {
            'bind': '/var/run/docker.sock',
            'mode': 'rw'
        }
        
        # SSH keys for git operations (if available)
        ssh_dir = os.path.expanduser('~/.ssh')
        if os.path.exists(ssh_dir):
            volumes[ssh_dir] = {
                'bind': '/home/claude/.ssh',
                'mode': 'ro'
            }
        
        logger.debug(f"Prepared {len(volumes)} volume mounts")
        return volumes
    
    async def _build_claude_command(self, request: ClaudeCodeRunRequest,
                                   workflow_config: Dict[str, Any]) -> List[str]:
        """Build the Claude CLI command to execute.
        
        Args:
            request: Execution request
            workflow_config: Workflow configuration
            
        Returns:
            List of command arguments
        """
        # The entrypoint.sh script will handle the actual claude command construction
        # We just pass the user message as the argument
        command = [request.message]
        
        logger.debug(f"Built Claude command: {' '.join(command)}")
        return command
    
    async def get_execution_logs(self, container_id: str) -> str:
        """Get execution logs from a container.
        
        Args:
            container_id: Container identifier
            
        Returns:
            Container logs as string
        """
        try:
            if container_id in self.container_manager.active_containers:
                container = self.container_manager.active_containers[container_id]['container']
                logs = container.logs(stdout=True, stderr=True).decode('utf-8')
                return logs
            else:
                return f"Container {container_id} not found"
                
        except Exception as e:
            logger.error(f"Error getting logs for container {container_id}: {str(e)}")
            return f"Error retrieving logs: {str(e)}"
    
    async def cancel_execution(self, container_id: str) -> bool:
        """Cancel a running execution.
        
        Args:
            container_id: Container identifier
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            if container_id in self.container_manager.active_containers:
                await self.container_manager._kill_container(container_id)
                await self.container_manager._cleanup_container(container_id)
                logger.info(f"Cancelled execution in container {container_id}")
                return True
            else:
                logger.warning(f"Container {container_id} not found for cancellation")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling execution in container {container_id}: {str(e)}")
            return False