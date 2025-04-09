"""Memory tool implementation.

This module provides the core functionality for reading, creating,
and updating memories for agents.
"""
import logging
import json
import os
import requests
import uuid
from typing import Dict, Any, Optional, Union, List
from uuid import UUID
from datetime import datetime

from pydantic_ai import RunContext
from pydantic_ai.messages import ModelRequest
from src.db import get_agent_by_name, create_memory as create_memory_in_db
from src.db import list_memories as list_memories_in_db
from src.db import get_memory as get_memory_in_db
from src.db import update_memory as update_memory_in_db
from src.db.repository.memory import get_memory_by_name as db_get_memory_by_name
from src.db.repository.memory import create_memory as db_create_memory
from src.db.models import Memory as DBMemory
from src.agents.models.agent_factory import AgentFactory

from .schema import (
    ReadMemoryInput, CreateMemoryInput, UpdateMemoryInput,
    MemoryReadResult, MemoryCreateResponse, MemoryUpdateResponse,
    Memory
)
from .interface import invalidate_memory_cache, validate_memory_name, format_memory_content

logger = logging.getLogger(__name__)

def get_read_memory_description() -> str:
    """Basic description for the read_memory tool."""
    return "Read memories from the database by name or ID, or list all available memories."

def get_create_memory_description() -> str:
    """Basic description for the create_memory tool."""
    return "Create a new memory in the database with the specified name, content, and metadata."

def get_update_memory_description() -> str:
    """Basic description for the update_memory tool."""
    return "Update an existing memory in the database with new content or metadata."

# Create mock objects for the RunContext initialization
def _create_mock_context():
    """Create a mock context with the required parameters for RunContext."""
    # Create minimal mock objects to satisfy RunContext requirements
    model = {"name": "mock-model", "provider": "mock"}
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    prompt = ModelRequest(parts=[])
    
    return model, usage, prompt

def map_agent_id(ctx: Optional[RunContext], agent_id_raw: Optional[str] = None) -> tuple:
    """Map agent ID to numeric ID and get user/session context.
    
    Args:
        ctx: The run context.
        agent_id_raw: Optional raw agent ID string.
        
    Returns:
        Tuple of (agent_id, user_id, session_id)
    """
    # Default values
    agent_id = None
    user_id = 1  # Default user ID
    session_id = None
    
    # Try to extract from context first
    if ctx and hasattr(ctx, 'deps'):
        deps = ctx.deps
        
        # Try to get agent_id from deps
        if hasattr(deps, '_agent_id_numeric'):
            agent_id = deps._agent_id_numeric
        
        # Try to get user_id from deps
        if hasattr(deps, '_user_id'):
            user_id = deps._user_id
        
        # Try to get session_id from deps
        if hasattr(deps, '_session_id'):
            session_id = deps._session_id
    
    # If agent_id is still None, try agent_id_raw
    if agent_id is None and agent_id_raw:
        try:
            # Try to get agent by name from database
            agent = get_agent_by_name(agent_id_raw)
            if agent and hasattr(agent, 'id'):
                agent_id = agent.id
        except Exception as e:
            logger.warning(f"Could not get agent by name '{agent_id_raw}': {str(e)}")
            
    if agent_id is None and ctx and isinstance(ctx, dict):
        agent_id = ctx.get('agent_id')
        user_id = ctx.get('user_id')
        session_id = ctx.get('session_id')
        logger.info(f"Extracted agent_id={agent_id}, user_id={user_id}, session_id={session_id} from context dict")
    # If still no agent_id, try to use first available agent
    if agent_id is None:
        try:
            available_agents = AgentFactory.list_available_agents()
            if available_agents:
                agent = get_agent_by_name(available_agents[0])
                if agent and hasattr(agent, 'id'):
                    agent_id = agent.id
        except Exception as e:
            logger.warning(f"Could not get first available agent: {str(e)}")
    
    return agent_id, user_id, session_id

def _convert_to_memory_object(memory_dict: Dict[str, Any]) -> Memory:
    """Convert a memory dictionary to a Memory object.
    
    Args:
        memory_dict: Dictionary representation of a memory
        
    Returns:
        Memory object
    """
    # Copy only the fields we need for the Memory model
    memory_data = {
        "id": str(memory_dict.get("id", "")),
        "name": memory_dict.get("name", ""),
        "content": memory_dict.get("content", ""),
        "description": memory_dict.get("description", None),
        "read_mode": memory_dict.get("read_mode", "tool_calling"),
    }
    
    # Add metadata if available
    metadata = memory_dict.get("metadata", None)
    if metadata:
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                pass
        memory_data["metadata"] = metadata
    
    # Create Memory object
    return Memory(**memory_data)

# SimpleAgent compatibility functions
async def get_memory_tool(ctx: dict, key: str) -> str:
    """Retrieve a memory by key.
    
    Args:
        ctx: The context dictionary with agent and user information
        key: The memory key to retrieve
        
    Returns:
        The memory content as a string, or an error message if not found
    """
    logger.info(f"Getting memory with key: {key}")
    try:
        # Create a proper context with required parameters
        model, usage, prompt = _create_mock_context()
        run_ctx = RunContext({}, model=model, usage=usage, prompt=prompt)
        
        # Extract user_id from context
        user_id = ctx.get("user_id") if isinstance(ctx, dict) else None
        logger.info(f"Using user_id from context: {user_id}")
        
        # Try to get memory by name with user_id filter if provided
        memory = db_get_memory_by_name(name=key, user_id=user_id)
        if memory:
            content = memory.content
            if isinstance(content, dict):
                return str(content)
            return content
        
        # If not found with user_id, try without user_id filter
        if user_id is not None:
            memory = db_get_memory_by_name(name=key)
            if memory:
                logger.info(f"Found memory {key} without user_id filter")
                content = memory.content
                if isinstance(content, dict):
                    return str(content)
                return content
                
        return f"Memory with key '{key}' not found"
    except Exception as e:
        logger.error(f"Error getting memory: {str(e)}")
        return f"Error getting memory with key '{key}': {str(e)}"

async def store_memory_tool(key: str, content: str, ctx: dict = None) -> str:
    """Store a memory with the given key.
    
    Args:
        key: The key to store the memory under
        content: The memory content to store
        ctx: Optional context dictionary with agent and user information
        
    Returns:
        Confirmation message
    """
    logger.info(f"Storing memory with key: {key}")
    try:
        # Create a proper context with required parameters
        model, usage, prompt = _create_mock_context()
        run_ctx = RunContext({}, model=model, usage=usage, prompt=prompt)
        logger.info(f"Create memory context: {run_ctx}")
        
        # Create default context if not provided
        if ctx is None:
            ctx = {}
        
        # Extract agent_id and user_id from the provided context if available
        agent_id = ctx.get("agent_id", 1)  # Default agent ID
        user_id = ctx.get("user_id", None)  # Default to None, will look for thread context
        
        # If still no user_id, try the thread context
        if user_id is None:
            try:
                # Try to get thread context (if available)
                import threading
                from src.context import ThreadContext
                thread_context = getattr(threading.current_thread(), "_context", None)
                if thread_context and isinstance(thread_context, ThreadContext):
                    if hasattr(thread_context, "user_id") and thread_context.user_id:
                        user_id = thread_context.user_id
                        logger.info(f"Extracted user_id={user_id} from thread context")
            except Exception as e:
                logger.warning(f"Could not extract user/session from thread context: {str(e)}")
        
        # If still no user_id, try the current request context
        if user_id is None:
            try:
                # Try to get from global request state if available
                from src.context import get_current_user_id
                current_user_id = get_current_user_id()
                if current_user_id:
                    user_id = current_user_id
                    logger.info(f"Extracted user_id={user_id} from current request")
            except Exception as e:
                logger.warning(f"Could not extract user_id from request context: {str(e)}")
        
        # Fallback to default user_id if not found
        if user_id is None:
            user_id = 1
            logger.warning(f"Using default user_id={user_id}, could not extract from context")
        
        logger.info(f"Using values: agent_id={agent_id}, user_id={user_id}, session_id=None")
        
        # Check if this memory already exists and get its read_mode
        read_mode = "tool_calling"  # Default for new memories
        try:
            # Import the repository function
            from src.db.repository.memory import get_memory_by_name
            
            # Try to find existing memory with this key
            existing_memory = get_memory_by_name(name=key, agent_id=agent_id, user_id=user_id)
            
            if existing_memory:
                # If memory exists, preserve its read_mode
                read_mode = existing_memory.read_mode
                logger.info(f"Found existing memory with key '{key}', preserving read_mode='{read_mode}'")
        except Exception as e:
            logger.warning(f"Error checking for existing memory: {str(e)}, using default read_mode='tool_calling'")
        
        logger.info(f"Creating/updating memory: name={key}, read_mode={read_mode}")
        
        # Create Memory object
        memory = DBMemory(
            id=uuid.uuid4(),
            name=key,
            content=content,
            description=f"Memory created by Agent {agent_id}",
            agent_id=agent_id,
            user_id=user_id,
            read_mode=read_mode,  # Use preserved read_mode
            metadata={"created_at": str(datetime.now())}
        )
        
        # Store the memory
        memory_id = db_create_memory(memory)
        
        # Format response in a standard way to avoid OpenAI pydantic-ai issues
        if memory_id:
            result = f"Memory stored with key '{key}'"
            logger.info(result)
            return result
        else:
            result = f"Failed to store memory with key '{key}'"
            logger.error(result)
            return result
    except Exception as e:
        error_msg = f"Error storing memory with key '{key}': {str(e)}"
        logger.error(error_msg)
        return error_msg

async def list_memories_tool(prefix: Optional[str] = None) -> str:
    """List available memories, optionally filtered by prefix.
    
    Args:
        prefix: Optional prefix to filter memory keys
        
    Returns:
        List of memory keys as a string
    """
    try:
        logger.info(f"Listing memories with prefix: {prefix if prefix else 'all'}")
        
        # Get all memories
        memories = list_memories_in_db()
        
        # Filter by prefix if needed
        memory_names = []
        for memory in memories:
            if not prefix or memory.name.startswith(prefix):
                memory_names.append(memory.name)
        
        if not memory_names:
            result = "No memories found"
            logger.info(result)
            return result
        
        result = "\n".join(memory_names)
        logger.info(f"Found {len(memory_names)} memories")
        return result
    except Exception as e:
        error_msg = f"Error listing memories: {str(e)}"
        logger.error(error_msg)
        return error_msg

@invalidate_memory_cache
async def read_memory(ctx: RunContext[Dict], memory_id: Optional[str] = None, 
                name: Optional[str] = None, list_all: bool = False) -> Dict[str, Any]:
    """Read a memory from the database.
    
    Args:
        ctx: The run context.
        memory_id: Optional ID of the memory to read.
        name: Optional name of the memory to read.
        list_all: If True and no specific memory is requested, list all memories.
        
    Returns:
        Dict with memory content or error message.
    """
    try:
        # Map agent ID and get context
        agent_id, user_id, session_id = map_agent_id(ctx)
        
        # Log what we're doing
        if memory_id:
            logger.info(f"Reading memory by ID: {memory_id}")
        elif name:
            logger.info(f"Reading memory by name: {name}")
        elif list_all:
            logger.info(f"Listing all memories for agent {agent_id}")
        else:
            result = MemoryReadResult(
                success=False,
                message="Either memory_id, name, or list_all must be provided"
            ).dict()
            logger.info(f"Read memory result: {result}")
            return result
        
        # Log context
        logger.info(f"Context: agent_id={agent_id}, user_id={user_id}, session_id={session_id}")
        
        # If list_all is True, return all memories
        if list_all:
            try:
                # Use direct database call with proper parameter
                memories = list_memories_in_db(agent_id=agent_id, user_id=user_id)
                
                # Convert to Memory objects
                memory_objects = []
                for memory in memories:
                    if hasattr(memory, '__dict__'):
                        memory_dict = memory.__dict__
                        memory_objects.append(_convert_to_memory_object(memory_dict))
                
                # Return response
                result = MemoryReadResult(
                    success=True,
                    message=f"Found {len(memory_objects)} memories",
                    memories=memory_objects
                ).dict()
                logger.info(f"Read memory result: {result}")
                return result
            except Exception as e:
                logger.error(f"Error listing memories: {str(e)}")
                result = MemoryReadResult(
                    success=False,
                    message=f"Error listing memories: {str(e)}"
                ).dict()
                logger.info(f"Read memory result: {result}")
                return result
        
        # Try to read specific memory
        try:
            # Determine how to retrieve the memory
            if memory_id:
                # Get memory by ID
                memory = get_memory_in_db(memory_id=memory_id)
            elif name:
                # Get memory by name - ensure we use name_pattern parameter
                memories = list_memories_in_db(agent_id=agent_id, name_pattern=name, user_id=user_id)
                memory = memories[0] if memories else None
            else:
                memory = None
            
            # Check if memory was found
            if not memory:
                result = MemoryReadResult(
                    success=False,
                    message=f"Memory not found"
                ).dict()
                logger.info(f"Read memory result: {result}")
                return result
            
            # Convert to Memory object
            memory_obj = _convert_to_memory_object(memory.__dict__)
            
            # Return response
            result = MemoryReadResult(
                success=True,
                message="Memory found",
                content=memory_obj.content,
                memory=memory_obj
            ).dict()
            logger.info(f"Read memory result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error reading memory: {str(e)}")
            result = MemoryReadResult(
                success=False,
                message=f"Error reading memory: {str(e)}"
            ).dict()
            logger.info(f"Read memory result: {result}")
            return result
    except Exception as e:
        logger.error(f"Error in read_memory: {str(e)}")
        result = MemoryReadResult(
            success=False,
            message=f"Error in read_memory: {str(e)}"
        ).dict()
        logger.info(f"Read memory result: {result}")
        return result

@invalidate_memory_cache
async def create_memory(ctx: RunContext[Dict], name: str, content: Union[str, Dict[str, Any]], 
                 description: Optional[str] = None, read_mode: str = "tool_calling",
                 scope: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a new memory in the database.
    
    Args:
        ctx: The run context.
        name: The name of the memory to create.
        content: The content to store in the memory.
        description: Optional description of the memory.
        read_mode: How this memory should be used.
        scope: Optional scope of the memory.
        metadata: Optional metadata to store with the memory.
        
    Returns:
        Dict with the result of the operation.
    """
    try:
        # Validate name
        if not validate_memory_name(name):
            return MemoryCreateResponse(
                success=False,
                message=f"Invalid memory name: {name}. Names must contain only letters, numbers, and underscores."
            ).dict()
        
        # Map agent ID and get context
        agent_id, user_id, session_id = map_agent_id(ctx)
        
        # Log what we're doing
        logger.info(f"Creating memory: name={name}, scope={scope}, read_mode={read_mode}")
        logger.info(f"Context: agent_id={agent_id}, user_id={user_id}, session_id={session_id}")
        
        # Format content
        processed_content = format_memory_content(content)
        
        # Determine the scope of the memory
        if scope == "global":
            # Global memories are accessible to all users of this agent
            memory_user_id = None
            memory_session_id = None
        elif scope == "user":
            # User memories are accessible to a specific user across all sessions
            memory_user_id = user_id
            memory_session_id = None
        elif scope == "session":
            # Session memories are accessible only in the current session
            memory_user_id = user_id
            memory_session_id = session_id
        else:
            # Default to user scope if not specified
            memory_user_id = user_id
            memory_session_id = None
        
        # Create the memory
        try:
            # Use direct database call
            memory_data = {
                "name": name,
                "content": processed_content,
                "agent_id": agent_id,
                "user_id": memory_user_id,
                "session_id": memory_session_id,
                "read_mode": read_mode,
                "description": description
            }
            
            # Add metadata if provided
            if metadata is not None:
                if isinstance(metadata, dict):
                    memory_data["metadata"] = json.dumps(metadata)
                else:
                    memory_data["metadata"] = metadata
            
            # Create memory in database
            memory = create_memory_in_db(**memory_data)
            
            # Check if memory was created
            if not memory or not hasattr(memory, 'id'):
                return MemoryCreateResponse(
                    success=False,
                    message="Memory creation failed"
                ).dict()
            
            # Return success response
            return MemoryCreateResponse(
                success=True,
                message="Memory created successfully",
                id=str(memory.id),
                name=memory.name
            ).dict()
        except Exception as e:
            logger.error(f"Error creating memory: {str(e)}")
            return MemoryCreateResponse(
                success=False,
                message=f"Error creating memory: {str(e)}"
            ).dict()
    except Exception as e:
        logger.error(f"Error in create_memory: {str(e)}")
        return MemoryCreateResponse(
            success=False,
            message=f"Error in create_memory: {str(e)}"
        ).dict()

@invalidate_memory_cache
async def update_memory(ctx: RunContext[Dict], content: Union[str, Dict[str, Any]], 
                 memory_id: Optional[str] = None, name: Optional[str] = None,
                 description: Optional[str] = None) -> Dict[str, Any]:
    """Update an existing memory in the database.
    
    Args:
        ctx: The run context.
        content: The new content for the memory.
        memory_id: The ID of the memory to update.
        name: The name of the memory to update.
        description: Optional new description for the memory.
        
    Returns:
        Dict with the result of the operation.
    """
    try:
        # Map agent ID and get context
        agent_id, user_id, session_id = map_agent_id(ctx)
        
        # Log what we're doing
        if memory_id:
            logger.info(f"Updating memory by ID: {memory_id}")
        elif name:
            logger.info(f"Updating memory by name: {name}")
        else:
            return MemoryUpdateResponse(
                success=False,
                message="Either memory_id or name must be provided"
            ).dict()
        
        # Log context
        logger.info(f"Context: agent_id={agent_id}, user_id={user_id}, session_id={session_id}")
        
        # Format content
        processed_content = format_memory_content(content)
        
        # Determine which memory to update
        try:
            if memory_id:
                # Get memory by ID first to make sure it exists
                memory = get_memory_in_db(memory_id=memory_id)
                if not memory:
                    return MemoryUpdateResponse(
                        success=False,
                        message=f"Memory with ID {memory_id} not found"
                    ).dict()
                
                # Update memory
                update_data = {"content": processed_content}
                if description is not None:
                    update_data["description"] = description
                if name is not None:
                    update_data["name"] = name
                
                # Update memory in database
                updated_memory = update_memory_in_db(memory_id=memory_id, **update_data)
                
                # Return response
                return MemoryUpdateResponse(
                    success=True,
                    message="Memory updated successfully",
                    id=str(updated_memory.id),
                    name=updated_memory.name
                ).dict()
            elif name:
                # Find memory by name
                memories = list_memories_in_db(agent_id=agent_id, name_pattern=name)
                if not memories:
                    return MemoryUpdateResponse(
                        success=False,
                        message=f"Memory with name {name} not found"
                    ).dict()
                
                # Use the first matching memory
                memory = memories[0]
                
                # Update memory
                update_data = {"content": processed_content}
                if description is not None:
                    update_data["description"] = description
                
                # Update memory in database
                updated_memory = update_memory_in_db(memory_id=str(memory.id), **update_data)
                
                # Return response
                return MemoryUpdateResponse(
                    success=True,
                    message="Memory updated successfully",
                    id=str(updated_memory.id),
                    name=updated_memory.name
                ).dict()
        except Exception as e:
            logger.error(f"Error updating memory: {str(e)}")
            return MemoryUpdateResponse(
                success=False,
                message=f"Error updating memory: {str(e)}"
            ).dict()
    except Exception as e:
        logger.error(f"Error in update_memory: {str(e)}")
        return MemoryUpdateResponse(
            success=False,
            message=f"Error in update_memory: {str(e)}"
        ).dict() 