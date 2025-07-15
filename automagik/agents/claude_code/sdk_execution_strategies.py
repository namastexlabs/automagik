"""Execution strategies for Claude SDK Executor.

This module contains different execution strategies and cancellation logic.
"""

import asyncio
import logging
import os
import sys
import time
import traceback
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from uuid import uuid4

from claude_code_sdk import query

from .models import ClaudeCodeRunRequest
from .sdk_process_manager import ProcessManager
from .sdk_metrics_handler import MetricsHandler
from .log_manager import get_log_manager

# Import new refactored modules
from .sdk_options_builder import SDKOptionsBuilder
from .sdk_message_processor import SDKMessageProcessor
from .sdk_progress_tracker import SDKProgressTracker
from .sdk_cli_manager import SDKCLIManager

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
        self.options_builder = SDKOptionsBuilder()
        self.cli_manager = SDKCLIManager()
    
    def build_options(self, workspace: Path, **kwargs):
        """Build options with file-based configuration loading."""
        return self.options_builder.build_options(workspace, **kwargs)
    
    
    async def execute_simple(
        self, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute claude task with simplified logic and process tracking."""
        # Check if stream-json input format is requested
        if hasattr(request, 'input_format') and request.input_format == "stream-json":
            return await self._execute_with_stream_input(request, agent_context)
        
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
        
        # Ensure Claude CLI is available
        claude_cli = self.cli_manager.ensure_claude_cli_available()
        
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
            workspace_path = Path(agent_context.get('workspace', f'/tmp/claude-code-temp/{request.run_id}'))
            
            # Ensure the workspace directory exists
            if not workspace_path.exists():
                workspace_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created workspace directory: {workspace_path}")
        
        # Update database with workspace_path immediately after determining it
        if hasattr(request, 'run_id') and request.run_id:
            try:
                from ...db.models import WorkflowRunUpdate
                from ...db.repository.workflow_run import update_workflow_run_by_run_id
                
                workspace_update = WorkflowRunUpdate(workspace_path=str(workspace_path))
                update_success = update_workflow_run_by_run_id(request.run_id, workspace_update)
                if update_success:
                    logger.info(f"Updated database with workspace_path: {workspace_path}")
                else:
                    logger.warning(f"Failed to update workspace_path in database for {request.run_id}")
                    
            except Exception as workspace_update_error:
                logger.error(f"Error updating workspace_path in database: {workspace_update_error}")
        
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
        
        # Initialize progress tracker
        progress_tracker = SDKProgressTracker(
            run_id=run_id,
            workflow_name=request.workflow_name if hasattr(request, 'workflow_name') else None,
            max_turns=request.max_turns
        )
        
        # Set tracing context if available
        if trace_id:
            progress_tracker.set_tracing_context(trace_id, parent_span_id, tracing)
        
        # Initialize message processor
        message_processor = SDKMessageProcessor(
            workflow_name=request.workflow_name if hasattr(request, 'workflow_name') else None
        )
        
        try:
            # Execute SDK query directly (SDK handles max_turns properly)
            try:
                
                logger.info(f"🚀 Starting query with prompt: {request.message[:100]}...")
                logger.info(f"📁 Working directory: {options.cwd}")
                logger.info(f"📝 System prompt length: {len(options.system_prompt) if options.system_prompt else 0} chars")
                
                # Debug environment
                logger.info(f"🔍 CLAUDECODE env: {os.environ.get('CLAUDECODE', 'not set')}")
                logger.info(f"🔍 CLAUDE_CODE_ENTRYPOINT env: {os.environ.get('CLAUDE_CODE_ENTRYPOINT', 'not set')}")
                logger.info(f"🔍 PATH contains claude: {'claude' in os.environ.get('PATH', '')}")
                
                # Additional debugging for PM2
                logger.info(f"🔍 Current PID: {os.getpid()}")
                logger.info(f"🔍 Python executable: {sys.executable}")
                logger.info(f"🔍 Working directory (cwd): {os.getcwd()}")
                logger.info(f"🔍 PM2_HOME: {os.environ.get('PM2_HOME', 'not set')}")
                import shutil
                logger.info(f"🔍 Which claude: {shutil.which('claude')}")
                
                message_count = 0
                logger.info("📡 About to start SDK query async generator...")
                
                async for message in query(prompt=request.message, options=options):
                    message_count += 1
                    logger.info(f"📨 Received message {message_count}: {type(message).__name__}")
                    
                    # TEMPORARILY DISABLED: Blocking database operations causing workflow hang
                    # TODO: Move these checks outside the message processing loop
                    
                    # Check for kill signal before processing each message
                    if hasattr(request, 'run_id') and request.run_id:
                        try:
                            # TEMPORARILY DISABLED: This blocks the async generator
                            # process_info = self.process_manager.get_process_info(request.run_id)
                            # if process_info and process_info.status == "killed":
                            #     logger.info(f"🛑 Workflow {request.run_id} killed during execution, stopping...")
                            #     break
                            pass
                        except Exception as kill_check_error:
                            logger.error(f"Kill signal check failed: {kill_check_error}")
                    
                    
                    # Process message using the message processor
                    processing_result = message_processor.process_message(message, messages, collected_messages)
                    
                    # Track progress
                    progress_tracker.track_turn(processing_result["message_type"])
                    
                    # Extract session ID if present
                    if "session_id" in processing_result.get("metadata", {}):
                        actual_claude_session_id = processing_result["metadata"]["session_id"]
                        progress_tracker.set_session_id(actual_claude_session_id)
                    
                    # Update token count if usage data available
                    if "usage" in processing_result.get("metadata", {}):
                        progress_tracker.update_tokens(processing_result["metadata"]["usage"])
                    
                    # Log message to individual workflow log file
                    if log_writer:
                        try:
                            await log_writer(str(message), "claude_message")
                        except Exception as log_error:
                            logger.error(f"Failed to write to workflow log: {log_error}")
                    
                    # Update database progress if needed
                    if hasattr(request, 'run_id') and request.run_id and progress_tracker.should_update_progress(processing_result["message_type"]):
                        await progress_tracker.update_database_progress()
                    
                    # Session ID capture is now handled by progress tracker
                        
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
                elif "JSONDecodeError" in str(stream_error) or "json.decoder.JSONDecodeError" in str(type(stream_error)):
                    logger.error(f"SDK Executor: JSON decode error in stream - likely malformed response: {stream_error}")
                    
                    # For brain workflow, try to recover using streaming buffer
                    if streaming_buffer and hasattr(request, 'workflow_name') and request.workflow_name == 'brain':
                        logger.info("Attempting to recover from JSON decode error using streaming buffer")
                        try:
                            # Get any remaining content from buffer
                            remaining_content = streaming_buffer.get_final_content()
                            if remaining_content:
                                logger.info(f"Recovered {len(remaining_content)} chars from streaming buffer")
                                
                                # Use brain-specific error handling
                                from .stream_utils import handle_brain_workflow_json_error
                                recovery_info = handle_brain_workflow_json_error(
                                    stream_error, remaining_content, request.workflow_name
                                )
                                
                                # Add recovered content based on what we found
                                if recovery_info.get("partial_content"):
                                    partial = recovery_info["partial_content"]
                                    logger.info(f"Recovered {partial['count']} {partial['type']} from buffer")
                                    
                                    # Add partial content as messages
                                    if partial["type"] == "memory_operations":
                                        for memory_op in partial["content"]:
                                            messages.append(f"Recovered memory operation: {memory_op}")
                                    elif partial["type"] == "yaml_structures":
                                        for yaml_section in partial["content"]:
                                            messages.append(f"Recovered YAML section: {yaml_section}")
                                
                                elif recovery_info.get("fallback_content"):
                                    fallback = recovery_info["fallback_content"]
                                    logger.info(f"Using fallback content: {fallback['type']}")
                                    messages.append(f"Recovered content: {fallback['content']}")
                                
                                else:
                                    # Even if no structured recovery, add raw content
                                    messages.append(remaining_content)
                            
                            # Get buffer stats for debugging
                            buffer_stats = streaming_buffer.get_stats()
                            logger.info(f"Buffer stats: {buffer_stats}")
                            
                            # Continue with whatever messages we have
                            if messages:
                                logger.info(f"Continuing with {len(messages)} messages after brain workflow recovery")
                            else:
                                logger.warning("No messages recovered from brain workflow, raising error")
                                raise stream_error
                        except Exception as buffer_error:
                            logger.error(f"Brain workflow buffer recovery failed: {buffer_error}")
                            raise stream_error
                    else:
                        # Try to continue if we have some messages
                        if messages:
                            logger.info(f"Continuing with {len(messages)} messages collected before JSON error")
                        else:
                            raise stream_error
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
        
        logger.info(f"SDK Executor: Completed successfully - Turns: {progress_tracker.turn_count}, Tokens: {progress_tracker.token_count}, Tools: {len(metrics_handler.tools_used)}")
        
        # Update workflow_runs table with success BEFORE marking process completed
        if hasattr(request, 'run_id') and request.run_id:
            try:
                from ...db.models import WorkflowRunUpdate
                from ...db.repository.workflow_run import update_workflow_run_by_run_id
                
                # Extract final metrics from collected_messages
                final_result = None
                total_cost = 0.0
                total_tokens = 0
                
                # Look for ResultMessage in collected messages
                for msg in collected_messages:
                    try:
                        # Check for ResultMessage from Claude SDK
                        if hasattr(msg, '__class__') and msg.__class__.__name__ == 'ResultMessage':
                            logger.info("Processing ResultMessage")
                            
                            # Extract result based on error status
                            if hasattr(msg, 'is_error') and msg.is_error:
                                final_result = f"Workflow completed {getattr(msg, 'num_turns', 0)} turns (error or limit reached)"
                            else:
                                final_result = getattr(msg, 'result', "Workflow completed successfully")
                            
                            # Extract metrics
                            total_cost = getattr(msg, 'total_cost_usd', 0.0)
                            
                            # Extract usage - check if it's a dict or object
                            if hasattr(msg, 'usage'):
                                usage = msg.usage
                                if isinstance(usage, dict):
                                    # Calculate total from components
                                    input_tokens = usage.get('input_tokens', 0)
                                    output_tokens = usage.get('output_tokens', 0)
                                    cache_creation = usage.get('cache_creation_input_tokens', 0)
                                    cache_read = usage.get('cache_read_input_tokens', 0)
                                    total_tokens = input_tokens + output_tokens + cache_creation + cache_read
                                elif hasattr(usage, 'total_tokens'):
                                    total_tokens = usage.total_tokens
                                else:
                                    # Try to calculate from components
                                    total_tokens = (getattr(usage, 'input_tokens', 0) + 
                                                  getattr(usage, 'output_tokens', 0))
                                logger.info(f"Extracted metrics: cost={total_cost}, tokens={total_tokens}")
                            break  # Found the completion result, stop looking
                            
                    except Exception as msg_error:
                        logger.error(f"Error processing result message: {msg_error}")
                        continue
                
                if not final_result:
                    final_result = result_text
                
                # Also include turn count in final update
                final_metadata = {
                    "final_turns": progress_tracker.turn_count,
                    "max_turns": request.max_turns,
                    "total_tokens": total_tokens,
                    "run_status": "completed"
                }
                
                update_data = WorkflowRunUpdate(
                    status="completed",
                    completed_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    result=final_result,
                    total_tokens=total_tokens,
                    cost_estimate=total_cost,
                    duration_seconds=int(execution_time),
                    metadata=final_metadata
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
        # - workspace in /tmp/claude-code-temp: always cleanup (temp workspace)
        # - persistent=true: keep workspace
        # - persistent=false: cleanup workspace
        # - Environment variable CLAUDE_LOCAL_CLEANUP is fallback when persistent not set
        if hasattr(request, 'run_id') and request.run_id:
            # Check if this is a temp workspace (either explicitly marked or in temp directory)
            is_temp_workspace = (
                (hasattr(request, 'temp_workspace') and request.temp_workspace) or
                str(workspace_path).startswith("/tmp/claude-code-temp")
            )
            
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

        # Get final metrics from progress tracker
        final_metrics = progress_tracker.get_final_metrics()
        
        return {
            'success': True,
            'session_id': progress_tracker.actual_claude_session_id or session_id,
            'result': result_text,
            'exit_code': 0,
            'execution_time': execution_time,
            'logs': f"SDK execution completed in {execution_time:.2f}s",
            'workspace_path': str(workspace_path),
            **metrics_handler.get_summary(),
            'result_metadata': final_metrics
        }
    
    async def _execute_with_stream_input(
        self, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute workflow with message queue monitoring for stream-json input."""
        from .message_queue import message_queue_manager
        from claude_code_sdk import query
        import subprocess
        
        start_time = time.time()
        session_id = request.session_id or str(uuid4())
        run_id = request.run_id or str(uuid4())
        
        logger.info(f"SDK Executor: Starting stream-json execution for run_id: {run_id}, session: {session_id}")
        
        try:
            # Initialize metrics handler
            metrics_handler = MetricsHandler()
            
            # Build workspace path
            workspace_path = self._get_workspace_path(request, session_id)
            
            # Build options for Claude CLI
            options = self.build_options(workspace_path, request=request)
            
            # We need to use subprocess to control stdin
            # Build the claude command
            cli_manager = SDKCLIManager()
            claude_path = await cli_manager.find_claude_cli()
            
            if not claude_path:
                raise RuntimeError("Claude CLI not found")
            
            # Build command with stream-json input format
            cmd = [
                str(claude_path),
                "--input-format", "stream-json",
                "--output-format", "stream-json"
            ]
            
            # Add other options
            if options.get("permission_mode"):
                cmd.extend(["--permission-mode", options["permission_mode"]])
            if options.get("working_directory"):
                cmd.extend(["--working-directory", str(options["working_directory"])])
            
            # Start Claude process with pipes for stdin/stdout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(workspace_path)
            )
            
            logger.info(f"Started Claude process with PID: {process.pid}")
            
            # Send initial message as stream-json
            initial_message = json.dumps({
                "type": "user",
                "message": request.message
            }) + "\n"
            
            process.stdin.write(initial_message.encode())
            await process.stdin.drain()
            
            # Create message queue monitoring task
            async def message_queue_monitor():
                """Monitor message queue and inject messages in batch."""
                logger.info(f"Starting message queue monitor for {run_id}")
                
                while process.returncode is None:
                    try:
                        # Wait a bit before checking queue
                        await asyncio.sleep(2.0)
                        
                        # Get all queued messages
                        messages = message_queue_manager.get_messages_for_injection(run_id)
                        
                        if messages:
                            logger.info(f"Injecting {len(messages)} queued messages for {run_id}")
                            
                            # Send all messages as a batch
                            for msg_json in messages:
                                process.stdin.write((msg_json + "\n").encode())
                            
                            # Flush to ensure messages are sent
                            await process.stdin.drain()
                            logger.info(f"Successfully injected {len(messages)} messages")
                                
                    except Exception as e:
                        logger.error(f"Error in message queue monitor: {e}")
                        if process.returncode is not None:
                            break
            
            # Create output processing task
            async def process_output():
                """Process Claude output stream."""
                output_lines = []
                try:
                    while True:
                        line = await process.stdout.readline()
                        if not line:
                            break
                        
                        decoded = line.decode('utf-8')
                        output_lines.append(decoded)
                        
                        # Log streaming output for debugging
                        if decoded.strip():
                            logger.debug(f"Claude output: {decoded.strip()}")
                            
                except Exception as e:
                    logger.error(f"Error processing output: {e}")
                
                return output_lines
            
            # Create error monitoring task
            async def monitor_stderr():
                """Monitor stderr for errors."""
                try:
                    stderr_output = await process.stderr.read()
                    if stderr_output:
                        logger.error(f"Claude stderr: {stderr_output.decode('utf-8')}")
                except Exception as e:
                    logger.error(f"Error reading stderr: {e}")
            
            # Run all tasks concurrently
            queue_task = asyncio.create_task(message_queue_monitor())
            output_task = asyncio.create_task(process_output())
            stderr_task = asyncio.create_task(monitor_stderr())
            
            # Wait for process to complete
            return_code = await process.wait()
            
            # Cancel monitoring task
            queue_task.cancel()
            try:
                await queue_task
            except asyncio.CancelledError:
                pass
            
            # Get output
            try:
                output_lines = await output_task
                await stderr_task
            except Exception as e:
                logger.error(f"Error getting task results: {e}")
                output_lines = []
            
            # Process results
            if return_code == 0:
                logger.info(f"Claude process completed successfully")
                result = "".join(output_lines)
            else:
                logger.error(f"Claude process failed with return code: {return_code}")
                result = f"Process failed with return code: {return_code}"
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Clean up message queue
            message_queue_manager.remove_queue(run_id)
            
            return {
                'status': 'completed' if return_code == 0 else 'failed',
                'result': result,
                'session_id': session_id,
                'run_id': run_id,
                'execution_time': execution_time,
                'input_format': 'stream-json',
                'workspace_path': str(workspace_path),
                'logs': f"Stream-JSON execution completed in {execution_time:.2f}s",
                'return_code': return_code,
                **metrics_handler.get_summary()
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Stream-JSON execution failed: {e}")
            
            # Clean up message queue on error
            message_queue_manager.remove_queue(run_id)
            
            return self._build_error_result(
                e, session_id, 
                workspace_path if 'workspace_path' in locals() else Path.cwd(), 
                execution_time
            )
    
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

