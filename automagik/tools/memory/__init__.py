"""Memory tools for Automagik Agents.

Provides tools for reading and writing memories for agents, implementing the pydantic-ai tool interface.
These tools allow agents to store and retrieve information across conversations and sessions.
"""

# Import core functionality
from automagik.tools.memory.tool import (
    read_memory,
    create_memory,
    update_memory,
    get_read_memory_description,
    get_create_memory_description,
    get_update_memory_description,
    # SimpleAgent compatibility functions
    get_memory_tool,
    store_memory_tool,
    list_memories_tool
)

# Import schemas
from automagik.tools.memory.schema import (
    MemoryReadResult,
    MemoryCreateResponse,
    MemoryUpdateResponse,
    Memory,
    ReadMemoryInput,
    CreateMemoryInput,
    UpdateMemoryInput
)

# Import utility functions
from automagik.tools.memory.interface import (
    invalidate_memory_cache,
    validate_memory_name,
    format_memory_content
)

# Import provider
from automagik.tools.memory.provider import (
    MemoryProvider,
    get_memory_provider_for_agent
)

# For backwards compatibility (to be removed in future versions)
def write_memory(*args, **kwargs):
    """Deprecated: Use create_memory or update_memory instead.
    
    This function is maintained for backward compatibility only.
    It will decide whether to create or update a memory based on the presence of memory_id.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("write_memory is deprecated - use create_memory or update_memory instead")
    
    # Check if memory_id exists in kwargs
    if 'memory_id' in kwargs and kwargs['memory_id'] is not None:
        # Update existing memory
        # Re-map parameters to match update_memory's signature
        # update_memory expects: content, memory_id, name
        if len(args) >= 3:
            return update_memory(args[0], args[2], memory_id=kwargs.get('memory_id'))
        else:
            return update_memory(kwargs.get('ctx'), kwargs.get('content', ''), 
                             memory_id=kwargs.get('memory_id'))
    else:
        # Create new memory
        # create_memory expects: ctx, name, content, description, read_mode, access, metadata
        return create_memory(*args, **kwargs)

# Expose only these functions at the package level
__all__ = [
    # Core memory functions
    'read_memory',
    'create_memory',
    'update_memory',
    'write_memory',  # For backwards compatibility
    
    # Description functions
    'get_read_memory_description',
    'get_create_memory_description',
    'get_update_memory_description',
    
    # SimpleAgent compatibility functions
    'get_memory_tool',
    'store_memory_tool', 
    'list_memories_tool',
    
    # Schemas
    'MemoryReadResult',
    'MemoryCreateResponse',
    'MemoryUpdateResponse',
    'Memory',
    'ReadMemoryInput',
    'CreateMemoryInput',
    'UpdateMemoryInput',
    
    # Utilities
    'invalidate_memory_cache',
    'validate_memory_name',
    'format_memory_content',
    'MemoryProvider',
    'get_memory_provider_for_agent'
] 