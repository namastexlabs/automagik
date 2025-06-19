"""SDK-based executor for Claude Code agent.

This module implements the ClaudeSDKExecutor that uses the official claude-code-sdk
instead of the legacy CLI approach. It provides file-based configuration loading
with proper priority handling and real-time streaming data extraction.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from uuid import uuid4

from claude_code_sdk import query, ClaudeCodeOptions
from ...utils.nodejs_detection import ensure_node_in_path

from .executor_base import ExecutorBase
from .models import ClaudeCodeRunRequest
from .sdk_stream_processor import SDKStreamProcessor
from .log_manager import get_log_manager

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
        self.stream_processors: Dict[str, SDKStreamProcessor] = {}
        
    def _build_options(self, workspace: Path, **kwargs) -> ClaudeCodeOptions:
        """Build options with file-based configuration loading.
        
        Args:
            workspace: The workspace directory path
            **kwargs: Additional options that override file-based configs
            
        Returns:
            Configured ClaudeCodeOptions instance
        """
        options = ClaudeCodeOptions()
        
        # Set working directory (SDK uses cwd, not workspace)
        options.cwd = str(workspace)
        
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
                if 'mcpServers' in mcp_data and isinstance(mcp_data['mcpServers'], dict):
                    options.mcp_servers = mcp_data['mcpServers']
                    logger.info(f"Loaded {len(mcp_data['mcpServers'])} MCP servers from config")
                else:
                    logger.warning(".mcp.json must contain 'mcpServers' object")
                    
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
            # Ensure Node.js is available for MCP servers before any execution
            node_available = ensure_node_in_path()
            if not node_available:
                logger.warning("Node.js not found - MCP servers using Node.js may not work")
            else:
                logger.info("Node.js detected and available for execution")
            
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
                'options': options,
                'start_time': start_time,
                'workspace': workspace_path
            }
            
            # Execute the task using SDK query function with comprehensive data extraction
            messages = []
            final_result_message = None
            
            # Initialize comprehensive metrics tracking
            total_cost = 0.0
            total_turns = 0
            tools_used = []
            token_details = {
                'total_tokens': 0,
                'input_tokens': 0,
                'output_tokens': 0,
                'cache_created': 0,
                'cache_read': 0
            }
            
            # Collect all messages first to avoid TaskGroup issues
            collected_messages = []
            final_metrics = None
            
            try:
                async for message in query(prompt=request.message, options=options):
                    messages.append(str(message))
                    collected_messages.append(message)  # Store actual message objects
                    
                    # Capture final metrics immediately during streaming to avoid loss
                    if hasattr(message, 'total_cost_usd') and message.total_cost_usd is not None:
                        final_metrics = {
                            'total_cost_usd': message.total_cost_usd,
                            'num_turns': getattr(message, 'num_turns', 0),
                            'duration_ms': getattr(message, 'duration_ms', 0),
                            'usage': getattr(message, 'usage', {})
                        }
                        logger.info(f"SDK Executor: Captured final metrics during streaming - Cost: ${final_metrics['total_cost_usd']:.4f}, Turns: {final_metrics['num_turns']}")
                    
            except Exception as sdk_error:
                # If SDK fails with TaskGroup errors, log it but continue with message processing
                if "TaskGroup" in str(sdk_error) or "cancel scope" in str(sdk_error):
                    logger.warning(f"SDK streaming failed with TaskGroup error: {sdk_error}")
                    logger.info("Continuing with message processing - using captured metrics if available")
                    # Continue to process any messages we collected before the error
                else:
                    # Re-raise other types of errors
                    raise sdk_error
            
            # Process collected messages OUTSIDE the streaming loop to avoid TaskGroup interference
            from claude_code_sdk import ResultMessage, AssistantMessage, ToolUseBlock
            
            logger.info(f"SDK Executor: Processing {len(collected_messages)} collected messages for data extraction")
            
            for message in collected_messages:
                if isinstance(message, ResultMessage):
                    final_result_message = message
                    # Extract comprehensive metrics from ResultMessage
                    total_cost = message.total_cost_usd or 0.0
                    total_turns = message.num_turns
                    
                    # Extract token usage details
                    if message.usage:
                        token_details = {
                            'total_tokens': (
                                message.usage.get('input_tokens', 0) +
                                message.usage.get('output_tokens', 0) +
                                message.usage.get('cache_creation_input_tokens', 0) +
                                message.usage.get('cache_read_input_tokens', 0)
                            ),
                            'input_tokens': message.usage.get('input_tokens', 0),
                            'output_tokens': message.usage.get('output_tokens', 0),
                            'cache_created': message.usage.get('cache_creation_input_tokens', 0),
                            'cache_read': message.usage.get('cache_read_input_tokens', 0)
                        }
                    
                elif isinstance(message, AssistantMessage):
                    # Extract tool usage from assistant messages
                    for block in message.content:
                        if isinstance(block, ToolUseBlock):
                            if block.name not in tools_used:
                                tools_used.append(block.name)
                                logger.info(f"SDK Executor: Captured tool usage - {block.name} (id: {block.id})")
            
            # If no final_result_message was found but we captured metrics during streaming, use those
            if not final_result_message and final_metrics:
                logger.info(f"SDK Executor: Using captured streaming metrics (no ResultMessage found)")
                total_cost = final_metrics['total_cost_usd']
                total_turns = final_metrics['num_turns']
                
                # Extract token usage from captured metrics
                usage = final_metrics.get('usage', {})
                if usage:
                    token_details = {
                        'total_tokens': (
                            usage.get('input_tokens', 0) +
                            usage.get('output_tokens', 0) +
                            usage.get('cache_creation_input_tokens', 0) +
                            usage.get('cache_read_input_tokens', 0)
                        ),
                        'input_tokens': usage.get('input_tokens', 0),
                        'output_tokens': usage.get('output_tokens', 0),
                        'cache_created': usage.get('cache_creation_input_tokens', 0),
                        'cache_read': usage.get('cache_read_input_tokens', 0)
                    }
            
            # Determine result text and success
            if final_result_message:
                result_text = final_result_message.result or '\n'.join(messages)
                success = not final_result_message.is_error
            else:
                result_text = '\n'.join(messages) if messages else "No response received"
                success = bool(messages)  # Basic success if we got any messages
            
            execution_time = time.time() - start_time
            
            # Log comprehensive tool capture results
            logger.info(f"SDK Executor: Final tool extraction results - {len(tools_used)} tools captured: {tools_used}")
            
            # If no tools were captured but we had messages, try fallback extraction
            if len(tools_used) == 0 and len(collected_messages) > 0:
                logger.warning(f"SDK Executor: No tools captured from {len(collected_messages)} messages - trying fallback extraction")
                
                # Log message types for debugging
                message_types = [type(msg).__name__ for msg in collected_messages]
                logger.debug(f"SDK Executor: Message types processed: {message_types}")
                
                # Fallback: try to extract tools from string representations
                import re
                for msg_str in messages:
                    # Look for tool use patterns in the string representation
                    tool_matches = re.findall(r'ToolUse.*?name["\']?\s*:\s*["\']?(\w+)', msg_str)
                    for tool_name in tool_matches:
                        if tool_name not in tools_used:
                            tools_used.append(tool_name)
                            logger.info(f"SDK Executor: Fallback captured tool - {tool_name}")
                
                if len(tools_used) > 0:
                    logger.info(f"SDK Executor: Fallback extraction successful - captured {len(tools_used)} tools")
                else:
                    logger.error(f"SDK Executor: Both primary and fallback tool extraction failed")
            elif len(tools_used) > 0:
                logger.info(f"SDK Executor: SUCCESS - Tool extraction working correctly!")
            
            # Extract git commits if any (TODO: parse from tool usage)
            git_commits = []
            
            return {
                'success': success,
                'session_id': session_id,
                'result': result_text,
                'exit_code': 0 if success else 1,
                'execution_time': execution_time,
                'logs': f"SDK execution completed in {execution_time:.2f}s",
                'git_commits': git_commits,
                'workspace_path': str(workspace_path),
                # Enhanced data extracted from SDK messages
                'cost_usd': total_cost,
                'total_turns': total_turns,
                'tools_used': tools_used,
                'token_details': token_details,
                # Store for session metadata
                'total_cost_usd': total_cost,
                'total_tokens': token_details['total_tokens'],
                'input_tokens': token_details['input_tokens'],
                'output_tokens': token_details['output_tokens'],
                'tool_names_used': tools_used
            }
            
        except Exception as e:
            logger.error(f"SDK execution failed: {e}")
            
            # Log additional details for TaskGroup errors
            if "TaskGroup" in str(e) or "cancel scope" in str(e):
                logger.warning("SDK TaskGroup error detected - this is a known issue with background execution")
                logger.warning("The SDK is designed for foreground CLI usage, not background API execution")
            
            return {
                'success': False,
                'session_id': session_id,
                'result': f"SDK execution failed: {str(e)}",
                'exit_code': 1,
                'execution_time': time.time() - start_time,
                'logs': f"SDK error: {str(e)}",
                'error': str(e),
                'workspace_path': str(workspace_path) if workspace_path else None,
                # Default values for status endpoint
                'cost_usd': 0.0,
                'total_turns': 0,
                'tools_used': []
            }
        finally:
            # Cleanup session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            if session_id in self.stream_processors:
                del self.stream_processors[session_id]
    
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
                'options': options,
                'start_time': time.time(),
                'workspace': workspace_path
            }
            
            # Start streaming execution using SDK query function
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
    
    async def execute_with_streaming(
        self, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any],
        run_id: str
    ) -> Dict[str, Any]:
        """Execute Claude Code with real-time streaming data extraction.
        
        This method provides full streaming execution with real-time logging
        of all events for the status endpoint.
        
        Args:
            request: Execution request with task details
            agent_context: Agent context including session info
            run_id: Unique run identifier for this execution
            
        Returns:
            Dictionary with execution results
        """
        start_time = time.time()
        session_id = request.session_id or str(uuid4())
        
        # Initialize stream processor
        processor = SDKStreamProcessor()
        self.stream_processors[run_id] = processor
        
        # Get log manager for real-time logging
        log_manager = get_log_manager()
        
        try:
            # Ensure Node.js is available
            node_available = ensure_node_in_path()
            if not node_available:
                logger.warning("Node.js not found - MCP servers using Node.js may not work")
            else:
                logger.info("Node.js detected and available for execution")
            
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
            session_info = {
                'options': options,
                'start_time': start_time,
                'workspace': workspace_path,
                'run_id': run_id,
                'request': request
            }
            self.active_sessions[session_id] = session_info
            
            # Log execution start (synchronous to avoid TaskGroup issues)
            try:
                await log_manager.log_event(run_id, "execution_start", {
                    "session_id": session_id,
                    "workflow_name": request.workflow_name,
                    "max_turns": request.max_turns,
                    "workspace_path": str(workspace_path)
                })
            except Exception as log_error:
                logger.warning(f"Failed to log execution start: {log_error}")
            
            # Execute with streaming and real-time processing
            result_messages = []
            final_result = None
            
            try:
                # Collect all messages first to avoid task scope issues
                messages_collected = []
                
                async for message in query(prompt=request.message, options=options):
                    messages_collected.append(message)
                    
                    # Store final result if this is a result message
                    from claude_code_sdk import ResultMessage
                    if isinstance(message, ResultMessage):
                        final_result = message
                        break
                
                # Process collected messages after streaming is complete
                for message in messages_collected:
                    # Process message through stream processor
                    event_data = processor.process_message(message)
                    
                    # Log the processed event (with error handling)
                    try:
                        await log_manager.log_event(run_id, event_data["event_type"], event_data["data"])
                    except Exception as log_error:
                        logger.warning(f"Failed to log event {event_data['event_type']}: {log_error}")
                    
                    # Collect result messages
                    result_messages.append(str(message))
                
                # Log final completion if we have a result
                if final_result:
                    try:
                        await log_manager.log_event(run_id, "execution_complete", {
                            "success": not final_result.is_error,
                            "total_cost_usd": final_result.total_cost_usd,
                            "duration_ms": final_result.duration_ms,
                            "total_turns": final_result.num_turns,
                            "session_id": final_result.session_id
                        })
                    except Exception as log_error:
                        logger.warning(f"Failed to log completion: {log_error}")
                        
            except Exception as streaming_error:
                logger.error(f"Error during SDK streaming: {streaming_error}")
                # Continue to process what we have so far
            
            # Get final metrics from processor
            metrics = processor.get_current_metrics()
            execution_time = time.time() - start_time
            
            # Extract git commits if any (TODO: implement based on tool usage)
            git_commits = []
            
            success = final_result and not final_result.is_error if final_result else False
            
            return {
                'success': success,
                'session_id': session_id,
                'result': metrics.final_result or '\n'.join(result_messages),
                'exit_code': 0 if success else 1,
                'execution_time': execution_time,
                'logs': f"SDK execution completed with {metrics.total_turns} turns",
                'git_commits': git_commits,
                'workspace_path': str(workspace_path),
                'metrics': metrics,
                'cost_usd': metrics.total_cost_usd,
                'total_turns': metrics.total_turns,
                'tools_used': metrics.tool_names_used
            }
            
        except Exception as e:
            logger.error(f"SDK streaming execution failed: {e}")
            
            # Log error
            await log_manager.log_event(run_id, "execution_error", {
                "error": str(e),
                "session_id": session_id
            })
            
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
    
    def get_execution_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get real-time execution status from stream processor.
        
        Args:
            run_id: Unique run identifier
            
        Returns:
            Dictionary with current execution status or None if not found
        """
        if run_id not in self.stream_processors:
            return None
            
        processor = self.stream_processors[run_id]
        status_data = processor.get_status_data()
        
        # Update with actual run_id and workflow name if available
        status_data["run_id"] = run_id
        
        # Try to get workflow name from active session
        for session_info in self.active_sessions.values():
            if session_info.get('run_id') == run_id:
                status_data["workflow_name"] = session_info.get('request', {}).workflow_name or "unknown"
                status_data["progress"]["max_turns"] = session_info.get('request', {}).max_turns
                break
        
        return status_data
    
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
                # For SDK mode, we can only remove the session tracking
                # The SDK query function doesn't provide cancellation
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
        
        # No SDK client cleanup needed for function-based API