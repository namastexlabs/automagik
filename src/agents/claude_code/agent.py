"""ClaudeCodeAgent implementation.

This module provides a ClaudeCodeAgent class that runs Claude CLI locally
while maintaining full integration with the Automagik Agents framework.
"""
import logging
import traceback
import uuid
import asyncio
import json
import os
import aiofiles
from typing import Dict, Optional, Any
from datetime import datetime

from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.models.response import AgentResponse
from src.memory.message_history import MessageHistory

# Import execution components
from .executor_factory import ExecutorFactory
from .models import ClaudeCodeRunRequest, ClaudeCodeRunResponse
from .log_manager import get_log_manager
from .utils import get_current_git_branch_with_fallback

logger = logging.getLogger(__name__)




class ClaudeCodeAgent(AutomagikAgent):
    """ClaudeCodeAgent implementation using local execution.
    
    This agent runs Claude CLI locally to enable
    long-running, autonomous AI workflows with state persistence and git integration.
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize the ClaudeCodeAgent.
        
        Args:
            config: Dictionary with configuration options
        """
        # First initialize the base agent
        super().__init__(config)
        
        # Set description for this agent type
        self.description = "Local Claude CLI agent for autonomous code tasks"
        
        # Workflow validation cache for performance
        self._workflow_cache = {}
        
        # Load and register the code-defined prompt from workflows
        # This will be loaded from the workflow configuration
        self._prompt_registered = False
        self._code_prompt_text = None  # Will be loaded from workflow
        
        # Configure dependencies for claude-code agent
        self.dependencies = AutomagikAgentsDependencies(
            model_name="claude-3-5-sonnet-20241022",  # Default model for Claude Code
            model_settings={}
        )
        
        # Set agent_id if available
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        
        # Claude-code specific configuration
        self.config.update({
            "agent_type": "claude-code",
            "framework": "claude-cli",
            "execution_timeout": int(config.get("execution_timeout", "7200")),  # 2 hours default
            "max_concurrent_sessions": int(config.get("max_concurrent_sessions", "10")),
            "workspace_base": config.get("workspace_base", "/tmp/claude-workspace"),
            "default_workflow": config.get("default_workflow", "bug-fixer"),
            "git_branch": config.get("git_branch")  # None by default, will use current branch
        })
        
        # Determine execution mode
        self.execution_mode = os.environ.get("CLAUDE_CODE_MODE", "local").lower()
        logger.info(f"ClaudeCodeAgent initializing in {self.execution_mode} mode")
        
        # Initialize local executor
        try:
            self.executor = ExecutorFactory.create_executor(
                mode="local",
                workspace_base=os.environ.get("CLAUDE_LOCAL_WORKSPACE", "/tmp/claude-workspace"),
                cleanup_on_complete=os.environ.get("CLAUDE_LOCAL_CLEANUP", "true").lower() == "true"
            )
        except ValueError as e:
            logger.error(f"Failed to create executor: {e}")
            raise
        
        # Register default tools (not applicable for local execution)
        # Tools are managed via workflow configurations
        
        logger.info(f"ClaudeCodeAgent initialized successfully in local mode")
    
    async def run(self, input_text: str, *, multimodal_content=None, 
                 system_message=None, message_history_obj: Optional[MessageHistory] = None,
                 channel_payload: Optional[Dict] = None,
                 message_limit: Optional[int] = None) -> AgentResponse:
        """Run the agent with the given input.
        
        Args:
            input_text: Text input for the agent (the task to execute)
            multimodal_content: Optional multimodal content (not used in claude-code)
            system_message: Optional system message (ignored - uses workflow prompts)
            message_history_obj: Optional MessageHistory instance for DB storage
            channel_payload: Optional channel payload dictionary
            message_limit: Optional message limit (not used in claude-code)
            
        Returns:
            AgentResponse object with result and metadata
        """
        # Check if claude CLI is available
        from pathlib import Path
        claude_credentials = Path.home() / ".claude" / ".credentials.json"
        if not claude_credentials.exists():
            return AgentResponse(
                text="Claude CLI not configured. Please install Claude CLI and authenticate.",
                success=False,
                error_message=f"No credentials found at {claude_credentials}"
            )
        
        try:
            # Get workflow from context or use default
            workflow_name = self.context.get("workflow_name", self.config.get("default_workflow"))
            run_id = self.context.get("run_id")  # Get run_id from context for logging
            
            # Setup log manager if we have a run_id
            log_manager = get_log_manager() if run_id else None
            if log_manager and run_id:
                async with log_manager.get_log_writer(run_id) as log_writer:
                    await log_writer(
                        f"ClaudeCodeAgent.run() called for workflow '{workflow_name}'",
                        "event",
                        {
                            "workflow_name": workflow_name,
                            "run_id": run_id,
                            "input_length": len(input_text),
                            "has_multimodal": multimodal_content is not None
                        }
                    )
            
            # Validate workflow exists
            if not await self._validate_workflow(workflow_name):
                error_msg = f"Workflow '{workflow_name}' not found or invalid"
                if log_manager and run_id:
                    async with log_manager.get_log_writer(run_id) as log_writer:
                        await log_writer(error_msg, "error", {"workflow_name": workflow_name})
                
                return AgentResponse(
                    text=error_msg,
                    success=False,
                    error_message=f"Invalid workflow: {workflow_name}"
                )
            
            # Get git branch - use current branch if not specified
            git_branch = self.config.get("git_branch")
            if git_branch is None:
                git_branch = await get_current_git_branch_with_fallback()
            
            # Create execution request
            request = ClaudeCodeRunRequest(
                message=input_text,
                session_id=self.context.get("session_id"),
                workflow_name=workflow_name,
                max_turns=int(self.config["max_turns"]) if "max_turns" in self.config else None,
                git_branch=git_branch,
                timeout=self.config.get("container_timeout"),
                repository_url=self.context.get("repository_url")  # Pass repository URL from context
            )
            
            # Store session metadata in database
            session_metadata = {
                "agent_type": "claude-code",
                "workflow_name": workflow_name,
                "git_branch": request.git_branch,
                "container_timeout": request.timeout,
                "started_at": datetime.utcnow().isoformat(),
                "run_id": run_id
            }
            
            # Update context with metadata
            self.context.update(session_metadata)
            
            # For async execution, we would normally return a run_id immediately
            # and let the client poll for status. For now, we'll run synchronously
            # to maintain compatibility with the existing agent interface.
            
            logger.info(f"Starting Claude CLI execution for workflow '{workflow_name}'")
            
            if log_manager and run_id:
                async with log_manager.get_log_writer(run_id) as log_writer:
                    await log_writer(
                        f"Starting Claude CLI execution with {request.max_turns} max turns",
                        "event",
                        {
                            "request": {
                                "workflow_name": request.workflow_name,
                                "max_turns": request.max_turns,
                                "git_branch": request.git_branch,
                                "timeout": request.timeout
                            }
                        }
                    )
            
            # Execute Claude CLI in container
            execution_result = await self.executor.execute_claude_task(
                request=request,
                agent_context=self.context
            )
            
            # Log execution completion
            if log_manager and run_id:
                async with log_manager.get_log_writer(run_id) as log_writer:
                    await log_writer(
                        "Claude CLI execution completed",
                        "event",
                        {
                            "success": execution_result.get("success", False),
                            "exit_code": execution_result.get("exit_code"),
                            "execution_time": execution_result.get("execution_time"),
                            "session_id": execution_result.get("session_id"),
                            "result_length": len(execution_result.get("result", "")),
                            "git_commits": len(execution_result.get("git_commits", []))
                        }
                    )
            
            # Store execution results in message history if provided
            if message_history_obj:
                # Store user message
                user_message = {
                    "role": "user",
                    "content": input_text,
                    "agent_id": self.db_id,
                    "channel_payload": channel_payload
                }
                message_history_obj.add_message(user_message)
                
                # Store agent response with execution metadata
                # Extract the actual Claude result text
                claude_result_text = execution_result.get("result", "Task completed")
                
                agent_message = {
                    "role": "assistant",
                    "content": claude_result_text,
                    "agent_id": self.db_id,
                    "raw_payload": {
                        "execution": execution_result,
                        "workflow": workflow_name,
                        "request": request.dict(),
                        "run_id": run_id,
                        "log_file": f"./logs/run_{run_id}.log" if run_id else None
                    },
                    "context": {
                        "container_id": execution_result.get("container_id"),
                        "execution_time": execution_result.get("execution_time"),
                        "exit_code": execution_result.get("exit_code"),
                        "git_commits": execution_result.get("git_commits", []),
                        "claude_session_id": execution_result.get("session_id"),
                        "streaming_messages": len(execution_result.get("streaming_messages", []))
                    }
                }
                message_history_obj.add_message(agent_message)
            
            # Create response based on execution result
            if execution_result.get("success", False):
                response_text = execution_result.get("result", "Task completed successfully")
                
                # Log successful response
                if log_manager and run_id:
                    async with log_manager.get_log_writer(run_id) as log_writer:
                        await log_writer(
                            f"Returning successful response: {response_text[:100]}...",
                            "event",
                            {"response_length": len(response_text)}
                        )
                
                return AgentResponse(
                    text=response_text,
                    success=True,
                    raw_message=execution_result,
                    tool_calls=[],  # Claude CLI handles its own tools
                    tool_outputs=[]
                )
            else:
                error_msg = f"Task failed: {execution_result.get('error', 'Unknown error')}"
                
                # Log error response
                if log_manager and run_id:
                    async with log_manager.get_log_writer(run_id) as log_writer:
                        await log_writer(
                            error_msg,
                            "error",
                            {
                                "error": execution_result.get("error"),
                                "exit_code": execution_result.get("exit_code")
                            }
                        )
                
                return AgentResponse(
                    text=error_msg,
                    success=False,
                    error_message=execution_result.get("error"),
                    raw_message=execution_result
                )
                
        except Exception as e:
            logger.error(f"Error running ClaudeCodeAgent: {str(e)}")
            logger.error(traceback.format_exc())
            return AgentResponse(
                text=f"Error executing Claude task: {str(e)}",
                success=False,
                error_message=str(e)
            )
    
    async def _validate_workflow(self, workflow_name: str) -> bool:
        """Validate that a workflow configuration exists.
        
        Args:
            workflow_name: Name of the workflow to validate
            
        Returns:
            True if workflow is valid, False otherwise
        """
        # Check cache first for performance
        if workflow_name in self._workflow_cache:
            return self._workflow_cache[workflow_name]
        
        try:
            # Check if workflow directory exists
            import os
            workflow_path = os.path.join(
                os.path.dirname(__file__), 
                "workflows", 
                workflow_name
            )
            
            if not os.path.exists(workflow_path):
                logger.warning(f"Workflow directory not found: {workflow_path}")
                return False
            
            # Check for required workflow files and validate JSON files
            required_files = ["prompt.md", ".mcp.json", "allowed_tools.json"]
            for required_file in required_files:
                file_path = os.path.join(workflow_path, required_file)
                if not os.path.exists(file_path):
                    logger.warning(f"Required workflow file missing: {file_path}")
                    return False
                
                # Validate JSON files
                if required_file.endswith('.json'):
                    try:
                        async with aiofiles.open(file_path, 'r') as f:
                            content = await f.read()
                            json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON in {file_path}: {str(e)}")
                        return False
                    except Exception as e:
                        logger.warning(f"Error reading {file_path}: {str(e)}")
                        return False
            
            logger.debug(f"Workflow '{workflow_name}' validated successfully")
            self._workflow_cache[workflow_name] = True
            return True
            
        except Exception as e:
            logger.error(f"Error validating workflow '{workflow_name}': {str(e)}")
            self._workflow_cache[workflow_name] = False
            return False
    
    async def get_available_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available workflows with their configurations.
        
        Returns:
            Dictionary of workflow names to their metadata
        """
        workflows = {}
        
        try:
            import os
            workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
            
            if not os.path.exists(workflows_dir):
                return workflows
            
            for item in os.listdir(workflows_dir):
                workflow_path = os.path.join(workflows_dir, item)
                if os.path.isdir(workflow_path):
                    # Try to load workflow metadata
                    try:
                        prompt_file = os.path.join(workflow_path, "prompt.md")
                        description = "No description available"
                        
                        if os.path.exists(prompt_file):
                            async with aiofiles.open(prompt_file, 'r') as f:
                                content = await f.read()
                                lines = content.splitlines()
                                # Extract first line as description
                                if lines:
                                    description = lines[0].strip("# \n")
                        
                        workflows[item] = {
                            "name": item,
                            "description": description,
                            "path": workflow_path,
                            "valid": await self._validate_workflow(item)
                        }
                        
                    except Exception as e:
                        logger.warning(f"Error loading workflow metadata for '{item}': {str(e)}")
                        workflows[item] = {
                            "name": item,
                            "description": "Error loading metadata",
                            "path": workflow_path,
                            "valid": False
                        }
            
            logger.info(f"Found {len(workflows)} workflows")
            return workflows
            
        except Exception as e:
            logger.error(f"Error getting available workflows: {str(e)}")
            return workflows
    
    async def execute_until_first_response(self, input_text: str, workflow_name: str, 
                                         session_id: str, **kwargs) -> Dict[str, Any]:
        """Execute Claude Code workflow and wait for first response from Claude.
        
        This method replaces background execution - it waits for the session to be
        confirmed and potentially the first substantial response from Claude.
        
        Args:
            input_text: Text input for the agent
            workflow_name: Name of the workflow to execute
            session_id: Session ID for this execution
            **kwargs: Additional execution parameters
            
        Returns:
            Dictionary with first response data including session_id and initial message
        """
        try:
            # Generate unique run ID - use standard UUID format for MCP server compatibility
            run_id = str(uuid.uuid4())
            
            # Get git branch - use current branch if not specified
            git_branch = kwargs.get("git_branch") or self.config.get("git_branch")
            if git_branch is None:
                git_branch = await get_current_git_branch_with_fallback()
            
            # Create execution request
            request = ClaudeCodeRunRequest(
                message=input_text,
                session_id=session_id,
                workflow_name=workflow_name,
                max_turns=kwargs.get("max_turns"),
                git_branch=git_branch,
                timeout=kwargs.get("timeout", self.config.get("container_timeout")),
                repository_url=kwargs.get("repository_url")
            )
            
            # Set context for execution
            self.context.update({
                "workflow_name": workflow_name,
                "session_id": session_id,
                "run_id": run_id
            })
            if kwargs.get("repository_url"):
                self.context["repository_url"] = kwargs["repository_url"]
            
            # Setup log manager
            log_manager = get_log_manager()
            
            # Log start of execution
            if log_manager:
                async with log_manager.get_log_writer(run_id) as log_writer:
                    await log_writer(
                        f"Starting execution until first response for workflow '{workflow_name}'",
                        "event",
                        {
                            "workflow_name": workflow_name,
                            "run_id": run_id,
                            "session_id": session_id,
                            "input_length": len(input_text)
                        }
                    )
            
            # Validate workflow exists
            if not await self._validate_workflow(workflow_name):
                error_msg = f"Workflow '{workflow_name}' not found or invalid"
                if log_manager:
                    async with log_manager.get_log_writer(run_id) as log_writer:
                        await log_writer(error_msg, "error", {"workflow_name": workflow_name})
                
                return {
                    "success": False,
                    "error": error_msg,
                    "status": "failed",
                    "run_id": run_id,
                    "session_id": session_id
                }
            
            # Execute Claude CLI until first response (not full completion)
            # This creates a background task but returns early
            first_response_data = await self.executor.execute_until_first_response(
                request=request,
                agent_context=self.context
            )
            
            # Extract session information and first response
            claude_session_id = first_response_data.get("session_id")
            first_response = first_response_data.get("first_response")
            
            # Default response if nothing found
            if not first_response:
                first_response = "Claude Code execution started. Processing your request..."
            
            # Log first response capture
            if log_manager:
                async with log_manager.get_log_writer(run_id) as log_writer:
                    await log_writer(
                        f"Captured first response: {first_response[:100]}...",
                        "event",
                        {
                            "response_length": len(first_response),
                            "claude_session_id": claude_session_id,
                            "streaming_started": first_response_data.get("streaming_started", False)
                        }
                    )
            
            return {
                "success": True,
                "message": first_response,
                "status": "running",
                "run_id": run_id,
                "session_id": session_id,
                "claude_session_id": claude_session_id,
                "workflow_name": workflow_name,
                "started_at": datetime.utcnow().isoformat(),
                "git_branch": git_branch
            }
            
        except Exception as e:
            logger.error(f"Error executing until first response: {str(e)}")
            logger.error(traceback.format_exc())
            
            return {
                "success": False,
                "error": str(e),
                "status": "failed",
                "run_id": run_id if 'run_id' in locals() else None,
                "session_id": session_id
            }
    
    async def create_async_run(self, input_text: str, workflow_name: str, 
                              **kwargs) -> ClaudeCodeRunResponse:
        """Create an async run and return immediately with run_id.
        
        This method implements the async API pattern described in the architecture.
        
        Args:
            input_text: Text input for the agent
            workflow_name: Name of the workflow to execute
            **kwargs: Additional execution parameters
            
        Returns:
            ClaudeCodeRunResponse with run_id and initial status
        """
        try:
            # Generate unique run ID - use standard UUID format for MCP server compatibility
            run_id = str(uuid.uuid4())
            
            # Create execution request
            request = ClaudeCodeRunRequest(
                message=input_text,
                session_id=kwargs.get("session_id"),
                workflow_name=workflow_name,
                max_turns=kwargs.get("max_turns"),
                git_branch=kwargs.get("git_branch", self.config.get("git_branch")),
                timeout=kwargs.get("timeout", self.config.get("container_timeout"))
            )
            
            # Store run metadata in database for status tracking
            # This would normally go in a runs table, but for now we'll use the context
            self.context[f"run_{run_id}"] = {
                "status": "pending",
                "request": request.dict(),
                "started_at": datetime.utcnow().isoformat(),
                "workflow_name": workflow_name
            }
            
            # Start background execution
            asyncio.create_task(
                self._execute_async_run(run_id, request)
            )
            
            # Return immediate response
            return ClaudeCodeRunResponse(
                run_id=run_id,
                status="pending",
                message="Container deployment initiated",
                session_id=request.session_id or str(uuid.uuid4()),
                started_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error creating async run: {str(e)}")
            raise
    
    async def _execute_async_run(self, run_id: str, request: ClaudeCodeRunRequest) -> None:
        """Execute a Claude task in the background.
        
        Args:
            run_id: Unique run identifier
            request: Execution request
        """
        try:
            # Update status to running
            self.context[f"run_{run_id}"]["status"] = "running"
            self.context[f"run_{run_id}"]["updated_at"] = datetime.utcnow().isoformat()
            
            # Execute the task
            result = await self.executor.execute_claude_task(
                request=request,
                agent_context=self.context
            )
            
            # Update status with results
            self.context[f"run_{run_id}"].update({
                "status": "completed" if result.get("success") else "failed",
                "result": result,
                "completed_at": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Async run {run_id} completed with status: {result.get('success', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Error in async run {run_id}: {str(e)}")
            self.context[f"run_{run_id}"].update({
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.utcnow().isoformat()
            })
    
    async def execute_workflow_background(self, input_text: str, workflow_name: str, 
                                         session_id: str, run_id: str, **kwargs) -> None:
        """Execute a workflow in the background without waiting for response.
        
        This method starts the workflow execution and returns immediately.
        The workflow continues running in the background and saves all output
        to log files that can be parsed later.
        
        Args:
            input_text: User message
            workflow_name: Workflow to execute
            session_id: Database session ID
            run_id: Unique run ID
            **kwargs: Additional parameters (git_branch, max_turns, timeout, etc.)
        """
        try:
            # Look up existing Claude session ID from database if session_id provided
            claude_session_id_for_resumption = None
            session_obj = None
            
            if session_id:
                from src.db import get_session
                session_obj = get_session(uuid.UUID(session_id))
                if session_obj and session_obj.metadata:
                    # Extract actual Claude session ID from metadata for resumption
                    claude_session_id_for_resumption = session_obj.metadata.get("claude_session_id")
            
            # Create execution request with proper Claude session ID for resumption
            request = ClaudeCodeRunRequest(
                message=input_text,
                session_id=claude_session_id_for_resumption,  # Use Claude session ID, not database session ID
                workflow_name=workflow_name,
                max_turns=kwargs.get("max_turns"),
                git_branch=kwargs.get("git_branch"),
                timeout=kwargs.get("timeout", self.config.get("container_timeout")),
                repository_url=kwargs.get("repository_url"),
                persistent=kwargs.get("persistent", True)
            )
            
            # Update session metadata with run information
            from src.db import update_session
            
            if session_obj:
                metadata = session_obj.metadata or {}
                metadata.update({
                    "run_id": run_id,
                    "run_status": "running",
                    "workflow_name": workflow_name,
                    "started_at": datetime.utcnow().isoformat(),
                })
                session_obj.metadata = metadata
                update_session(session_obj)
            
            # Execute the workflow - use standard execution to avoid SDK TaskGroup issues
            # The SDK executor can extract data from the result without streaming complications
            result = await self.executor.execute_claude_task(
                request=request,
                agent_context={
                    "workflow_name": workflow_name,
                    "session_id": session_id,
                    "run_id": run_id,  # Ensure run_id is always present for logging
                    "db_id": self.db_id
                }
            )
            
            # Update session with final status and correct Claude session ID
            if session_obj:
                metadata = session_obj.metadata or {}
                
                # Extract the ACTUAL Claude session ID from the execution result
                actual_claude_session_id = result.get("session_id") 
                if actual_claude_session_id:
                    # Store the real Claude session ID for future resumption
                    metadata["claude_session_id"] = actual_claude_session_id
                
                # Determine proper status based on result
                final_status = "completed" if result.get("success") else "failed"
                
                # Extract comprehensive SDK executor data
                token_details = result.get("token_details", {})
                
                metadata.update({
                    "run_status": final_status,
                    "completed_at": datetime.utcnow().isoformat(),
                    "exit_code": result.get("exit_code", -1),
                    "success": result.get("success", False),
                    "final_result": result.get("result", ""),
                    # Cost and turn data
                    "total_cost_usd": result.get("total_cost_usd", result.get("cost_usd", 0.0)),
                    "total_turns": result.get("total_turns", 0),
                    # Comprehensive token data from SDK
                    "total_tokens": token_details.get("total_tokens", result.get("total_tokens", 0)),
                    "input_tokens": token_details.get("input_tokens", result.get("input_tokens", 0)),
                    "output_tokens": token_details.get("output_tokens", result.get("output_tokens", 0)),
                    "cache_created": token_details.get("cache_created", 0),
                    "cache_read": token_details.get("cache_read", 0),
                    # Tools data
                    "tools_used": result.get("tools_used", result.get("tool_names_used", [])),
                    "tool_names_used": result.get("tool_names_used", result.get("tools_used", [])),
                    # Store complete execution results for completion tracker
                    "execution_results": result
                })
                
                logger.info(f"Updated session {session_id} with final status: {final_status}, cost: ${metadata.get('total_cost_usd', 0):.4f}, tokens: {metadata.get('total_tokens', 0)}, tools: {len(metadata.get('tools_used', []))}")
                session_obj.metadata = metadata
                update_session(session_obj)
            
            logger.info(f"Background workflow {workflow_name} completed: {result.get('success')}")
            
            # 🩺 SURGEON FIX: Auto-commit changes if workflow succeeded
            if result.get("success") and hasattr(self.executor, 'environment_manager') and self.executor.environment_manager:
                try:
                    # Get workspace path from environment manager
                    workspace_path = self.executor.environment_manager.workspace
                    if workspace_path and workspace_path.exists():
                        logger.info(f"Attempting auto-commit for successful workflow {run_id}")
                        
                        # Create meaningful commit message
                        commit_message = f"{workflow_name}: {input_text[:80]}..." if input_text else f"Workflow {workflow_name} - Run {run_id[:8]}"
                        
                        # Execute auto-commit with options
                        commit_result = await self.executor.environment_manager.auto_commit_with_options(
                            workspace=workspace_path,
                            run_id=run_id,
                            message=commit_message,
                            create_pr=False,  # Start conservative, can be enhanced later
                            merge_to_main=False,  # Start conservative 
                            workflow_name=workflow_name
                        )
                        
                        if commit_result.get('success'):
                            logger.info(f"Auto-commit successful for run {run_id}: {commit_result.get('commit_sha', 'N/A')}")
                            # Update session metadata with commit info
                            if session_obj:
                                metadata = session_obj.metadata or {}
                                metadata.update({
                                    "auto_commit_sha": commit_result.get('commit_sha'),
                                    "auto_commit_operations": commit_result.get('operations', []),
                                    "auto_commit_success": True
                                })
                                session_obj.metadata = metadata
                                update_session(session_obj)
                        else:
                            logger.warning(f"Auto-commit failed for run {run_id}: {commit_result.get('error', 'Unknown error')}")
                            
                except Exception as commit_error:
                    logger.error(f"Auto-commit exception for run {run_id}: {commit_error}")
                    # Don't fail the workflow for commit errors
            
        except Exception as e:
            logger.error(f"Error in background workflow execution: {str(e)}")
            
            # Update session with error status
            try:
                session_obj = get_session(uuid.UUID(session_id))
                if session_obj:
                    metadata = session_obj.metadata or {}
                    metadata.update({
                        "run_status": "failed",
                        "error": str(e),
                        "completed_at": datetime.utcnow().isoformat(),
                    })
                    session_obj.metadata = metadata
                    update_session(session_obj)
            except Exception as update_error:
                logger.error(f"Failed to update session status: {update_error}")
    
    async def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """Get the status of an async run.
        
        Args:
            run_id: Unique run identifier
            
        Returns:
            Dictionary with run status and results
        """
        run_key = f"run_{run_id}"
        if run_key not in self.context:
            return {
                "run_id": run_id,
                "status": "not_found",
                "error": f"Run {run_id} not found"
            }
        
        return {
            "run_id": run_id,
            **self.context[run_key]
        }
    
    async def cleanup(self) -> None:
        """Clean up resources used by the agent."""
        try:
            # Clean up executor resources
            if hasattr(self, 'executor') and self.executor:
                await self.executor.cleanup()
            
            # Call parent cleanup
            await super().cleanup()
            
        except Exception as e:
            logger.error(f"Error during ClaudeCodeAgent cleanup: {str(e)}")
        
        logger.info("ClaudeCodeAgent cleanup completed")