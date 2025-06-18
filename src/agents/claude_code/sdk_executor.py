"""Claude SDK Executor - Drop-in replacement for ClaudeCLIExecutor using official SDK.

This module provides a ClaudeSDKExecutor that maintains API compatibility with 
ClaudeCLIExecutor while using the claude-code-sdk instead of subprocess execution.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, AsyncIterator, Callable, Tuple
from dataclasses import dataclass

from claude_code_sdk import ClaudeCodeOptions, query, McpServerConfig
from claude_code_sdk import UserMessage, AssistantMessage, SystemMessage, ResultMessage

from .cli_executor import CLIResult
from .cli_environment import CLIEnvironmentManager

logger = logging.getLogger(__name__)


class ClaudeSDKExecutor:
    """Drop-in replacement for ClaudeCLIExecutor using official SDK."""
    
    def __init__(self, environment_manager: CLIEnvironmentManager):
        """Initialize SDK executor.
        
        Args:
            environment_manager: Manager for CLI environments
        """
        self.env_mgr = environment_manager
        logger.info("ClaudeSDKExecutor initialized")
    
    def _build_options(
        self,
        workspace: Path,
        max_tokens: Optional[int] = None,
        max_thinking_tokens: Optional[int] = None,
        model: Optional[str] = None,
        resume_session_id: Optional[str] = None,
        max_turns: Optional[int] = None,
    ) -> ClaudeCodeOptions:
        """Build SDK options from parameters and workspace files.
        
        Args:
            workspace: Path to workspace directory
            max_tokens: Maximum output tokens (not supported by SDK yet)
            max_thinking_tokens: Maximum thinking tokens
            model: Model to use
            resume_session_id: Session ID to resume
            max_turns: Maximum conversation turns
            
        Returns:
            Configured ClaudeCodeOptions instance
        """
        options = ClaudeCodeOptions()
        
        # Core options
        if max_thinking_tokens:
            options.max_thinking_tokens = max_thinking_tokens
        if model:
            options.model = model
        if resume_session_id:
            # Use resume instead of continue_session (correct SDK field)
            options.resume = resume_session_id
        if max_turns:
            options.max_turns = max_turns
        
        # Working directory
        options.cwd = str(workspace)
        
        # Load prompt.md if exists - IMPORTANT: Use system_prompt, NOT append_system_prompt
        prompt_file = workspace / "prompt.md"
        if prompt_file.exists():
            options.system_prompt = prompt_file.read_text().strip()
            logger.info(f"Loaded system prompt from {prompt_file}")
        
        # Load MCP configuration
        mcp_file = workspace / ".mcp.json"
        if mcp_file.exists():
            try:
                with open(mcp_file) as f:
                    mcp_config = json.load(f)
                    # Convert to SDK format - SDK expects dict[str, McpServerConfig]
                    servers = mcp_config.get("servers", {})
                    options.mcp_servers = {}
                    for name, config in servers.items():
                        # Create McpServerConfig from dict
                        options.mcp_servers[name] = McpServerConfig(**config)
                    logger.info(f"Loaded MCP configuration with {len(options.mcp_servers)} servers")
            except Exception as e:
                logger.warning(f"Failed to load MCP config from {mcp_file}: {e}")
        
        # Load allowed tools
        tools_file = workspace / "allowed_tools.json"
        if tools_file.exists():
            try:
                with open(tools_file) as f:
                    options.allowed_tools = json.load(f)
                    logger.info(f"Loaded {len(options.allowed_tools)} allowed tools")
            except Exception as e:
                logger.warning(f"Failed to load allowed tools from {tools_file}: {e}")
        else:
            # Default tools if no file exists
            options.allowed_tools = [
                "Bash", "LS", "Read", "Write", "Edit", "Glob", "Grep", "Task"
            ]
            logger.info("Using default allowed tools")
        
        # Set permission mode to avoid interactive prompts
        options.permission_mode = "acceptEdits"
        
        return options
    
    async def execute(
        self,
        prompt: str,
        *,
        workspace: Path,
        max_tokens: Optional[int] = None,
        max_thinking_tokens: Optional[int] = None,
        model: Optional[str] = None,
        resume_session_id: Optional[str] = None,
        timeout: Optional[float] = None,
        max_turns: Optional[int] = None,
        **kwargs
    ) -> CLIResult:
        """Execute prompt and return complete result.
        
        Args:
            prompt: User prompt to execute
            workspace: Workspace directory path
            max_tokens: Maximum output tokens (not yet supported by SDK)
            max_thinking_tokens: Maximum thinking tokens
            model: Model to use
            resume_session_id: Session ID to resume
            timeout: Execution timeout in seconds
            max_turns: Maximum conversation turns
            **kwargs: Additional arguments (ignored for compatibility)
            
        Returns:
            CLIResult with execution details
        """
        options = self._build_options(
            workspace, 
            max_tokens, 
            max_thinking_tokens, 
            model, 
            resume_session_id,
            max_turns
        )
        
        messages = []
        start_time = time.time()
        session_id = resume_session_id  # Keep track of session
        
        try:
            # Apply timeout if specified
            if timeout:
                async with asyncio.timeout(timeout):
                    async for message in query(prompt=prompt, options=options):
                        messages.append(self._convert_message(message))
                        # Extract session ID from system messages if available
                        if isinstance(message, SystemMessage) and hasattr(message, 'session_id'):
                            session_id = getattr(message, 'session_id')
            else:
                async for message in query(prompt=prompt, options=options):
                    messages.append(self._convert_message(message))
                    # Extract session ID from system messages if available
                    if isinstance(message, SystemMessage) and hasattr(message, 'session_id'):
                        session_id = getattr(message, 'session_id')
                        
        except asyncio.TimeoutError:
            # Handle timeout gracefully
            return CLIResult(
                success=False,
                session_id=session_id,
                result="Execution timed out",
                exit_code=1,
                execution_time=time.time() - start_time,
                logs="",
                error=f"Execution timed out after {timeout} seconds",
                streaming_messages=messages
            )
        except Exception as e:
            logger.error(f"SDK execution error: {e}", exc_info=True)
            return CLIResult(
                success=False,
                session_id=session_id,
                result=str(e),
                exit_code=1,
                execution_time=time.time() - start_time,
                logs="",
                error=str(e),
                streaming_messages=messages
            )
        
        # Extract result text from messages
        result_text = self._extract_result_text(messages)
        
        return CLIResult(
            success=True,
            session_id=session_id,
            result=result_text,
            exit_code=0,
            execution_time=time.time() - start_time,
            logs="",  # SDK doesn't provide raw logs
            streaming_messages=messages
        )
    
    async def execute_until_first_response(
        self,
        prompt: str,
        *,
        workspace: Path,
        **kwargs
    ) -> Tuple[List[Dict[str, Any]], asyncio.Task]:
        """Execute until first assistant response for UI streaming.
        
        Args:
            prompt: User prompt to execute
            workspace: Workspace directory path
            **kwargs: Additional options passed to execute
            
        Returns:
            Tuple of (consumed messages, continuation task)
        """
        options = self._build_options(workspace, **kwargs)
        consumed = []
        
        # Create a queue for message passing
        queue: asyncio.Queue = asyncio.Queue()
        
        async def stream_messages():
            """Stream all messages to queue."""
            try:
                async for message in query(prompt=prompt, options=options):
                    await queue.put(message)
            finally:
                await queue.put(None)  # Sentinel
        
        # Start streaming task
        stream_task = asyncio.create_task(stream_messages())
        
        # Consume until first assistant response
        while True:
            message = await queue.get()
            if message is None:  # Stream ended
                break
            
            converted = self._convert_message(message)
            consumed.append(converted)
            
            # Check if this is an assistant message with content
            if (isinstance(message, AssistantMessage) and 
                hasattr(message, 'content') and 
                message.content):
                break
        
        # Create continuation task
        async def continue_stream():
            """Continue consuming from queue."""
            remaining = []
            while True:
                message = await queue.get()
                if message is None:
                    break
                remaining.append(self._convert_message(message))
            await stream_task  # Ensure task completes
            return consumed + remaining
        
        continuation_task = asyncio.create_task(continue_stream())
        return consumed, continuation_task
    
    def _convert_message(self, message) -> Dict[str, Any]:
        """Convert SDK message to CLI format.
        
        Args:
            message: SDK message object
            
        Returns:
            Dictionary in CLI message format
        """
        # Convert SDK message types to CLI format
        msg_dict = {
            "type": message.__class__.__name__.lower().replace("message", ""),
            "timestamp": time.time()
        }
        
        if isinstance(message, UserMessage):
            msg_dict["role"] = "user"
            msg_dict["content"] = getattr(message, "content", "")
        elif isinstance(message, AssistantMessage):
            msg_dict["role"] = "assistant"
            # Extract content from content blocks
            content_blocks = getattr(message, "content", [])
            content_parts = []
            for block in content_blocks:
                if hasattr(block, "text"):
                    content_parts.append(block.text)
            msg_dict["content"] = " ".join(content_parts)
            # Extract any tool uses if present
            if hasattr(message, "tool_uses"):
                msg_dict["tool_uses"] = message.tool_uses
        elif isinstance(message, SystemMessage):
            msg_dict["role"] = "system"
            # Extract from data dict
            data = getattr(message, "data", {})
            msg_dict["content"] = data.get("message", "")
        elif isinstance(message, ResultMessage):
            msg_dict["role"] = "result"
            msg_dict["result"] = getattr(message, "result", "")
            msg_dict["success"] = not getattr(message, "is_error", False)
            msg_dict["session_id"] = getattr(message, "session_id", None)
        
        return msg_dict
    
    def _extract_result_text(self, messages: List[Dict[str, Any]]) -> str:
        """Extract result text from messages.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Combined result text
        """
        result_parts = []
        
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("content"):
                result_parts.append(msg["content"])
            elif msg.get("role") == "result" and msg.get("result"):
                result_parts.append(msg["result"])
        
        return "\n\n".join(result_parts)