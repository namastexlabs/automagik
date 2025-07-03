"""Message parsing utilities for agents.

This module provides functions for parsing agent messages, extracting tool calls,
tool outputs, and formatting message history.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple

logger = logging.getLogger(__name__)

def extract_tool_calls(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract tool calls from a message.
    
    Args:
        message: The message to extract tool calls from
        
    Returns:
        List of extracted tool calls as dictionaries
    """
    tool_calls = []
    
    try:
        # Check direct tool_calls attribute
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tc in message.tool_calls:
                tool_call = {
                    'tool_name': getattr(tc, 'name', getattr(tc, 'tool_name', '')),
                    'args': getattr(tc, 'args', getattr(tc, 'arguments', {})),
                    'tool_call_id': getattr(tc, 'id', getattr(tc, 'tool_call_id', ''))
                }
                tool_calls.append(tool_call)
                logger.info(f"Extracted direct tool call: {tool_call['tool_name']}")
        
        # Check for parts with tool calls
        if hasattr(message, 'parts'):
            for part in message.parts:
                if (hasattr(part, 'part_kind') and part.part_kind == 'tool-call') or \
                   type(part).__name__ == 'ToolCallPart' or \
                   hasattr(part, 'tool_name') and hasattr(part, 'args'):
                    
                    tool_call = {
                        'tool_name': getattr(part, 'tool_name', ''),
                        'args': getattr(part, 'args', {}),
                        'tool_call_id': getattr(part, 'tool_call_id', getattr(part, 'id', ''))
                    }
                    tool_calls.append(tool_call)
                    logger.info(f"Extracted part tool call: {tool_call['tool_name']}")
    except Exception as e:
        logger.error(f"Error extracting tool calls: {str(e)}")
    
    return tool_calls

def extract_tool_outputs(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract tool outputs from a message.
    
    Args:
        message: The message to extract tool outputs from
        
    Returns:
        List of extracted tool outputs as dictionaries
    """
    tool_outputs = []
    
    try:
        # Check direct tool_outputs attribute
        if hasattr(message, 'tool_outputs') and message.tool_outputs:
            for to in message.tool_outputs:
                tool_output = {
                    'tool_name': getattr(to, 'name', getattr(to, 'tool_name', '')),
                    'content': getattr(to, 'content', ''),
                    'tool_call_id': getattr(to, 'id', getattr(to, 'tool_call_id', ''))
                }
                tool_outputs.append(tool_output)
                logger.info(f"Extracted direct tool output: {tool_output['tool_name']}")
        
        # Check for parts with tool outputs
        if hasattr(message, 'parts'):
            for part in message.parts:
                if (hasattr(part, 'part_kind') and part.part_kind == 'tool-return') or \
                   type(part).__name__ == 'ToolReturnPart' or \
                   (hasattr(part, 'tool_name') and hasattr(part, 'content')):
                    
                    content = getattr(part, 'content', None)
                    
                    tool_output = {
                        'tool_name': getattr(part, 'tool_name', ''),
                        'content': content,
                        'tool_call_id': getattr(part, 'tool_call_id', getattr(part, 'id', ''))
                    }
                    tool_outputs.append(tool_output)
                    
                    try:
                        if content is None:
                            content_preview = "None"
                        elif isinstance(content, str):
                            content_preview = content[:50] + ("..." if len(content) > 50 else "")
                        elif isinstance(content, dict):
                            content_preview = f"Dict with keys: {', '.join(list(content.keys())[:3])}"
                        else:
                            content_preview = f"{type(content).__name__}[...]"
                        
                        logger.info(f"Extracted part tool output for {tool_output['tool_name']} with content: {content_preview}")
                    except Exception as e:
                        logger.warning(f"Error creating content preview: {str(e)}")
    except Exception as e:
        logger.error(f"Error extracting tool outputs: {str(e)}")
    
    return tool_outputs

def extract_all_messages(result: Any) -> List[Dict[str, Any]]:
    """Extract all messages from a result object.
    
    Args:
        result: The result object to extract messages from
        
    Returns:
        List of extracted messages
    """
    try:
        if hasattr(result, "all_messages") and callable(getattr(result, "all_messages")):
            return result.all_messages()
        elif hasattr(result, "messages"):
            return result.messages
        else:
            logger.warning("No messages found in result object")
            return []
    except Exception as e:
        logger.error(f"Error extracting messages: {str(e)}")
        return []

def format_message_for_db(role: str, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None, 
                          tool_outputs: Optional[List[Dict[str, Any]]] = None,
                          system_prompt: Optional[str] = None,
                          agent_id: Optional[int] = None,
                          channel_payload: Optional[Dict] = None,
                          usage: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Format a message for database storage.
    
    Args:
        role: Message role (user, assistant, system)
        content: Message content
        tool_calls: Optional list of tool calls
        tool_outputs: Optional list of tool outputs
        system_prompt: Optional system prompt
        agent_id: Optional agent ID
        channel_payload: Optional channel-specific data
        usage: Optional token usage information
    Returns:
        Formatted message dictionary
    """
    message = {
        "role": role,
        "content": content,
        "agent_id": agent_id
    }
    
    if tool_calls:
        message["tool_calls"] = tool_calls
    
    if tool_outputs:
        message["tool_outputs"] = tool_outputs
    
    if system_prompt:
        message["system_prompt"] = system_prompt
    
    if channel_payload:
        message["channel_payload"] = channel_payload
    
    if usage:
        message["usage"] = usage
    
    return message

def parse_user_message(user_message: Union[str, Dict[str, Any]]) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Parse a user message into content and metadata.
    
    Args:
        user_message: User message as string or dictionary
        
    Returns:
        Tuple of (content, metadata)
    """
    metadata = {}
    
    if isinstance(user_message, dict):
        content = user_message.get("content", "")
        # Extract other metadata
        for key, value in user_message.items():
            if key != "content":
                metadata[key] = value
    else:
        content = user_message
    
    return content, metadata 