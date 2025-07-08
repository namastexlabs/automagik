"""Execution strategies for Claude SDK Executor.

This module contains different execution strategies and cancellation logic.
"""

import asyncio
import logging
import os
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from uuid import uuid4

from claude_code_sdk import query, ClaudeCodeOptions
from ...utils.nodejs_detection import ensure_node_in_path

from .models import ClaudeCodeRunRequest
from .sdk_process_manager import ProcessManager
from .sdk_metrics_handler import MetricsHandler
from .log_manager import get_log_manager

# Import tracing
from automagik.tracing import get_tracing_manager

logger = logging.getLogger(__name__)


# Strategy classes for SDK executor
class StandardExecutionStrategy:
    """Standard execution strategy using ExecutionStrategies."""
    
    def __init__(self, environment_manager=None):
        self.environment_manager = environment_manager
        self.execution_strategies = ExecutionStrategies(environment_manager)
    
    async def execute(self, request, agent_context):
        """Execute using standard strategy."""
        return await self.execution_strategies.execute_simple(request, agent_context)


class FirstResponseStrategy:
    """First response strategy using ExecutionStrategies."""
    
    def __init__(self, environment_manager=None):
        self.environment_manager = environment_manager
        self.execution_strategies = ExecutionStrategies(environment_manager)
    
    async def execute(self, request, agent_context):
        """Execute and return first response."""
        return await self.execution_strategies.execute_first_response(request, agent_context)


class ExecutionStrategies:
    """Different execution strategies for Claude SDK."""
    
    def __init__(self, environment_manager=None):
        self.environment_manager = environment_manager
        self.process_manager = ProcessManager()
    
    def build_options(self, workspace: Path, **kwargs) -> ClaudeCodeOptions:
        """Build options with file-based configuration loading."""
        options = ClaudeCodeOptions()
        
        # Set working directory (SDK uses cwd, not workspace)
        options.cwd = str(workspace)
        
        # Load system prompt from prompt.md
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
        
        # Load allowed tools if file exists
        if 'allowed_tools' not in kwargs:
            allowed_tools_file = workspace / "allowed_tools.json"
            if allowed_tools_file.exists():
                try:
                    import json
                    with open(allowed_tools_file) as f:
                        tools_list = json.load(f)
                        if isinstance(tools_list, list):
                            options.allowed_tools = tools_list
                            logger.info(f"Loaded {len(tools_list)} allowed tools from file")
                except Exception as e:
                    logger.error(f"Failed to load allowed_tools.json: {e}")
        
        # Load disallowed tools if file exists
        if 'disallowed_tools' not in kwargs:
            disallowed_tools_file = workspace / "disallowed_tools.json"
            if disallowed_tools_file.exists():
                try:
                    import json
                    with open(disallowed_tools_file) as f:
                        tools_list = json.load(f)
                        if isinstance(tools_list, list):
                            options.disallowed_tools = tools_list
                            logger.info(f"Loaded {len(tools_list)} disallowed tools from file")
                except Exception as e:
                    logger.error(f"Failed to load disallowed_tools.json: {e}")
        
        # Load MCP configuration
        mcp_config_file = workspace / ".mcp.json"
        if mcp_config_file.exists():
            try:
                import json
                with open(mcp_config_file) as f:
                    mcp_data = json.load(f)
                    
                if 'mcpServers' in mcp_data and isinstance(mcp_data['mcpServers'], dict):
                    options.mcp_servers = mcp_data['mcpServers']
                    logger.info(f"Loaded {len(mcp_data['mcpServers'])} MCP servers from config")
                else:
                    logger.warning(".mcp.json must contain 'mcpServers' object")
                    
            except Exception as e:
                logger.error(f"Failed to load .mcp.json: {e}")
        
        # Apply explicit kwargs (highest priority)
        for key, value in kwargs.items():
            if hasattr(options, key) and value is not None:
                setattr(options, key, value)
        
        # Handle session resumption
        if 'session_id' in kwargs and kwargs['session_id']:
            options.resume = kwargs['session_id']
            logger.info(f"Setting session resumption with Claude session ID: {kwargs['session_id']}")
        
        # Set permission mode to bypass tool permission prompts
        options.permission_mode = "bypassPermissions"
        logger.info("Set permission_mode to bypassPermissions for automated workflow execution")
        
        return options
    
    async def _check_and_process_pending_messages(
        self, 
        workspace_path: Path, 
        run_id: str
    ) -> List[str]:
        """
        Check for pending injected messages and process them.
        
        Args:
            workspace_path: Path to the workflow workspace
            run_id: The workflow run ID
            
        Returns:
            List of messages to inject into the conversation
        """
        try:
            message_queue_file = workspace_path / ".pending_messages.json"
            
            if not message_queue_file.exists():
                return []
            
            # Read and parse pending messages
            import json
            try:
                with open(message_queue_file, 'r') as f:
                    pending_messages = json.load(f)
                
                if not isinstance(pending_messages, list):
                    return []
                    
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to read pending messages file: {e}")
                return []
            
            # Filter unprocessed messages
            unprocessed_messages = [
                msg for msg in pending_messages 
                if not msg.get("processed", False)
            ]
            
            if not unprocessed_messages:
                return []
            
            # Extract messages to inject
            messages_to_inject = []
            for msg in unprocessed_messages:
                messages_to_inject.append(msg["message"])
                # Mark as processed
                msg["processed"] = True
                msg["processed_at"] = datetime.utcnow().isoformat()
            
            # Write back the updated queue with processed flags
            try:
                with open(message_queue_file, 'w') as f:
                    json.dump(pending_messages, f, indent=2)
                
                logger.info(f"Processed {len(messages_to_inject)} injected messages for run {run_id}")
                
            except IOError as e:
                logger.error(f"Failed to update message queue file: {e}")
                # Still return the messages even if we can't update the file
            
            return messages_to_inject
            
        except Exception as e:
            logger.error(f"Error checking pending messages for run {run_id}: {e}")
            return []
    
    async def execute_simple(
        self, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute claude task with simplified logic and process tracking."""
        start_time = time.time()
        session_id = request.session_id or str(uuid4())
        run_id = request.run_id or str(uuid4())
        
        logger.info(f"SDK Executor: Starting simple execution for run_id: {run_id}, session: {session_id}")
        
        # Extract tracing context from agent_context
        trace_id = agent_context.get("trace_id")
        parent_span_id = agent_context.get("parent_span_id")
        tracing = get_tracing_manager() if trace_id else None
        
        # Initialize metrics handler
        metrics_handler = MetricsHandler()
        
        # Register workflow process
        if hasattr(request, 'run_id') and request.run_id:
            await self.process_manager.register_workflow_process(request.run_id, request, agent_context)
        
        # Ensure Node.js is available
        ensure_node_in_path()
        
        # Start heartbeat updates
        heartbeat_task = None
        if hasattr(request, 'run_id') and request.run_id:
            heartbeat_task = self.process_manager.create_heartbeat_task(request.run_id)
        
        # Handle temporary workspace creation if requested
        if hasattr(request, 'temp_workspace') and request.temp_workspace:
            # Create temporary workspace instead of using git worktree
            user_id = agent_context.get('user_id', 'anonymous')
            
            # Fallback: If user_id is 'anonymous', try to get it from the database using run_id
            if user_id == 'anonymous' and run_id:
                try:
                    from ...db.repository.workflow_run import get_workflow_run_by_run_id
                    workflow_run = get_workflow_run_by_run_id(run_id)
                    if workflow_run and workflow_run.user_id:
                        user_id = workflow_run.user_id
                        logger.info(f"Retrieved user_id {user_id} from database for run {run_id}")
                except Exception as e:
                    logger.warning(f"Failed to retrieve user_id from database: {e}")
            
            workspace_path = await self.environment_manager.create_temp_workspace(user_id, run_id)
            logger.info(f"Using temporary workspace: {workspace_path} (user_id: {user_id})")
        else:
            # Extract workspace from agent context (normal flow)
            workspace_path = Path(agent_context.get('workspace', '.'))
        
        # Build options for SDK
        options = self.build_options(
            workspace_path,
            model=request.model,
            max_turns=request.max_turns,
            max_thinking_tokens=request.max_thinking_tokens,
            session_id=request.session_id
        )
        
        # Execute the task using SDK query function
        messages = []
        collected_messages = []
        actual_claude_session_id = None
        
        # Initialize LogManager for workflow log file creation
        log_manager = get_log_manager()
        log_writer = None
        log_writer_context = None
        
        try:
            # Add real-time progress tracking
            turn_count = 0
            token_count = 0
            
            # Execute SDK query directly (SDK handles max_turns properly)
            try:
                async for message in query(prompt=request.message, options=options):
                    # Check for kill signal before processing each message
                    if hasattr(request, 'run_id') and request.run_id:
                        try:
                            process_info = self.process_manager.get_process_info(request.run_id)
                            if process_info and process_info.status == "killed":
                                logger.info(f"🛑 Workflow {request.run_id} killed during execution, stopping...")
                                break
                        except Exception as kill_check_error:
                            logger.error(f"Kill signal check failed: {kill_check_error}")
                    
                    # Check for pending injected messages
                    if hasattr(request, 'run_id') and request.run_id and workspace_path:
                        try:
                            injected_messages = await self._check_and_process_pending_messages(
                                workspace_path, request.run_id
                            )
                            
                            if injected_messages:
                                logger.info(f"📨 Found {len(injected_messages)} injected messages for run {request.run_id}")
                                
                                # Process each injected message by adding them to the conversation
                                # Note: This is a simplified approach - in a more sophisticated implementation,
                                # you might want to modify the Claude SDK query to accept new messages
                                for injected_msg in injected_messages:
                                    # Add the injected message to the collected messages
                                    # This simulates the user sending additional input
                                    messages.append(f"[INJECTED MESSAGE] {injected_msg}")
                                    
                                    # Log the injection for debugging
                                    if log_writer:
                                        try:
                                            await log_writer(
                                                f"💉 Injected message: {injected_msg[:100]}...",
                                                "message_injection"
                                            )
                                        except Exception as log_error:
                                            logger.error(f"Failed to log injected message: {log_error}")
                                
                        except Exception as message_check_error:
                            logger.error(f"Failed to check pending messages: {message_check_error}")
                    
                    messages.append(str(message))
                    collected_messages.append(message)
                    
                    # Log message to individual workflow log file
                    if log_writer:
                        try:
                            await log_writer(str(message), "claude_message")
                        except Exception as log_error:
                            logger.error(f"Failed to write to workflow log: {log_error}")
                    
                    # Track turns and tokens for real-time progress
                    if hasattr(message, 'type') and message.type == 'assistant':
                        turn_count += 1
                        
                        # Log message turn span if tracing is enabled
                        if tracing and trace_id:
                            # Get LangWatch provider if available
                            langwatch_provider = None
                            if tracing.observability:
                                for provider in tracing.observability.providers.values():
                                    if hasattr(provider, 'log_metadata'):
                                        langwatch_provider = provider
                                        break
                            
                            if langwatch_provider:
                                turn_span_id = str(uuid4())
                                langwatch_provider.log_metadata({
                                    "trace_id": trace_id,
                                    "span_id": turn_span_id,
                                    "parent_span_id": parent_span_id,
                                    "event_type": "span_start",
                                    "name": f"claude_code.message.turn_{turn_count}",
                                    "attributes": {
                                        "turn_number": turn_count,
                                        "workflow_name": request.workflow_name,
                                        "message_type": "assistant"
                                    },
                                    "timestamp": datetime.utcnow().isoformat()
                                })
                                
                                # Log turn completion with token usage
                                langwatch_provider.log_metadata({
                                    "trace_id": trace_id,
                                    "span_id": turn_span_id,
                                    "parent_span_id": parent_span_id,
                                    "event_type": "span_end",
                                    "name": f"claude_code.message.turn_{turn_count}",
                                    "attributes": {
                                        "tokens_used": token_count - last_token_count if 'last_token_count' in locals() else token_count
                                    },
                                    "timestamp": datetime.utcnow().isoformat()
                                })
                                last_token_count = token_count
                        
                    if hasattr(message, 'usage') and message.usage:
                        if hasattr(message.usage, 'total_tokens'):
                            token_count = message.usage.total_tokens
                    
                    # Real-time progress update every turn
                    if hasattr(request, 'run_id') and request.run_id and turn_count > 0:
                        try:
                            from ...db.models import WorkflowRunUpdate
                            from ...db.repository.workflow_run import update_workflow_run_by_run_id
                            
                            # Build metadata with current progress
                            progress_metadata = {
                                "current_turns": turn_count,
                                "max_turns": request.max_turns,
                                "total_tokens": token_count,
                                "last_activity": datetime.utcnow().isoformat(),
                                "run_status": "running"
                            }
                            
                            # Update database with real-time progress
                            progress_update = WorkflowRunUpdate(
                                total_tokens=token_count,
                                metadata=progress_metadata
                            )
                            update_workflow_run_by_run_id(request.run_id, progress_update)
                            
                        except Exception as progress_error:
                            logger.error(f"Real-time progress update failed: {progress_error}")
                    
                    # Capture session ID from first SystemMessage
                    if (hasattr(message, 'subtype') and message.subtype == 'init' and 
                        hasattr(message, 'data') and 'session_id' in message.data):
                        actual_claude_session_id = message.data['session_id']
                        logger.info(f"SDK Executor: Captured REAL Claude session ID: {actual_claude_session_id}")
                        
                        # Create individual workflow log file NOW with correct naming
                        if log_manager and hasattr(request, 'run_id') and request.run_id and hasattr(request, 'workflow_name') and request.workflow_name:
                            try:
                                # Get the async context manager and enter it properly
                                log_writer_context = log_manager.get_log_writer(request.run_id, request.workflow_name, actual_claude_session_id)
                                log_writer = await log_writer_context.__aenter__()
                                await log_writer(f"Workflow {request.workflow_name} started with Claude session: {actual_claude_session_id}", "execution_init")
                                logger.info(f"Created individual log file: {request.workflow_name}_{actual_claude_session_id}.log")
                            except Exception as log_error:
                                logger.error(f"Failed to create workflow log file: {log_error}")
                        
                        # Update database AND session metadata with real Claude session_id immediately
                        if hasattr(request, 'run_id') and request.run_id:
                            try:
                                from ...db.models import WorkflowRunUpdate
                                from ...db.repository.workflow_run import update_workflow_run_by_run_id
                                
                                # Update workflow_runs table
                                session_update = WorkflowRunUpdate(session_id=actual_claude_session_id)
                                update_success = update_workflow_run_by_run_id(request.run_id, session_update)
                                if update_success:
                                    logger.info(f"Database updated with real Claude session_id: {actual_claude_session_id}")
                                
                                # Also update session metadata for continuation
                                try:
                                    from ...db import get_session, update_session
                                    from ...db.repository.workflow_run import get_workflow_run_by_run_id
                                    from uuid import UUID
                                    
                                    # Find session by workflow run
                                    workflow_run = get_workflow_run_by_run_id(request.run_id)
                                    if workflow_run and workflow_run.session_id:
                                        # Handle both string and UUID types
                                        session_id = workflow_run.session_id
                                        if isinstance(session_id, str):
                                            session_id = UUID(session_id)
                                        session_obj = get_session(session_id)
                                        if session_obj and session_obj.metadata:
                                            session_obj.metadata["claude_session_id"] = actual_claude_session_id
                                            update_session(session_obj)
                                            logger.info(f"Session metadata updated with Claude session_id: {actual_claude_session_id}")
                                except Exception as session_error:
                                    logger.error(f"Session metadata update failed: {session_error}")
                                    
                            except Exception as db_error:
                                logger.error(f"Database session_id update failed: {db_error}")
            
            except Exception as stream_error:
                # Handle EndOfStream and other streaming errors gracefully
                if "EndOfStream" in str(stream_error) or "anyio.EndOfStream" in str(type(stream_error)):
                    logger.info("SDK Executor: Stream ended successfully (EndOfStream is normal after completion)")
                else:
                    logger.error(f"SDK Executor: Stream error: {stream_error}")
                    raise stream_error
                    
        except Exception as e:
            logger.error(f"SDK Executor: SDK execution failed: {e}")
            logger.error(f"Full exception details: {traceback.format_exc()}")
            if hasattr(request, 'run_id') and request.run_id:
                await self.process_manager.terminate_process(request.run_id, status="failed")
            
            # Clean up workspace on failure based on persistence settings and workspace type
            if hasattr(request, 'run_id') and request.run_id:
                # Check if this is a temp workspace
                is_temp_workspace = hasattr(request, 'temp_workspace') and request.temp_workspace
                
                if is_temp_workspace:
                    # Always cleanup temp workspaces even on failure
                    try:
                        cleanup_success = await self.environment_manager.cleanup_temp_workspace(workspace_path)
                        if cleanup_success:
                            logger.info(f"Successfully cleaned up temporary workspace after failure for {request.run_id}")
                        else:
                            logger.warning(f"Failed to clean up temporary workspace after failure for {request.run_id}")
                    except Exception as cleanup_error:
                        logger.error(f"Error during temp workspace failure cleanup: {cleanup_error}")
                else:
                    # Normal workspace cleanup logic
                    should_cleanup = False
                    
                    if hasattr(request, 'persistent'):
                        # Explicit persistent parameter takes precedence
                        should_cleanup = not request.persistent
                    else:
                        # Fallback to environment variable
                        should_cleanup = os.environ.get("AUTOMAGIK_CLAUDE_LOCAL_CLEANUP", "true").lower() == "true"
                    
                    if should_cleanup:
                        try:
                            from .utils.worktree_cleanup import cleanup_workflow_worktree
                            cleanup_success = await cleanup_workflow_worktree(request.run_id)
                            if cleanup_success:
                                logger.info(f"Successfully cleaned up worktree after failure for workflow {request.run_id}")
                        except Exception as cleanup_error:
                            logger.error(f"Error during failure cleanup: {cleanup_error}")
                    else:
                        logger.info(f"Keeping persistent workspace after failure for workflow {request.run_id}")
            
            return self._build_error_result(e, session_id, workspace_path, start_time)
        finally:
            if heartbeat_task:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            # Clean up log writer context
            if log_writer_context:
                try:
                    await log_writer_context.__aexit__(None, None, None)
                    logger.info("Closed workflow log file")
                except Exception as log_cleanup_error:
                    logger.error(f"Failed to close workflow log file: {log_cleanup_error}")
        
        # Process metrics
        metrics_handler.update_metrics_from_messages(collected_messages, messages)
        
        execution_time = time.time() - start_time
        result_text = '\n'.join(messages) if messages else "Subprocess execution completed"
        
        logger.info(f"SDK Executor: Completed successfully - Turns: {metrics_handler.total_turns}, Tools: {len(metrics_handler.tools_used)}")
        
        # Update workflow_runs table with success BEFORE marking process completed
        if hasattr(request, 'run_id') and request.run_id:
            try:
                from ...db.models import WorkflowRunUpdate
                from ...db.repository.workflow_run import update_workflow_run_by_run_id
                
                # Extract final metrics from collected_messages
                final_result = None
                total_cost = 0.0
                total_tokens = 0
                
                # Look for completion result in messages (success OR max_turns)
                for msg in collected_messages:
                    try:
                        # Check if msg is a dictionary (Claude SDK JSON format)
                        if isinstance(msg, dict) and msg.get('subtype') in ['success', 'error_max_turns']:
                            logger.info(f"Processing completion message: {msg.get('subtype')}")
                            
                            # For max_turns, create a meaningful result message
                            if msg.get('subtype') == 'error_max_turns':
                                final_result = f"Workflow completed {msg.get('num_turns', 0)} turns (max_turns limit reached)"
                            else:
                                final_result = msg.get('result')
                            
                            total_cost = msg.get('total_cost_usd', 0.0)
                            if 'usage' in msg and isinstance(msg['usage'], dict):
                                usage = msg['usage']
                                total_tokens = (usage.get('input_tokens', 0) + 
                                              usage.get('cache_creation_input_tokens', 0) + 
                                              usage.get('cache_read_input_tokens', 0) + 
                                              usage.get('output_tokens', 0))
                                logger.info(f"Extracted metrics: cost={total_cost}, tokens={total_tokens}")
                            break  # Found the completion result, stop looking
                    except Exception as msg_error:
                        logger.error(f"Error processing completion message: {msg_error}")
                        continue
                    
                    # Check for completion result in object attributes
                    if hasattr(msg, 'subtype') and msg.subtype in ['success', 'error_max_turns']:
                        # For max_turns, create a meaningful result message
                        if msg.subtype == 'error_max_turns':
                            final_result = f"Workflow completed {getattr(msg, 'num_turns', 0)} turns (max_turns limit reached)"
                        else:
                            final_result = getattr(msg, 'result', None)
                        
                        total_cost = getattr(msg, 'total_cost_usd', 0.0)
                        if hasattr(msg, 'usage'):
                            usage = msg.usage
                            total_tokens = (usage.get('input_tokens', 0) + 
                                          usage.get('cache_creation_input_tokens', 0) + 
                                          usage.get('cache_read_input_tokens', 0) + 
                                          usage.get('output_tokens', 0))
                        break  # Found the completion result, stop looking
                    
                    # Check for completion result in msg.data structure
                    elif hasattr(msg, 'data') and isinstance(msg.data, dict):
                        if msg.data.get('subtype') in ['success', 'error_max_turns']:
                            # For max_turns, create a meaningful result message
                            if msg.data.get('subtype') == 'error_max_turns':
                                final_result = f"Workflow completed {msg.data.get('num_turns', 0)} turns (max_turns limit reached)"
                            else:
                                final_result = msg.data.get('result')
                            
                            total_cost = msg.data.get('total_cost_usd', 0.0)
                            if 'usage' in msg.data:
                                usage = msg.data['usage']
                                total_tokens = (usage.get('input_tokens', 0) + 
                                              usage.get('cache_creation_input_tokens', 0) + 
                                              usage.get('cache_read_input_tokens', 0) + 
                                              usage.get('output_tokens', 0))
                            break  # Found the completion result, stop looking
                
                if not final_result:
                    final_result = result_text
                
                update_data = WorkflowRunUpdate(
                    status="completed",
                    completed_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    result=final_result,
                    total_tokens=total_tokens,
                    cost_estimate=total_cost,
                    duration_seconds=int(execution_time)
                )
                
                update_success = update_workflow_run_by_run_id(request.run_id, update_data)
                if update_success:
                    logger.info(f"Successfully updated workflow_runs table for {request.run_id}")
                else:
                    logger.warning(f"Failed to update workflow_runs table for {request.run_id}")
                    
            except Exception as db_update_error:
                logger.error(f"Error updating workflow_runs table: {db_update_error}")
        
        # Mark process as completed
        if hasattr(request, 'run_id') and request.run_id:
            await self.process_manager.terminate_process(request.run_id, status="completed")
        
        # Persist metrics to database
        if hasattr(request, 'run_id') and request.run_id:
            await metrics_handler.persist_to_database(request.run_id, True, result_text, execution_time)
        
        # Clean up workspace based on persistence settings and workspace type
        # Logic: 
        # - temp_workspace=true: always cleanup (ignore persistent)
        # - persistent=true: keep workspace
        # - persistent=false: cleanup workspace
        # - Environment variable CLAUDE_LOCAL_CLEANUP is fallback when persistent not set
        if hasattr(request, 'run_id') and request.run_id:
            # Check if this is a temp workspace
            is_temp_workspace = hasattr(request, 'temp_workspace') and request.temp_workspace
            
            if is_temp_workspace:
                # Always cleanup temp workspaces
                try:
                    cleanup_success = await self.environment_manager.cleanup_temp_workspace(workspace_path)
                    if cleanup_success:
                        logger.info(f"Successfully cleaned up temporary workspace for {request.run_id}")
                    else:
                        logger.warning(f"Failed to clean up temporary workspace for {request.run_id}")
                except Exception as cleanup_error:
                    logger.error(f"Error during temp workspace cleanup: {cleanup_error}")
            else:
                # Normal workspace cleanup logic
                should_cleanup = False
                
                if hasattr(request, 'persistent'):
                    # Explicit persistent parameter takes precedence
                    should_cleanup = not request.persistent
                else:
                    # Fallback to environment variable
                    should_cleanup = os.environ.get("AUTOMAGIK_CLAUDE_LOCAL_CLEANUP", "true").lower() == "true"
                
                if should_cleanup:
                    try:
                        from .utils.worktree_cleanup import cleanup_workflow_worktree
                        cleanup_success = await cleanup_workflow_worktree(request.run_id)
                        if cleanup_success:
                            logger.info(f"Successfully cleaned up worktree for non-persistent workflow {request.run_id}")
                        else:
                            logger.warning(f"Failed to clean up worktree for workflow {request.run_id}")
                    except Exception as cleanup_error:
                        logger.error(f"Error during worktree cleanup: {cleanup_error}")
                else:
                    logger.info(f"Keeping persistent workspace for workflow {request.run_id}")

        return {
            'success': True,
            'session_id': actual_claude_session_id or session_id,
            'result': result_text,
            'exit_code': 0,
            'execution_time': execution_time,
            'logs': f"SDK execution completed in {execution_time:.2f}s",
            'workspace_path': str(workspace_path),
            **metrics_handler.get_summary(),
            'result_metadata': metrics_handler.final_metrics or {}
        }
    
    async def execute_first_response(
        self, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Claude Code and return after first response."""
        session_id = request.session_id or str(uuid4())
        
        try:
            # Get workspace
            workspace_path = self._get_workspace_path(request, session_id)
            
            # Build options
            options = self.build_options(
                workspace_path,
                model=request.model,
                max_turns=request.max_turns,
                environment=request.environment
            )
            
            # Start streaming execution
            first_response = None
            async for message in query(prompt=request.message, options=options):
                if message and str(message).strip():
                    first_response = str(message)
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
    
    def _get_workspace_path(self, request: ClaudeCodeRunRequest, session_id: str) -> Path:
        """Get workspace path from environment manager or current directory."""
        if self.environment_manager:
            workspace_info = asyncio.create_task(
                self.environment_manager.prepare_workspace(
                    repository_url=request.repository_url,
                    git_branch=request.git_branch,
                    session_id=session_id,
                    workflow_name=request.workflow_name,
                    persistent=request.persistent
                )
            )
            return Path(workspace_info['workspace_path'])
        else:
            return Path.cwd()
    
    def _build_error_result(
        self, 
        error: Exception, 
        session_id: str, 
        workspace_path: Path, 
        start_time: float
    ) -> Dict[str, Any]:
        """Build standardized error result."""
        return {
            'success': False,
            'session_id': session_id,
            'result': f"SDK execution failed: {str(error)}",
            'exit_code': 1,
            'execution_time': time.time() - start_time,
            'logs': f"Error: {str(error)}",
            'workspace_path': str(workspace_path),
            'cost_usd': 0.0,
            'total_turns': 0,
            'tools_used': []
        }


class CancellationManager:
    """Handles execution cancellation and cleanup."""
    
    def __init__(self):
        self.process_manager = ProcessManager()
    
    async def cancel_execution(self, execution_id: str, active_sessions: Dict[str, Any]) -> bool:
        """Cancel a running execution."""
        logger.info(f"Attempting to cancel execution: {execution_id}")
        success = False
        
        # Get process information and terminate if needed
        process_info = self.process_manager.get_process_info(execution_id)
        
        if process_info and process_info.pid:
            success = await self._terminate_system_process(process_info.pid, execution_id)
        
        # Check active sessions for cancellation
        if execution_id in active_sessions:
            success = await self._cancel_session_task(execution_id, active_sessions) or success
        
        # Update database status
        try:
            await self.process_manager.terminate_process(execution_id, status="killed")
            logger.info(f"Updated database status for {execution_id} to killed")
        except Exception as e:
            logger.error(f"Failed to update database status for {execution_id}: {e}")
        
        if success:
            logger.info(f"Successfully cancelled execution: {execution_id}")
        else:
            logger.warning(f"Could not fully cancel execution: {execution_id}")
            
        return success
    
    async def _terminate_system_process(self, target_pid: int, execution_id: str) -> bool:
        """Terminate system process safely."""
        try:
            import psutil
            
            # Safety check: Never kill the main server process
            current_pid = os.getpid()
            if target_pid == current_pid:
                logger.error(f"SAFETY: Refusing to kill main server process (PID: {current_pid})")
                return False
            
            # Check if process still exists and terminate
            try:
                process = psutil.Process(target_pid)
                if process.is_running():
                    logger.info(f"Terminating process {target_pid} for execution {execution_id}")
                    
                    # Try graceful termination first
                    process.terminate()
                    
                    try:
                        process.wait(timeout=3)
                        logger.info(f"Process {target_pid} terminated gracefully")
                    except psutil.TimeoutExpired:
                        process.kill()
                        logger.warning(f"Process {target_pid} was force killed")
                    
                    return True
                else:
                    logger.info(f"Process {target_pid} already terminated")
                    return True
                    
            except psutil.NoSuchProcess:
                logger.info(f"Process {target_pid} not found (already terminated)")
                return True
        
        except ImportError:
            logger.error("psutil not available for process termination")
            return False
        except Exception as e:
            logger.error(f"Failed to terminate process: {e}")
            return False
    
    async def _cancel_session_task(self, execution_id: str, active_sessions: Dict[str, Any]) -> bool:
        """Cancel asyncio task associated with session."""
        try:
            session_info = active_sessions[execution_id]
            
            # If there's a task associated, try to cancel it
            if "task" in session_info and session_info["task"] is not None:
                task = session_info["task"]
                if not task.done():
                    task.cancel()
                    logger.info(f"Cancelled asyncio task for session {execution_id}")
                    return True
            
            # Remove session tracking
            del active_sessions[execution_id]
            logger.info(f"Removed session tracking for {execution_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel session {execution_id}: {e}")
            return False