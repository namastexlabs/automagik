"""Message history management for PydanticAI compatibility.

This module provides a simplified MessageHistory class that directly uses
the repository pattern for database operations and implements PydanticAI-compatible 
message history methods.
"""

import logging
import uuid
from typing import List, Optional, Dict, Any, Union, Tuple
from datetime import datetime, UTC

# PydanticAI imports
from pydantic_ai.messages import (
    ModelMessage, 
    ModelRequest, 
    ModelResponse,
    SystemPromptPart, 
    UserPromptPart, 
    TextPart,
    ToolCallPart,
    ToolReturnPart
)

# Import repository functions
from src.db.repository.message import (
    create_message,
    get_message,
    list_messages,
    delete_session_messages,
    get_system_prompt,
    list_session_messages
)
from src.db.repository.session import (
    get_session,
    create_session,
    update_session,
    delete_session
)
from src.db.models import Message, Session

# Configure logger
logger = logging.getLogger(__name__)

# Helper function for UUID validation
def is_valid_uuid(value: Any) -> bool:
    """Check if a value is a valid UUID or can be converted to one.
    
    Args:
        value: The value to check
        
    Returns:
        True if the value is a valid UUID or can be converted to one
    """
    if value is None:
        return False
    if isinstance(value, uuid.UUID):
        return True
    if not isinstance(value, str):
        return False
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


class MessageHistory:
    """Maintains a history of messages between the user and the agent.
    
    This class integrates with pydantic-ai's message system to maintain context
    across multiple agent runs. It handles system prompts, user messages, and
    assistant responses in a format compatible with pydantic-ai.
    
    This simplified implementation directly uses the repository pattern
    for database operations without intermediate abstractions.
    """
    
    def __init__(self, session_id: str, system_prompt: Optional[str] = None, user_id: int = 1, no_auto_create: bool = False):
        """Initialize a new message history.
        
        Args:
            session_id: The unique session identifier.
            system_prompt: Optional system prompt to set at initialization.
            user_id: The user identifier to associate with this session (defaults to 1).
            no_auto_create: If True, don't automatically create a session in the database.
        """
        self.session_id = self._ensure_session_id(session_id, user_id, no_auto_create)
        self.user_id = user_id
        
        # Add system prompt if provided
        if system_prompt:
            self.add_system_prompt(system_prompt)
    
    def _ensure_session_id(self, session_id: str, user_id: int, no_auto_create: bool = False) -> str:
        """Ensure the session exists, creating it if necessary.
        
        Args:
            session_id: The session ID (string or UUID)
            user_id: The user ID to associate with the session
            no_auto_create: If True, don't automatically create a session
            
        Returns:
            The validated session ID as a string
        """
        try:
            # Generate new UUID if session_id is None or invalid
            if not session_id or not is_valid_uuid(session_id):
                new_uuid = uuid.uuid4()
                logger.info(f"Creating new session with UUID: {new_uuid}")
                
                if not no_auto_create:
                    # Create a new session
                    session = Session(
                        id=new_uuid,
                        user_id=user_id,
                        name=f"Session-{new_uuid}",
                        platform="automagik"
                    )
                    create_session(session)
                else:
                    logger.info("Auto-creation disabled, not creating session in database")
                
                return str(new_uuid)
            
            # Convert string to UUID
            if isinstance(session_id, str):
                session_uuid = uuid.UUID(session_id)
            else:
                session_uuid = session_id
                
            # Check if session exists
            session = get_session(session_uuid)
            if not session and not no_auto_create:
                # Create new session with this ID
                session = Session(
                    id=session_uuid,
                    user_id=user_id,
                    name=f"Session-{session_uuid}",
                    platform="automagik"
                )
                create_session(session)
                
            return str(session_uuid)
        except Exception as e:
            logger.error(f"Error ensuring session ID: {str(e)}")
            # Create a fallback UUID
            fallback_uuid = uuid.uuid4()
            return str(fallback_uuid)
    
    def add_system_prompt(self, content: str, agent_id: Optional[int] = None) -> ModelMessage:
        """Add or update the system prompt for this conversation.
        
        Args:
            content: The system prompt content.
            agent_id: Optional agent ID associated with the message.
            
        Returns:
            The created system prompt message.
        """
        try:
            # Create a system prompt message
            system_message = ModelRequest(parts=[SystemPromptPart(content=content)])
            
            # Store the system prompt in the session metadata
            session_uuid = uuid.UUID(self.session_id)
            session = get_session(session_uuid)
            
            if session:
                # Get existing metadata or create new dictionary
                metadata = session.metadata or {}
                if isinstance(metadata, str):
                    try:
                        import json
                        metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        metadata = {}
                
                # Store system prompt in metadata
                metadata["system_prompt"] = content
                session.metadata = metadata
                
                # Update session
                update_session(session)
                logger.debug(f"Stored system prompt in session metadata: {content[:50]}...")
            
            # Also create a system message in the database
            message = Message(
                id=uuid.uuid4(),
                session_id=session_uuid,
                user_id=self.user_id,
                agent_id=agent_id,
                role="system",
                text_content=content,
                message_type="text",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            create_message(message)
            
            return system_message
        except Exception as e:
            logger.error(f"Error adding system prompt: {str(e)}")
            # Return a basic system message as fallback
            return ModelRequest(parts=[SystemPromptPart(content=content)])
    
    def add(self, content: str, agent_id: Optional[int] = None, context: Optional[Dict] = None) -> ModelMessage:
        """Add a user message to the history.
        
        Args:
            content: The message content.
            agent_id: Optional agent ID associated with the message.
            context: Optional context data to include with the message.
            
        Returns:
            The created user message.
        """
        try:
            # Create a user message in the database
            message = Message(
                id=uuid.uuid4(),
                session_id=uuid.UUID(self.session_id),
                user_id=self.user_id,
                agent_id=agent_id,
                role="user",
                text_content=content,
                message_type="text",
                context=context,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            
            # Log before attempting to create message
            logger.info(f"Adding user message to history for session {self.session_id}, user {self.user_id}")
            logger.debug(f"Message details: id={message.id}, session_id={self.session_id}, content_length={len(content) if content else 0}")
            
            # Create the message in the database
            message_id = create_message(message)
            
            if not message_id:
                # If message creation failed, log a more detailed error
                logger.error(f"Failed to create user message in database: message_id={message.id}, session_id={self.session_id}, user_id={self.user_id}")
                # Don't raise exception to maintain backward compatibility, but log the error
            else:
                logger.info(f"Successfully added user message {message_id} to history")
            
            # Create and return a PydanticAI compatible message
            return ModelRequest(parts=[UserPromptPart(content=content)])
        except Exception as e:
            import traceback
            logger.error(f"Exception adding user message: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.error(f"Message details: session_id={self.session_id}, user_id={self.user_id}, content_length={len(content) if content else 0}")
            
            # Return a basic user message as fallback to maintain backwards compatibility
            return ModelRequest(parts=[UserPromptPart(content=content)])
    
    def add_response(
        self, 
        content: str, 
        assistant_name: Optional[str] = None, 
        tool_calls: Optional[List[Dict]] = None, 
        tool_outputs: Optional[List[Dict]] = None,
        agent_id: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> ModelMessage:
        """Add an assistant response message to the history.
        
        Args:
            content: The text content of the assistant's response.
            assistant_name: Optional name of the assistant.
            tool_calls: Optional list of tool calls made during processing.
            tool_outputs: Optional list of outputs from tool calls.
            agent_id: Optional agent ID associated with the message.
            system_prompt: Optional system prompt to store directly with the message.
            
        Returns:
            The created assistant response message.
        """
        try:
            # Prepare tool calls and outputs for storage
            tool_calls_dict = {}
            tool_outputs_dict = {}
            
            if tool_calls:
                for i, tc in enumerate(tool_calls):
                    if isinstance(tc, dict) and "tool_name" in tc:
                        tool_calls_dict[str(i)] = tc
            
            if tool_outputs:
                for i, to in enumerate(tool_outputs):
                    if isinstance(to, dict) and "tool_name" in to:
                        tool_outputs_dict[str(i)] = to
            
            # Prepare raw payload
            raw_payload = {
                "content": content,
                "assistant_name": assistant_name,
                "tool_calls": tool_calls,
                "tool_outputs": tool_outputs,
            }
            
            # If system_prompt isn't directly provided or is None, try to get it from:
            # 1. Session metadata
            # 2. Last system prompt in the message history
            # 3. Agent configuration (through agent_id)
            if not system_prompt:
                try:
                    # Try to get from session metadata first
                    session_system_prompt = get_system_prompt(uuid.UUID(self.session_id))
                    if session_system_prompt:
                        system_prompt = session_system_prompt
                        logger.debug(f"Using system prompt from session metadata")
                    else:
                        # If not found, try other sources
                        if agent_id:
                            # Try to get system prompt from agent configuration
                            from src.db.repository.agent import get_agent
                            agent = get_agent(agent_id)
                            if agent and agent.system_prompt:
                                system_prompt = agent.system_prompt
                                logger.debug(f"Using system prompt from agent configuration")
                except Exception as e:
                    logger.error(f"Error getting system prompt: {str(e)}")
            
            # Log message details - reduced logging
            tool_calls_count = len(tool_calls_dict) if tool_calls_dict else 0
            tool_outputs_count = len(tool_outputs_dict) if tool_outputs_dict else 0
            content_length = len(content) if content else 0
            
            # For INFO level, just log basic info
            logger.info(f"Adding assistant response to MessageHistory in the database")
            logger.info(f"System prompt status: {'Present' if system_prompt else 'Not provided'}")
            
            # For DEBUG level (verbose logging), add more details
            logger.debug(f"Adding assistant response to history for session {self.session_id}, user {self.user_id}")
            logger.debug(f"Assistant response details: tool_calls={tool_calls_count}, tool_outputs={tool_outputs_count}, content_length={content_length}")
            
            # Create message in database
            logger.debug(f"Creating message with parameters: session_id={self.session_id}, role=assistant, user_id={self.user_id}, agent_id={agent_id}, message_type=text, text_length={content_length}")
            
            message = Message(
                id=uuid.uuid4(),
                session_id=uuid.UUID(self.session_id),
                user_id=self.user_id,
                agent_id=agent_id,
                role="assistant",
                text_content=content,
                message_type="text",
                raw_payload=raw_payload,
                tool_calls=tool_calls_dict,
                tool_outputs=tool_outputs_dict,
                system_prompt=system_prompt,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            
            # Log query only in debug mode
            logger.debug("Executing message creation query: \n            INSERT INTO messages (\n                id, session_id, user_id, agent_id, role, text_content, \n                message_type, raw_payload, tool_calls, tool_outputs, \n                context, system_prompt, created_at, updated_at\n            ) VALUES (\n                %s, %s, %s, %s, %s, %s, \n                %s, %s, %s, %s, \n                %s, %s, %s, %s\n            )\n            RETURNING id\n         ")
            logger.debug(f"Query parameters: id={message.id}, session_id={self.session_id}, user_id={self.user_id}, agent_id={agent_id}")
            
            # Create the message in the database
            message_id = create_message(message)
            
            if not message_id:
                # If message creation failed, log a more detailed error
                logger.error(f"Failed to create assistant message in database: message_id={message.id}, session_id={self.session_id}, user_id={self.user_id}")
                # Don't raise exception to maintain backward compatibility, but log the error
            else:
                logger.info(f"Successfully created message {message_id} for session {self.session_id}")
                logger.debug(f"Successfully added assistant message {message_id} to history for session {self.session_id}")
            
            # Create parts for PydanticAI message
            parts = [TextPart(content=content)]
            
            # Add tool call parts
            if tool_calls:
                for tc in tool_calls:
                    if isinstance(tc, dict) and "tool_name" in tc and "args" in tc:
                        parts.append(
                            ToolCallPart(
                                tool_name=tc["tool_name"],
                                args=tc["args"],
                                tool_call_id=tc.get("tool_call_id", "")
                            )
                        )
            
            # Add tool output parts
            if tool_outputs:
                for to in tool_outputs:
                    if isinstance(to, dict) and "tool_name" in to and "content" in to:
                        parts.append(
                            ToolReturnPart(
                                tool_name=to["tool_name"],
                                content=to["content"],
                                tool_call_id=to.get("tool_call_id", "")
                            )
                        )
            
            # Create and return PydanticAI message
            return ModelResponse(parts=parts)
        except Exception as e:
            import traceback
            logger.error(f"Exception adding assistant message: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.error(f"Message details: session_id={self.session_id}, user_id={self.user_id}, content_length={len(content) if content else 0}, tool_calls={len(tool_calls) if tool_calls else 0}")
            
            # Return a basic assistant message as fallback to maintain backward compatibility
            return ModelResponse(parts=[TextPart(content=content)])
    
    def clear(self) -> None:
        """Clear all messages in the current session."""
        try:
            delete_session_messages(uuid.UUID(self.session_id))
        except Exception as e:
            logger.error(f"Error clearing session messages: {str(e)}")
    
    def add_message(self, message: Dict[str, Any]) -> ModelMessage:
        """Add a message to the history based on a message dictionary.
        
        This method processes an incoming message dictionary and stores it
        in the database, handling both user and assistant messages.
        
        Args:
            message: Dictionary containing the message details including 'role' and 'content'
            
        Returns:
            The created ModelMessage object
        """
        try:
            role = message.get("role", "")
            content = message.get("content", "")
            agent_id = message.get("agent_id")
            
            if role == "user":
                # Handle user message
                return self.add(content, agent_id=agent_id)
            elif role == "assistant":
                # Handle assistant message with potential tool calls and outputs
                tool_calls = message.get("tool_calls", [])
                tool_outputs = message.get("tool_outputs", [])
                return self.add_response(
                    content, 
                    tool_calls=tool_calls, 
                    tool_outputs=tool_outputs,
                    agent_id=agent_id
                )
            elif role == "system":
                # Handle system message
                return self.add_system_prompt(content, agent_id=agent_id)
            else:
                logger.warning(f"Unknown message role: {role}")
                # Default to user message if role is unknown
                return self.add(content, agent_id=agent_id)
        except Exception as e:
            logger.error(f"Error adding message: {str(e)}")
            # Create a basic message as fallback
            if message.get("role") == "user":
                return ModelRequest(parts=[UserPromptPart(content=message.get("content", ""))])
            else:
                # Default to a text response for non-user messages
                return ModelResponse(parts=[TextPart(content=message.get("content", ""))])
    
    # PydanticAI compatible methods
    
    def all_messages(self) -> List[ModelMessage]:
        """Return all messages in the history, including those from prior runs.
        
        This method is required for PydanticAI compatibility.
        
        Returns:
            List of all messages in the history
        """
        try:
            # Get all messages from the database
            logger.debug(f"Retrieving all messages for session {self.session_id}")
            # IMPORTANT: Use sort_desc=False to get messages in chronological order (oldest first)
            db_messages = list_messages(uuid.UUID(self.session_id), sort_desc=False)
            
            # Convert to PydanticAI format - only log detailed info in debug mode
            messages = self._convert_db_messages_to_model_messages(db_messages)
            logger.debug(f"Retrieved and converted {len(messages)} messages for session {self.session_id}")
            return messages
        except Exception as e:
            import traceback
            logger.error(f"Error retrieving messages: {str(e)}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return []
    
    def new_messages(self) -> List[ModelMessage]:
        """Return only the messages from the current run.
        
        This method is required for PydanticAI compatibility.
        Since we don't track runs explicitly, this returns all messages.
        
        Returns:
            List of messages from the current run
        """
        # For now, identical to all_messages since we don't track runs
        return self.all_messages()
    
    def all_messages_json(self) -> bytes:
        """Return all messages as JSON.
        
        This method is required for PydanticAI compatibility.
        
        Returns:
            JSON bytes representation of all messages
        """
        try:
            from pydantic_core import to_json
            return to_json(self.all_messages())
        except Exception as e:
            logger.error(f"Error serializing messages to JSON: {str(e)}")
            return b"[]"
    
    def new_messages_json(self) -> bytes:
        """Return only the messages from the current run as JSON.
        
        This method is required for PydanticAI compatibility.
        
        Returns:
            JSON bytes representation of messages from the current run
        """
        # For now, identical to all_messages_json since we don't track runs
        return self.all_messages_json()
    
    def get_formatted_pydantic_messages(self, limit: int = 20) -> List[ModelMessage]:
        """Get formatted messages in PydanticAI format, limited to the most recent ones.
        
        This method is used by the SimpleAgent to get correctly formatted messages
        for the PydanticAI agent. It retrieves the last N messages from the database
        and formats them according to PydanticAI message structures.
        
        Args:
            limit: Maximum number of messages to retrieve (default 20)
            
        Returns:
            List of PydanticAI ModelMessage objects
        """
        try:
            # Get the last N messages from the database (most recent first)
            logger.debug(f"Retrieving latest {limit} messages for session {self.session_id}")
            db_messages = list_messages(
                uuid.UUID(self.session_id), 
                sort_desc=True, 
                limit=limit
            )
            
            # Reverse the list to get chronological order (oldest first)
            # This is important for proper context in conversation
            db_messages.reverse()
            
            # Convert to PydanticAI format
            messages = self._convert_db_messages_to_model_messages(db_messages)
            logger.debug(f"Retrieved and converted {len(messages)} messages for session {self.session_id}")
            
            # Check if we have a system prompt
            has_system_prompt = any(
                isinstance(msg, ModelRequest) and 
                any(isinstance(part, SystemPromptPart) for part in msg.parts)
                for msg in messages
            )
            
            # If no system prompt found, try to get it from session metadata
            if not has_system_prompt:
                try:
                    system_prompt = get_system_prompt(uuid.UUID(self.session_id))
                    if system_prompt:
                        # Insert system prompt at the beginning
                        messages.insert(0, ModelRequest(parts=[SystemPromptPart(content=system_prompt)]))
                except Exception as e:
                    logger.warning(f"Failed to retrieve system prompt from metadata: {str(e)}")
            
            return messages
        except Exception as e:
            import traceback
            logger.error(f"Error retrieving formatted pydantic messages: {str(e)}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return []
    
    @classmethod
    def from_model_messages(cls, messages: List[ModelMessage], session_id: Optional[str] = None) -> 'MessageHistory':
        """Create a new MessageHistory from a list of model messages.
        
        Args:
            messages: List of ModelMessage objects to populate the history with
            session_id: Optional session ID to use, otherwise generates a new one
            
        Returns:
            A new MessageHistory instance with the provided messages
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            
        # Create a new MessageHistory instance
        history = cls(session_id=session_id)
        
        # Add system prompt message if present
        system_prompt = None
        for msg in messages:
            if hasattr(msg, "parts"):
                for part in msg.parts:
                    if isinstance(part, SystemPromptPart):
                        system_prompt = part.content
                        break
                if system_prompt:
                    history.add_system_prompt(system_prompt)
                    break
        
        # Add all user messages
        for msg in messages:
            if hasattr(msg, "parts"):
                # Skip system messages as we've already handled them
                if any(isinstance(part, SystemPromptPart) for part in msg.parts):
                    continue
                    
                # Handle user messages
                for part in msg.parts:
                    if isinstance(part, UserPromptPart):
                        history.add(part.content)
                        break
                        
                # Handle assistant messages with potential tool calls
                if any(isinstance(part, TextPart) and not isinstance(part, UserPromptPart) for part in msg.parts):
                    content = ""
                    tool_calls = []
                    tool_outputs = []
                    
                    # Extract content
                    for part in msg.parts:
                        if isinstance(part, TextPart) and not isinstance(part, UserPromptPart):
                            content = part.content
                            break
                    
                    # Extract tool calls
                    for part in msg.parts:
                        if isinstance(part, ToolCallPart):
                            tool_calls.append({
                                "tool_name": part.tool_name,
                                "args": part.args,
                                "tool_call_id": part.tool_call_id
                            })
                    
                    # Extract tool outputs
                    for part in msg.parts:
                        if isinstance(part, ToolReturnPart):
                            tool_outputs.append({
                                "tool_name": part.tool_name,
                                "content": part.content,
                                "tool_call_id": part.tool_call_id
                            })
                    
                    # Add response if we have content
                    if content:
                        history.add_response(
                            content=content,
                            tool_calls=tool_calls if tool_calls else None,
                            tool_outputs=tool_outputs if tool_outputs else None
                        )
        
        return history
    
    @classmethod
    def from_json(cls, json_data: Union[str, bytes], session_id: Optional[str] = None) -> 'MessageHistory':
        """Create a MessageHistory from JSON data.
        
        Args:
            json_data: JSON string or bytes containing serialized messages
            session_id: Optional session ID to use, otherwise generates a new one
            
        Returns:
            New MessageHistory instance with the deserialized messages
        """
        try:
            from pydantic_ai.messages import ModelMessagesTypeAdapter
            messages = ModelMessagesTypeAdapter.validate_json(json_data)
            return cls.from_model_messages(messages, session_id)
        except Exception as e:
            logger.error(f"Error deserializing messages from JSON: {str(e)}")
            # Return an empty history with a new session
            return cls(session_id=session_id or str(uuid.uuid4()))
    
    def to_json(self) -> bytes:
        """Serialize all messages to JSON.
        
        Returns:
            JSON bytes representation of all messages
        """
        return self.all_messages_json()
    
    # Helper methods for converting between database and PydanticAI models
    
    def _convert_db_messages_to_model_messages(self, db_messages: List[Message], include_tools: bool = False) -> List[ModelMessage]:
        """Convert database messages to PydanticAI ModelMessage objects.
        
        Args:
            db_messages: List of database Message objects
            include_tools: Whether to include tool calls and tool outputs (default: False)
            
        Returns:
            List of PydanticAI ModelMessage objects
        """
        model_messages = []
        
        for db_message in db_messages:
            # Convert database message to ModelMessage
            if db_message.role == "system":
                # Create system message
                model_messages.append(
                    ModelRequest(parts=[SystemPromptPart(content=db_message.text_content or "")])
                )
            elif db_message.role == "user":
                # Create user message
                model_messages.append(
                    ModelRequest(parts=[UserPromptPart(content=db_message.text_content or "")])
                )
            elif db_message.role == "assistant":
                # Create assistant message with potential tool calls and outputs
                parts = [TextPart(content=db_message.text_content or "")]
                
                # Add tool calls if present and include_tools is True
                if include_tools and db_message.tool_calls:
                    tool_calls = db_message.tool_calls
                    if isinstance(tool_calls, dict):
                        for tc in tool_calls.values():
                            if isinstance(tc, dict) and "tool_name" in tc and "args" in tc:
                                parts.append(
                                    ToolCallPart(
                                        tool_name=tc["tool_name"],
                                        args=tc["args"],
                                        tool_call_id=tc.get("tool_call_id", "")
                                    )
                                )
                
                # Add tool outputs if present and include_tools is True
                if include_tools and db_message.tool_outputs:
                    tool_outputs = db_message.tool_outputs
                    if isinstance(tool_outputs, dict):
                        for to in tool_outputs.values():
                            if isinstance(to, dict) and "tool_name" in to and "content" in to:
                                parts.append(
                                    ToolReturnPart(
                                        tool_name=to["tool_name"],
                                        content=to["content"],
                                        tool_call_id=to.get("tool_call_id", "")
                                    )
                                )
                
                # Create and add assistant message
                model_messages.append(ModelResponse(parts=parts))
        
        return model_messages

    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current session.
        
        Returns:
            Dictionary with session information, or None if not found
        """
        try:
            # Get session from database
            session_uuid = uuid.UUID(self.session_id)
            session = get_session(session_uuid)
            
            if not session:
                return None
                
            # Convert session to dictionary
            return {
                "id": str(session.id),
                "name": session.name,
                "user_id": session.user_id,
                "agent_id": session.agent_id,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None
            }
        except Exception as e:
            logger.error(f"Error getting session info: {str(e)}")
            return None
            
    def get_messages(self, page: int = 1, page_size: int = 50, sort_desc: bool = True) -> Tuple[List[Dict[str, Any]], int]:
        """Get messages for the current session with pagination.
        
        Args:
            page: Page number to retrieve (1-indexed)
            page_size: Number of messages per page
            sort_desc: Whether to sort by descending creation time (newest first)
            
        Returns:
            Tuple of (list of messages, total message count)
        """
        try:
            # Validate pagination parameters
            page = max(1, page)  # Ensure page is at least 1
            page_size = max(1, min(page_size, 100))  # Between 1 and 100
            
            # Get messages from database
            session_uuid = uuid.UUID(self.session_id)
            messages_tuple = list_session_messages(
                session_uuid, 
                page=page,
                page_size=page_size,
                sort_desc=sort_desc
            )
            
            # Unpack the tuple from list_session_messages
            messages, total_count = messages_tuple
            
            # Convert database messages to dictionaries
            result = []
            for msg in messages:
                # Messages from list_session_messages are already dictionaries
                message_dict = {
                    "id": str(msg.get("id", "")),
                    "role": msg.get("role", ""),
                    "content": msg.get("text_content", ""),
                    "created_at": msg.get("created_at", "").isoformat() if msg.get("created_at") else None
                }
                
                # Add tool calls and outputs if present
                if msg.get("tool_calls"):
                    message_dict["tool_calls"] = msg["tool_calls"]
                
                if msg.get("tool_outputs"):
                    message_dict["tool_outputs"] = msg["tool_outputs"]
                    
                result.append(message_dict)
            
            return result, total_count
        except Exception as e:
            logger.error(f"Error getting messages: {str(e)}")
            return [], 0

    def delete_session(self) -> bool:
        """Delete the session and all its messages.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            from src.db.repository.session import delete_session
            from src.db.repository.message import delete_session_messages
            import uuid
            
            # Convert session_id to UUID
            session_uuid = uuid.UUID(self.session_id) if isinstance(self.session_id, str) else self.session_id
            
            # Delete all messages first
            delete_session_messages(session_uuid)
            
            # Then delete the session itself
            success = delete_session(session_uuid)
            
            return success
        except Exception as e:
            logger.error(f"Failed to delete session {self.session_id}: {str(e)}")
            return False
