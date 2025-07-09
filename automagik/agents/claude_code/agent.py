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
import time
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime

from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.models.dependencies import AutomagikAgentsDependencies
from automagik.agents.models.response import AgentResponse
from automagik.memory.message_history import MessageHistory

# Import execution components
from .executor_factory import ExecutorFactory
from .models import ClaudeCodeRunRequest, ClaudeCodeRunResponse
from .log_manager import get_log_manager
from .utils import get_current_git_branch_with_fallback

# Import tracing
from automagik.tracing import get_tracing_manager

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
            model_name="sonnet",  # Default model for Claude Code
            model_settings={}
        )
        
        # Set agent_id if available
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        
        # Claude-code specific configuration
        self.config.update({
            "agent_type": "claude-code",
            "framework": "claude-cli",
            "execution_timeout": int(self.config.get("execution_timeout", "7200")),  # 2 hours default
            "max_concurrent_sessions": int(self.config.get("max_concurrent_sessions", "10")),
            "workspace_base": self.config.get("workspace_base", "/tmp/claude-workspace"),
            "default_workflow": self.config.get("default_workflow", "surgeon"),
            "git_branch": self.config.get("git_branch")  # None by default, will use current branch
        })
        
        # Initialize local executor
        try:
            self.executor = ExecutorFactory.create_executor(
                mode="local",
                workspace_base=os.environ.get("AUTOMAGIK_CLAUDE_LOCAL_WORKSPACE", "/tmp/claude-workspace"),
                cleanup_on_complete=os.environ.get("AUTOMAGIK_CLAUDE_LOCAL_CLEANUP", "true").lower() == "true"
            )
        except ValueError as e:
            logger.error(f"Failed to create executor: {e}")
            raise
        
        # Register default tools (not applicable for local execution)
        # Tools are managed via workflow configurations
        
        logger.debug("ClaudeCodeAgent initialized successfully in local mode")
    
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
            # Skip initial logging - will log when we have Claude session ID
            
            # Validate workflow exists
            if not await self._validate_workflow(workflow_name):
                error_msg = f"Workflow '{workflow_name}' not found or invalid"
                # Skip logging validation errors - no session ID available yet
                
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
                run_id=run_id,
                workflow_name=workflow_name,
                max_turns=int(self.config.get("max_turns")) if self.config.get("max_turns") else None,
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
            
            # Skip initial logging - we'll log once we have the session ID from Claude execution
            
            # Execute Claude CLI in container
            execution_result = await self.executor.execute_claude_task(
                request=request,
                agent_context=self.context
            )
            
            # Log execution completion (first log entry creates the file with correct name)
            session_id = execution_result.get("session_id")
            if log_manager and run_id and session_id:
                try:
                    async with log_manager.get_log_writer(run_id, workflow_name, session_id) as log_writer:
                        await log_writer(
                            f"Claude CLI execution completed for workflow '{workflow_name}'",
                            "event",
                            {
                                "workflow_start": {
                                    "workflow_name": request.workflow_name,
                                    "max_turns": request.max_turns,
                                    "git_branch": request.git_branch,
                                    "timeout": request.timeout
                                },
                                "execution_result": {
                                    "success": execution_result.get("success", False),
                                    "exit_code": execution_result.get("exit_code"),
                                    "execution_time": execution_result.get("execution_time"),
                                    "session_id": execution_result.get("session_id"),
                                    "result_length": len(execution_result.get("result", "")),
                                    "git_commits": len(execution_result.get("git_commits", []))
                                }
                            }
                        )
                except Exception as log_error:
                    logger.error(f"Failed to create workflow log file: {log_error}")
            
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
                if log_manager and run_id and execution_result.get("session_id"):
                    try:
                        async with log_manager.get_log_writer(run_id, workflow_name, execution_result.get("session_id")) as log_writer:
                            await log_writer(
                                f"Returning successful response: {response_text[:100]}...",
                                "event",
                                {"response_length": len(response_text)}
                            )
                    except Exception as log_error:
                        logger.error(f"Failed to log successful response: {log_error}")
                
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
                if log_manager and run_id and execution_result.get("session_id"):
                    try:
                        async with log_manager.get_log_writer(run_id, workflow_name, execution_result.get("session_id")) as log_writer:
                            await log_writer(
                                error_msg,
                                "error",
                                {
                                    "error": execution_result.get("error"),
                                    "exit_code": execution_result.get("exit_code")
                                }
                            )
                    except Exception as log_error:
                        logger.error(f"Failed to log error response: {log_error}")
                
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
            # Note: prompt.md is optional - when missing, workflow uses default Claude behavior
            # .mcp.json is also optional - will use root project .mcp.json as fallback
            required_files = ["allowed_tools.json"]
            optional_files = ["prompt.md", ".mcp.json", "config.json"]
            
            for required_file in required_files:
                file_path = os.path.join(workflow_path, required_file)
                if not os.path.exists(file_path):
                    logger.warning(f"Required workflow file missing: {file_path}")
                    return False
            
            # Check optional files (log info but don't fail validation)
            for optional_file in optional_files:
                file_path = os.path.join(workflow_path, optional_file)
                if not os.path.exists(file_path):
                    logger.debug(f"Optional workflow file missing (will use default behavior): {file_path}")
            
            # Validate JSON files for both required and optional files that exist
            all_files = required_files + optional_files
            for file_name in all_files:
                file_path = os.path.join(workflow_path, file_name)
                if not os.path.exists(file_path):
                    continue  # Skip files that don't exist (already logged above)
                
                # Validate JSON files
                if file_name.endswith('.json'):
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
            
            logger.debug(f"Found {len(workflows)} workflows")
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
                run_id=run_id,
                workflow_name=workflow_name,
                max_turns=kwargs.get("max_turns"),
                git_branch=git_branch,
                timeout=kwargs.get("timeout", self.config.get("container_timeout")),
                repository_url=kwargs.get("repository_url"),
                persistent=kwargs.get("persistent", True),
                auto_merge=kwargs.get("auto_merge", False),
                temp_workspace=kwargs.get("temp_workspace", False)
            )
            
            # Set context for execution
            self.context.update({
                "workflow_name": workflow_name,
                "session_id": session_id,
                "run_id": run_id
            })
            if kwargs.get("repository_url"):
                self.context["repository_url"] = kwargs["repository_url"]
            if kwargs.get("user_id"):
                self.context["user_id"] = kwargs["user_id"]
            
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
                run_id=run_id,
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
        
        Args:
            input_text: User message
            workflow_name: Workflow to execute
            session_id: Database session ID
            run_id: Unique run ID
            **kwargs: Additional parameters (git_branch, max_turns, timeout, etc.)
        """
        # Track execution timing for message persistence
        start_time = time.time()
        
        # Initialize tracing
        tracing = get_tracing_manager()
        trace_id = str(uuid.uuid4())
        root_span_id = str(uuid.uuid4())
        langwatch_provider = None
        
        # Get LangWatch provider if available
        if tracing and tracing.observability:
            for provider in tracing.observability.providers.values():
                if hasattr(provider, 'log_metadata'):
                    langwatch_provider = provider
                    break
        
        # Helper function for logging to LangWatch
        def log_workflow_trace(event_type: str, span_id: str, parent_span_id: Optional[str] = None, 
                              name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
            """Log workflow trace to LangWatch if available."""
            if langwatch_provider:
                langwatch_provider.log_metadata({
                    "trace_id": trace_id,
                    "span_id": span_id,
                    "parent_span_id": parent_span_id,
                    "event_type": event_type,
                    "name": name or f"claude_code.workflow.{workflow_name}",
                    "attributes": attributes or {},
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        # Start root trace for workflow execution
        log_workflow_trace(
            event_type="trace_start",
            span_id=root_span_id,
            attributes={
                "workflow_name": workflow_name,
                "run_id": run_id,
                "session_id": session_id,
                "user_id": kwargs.get("user_id"),
                "git_branch": kwargs.get("git_branch"),
                "repository_url": kwargs.get("repository_url"),
                "persistent": kwargs.get("persistent", True),
                "temp_workspace": kwargs.get("temp_workspace", False),
                "auto_merge": kwargs.get("auto_merge", False),
                "max_turns": kwargs.get("max_turns"),
                "input_length": len(input_text)
            }
        )
        
        try:
            # Look up existing Claude session ID from database if session_id provided
            claude_session_id_for_resumption = None
            session_obj = None
            # Don't overwrite the session_id parameter
            lookup_session_id = session_id or self.context.get("session_id")
            
            if lookup_session_id:
                from automagik.db import get_session
                session_obj = get_session(uuid.UUID(lookup_session_id))
                if session_obj and session_obj.metadata:
                    # Extract actual Claude session ID from metadata for resumption
                    claude_session_id_for_resumption = session_obj.metadata.get("claude_session_id")
            
            # Create execution request with proper Claude session ID for resumption
            request = ClaudeCodeRunRequest(
                message=input_text,
                session_id=claude_session_id_for_resumption,  # Use Claude session ID, not database session ID
                run_id=run_id,
                workflow_name=workflow_name,
                max_turns=kwargs.get("max_turns"),
                git_branch=kwargs.get("git_branch"),
                timeout=kwargs.get("timeout", self.config.get("container_timeout")),
                repository_url=kwargs.get("repository_url"),
                persistent=kwargs.get("persistent", True),
                auto_merge=kwargs.get("auto_merge", False),
                temp_workspace=kwargs.get("temp_workspace", False)
            )
            
            # Update session metadata with run information
            from automagik.db import update_session
            from automagik.db.models import WorkflowRunCreate
            from automagik.db.repository.workflow_run import create_workflow_run
            
            # Capture initial git state if available
            initial_git_info = {}
            if hasattr(self, 'executor') and hasattr(self.executor, 'environment_manager'):
                try:
                    from automagik.services.git_service import extract_git_info_from_workspace
                    
                    # Try to get current git information from workspace
                    env_mgr = self.executor.environment_manager
                    main_workspace = getattr(env_mgr, 'main_workspace_path', None)
                    
                    if main_workspace and hasattr(main_workspace, 'exists') and main_workspace.exists():
                        # Use git service for comprehensive git information
                        initial_git_info = extract_git_info_from_workspace(main_workspace)
                    
                    # Fallback to environment manager attributes
                    if not initial_git_info.get("git_repo"):
                        initial_git_info["git_repo"] = getattr(env_mgr, 'repository_url', None) or kwargs.get("repository_url")
                    if not initial_git_info.get("git_branch"):
                        initial_git_info["git_branch"] = getattr(env_mgr, 'default_branch', None) or kwargs.get("git_branch")
                            
                except Exception as e:
                    logger.warning(f"Failed to extract initial git info: {e}")
                    # Fallback to basic info
                    initial_git_info = {
                        "git_repo": kwargs.get("repository_url"),
                        "git_branch": kwargs.get("git_branch")
                    }
            
            # Create workflow run record for comprehensive tracking
            workflow_run_data = WorkflowRunCreate(
                run_id=run_id,
                workflow_name=workflow_name,
                task_input=input_text,
                session_id=session_id if session_id else None,
                session_name=session_obj.name if session_obj else None,
                git_repo=initial_git_info.get("git_repo") or kwargs.get("repository_url"),
                git_branch=initial_git_info.get("git_branch") or kwargs.get("git_branch"),
                initial_commit_hash=initial_git_info.get("initial_commit_hash"),
                status="running",
                user_id=session_obj.user_id if session_obj else None,
                workspace_persistent=kwargs.get("persistent", True),
                temp_workspace=kwargs.get("temp_workspace", False),
                ai_model="sonnet"  # Default model for Claude Code
            )
            
            try:
                workflow_run_id = create_workflow_run(workflow_run_data)
                logger.info(f"Created workflow run record {workflow_run_id} for run_id {run_id}")
            except Exception as e:
                logger.warning(f"Failed to create workflow run record: {e}")
                workflow_run_id = None
            
            if session_obj:
                metadata = session_obj.metadata or {}
                # Simplified session metadata - comprehensive tracking is in workflow_runs table
                metadata.update({
                    "run_id": run_id,
                    "run_status": "running",
                    "workflow_name": workflow_name,
                    "started_at": datetime.utcnow().isoformat(),
                    "workflow_run_id": workflow_run_id  # Primary link to workflow_runs table
                })
                session_obj.metadata = metadata
                update_session(session_obj)
            
            # Create workspace for this workflow run
            workspace_path = None
            workspace_span_id = str(uuid.uuid4())
            
            # Log workspace creation span
            log_workflow_trace(
                event_type="span_start",
                span_id=workspace_span_id,
                parent_span_id=root_span_id,
                name="claude_code.workspace.creation",
                attributes={
                    "repository_url": request.repository_url,
                    "git_branch": request.git_branch,
                    "persistent": request.persistent,
                    "temp_workspace": request.temp_workspace
                }
            )
            
            workspace_start_time = time.time()
            
            if hasattr(self.executor, 'environment_manager') and self.executor.environment_manager:
                # Use prepare_workspace for external repositories, create_workspace for local worktrees
                if request.repository_url:
                    # External repository flow
                    workspace_info = await self.executor.environment_manager.prepare_workspace(
                        repository_url=request.repository_url,
                        git_branch=request.git_branch,
                        session_id=run_id,
                        workflow_name=workflow_name,
                        persistent=request.persistent
                    )
                    workspace_path = Path(workspace_info['workspace_path'])
                    logger.info(f"Prepared external repository workspace for run {run_id}: {workspace_path}")
                else:
                    # Local worktree flow
                    workspace_path = await self.executor.environment_manager.create_workspace(
                        run_id=run_id,
                        workflow_name=workflow_name,
                        persistent=request.persistent,  # Use the persistent flag from request
                        git_branch=request.git_branch
                    )
                    logger.info(f"Created workspace for run {run_id}: {workspace_path}")
            
            # Log workspace creation completion
            log_workflow_trace(
                event_type="span_end",
                span_id=workspace_span_id,
                parent_span_id=root_span_id,
                name="claude_code.workspace.creation",
                attributes={
                    "workspace_path": str(workspace_path) if workspace_path else None,
                    "duration_ms": (time.time() - workspace_start_time) * 1000
                }
            )
            
            # Update workflow run with workspace path
            if workspace_path and run_id:
                try:
                    from automagik.db.models import WorkflowRunUpdate
                    from automagik.db.repository.workflow_run import update_workflow_run_by_run_id
                    
                    update_data = WorkflowRunUpdate(
                        workspace_path=str(workspace_path)
                    )
                    update_workflow_run_by_run_id(run_id, update_data)
                    logger.info(f"Updated workflow run {run_id} with workspace path: {workspace_path}")
                except Exception as e:
                    logger.error(f"Failed to update workspace path: {e}")

            # Execute the workflow - use standard execution to avoid SDK TaskGroup issues
            # The SDK executor can extract data from the result without streaming complications
            execution_span_id = str(uuid.uuid4())
            
            # Log Claude execution span
            log_workflow_trace(
                event_type="span_start",
                span_id=execution_span_id,
                parent_span_id=root_span_id,
                name="claude_code.execution",
                attributes={
                    "workflow_name": workflow_name,
                    "session_id": session_id,
                    "run_id": run_id,
                    "workspace": str(workspace_path) if workspace_path else ".",
                    "max_turns": request.max_turns,
                    "timeout": request.timeout
                }
            )
            
            execution_start_time = time.time()
            
            result = await self.executor.execute_claude_task(
                request=request,
                agent_context={
                    "workflow_name": workflow_name,
                    "session_id": session_id,
                    "run_id": run_id,  # Ensure run_id is always present for logging
                    "db_id": self.db_id,
                    "workspace": str(workspace_path) if workspace_path else ".",  # Add workspace path
                    "user_id": kwargs.get("user_id"),  # Pass user_id for temp workspace creation
                    "trace_id": trace_id,  # Pass trace context for SDK executor
                    "parent_span_id": execution_span_id
                }
            )
            
            # Log Claude execution completion
            log_workflow_trace(
                event_type="span_end",
                span_id=execution_span_id,
                parent_span_id=root_span_id,
                name="claude_code.execution",
                attributes={
                    "success": result.get("success", False),
                    "claude_session_id": result.get("session_id"),
                    "turns_used": result.get("turn_count", 0),
                    "total_tokens": result.get("token_details", {}).get("total_tokens", 0),
                    "cost_usd": result.get("cost_usd", 0.0),
                    "duration_ms": (time.time() - execution_start_time) * 1000,
                    "tools_used": result.get("tools_used", [])
                }
            )
            
            # Update session with final status and correct Claude session ID
            if session_obj:
                metadata = session_obj.metadata or {}
                
                # Extract the ACTUAL Claude session ID from the execution result
                actual_claude_session_id = result.get("session_id") 
                if actual_claude_session_id:
                    # Only set Claude session ID if not already set (preserve first workflow's session)
                    if not metadata.get("claude_session_id"):
                        metadata["claude_session_id"] = actual_claude_session_id
                        logger.info(f"Setting initial Claude session ID: {actual_claude_session_id}")
                    else:
                        logger.info(f"Preserving existing Claude session ID: {metadata.get('claude_session_id')} (new: {actual_claude_session_id})")
                
                # Determine proper status based on result
                final_status = "completed" if result.get("success") else "failed"
                
                # Extract comprehensive SDK executor data
                token_details = result.get("token_details", {})
                
                # Create usage_tracker from SDK executor result data
                usage_tracker = {
                    "total_tokens": token_details.get("total_tokens", 0),
                    "input_tokens": token_details.get("input_tokens", 0),
                    "output_tokens": token_details.get("output_tokens", 0),
                    "cost_usd": result.get("cost_usd", 0.0)
                }
                
                # Simplified session metadata - only store session-level info
                # Detailed workflow tracking is now handled by workflow_runs table
                metadata.update({
                    "run_status": final_status,
                    "completed_at": datetime.utcnow().isoformat(),
                    "success": result.get("success", False),
                    # Keep essential session info
                    "workflow_run_id": workflow_run_id,  # Link to workflow_runs table
                    "final_result_summary": result.get("result", "")[:200] + "..." if result.get("result", "") and len(result.get("result", "")) > 200 else result.get("result", ""),
                    # Add usage_tracker data to metadata for database update
                    "total_cost_usd": usage_tracker.get("cost_usd", 0.0),
                    "total_tokens": usage_tracker.get("total_tokens", 0),
                    "input_tokens": usage_tracker.get("input_tokens", 0),
                    "output_tokens": usage_tracker.get("output_tokens", 0)
                })
                
                logger.info(f"Updated session {session_id} with final status: {final_status} (workflow_run_id: {workflow_run_id})")
                session_obj.metadata = metadata
                update_session(session_obj)
                
                # ADD: Message persistence after workflow completion
                if session_obj and hasattr(self, 'db_id'):
                    try:
                        from automagik.memory.message_history import MessageHistory
                        message_history = MessageHistory(
                            session_id=session_id, 
                            user_id=session_obj.user_id
                        )
                        
                        # Build comprehensive workflow response for message storage
                        response_content = self._build_workflow_response_content(result, start_time)
                        
                        # Store assistant workflow completion message
                        assistant_message_id = message_history.add_response(
                            content=response_content,
                            agent_id=self.db_id,
                            tool_calls=self._extract_tool_calls_from_result(result),
                            tool_outputs=self._extract_tool_outputs_from_result(result),
                            usage={
                                "total_tokens": usage_tracker.get("total_tokens", 0),
                                "input_tokens": usage_tracker.get("input_tokens", 0), 
                                "output_tokens": usage_tracker.get("output_tokens", 0),
                                "cost_usd": usage_tracker.get("cost_usd", 0.0),
                                "duration_seconds": time.time() - start_time,
                                "turns": result.get("total_turns", 0),
                                "workflow_run_id": workflow_run_id,
                                # Store workflow context in usage field
                                "workflow_context": {
                                    "workflow_name": workflow_name,
                                    "run_id": run_id,
                                    "session_name": session_obj.name if session_obj else None,
                                    "completion_status": final_status,
                                    "files_created": result.get("files_created", []),
                                    "git_commits": result.get("git_commits", []),
                                    "workspace_path": result.get("workspace_path"),
                                    "auto_commit_success": result.get("auto_commit_success", False),
                                    "session_continuation": session_obj.metadata.get("run_status") != "pending"  # Not first run
                                },
                                "execution_result": result,
                                "workflow_metadata": metadata,
                                "usage_tracking": usage_tracker
                            }
                        )
                        
                        logger.info(f"Stored workflow completion as message {assistant_message_id}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to persist workflow conversation turn: {e}")
                        # Don't fail the workflow if message storage fails
                
                # Update workflow run record with final execution data
                if workflow_run_id:
                    from automagik.db.models import WorkflowRunUpdate
                    from automagik.db.repository.workflow_run import update_workflow_run
                    
                    # Extract git information if available
                    git_info = {}
                    if hasattr(self, 'executor') and hasattr(self.executor, 'environment_manager'):
                        env_mgr = self.executor.environment_manager
                        claude_session_id = result.get("session_id")
                        workspace_path = env_mgr.active_workspaces.get(run_id) if env_mgr.active_workspaces else None
                        if workspace_path:
                            git_info["workspace_path"] = str(workspace_path)
                            # TODO: Extract git diff stats from workspace
                    
                    # Calculate execution duration (start_time is Unix timestamp)
                    execution_duration = int(time.time() - start_time)
                    
                    workflow_update = WorkflowRunUpdate(
                        status=final_status,
                        result=result.get("result", ""),
                        error_message=None if result.get("success") else result.get("error"),
                        cost_estimate=metadata.get('total_cost_usd', 0.0),
                        input_tokens=metadata.get('input_tokens', 0),
                        output_tokens=metadata.get('output_tokens', 0),
                        total_tokens=metadata.get('total_tokens', 0),
                        duration_seconds=execution_duration,
                        workspace_path=git_info.get("workspace_path"),
                        metadata={
                            "execution_results": result,
                            "tools_used": result.get('tools_used', []),
                            "total_turns": result.get('total_turns', 0),
                            "cache_created": token_details.get('cache_created', 0),
                            "cache_read": token_details.get('cache_read', 0),
                            "cache_efficiency": token_details.get('cache_efficiency', 0.0),
                            "performance_score": 85.0,  # Default score, could be calculated
                            "files_created": result.get('files_created', []),
                            "files_changed": result.get('files_changed', []),
                            "git_commits": result.get('git_commits', []),
                            "completion_type": "completed_successfully" if result.get("success") else "failed",
                            # Include comprehensive ResultMessage metadata
                            "result_metadata": result.get('result_metadata', {}),
                            "subtype": result.get('result_metadata', {}).get('subtype', ''),
                            "duration_ms": result.get('result_metadata', {}).get('duration_ms', 0),
                            "api_duration_ms": result.get('result_metadata', {}).get('duration_api_ms', 0),
                            "is_error": result.get('result_metadata', {}).get('is_error', False),
                            "claude_session_id": result.get('result_metadata', {}).get('session_id', result.get('session_id', '')),
                            "claude_result_text": result.get('result_metadata', {}).get('result', '')
                        }
                    )
                    
                    try:
                        update_workflow_run(workflow_run_id, workflow_update)
                        logger.info(f"Updated workflow run record {workflow_run_id} with final execution data")
                    except Exception as e:
                        logger.warning(f"Failed to update workflow run record: {e}")
            
            logger.info(f"Background workflow {workflow_name} completed: {result.get('success')}")
            
            # Auto-commit changes if workflow succeeded
            logger.info(f"📝 AUTO-COMMIT: Checking conditions - Success: {result.get('success')}, Has executor: {hasattr(self, 'executor')}, Has env_mgr: {hasattr(self.executor, 'environment_manager') if hasattr(self, 'executor') else False}")
            if result.get("success") and hasattr(self, 'executor') and hasattr(self.executor, 'environment_manager') and self.executor.environment_manager:
                try:
                    # Get workspace path from environment manager for this specific run
                    logger.info(f"📝 AUTO-COMMIT: Active workspaces: {list(self.executor.environment_manager.active_workspaces.keys())}")
                    claude_session_id = result.get("session_id")
                    workspace_path = self.executor.environment_manager.active_workspaces.get(run_id)
                    logger.info(f"📝 AUTO-COMMIT: Workspace path for run_id={run_id}, claude_session_id={claude_session_id}: {workspace_path}")
                    if workspace_path and workspace_path.exists():
                        logger.info(f"📝 AUTO-COMMIT: Attempting auto-commit for successful workflow {run_id}")
                        
                        # Create meaningful commit message
                        commit_message = f"{workflow_name}: {input_text[:80]}..." if input_text else f"Workflow {workflow_name} - Run {run_id[:8]}"
                        
                        # Get auto_merge flag from kwargs (defaults to False if not specified)
                        auto_merge = kwargs.get('auto_merge', False)
                        logger.info(f"📝 AUTO-COMMIT: Auto-merge flag: {auto_merge}")
                        
                        # Execute auto-commit with options
                        commit_result = await self.executor.environment_manager.auto_commit_with_options(
                            workspace=workspace_path,
                            run_id=run_id,
                            message=commit_message,
                            create_pr=False,  # Start conservative, can be enhanced later
                            merge_to_main=auto_merge,  # Use the auto_merge flag from request
                            workflow_name=workflow_name
                        )
                        
                        if commit_result.get('success'):
                            logger.info(f"📝 AUTO-COMMIT: ✅ SUCCESS for run {run_id}: {commit_result.get('commit_sha', 'N/A')}")
                            
                            # If merged to main, cleanup the worktree to save space
                            if 'merged_to_main' in commit_result.get('operations', []):
                                logger.info(f"🧹 CLEANUP: Cleaning up worktree for run {run_id} after successful merge")
                                cleanup_success = await self.executor.environment_manager.cleanup_workspace(
                                    workspace_path, force=False
                                )
                                if cleanup_success:
                                    logger.info(f"🧹 CLEANUP: ✅ SUCCESS for run {run_id}")
                                else:
                                    logger.warning(f"🧹 CLEANUP: ❌ FAILED for run {run_id}")
                            
                            # Update session metadata with commit info
                            if session_obj:
                                metadata = session_obj.metadata or {}
                                metadata.update({
                                    "auto_commit_sha": commit_result.get('commit_sha'),
                                    "auto_commit_operations": commit_result.get('operations', []),
                                    "auto_commit_success": True
                                })
                                session_obj.metadata = metadata
                                
                                # Update workflow run with git information
                                if workflow_run_id:
                                    from automagik.db.models import WorkflowRunUpdate
                                    from automagik.db.repository.workflow_run import update_workflow_run
                                    from automagik.services.git_service import extract_commit_diff_stats
                                    
                                    # Extract git diff statistics from commit result or workspace
                                    git_stats = commit_result.get('diff_stats', {})
                                    
                                    # If no diff stats in commit result, try to extract from workspace
                                    if not git_stats and workspace_path:
                                        try:
                                            # Get the workflow run to find initial commit
                                            from automagik.db.repository.workflow_run import get_workflow_run
                                            existing_run = get_workflow_run(workflow_run_id)
                                            if existing_run and existing_run.initial_commit_hash:
                                                diff_data = extract_commit_diff_stats(
                                                    workspace_path, 
                                                    existing_run.initial_commit_hash,
                                                    commit_result.get('commit_sha')
                                                )
                                                git_stats = diff_data
                                        except Exception as e:
                                            logger.warning(f"Failed to extract diff stats: {e}")
                                    
                                    git_update = WorkflowRunUpdate(
                                        final_commit_hash=commit_result.get('commit_sha'),
                                        git_diff_added_lines=git_stats.get('git_diff_added_lines', git_stats.get('added_lines', 0)),
                                        git_diff_removed_lines=git_stats.get('git_diff_removed_lines', git_stats.get('removed_lines', 0)),
                                        git_diff_files_changed=git_stats.get('git_diff_files_changed', git_stats.get('files_changed', 0)),
                                        git_diff_stats=git_stats.get('git_diff_stats', git_stats),
                                        workspace_cleaned_up=True if 'merged_to_main' in commit_result.get('operations', []) else False,
                                        metadata={
                                            **(metadata.get('metadata', {}) if 'metadata' in metadata else {}),
                                            "git_operations": commit_result.get('operations', []),
                                            "auto_commit_result": commit_result
                                        }
                                    )
                                    
                                    try:
                                        update_workflow_run(workflow_run_id, git_update)
                                        logger.info(f"Updated workflow run {workflow_run_id} with git information: {commit_result.get('commit_sha')}")
                                    except Exception as e:
                                        logger.warning(f"Failed to update workflow run with git information: {e}")
                                update_session(session_obj)
                        else:
                            logger.warning(f"📝 AUTO-COMMIT: ❌ FAILED for run {run_id}: {commit_result.get('error', 'Unknown error')}")
                    else:
                        logger.warning(f"📝 AUTO-COMMIT: ⚠️  No workspace path found for run {run_id}")
                            
                except Exception as commit_error:
                    logger.error(f"📝 AUTO-COMMIT: 💥 EXCEPTION for run {run_id}: {commit_error}")
                    # Don't fail the workflow for commit errors
            else:
                logger.info("📝 AUTO-COMMIT: ⏭️  SKIPPED - Conditions not met")
            
        except Exception as e:
            logger.error(f"Error in background workflow execution: {str(e)}")
            
            # Log trace completion with error
            log_workflow_trace(
                event_type="trace_end",
                span_id=root_span_id,
                attributes={
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_ms": (time.time() - start_time) * 1000
                }
            )
            raise
        finally:
            # Log successful trace completion
            if 'e' not in locals():
                log_workflow_trace(
                    event_type="trace_end",
                    span_id=root_span_id,
                    attributes={
                        "success": result.get("success", False) if 'result' in locals() else False,
                        "duration_ms": (time.time() - start_time) * 1000,
                        "final_status": "completed" if ('result' in locals() and result.get("success", False)) else "failed",
                        "total_tokens": result.get("token_details", {}).get("total_tokens", 0) if 'result' in locals() else 0,
                        "cost_usd": result.get("cost_usd", 0.0) if 'result' in locals() else 0.0,
                        "auto_commit": kwargs.get('auto_merge', False),
                        "workspace_path": str(workspace_path) if 'workspace_path' in locals() and workspace_path else None
                    }
                )
            
            # Update workflow_runs table with failure status if there was an error
            if 'e' in locals():
                try:
                    from automagik.db.models import WorkflowRunUpdate
                    from automagik.db.repository.workflow_run import update_workflow_run_by_run_id
                    
                    update_data = WorkflowRunUpdate(
                        status="failed",
                        error_message=str(e),
                        completed_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    update_workflow_run_by_run_id(run_id, update_data)
                    logger.info(f"Updated workflow run {run_id} status to failed: {str(e)}")
                except Exception as workflow_update_error:
                    logger.error(f"Failed to update workflow run status: {workflow_update_error}")
                
                # Update session with error status
                if 'session_id' in locals() and session_id:
                    try:
                        from automagik.db import get_session, update_session
                        # Check if session_id is already a UUID or needs conversion
                        if isinstance(session_id, str):
                            try:
                                session_uuid = uuid.UUID(session_id)
                            except ValueError:
                                logger.error(f"Invalid session_id format: {session_id}")
                                session_uuid = None
                        else:
                            session_uuid = session_id
                            
                        if session_uuid:
                            session_obj = get_session(session_uuid)
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
    
    def _build_workflow_response_content(self, result: Dict, start_time: float) -> str:
        """Build comprehensive workflow response content for message history."""
        
        duration = time.time() - start_time
        content_parts = []
        
        # Workflow completion status
        if result.get("success"):
            content_parts.append("✅ **Workflow completed successfully**")
        else:
            content_parts.append("❌ **Workflow failed**")
            if error := result.get("error"):
                content_parts.append(f"**Error:** {error}")
        
        # File operations summary
        if files_created := result.get("files_created", []):
            content_parts.append(f"📁 **Files created:** {len(files_created)} files")
            for file_path in files_created[:5]:  # Show first 5
                content_parts.append(f"  - {file_path}")
            if len(files_created) > 5:
                content_parts.append(f"  - ... and {len(files_created) - 5} more")
        
        # Git operations summary  
        if git_commits := result.get("git_commits", []):
            content_parts.append(f"🔄 **Git commits:** {len(git_commits)} commits")
            for commit in git_commits[:3]:  # Show first 3
                content_parts.append(f"  - {commit.get('message', 'No message')[:60]}...")
        
        # Tool usage summary
        if tools_used := result.get("tools_used", []):
            content_parts.append(f"🛠️ **Tools used:** {', '.join(set(tools_used))}")
        
        # Execution metrics
        content_parts.append("⚡ **Execution metrics:**")
        content_parts.append(f"  - Duration: {duration:.1f}s")
        content_parts.append(f"  - Turns: {result.get('total_turns', 0)}")
        if tokens := result.get("total_tokens", 0):
            content_parts.append(f"  - Tokens: {tokens:,}")
        if cost := result.get("cost_usd", 0):
            content_parts.append(f"  - Cost: ${cost:.4f}")
        
        # Final output (truncated for message storage)
        if final_output := result.get("result"):
            content_parts.append("📝 **Final output:**")
            content_parts.append(f"```\n{final_output[:1000]}{'...' if len(final_output) > 1000 else ''}\n```")
        
        return "\n\n".join(content_parts)

    def _extract_tool_calls_from_result(self, result: Dict) -> List[Dict]:
        """Extract tool calls from workflow result for message storage."""
        tool_calls = []
        
        if raw_tool_calls := result.get("tool_calls", []):
            for tool_call in raw_tool_calls:
                tool_calls.append({
                    "name": tool_call.get("name", "unknown"),
                    "arguments": tool_call.get("arguments", {}),
                    "id": tool_call.get("id", str(uuid.uuid4()))
                })
        
        return tool_calls

    def _extract_tool_outputs_from_result(self, result: Dict) -> List[Dict]:
        """Extract tool outputs from workflow result for message storage."""
        tool_outputs = []
        
        if raw_tool_outputs := result.get("tool_outputs", []):
            for tool_output in raw_tool_outputs:
                tool_outputs.append({
                    "call_id": tool_output.get("call_id", "unknown"),
                    "output": str(tool_output.get("output", ""))[:2000],  # Truncate large outputs
                    "success": tool_output.get("success", True)
                })
        
        return tool_outputs
    
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