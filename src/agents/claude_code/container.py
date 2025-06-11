"""Container management for Claude-Code agent.

This module provides Docker container lifecycle management for running
Claude CLI in isolated environments.
"""
import logging
import asyncio
import uuid
import time
import json
import tempfile
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta

from .repository_utils import setup_repository

try:
    import docker
    from docker.errors import DockerException, APIError, ContainerError
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None
    DockerException = Exception
    APIError = Exception
    ContainerError = Exception

logger = logging.getLogger(__name__)

class ContainerManager:
    """Manages Docker container lifecycle for Claude CLI execution."""
    
    def __init__(self, docker_image: str = "claude-code-agent:latest", 
                 container_timeout: int = 7200, max_concurrent: int = 10):
        """Initialize the container manager.
        
        Args:
            docker_image: Docker image to use for containers
            container_timeout: Maximum container runtime in seconds
            max_concurrent: Maximum number of concurrent containers
        """
        if not DOCKER_AVAILABLE:
            raise RuntimeError("Docker Python library not available. Install with: pip install docker")
        
        self.docker_image = docker_image
        self.container_timeout = container_timeout
        self.max_concurrent = max_concurrent
        
        # Container tracking
        self.active_containers: Dict[str, Dict[str, Any]] = {}
        self.container_semaphore = asyncio.BoundedSemaphore(max_concurrent)
        
        # Docker client
        self.docker_client = None
        
        logger.info(f"ContainerManager initialized with image: {docker_image}, timeout: {container_timeout}s")
    
    async def setup_repository_for_container(
        self, 
        session_id: str,
        git_branch: Optional[str] = None,
        repository_url: Optional[str] = None
    ) -> tuple[Path, str]:
        """Setup repository for container execution.
        
        Args:
            session_id: Unique session identifier
            git_branch: Git branch to use
            repository_url: Optional remote repository URL
            
        Returns:
            Tuple of (temp_workspace_path, repo_name)
        """
        # Create temporary workspace for repository setup
        temp_workspace = Path(tempfile.mkdtemp(prefix=f"claude-workspace-{session_id}-"))
        
        try:
            # Setup repository (copy local or clone remote)
            repo_path = await setup_repository(
                workspace=temp_workspace,
                branch=git_branch,
                repository_url=repository_url
            )
            
            repo_name = repo_path.name
            logger.info(f"Repository setup completed: {repo_path}")
            return temp_workspace, repo_name
            
        except Exception as e:
            # Cleanup on failure
            import shutil
            try:
                shutil.rmtree(temp_workspace)
            except Exception:
                pass
            raise RuntimeError(f"Failed to setup repository: {str(e)}")
    
    async def initialize(self) -> bool:
        """Initialize the Docker client and validate setup.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Initialize Docker client
            self.docker_client = docker.from_env()
            
            # Test Docker connection
            self.docker_client.ping()
            
            # Check if image exists, build if needed
            await self._ensure_image_exists()
            
            logger.info("Docker client initialized successfully")
            return True
            
        except RuntimeError:
            # Re-raise RuntimeError for missing Dockerfile
            raise
        except DockerException as e:
            logger.error(f"Failed to initialize Docker client: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error initializing Docker: {str(e)}")
            return False
    
    async def _ensure_image_exists(self) -> None:
        """Ensure the Claude Code Docker image exists."""
        try:
            # Try to get the image
            self.docker_client.images.get(self.docker_image)
            logger.debug(f"Docker image {self.docker_image} found")
            
        except docker.errors.ImageNotFound:
            logger.info(f"Docker image {self.docker_image} not found, building...")
            
            # Build the image from the Dockerfile
            import os
            dockerfile_path = os.path.join(os.path.dirname(__file__), "docker")
            
            if not os.path.exists(os.path.join(dockerfile_path, "Dockerfile")):
                raise RuntimeError(f"Dockerfile not found at {dockerfile_path}")
            
            # Build the image
            image, build_logs = self.docker_client.images.build(
                path=dockerfile_path,
                tag=self.docker_image,
                rm=True,
                forcerm=True
            )
            
            logger.info(f"Successfully built Docker image: {self.docker_image}")
            
            # Log build output for debugging
            for log in build_logs:
                if 'stream' in log:
                    logger.debug(f"Build: {log['stream'].strip()}")
    
    async def create_container(
        self, 
        session_id: str, 
        workflow_name: str, 
        environment: Optional[Dict[str, str]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        git_branch: Optional[str] = None,
        repository_url: Optional[str] = None
    ) -> str:
        """Create a new container for Claude CLI execution.
        
        Args:
            session_id: Unique session identifier
            workflow_name: Name of the workflow to execute
            environment: Environment variables for the container
            volumes: Volume mounts for the container
            git_branch: Git branch to use
            repository_url: Optional remote repository URL
            
        Returns:
            Container ID
        """
        if not self.docker_client:
            await self.initialize()
        
        # Wait for available slot
        await self.container_semaphore.acquire()
        
        try:
            container_id = f"claude-code-{session_id}-{uuid.uuid4().hex[:8]}"
            
            # Setup repository (copy local or clone remote)
            workspace_path, repo_name = await self.setup_repository_for_container(
                session_id=session_id,
                git_branch=git_branch,
                repository_url=repository_url
            )
            
            # Prepare default volumes
            default_volumes = {
                str(workspace_path): {
                    'bind': '/workspace',
                    'mode': 'rw'
                }
            }
            
            # Add workflow-specific volume mount
            import os
            workflow_path = os.path.join(os.path.dirname(__file__), "workflows", workflow_name)
            if os.path.exists(workflow_path):
                default_volumes[workflow_path] = {
                    'bind': '/workspace/workflow',
                    'mode': 'ro'
                }
            
            # Merge with provided volumes
            if volumes:
                default_volumes.update(volumes)
            
            # Prepare environment variables
            default_env = {
                'SESSION_ID': session_id,
                'WORKFLOW_NAME': workflow_name,
                'GIT_BRANCH': git_branch or 'main',
                'WORKSPACE_DIR': f'/workspace/{repo_name}',
                'WORKFLOW_DIR': '/workspace/workflow',
                'REPOSITORY_URL': repository_url or '',
                'REPO_SETUP_TYPE': 'local_copy' if not repository_url else 'remote_clone'
            }
            
            if environment:
                default_env.update(environment)
            
            # Create container
            container = self.docker_client.containers.create(
                image=self.docker_image,
                name=container_id,
                environment=default_env,
                volumes=default_volumes,
                network_mode='bridge',
                detach=True,
                mem_limit='2g',
                cpuset_cpus='0-1',  # Set CPU limit for resource control
                security_opt=['no-new-privileges:true'],
                working_dir=f'/workspace/{repo_name}',
                # Container will run entrypoint.sh by default
                command=None  # Will be set when starting execution
            )
            
            # Track the container
            self.active_containers[container_id] = {
                'container': container,
                'session_id': session_id,
                'workflow_name': workflow_name,
                'created_at': datetime.utcnow(),
                'status': 'created',
                'last_heartbeat': time.time(),
                'workspace_path': workspace_path,
                'repo_name': repo_name,
                'git_branch': git_branch,
                'repository_url': repository_url
            }
            
            logger.info(f"Created container {container_id} for session {session_id}")
            return container_id
            
        except Exception as e:
            # Release semaphore on error
            self.container_semaphore.release()
            logger.error(f"Failed to create container: {str(e)}")
            raise
    
    async def start_container(self, container_id: str, claude_command: List[str]) -> bool:
        """Start a container with the specified Claude command.
        
        Args:
            container_id: Container identifier
            claude_command: Claude CLI command arguments
            
        Returns:
            True if started successfully, False otherwise
        """
        if container_id not in self.active_containers:
            logger.error(f"Container {container_id} not found")
            return False
        
        try:
            container_info = self.active_containers[container_id]
            container = container_info['container']
            
            # Update container command
            # The entrypoint.sh script will handle the Claude execution
            # We pass the command as arguments to the entrypoint
            container.attrs['Config']['Cmd'] = claude_command
            
            # Start the container
            container.start()
            
            # Update tracking info
            container_info.update({
                'status': 'running',
                'started_at': datetime.utcnow(),
                'command': claude_command
            })
            
            logger.info(f"Started container {container_id} with command: {' '.join(claude_command)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start container {container_id}: {str(e)}")
            await self._cleanup_container(container_id)
            return False
    
    async def wait_for_completion(self, container_id: str) -> Dict[str, Any]:
        """Wait for container to complete and return results.
        
        Args:
            container_id: Container identifier
            
        Returns:
            Dictionary with execution results
        """
        if container_id not in self.active_containers:
            return {
                'success': False,
                'error': f'Container {container_id} not found',
                'exit_code': -1
            }
        
        try:
            container_info = self.active_containers[container_id]
            container = container_info['container']
            
            # Wait for container to finish with timeout
            start_time = time.time()
            timeout_seconds = self.container_timeout
            
            while True:
                # Refresh container status
                container.reload()
                
                if container.status in ['exited', 'dead']:
                    break
                
                # Check timeout
                if time.time() - start_time > timeout_seconds:
                    logger.warning(f"Container {container_id} timed out after {timeout_seconds}s")
                    await self._kill_container(container_id)
                    return {
                        'success': False,
                        'error': f'Container execution timed out after {timeout_seconds}s',
                        'exit_code': -1,
                        'timeout': True
                    }
                
                # Wait a bit before checking again
                await asyncio.sleep(1)
            
            # Get exit code
            exit_code = container.attrs['State']['ExitCode']
            
            # Get container logs
            logs = container.logs(stdout=True, stderr=True).decode('utf-8')
            
            # Extract result from container output
            # The entrypoint.sh script outputs JSON with the final result
            result_json = None
            try:
                # Look for JSON output in the last few lines
                log_lines = logs.strip().split('\n')
                for line in reversed(log_lines[-10:]):  # Check last 10 lines
                    try:
                        result_json = json.loads(line)
                        break
                    except (json.JSONDecodeError, ValueError):
                        continue
            except Exception as e:
                logger.warning(f"Failed to extract JSON result from container logs: {str(e)}")
            
            # Calculate execution time
            started_at = container_info.get('started_at', datetime.utcnow())
            execution_time = (datetime.utcnow() - started_at).total_seconds()
            
            # Prepare result
            result = {
                'success': exit_code == 0,
                'exit_code': exit_code,
                'execution_time': execution_time,
                'container_id': container_id,
                'logs': logs
            }
            
            # Add parsed JSON result if available
            if result_json:
                result.update({
                    'session_id': result_json.get('session_id'),
                    'result': result_json.get('result'),
                    'claude_exit_code': result_json.get('exit_code')
                })
            
            if exit_code != 0:
                result['error'] = f'Container exited with code {exit_code}'
            
            logger.info(f"Container {container_id} completed with exit code: {exit_code}")
            return result
            
        except Exception as e:
            logger.error(f"Error waiting for container {container_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'exit_code': -1
            }
        finally:
            # Clean up container
            await self._cleanup_container(container_id)
    
    async def _kill_container(self, container_id: str) -> None:
        """Kill a running container.
        
        Args:
            container_id: Container identifier
        """
        try:
            if container_id in self.active_containers:
                container = self.active_containers[container_id]['container']
                container.kill()
                logger.info(f"Killed container {container_id}")
        except Exception as e:
            logger.error(f"Error killing container {container_id}: {str(e)}")
    
    async def _cleanup_container(self, container_id: str) -> None:
        """Clean up a container and release resources.
        
        Args:
            container_id: Container identifier
        """
        try:
            if container_id in self.active_containers:
                container_info = self.active_containers[container_id]
                container = container_info['container']
                
                # Stop container if still running
                try:
                    if container.status == 'running':
                        container.stop(timeout=10)
                except Exception as e:
                    logger.warning(f"Error stopping container {container_id}: {str(e)}")
                
                # Remove container
                try:
                    container.remove()
                except Exception as e:
                    logger.warning(f"Error removing container {container_id}: {str(e)}")
                
                # Clean up workspace directory
                workspace_path = container_info.get('workspace_path')
                if workspace_path and workspace_path.exists():
                    try:
                        import shutil
                        shutil.rmtree(workspace_path)
                        logger.debug(f"Cleaned up workspace directory: {workspace_path}")
                    except Exception as e:
                        logger.warning(f"Error removing workspace directory {workspace_path}: {str(e)}")
                
                # Remove from tracking
                del self.active_containers[container_id]
                
                # Release semaphore
                self.container_semaphore.release()
                
                logger.debug(f"Cleaned up container {container_id}")
                
        except Exception as e:
            logger.error(f"Error cleaning up container {container_id}: {str(e)}")
    
    async def get_container_status(self, container_id: str) -> Dict[str, Any]:
        """Get status of a container.
        
        Args:
            container_id: Container identifier
            
        Returns:
            Dictionary with container status
        """
        if container_id not in self.active_containers:
            return {'status': 'not_found'}
        
        try:
            container_info = self.active_containers[container_id]
            container = container_info['container']
            
            # Refresh container status
            container.reload()
            
            return {
                'status': container.status,
                'created_at': container_info['created_at'].isoformat(),
                'session_id': container_info['session_id'],
                'workflow_name': container_info['workflow_name']
            }
            
        except Exception as e:
            logger.error(f"Error getting container status for {container_id}: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    async def list_active_containers(self) -> List[Dict[str, Any]]:
        """List all active containers.
        
        Returns:
            List of container information dictionaries
        """
        containers = []
        
        for container_id, info in self.active_containers.items():
            try:
                container = info['container']
                container.reload()
                
                containers.append({
                    'container_id': container_id,
                    'status': container.status,
                    'session_id': info['session_id'],
                    'workflow_name': info['workflow_name'],
                    'created_at': info['created_at'].isoformat(),
                    'started_at': info.get('started_at', {}).isoformat() if info.get('started_at') else None
                })
                
            except Exception as e:
                logger.warning(f"Error getting info for container {container_id}: {str(e)}")
        
        return containers
    
    async def cleanup_stale_containers(self) -> int:
        """Clean up stale or stuck containers.
        
        Returns:
            Number of containers cleaned up
        """
        cleaned_count = 0
        stale_containers = []
        
        # Find stale containers
        for container_id, info in self.active_containers.items():
            try:
                container = info['container']
                container.reload()
                
                # Check if container is stuck or too old
                created_time = info['created_at']
                max_age = timedelta(hours=3)  # 3 hours max age
                
                if (datetime.utcnow() - created_time) > max_age:
                    stale_containers.append(container_id)
                elif container.status in ['dead', 'exited']:
                    stale_containers.append(container_id)
                    
            except Exception as e:
                logger.warning(f"Error checking container {container_id} for staleness: {str(e)}")
                stale_containers.append(container_id)
        
        # Clean up stale containers
        for container_id in stale_containers:
            try:
                await self._cleanup_container(container_id)
                cleaned_count += 1
                logger.info(f"Cleaned up stale container: {container_id}")
            except Exception as e:
                logger.error(f"Error cleaning up stale container {container_id}: {str(e)}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} stale containers")
        
        return cleaned_count
    
    async def cleanup(self) -> None:
        """Clean up all resources and containers."""
        logger.info("Starting container manager cleanup...")
        
        # Clean up all active containers
        container_ids = list(self.active_containers.keys())
        for container_id in container_ids:
            await self._cleanup_container(container_id)
        
        # Close Docker client
        if self.docker_client:
            try:
                self.docker_client.close()
            except Exception as e:
                logger.warning(f"Error closing Docker client: {str(e)}")
        
        logger.info("Container manager cleanup completed")