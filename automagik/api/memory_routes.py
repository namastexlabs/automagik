import logging
import math
import uuid
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List

from automagik.api.memory_models import (
    MemoryCreate,
    MemoryUpdate,
    MemoryResponse,
    MemoryListResponse
)
from automagik.db import (
    Memory, 
    get_memory, 
    create_memory as repo_create_memory,
    update_memory as repo_update_memory,
    list_memories as repo_list_memories,
    delete_memory as repo_delete_memory,
    get_user,
    User,
    create_user
)

# Create API router for memory endpoints
memory_router = APIRouter()

# Get our module's logger
logger = logging.getLogger(__name__)

# Utility function to ensure user exists without requiring MessageHistory
def ensure_user_exists(user_id: Optional[UUID]) -> Optional[UUID]:
    """
    Ensures a user exists in the database before performing operations.
    If the user doesn't exist, it creates a minimal user record.
    
    Args:
        user_id: The user ID to check/create
        
    Returns:
        The same user_id if provided, or None if not
    """
    if not user_id:
        return None
        
    try:
        # Check if user exists
        user = get_user(user_id)
        if not user:
            # Create minimal user with just the ID
            from datetime import datetime
            user = User(
                id=user_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            created_id = create_user(user)
            if created_id:
                logger.info(f"Auto-created user with ID {user_id} for memory operations")
                return created_id
            else:
                logger.warning(f"Failed to auto-create user with ID {user_id}")
        return user_id
    except Exception as e:
        logger.error(f"Error ensuring user exists: {str(e)}")
        return user_id  # Return the original ID anyway to not break existing code

# Validate UUID helper function (duplicated from routes.py for modularity)
def is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID.
    
    Args:
        value: The string to check
        
    Returns:
        True if the string is a valid UUID, False otherwise
    """
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False

@memory_router.get("/memories", response_model=MemoryListResponse, tags=["Memories"],
            summary="List Memories",
            description="List all memories with optional filters and pagination.")
async def list_memories(
    user_id: Optional[str] = Query(None, description="Filter by user ID (UUID)"),
    agent_id: Optional[int] = Query(None, description="Filter by agent ID"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    page: int = Query(1, description="Page number (1-based)"),
    page_size: int = Query(50, description="Number of memories per page"),
    sort_desc: bool = Query(True, description="Sort by most recent first if True")
):
    # Validate and parse session_id as UUID if provided
    session_uuid = None
    if session_id:
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid session_id format: {session_id}")
    
    # Convert user_id to UUID if provided
    user_uuid = None
    if user_id:
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid user_id format: {user_id}")
    
    # Use the repository pattern to list memories
    memories = repo_list_memories(
        agent_id=agent_id,
        user_id=user_uuid,
        session_id=session_uuid
    )
    
    # Total number of memories
    total_count = len(memories)
    
    # Calculate total pages
    total_pages = math.ceil(total_count / page_size)
    
    # Apply sorting
    if sort_desc:
        memories.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
    else:
        memories.sort(key=lambda x: x.created_at or datetime.min)
    
    # Apply pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_memories = memories[start_idx:end_idx]
    
    # Convert to response format
    memory_responses = []
    for memory in paginated_memories:
        memory_responses.append({
            "id": str(memory.id),
            "name": memory.name,
            "description": memory.description,
            "content": memory.content,
            "session_id": str(memory.session_id) if memory.session_id else None,
            "user_id": memory.user_id,
            "agent_id": memory.agent_id,
            "read_mode": memory.read_mode,
            "access": memory.access,
            "metadata": memory.metadata,
            "created_at": memory.created_at,
            "updated_at": memory.updated_at
        })
    
    return {
        "memories": memory_responses,
        "count": total_count,
        "page": page,
        "page_size": page_size,
        "pages": total_pages
    }

@memory_router.post("/memories", response_model=MemoryResponse, tags=["Memories"],
             summary="Create Memory",
             description="Create a new memory with the provided details.")
async def create_memory(memory: MemoryCreate):
    try:
        # Validate memory creation requirements for agent global memory
        if not memory.user_id and not memory.agent_id:
            raise HTTPException(
                status_code=400, 
                detail="agent_id is required when user_id is not provided (for agent global memory)"
            )
        
        # Convert session_id to UUID if provided
        session_uuid = None
        if memory.session_id:
            try:
                session_uuid = uuid.UUID(memory.session_id)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid session_id format: {memory.session_id}")
                
        # Ensure user exists before creating the memory (auto-create if needed)
        if memory.user_id:
            # Use our direct utility function instead of MessageHistory
            memory.user_id = ensure_user_exists(memory.user_id)
        
        # Create a Memory model for the repository
        memory_model = Memory(
            id=None,  # Will be generated
            name=memory.name,
            description=memory.description,
            content=memory.content,
            session_id=session_uuid,
            user_id=memory.user_id,  # Already UUID from Pydantic model
            agent_id=memory.agent_id,
            read_mode=memory.read_mode,
            access=memory.access,
            metadata=memory.metadata,
            created_at=None,  # Will be set by DB
            updated_at=None   # Will be set by DB
        )
        
        # Create the memory using the repository
        memory_id = repo_create_memory(memory_model)
        
        if memory_id is None:
            raise HTTPException(status_code=500, detail="Failed to create memory")
        
        # Retrieve the created memory to get all fields
        created_memory = get_memory(memory_id)
        
        if not created_memory:
            raise HTTPException(status_code=404, detail=f"Memory created but not found with ID {memory_id}")
        
        # Convert to response format
        return {
            "id": str(created_memory.id),
            "name": created_memory.name,
            "description": created_memory.description,
            "content": created_memory.content,
            "session_id": str(created_memory.session_id) if created_memory.session_id else None,
            "user_id": created_memory.user_id,
            "agent_id": created_memory.agent_id,
            "read_mode": created_memory.read_mode,
            "access": created_memory.access,
            "metadata": created_memory.metadata,
            "created_at": created_memory.created_at,
            "updated_at": created_memory.updated_at
        }
    except HTTPException:
        raise  # Re-raise HTTPExceptions as-is (with their original status codes)
    except Exception as e:
        logger.error(f"Error creating memory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating memory: {str(e)}")

@memory_router.post("/memories/batch", response_model=List[MemoryResponse], tags=["Memories"],
             summary="Create Multiple Memories",
             description="Create multiple memories in a single batch operation.")
async def create_memories_batch(memories: List[MemoryCreate]):
    try:
        results = []
        success_count = 0
        error_count = 0
        
        for memory in memories:
            try:
                # Validate memory creation requirements for agent global memory
                if not memory.user_id and not memory.agent_id:
                    raise HTTPException(
                        status_code=400,
                        detail="agent_id is required when user_id is not provided (for agent global memory)"
                    )
                
                # Convert session_id to UUID if provided
                session_uuid = None
                if memory.session_id:
                    try:
                        session_uuid = uuid.UUID(memory.session_id)
                    except ValueError:
                        logger.warning(f"Invalid session_id format in batch: {memory.session_id}")
                        error_count += 1
                        continue
                
                # Ensure user exists before creating the memory (auto-create if needed)
                if memory.user_id:
                    # Use our direct utility function instead of MessageHistory
                    memory.user_id = ensure_user_exists(memory.user_id)
                
                # Create a Memory model for the repository
                memory_model = Memory(
                    id=None,  # Will be generated
                    name=memory.name,
                    description=memory.description,
                    content=memory.content,
                    session_id=session_uuid,
                    user_id=memory.user_id,  # Already UUID from Pydantic model
                    agent_id=memory.agent_id,
                    read_mode=memory.read_mode,
                    access=memory.access,
                    metadata=memory.metadata,
                    created_at=None,  # Will be set by DB
                    updated_at=None   # Will be set by DB
                )
                
                # Create the memory using the repository
                memory_id = repo_create_memory(memory_model)
                
                if memory_id is None:
                    logger.warning(f"Failed to create memory in batch: {memory.name}")
                    error_count += 1
                    continue
                
                # Retrieve the created memory to get all fields
                created_memory = get_memory(memory_id)
                
                if not created_memory:
                    logger.warning(f"Memory created but not found with ID {memory_id}")
                    error_count += 1
                    continue
                
                # Add to results
                success_count += 1
                results.append(MemoryResponse(
                    id=str(created_memory.id),
                    name=created_memory.name,
                    description=created_memory.description,
                    content=created_memory.content,
                    session_id=str(created_memory.session_id) if created_memory.session_id else None,
                    user_id=created_memory.user_id,
                    agent_id=created_memory.agent_id,
                    read_mode=created_memory.read_mode,
                    access=created_memory.access,
                    metadata=created_memory.metadata,
                    created_at=created_memory.created_at,
                    updated_at=created_memory.updated_at
                ))
            except Exception as e:
                # Log error but continue with other memories
                logger.error(f"Error creating memory in batch: {str(e)}")
                error_count += 1
                continue
        
        # Log a summary of the operation
        logger.info(f"Batch memory creation complete: {success_count} succeeded, {error_count} failed")
        
        # Return all successfully created memories
        return results
    except HTTPException:
        raise  # Re-raise HTTPExceptions as-is (with their original status codes)
    except Exception as e:
        logger.error(f"Error creating memories in batch: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating memories in batch: {str(e)}")

@memory_router.get("/memories/{memory_id}", response_model=MemoryResponse, tags=["Memories"],
            summary="Get Memory",
            description="Get a memory by its ID.")
async def get_memory_endpoint(memory_id: str = Path(..., description="The memory ID")):
    try:
        # Validate UUID format
        try:
            uuid_obj = uuid.UUID(memory_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid memory ID format: {memory_id}")
        
        # Query the database using the repository function
        # The repository get_memory function is synchronous, so no need to await
        memory = get_memory(uuid_obj)
        
        if not memory:
            raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")
        
        # Return the memory response
        return MemoryResponse(
            id=str(memory.id),
            name=memory.name,
            description=memory.description,
            content=memory.content,
            session_id=str(memory.session_id) if memory.session_id else None,
            user_id=memory.user_id,
            agent_id=memory.agent_id,
            read_mode=memory.read_mode,
            access=memory.access,
            metadata=memory.metadata,
            created_at=memory.created_at,
            updated_at=memory.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving memory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving memory: {str(e)}")

@memory_router.put("/memories/{memory_id}", response_model=MemoryResponse, tags=["Memories"],
            summary="Update Memory",
            description="Update an existing memory with the provided details.")
async def update_memory_endpoint(
    memory_update: MemoryUpdate,
    memory_id: str = Path(..., description="The memory ID")
):
    try:
        # Validate UUID format
        try:
            uuid_obj = uuid.UUID(memory_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid memory ID format: {memory_id}")
        
        # Check if memory exists using repository function
        existing_memory = get_memory(uuid_obj)
        
        if not existing_memory:
            raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")
        
        # Determine final values after update - use model_dump to distinguish between None and not provided
        update_dict = memory_update.model_dump(exclude_unset=True)
        final_user_id = update_dict.get('user_id', existing_memory.user_id)
        final_agent_id = update_dict.get('agent_id', existing_memory.agent_id)
        
        # Validate the update doesn't create invalid state (both user_id and agent_id as None)
        if not final_user_id and not final_agent_id:
            raise HTTPException(
                status_code=400, 
                detail="agent_id is required when user_id is not provided (for agent global memory)"
            )
        
        # Update existing memory with new values - only update fields that were explicitly provided
        if 'name' in update_dict:
            existing_memory.name = update_dict['name']
            
        if 'description' in update_dict:
            existing_memory.description = update_dict['description']
            
        if 'content' in update_dict:
            existing_memory.content = update_dict['content']
            
        if 'session_id' in update_dict:
            session_value = update_dict['session_id']
            if session_value is None:
                existing_memory.session_id = None
            else:
                try:
                    if isinstance(session_value, str):
                        existing_memory.session_id = uuid.UUID(session_value)
                    else:
                        existing_memory.session_id = session_value
                except ValueError:
                    # If not a valid UUID, store as None
                    existing_memory.session_id = None
                
        if 'user_id' in update_dict:
            existing_memory.user_id = update_dict['user_id']
            
        if 'agent_id' in update_dict:
            existing_memory.agent_id = update_dict['agent_id']
            
        if 'read_mode' in update_dict:
            existing_memory.read_mode = update_dict['read_mode']
            
        if 'access' in update_dict:
            existing_memory.access = update_dict['access']
            
        if 'metadata' in update_dict:
            existing_memory.metadata = update_dict['metadata']
        
        # Update the memory using repository function
        updated_memory_id = repo_update_memory(existing_memory)
        
        if not updated_memory_id:
            raise HTTPException(status_code=500, detail="Failed to update memory")
        
        # Get the updated memory
        updated_memory = get_memory(uuid_obj)
        
        # Return the updated memory
        return MemoryResponse(
            id=str(updated_memory.id),
            name=updated_memory.name,
            description=updated_memory.description,
            content=updated_memory.content,
            session_id=str(updated_memory.session_id) if updated_memory.session_id else None,
            user_id=updated_memory.user_id,
            agent_id=updated_memory.agent_id,
            read_mode=updated_memory.read_mode,
            access=updated_memory.access,
            metadata=updated_memory.metadata,
            created_at=updated_memory.created_at,
            updated_at=updated_memory.updated_at
        )
    except HTTPException:
        raise  # Re-raise HTTPExceptions as-is (with their original status codes)
    except Exception as e:
        logger.error(f"Error updating memory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating memory: {str(e)}")

@memory_router.delete("/memories/{memory_id}", response_model=MemoryResponse, tags=["Memories"],
               summary="Delete Memory",
               description="Delete a memory by its ID.")
async def delete_memory_endpoint(memory_id: str = Path(..., description="The memory ID")):
    try:
        # Validate UUID format
        try:
            uuid_obj = uuid.UUID(memory_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid memory ID format: {memory_id}")
        
        # Get the memory for response before deletion
        existing_memory = get_memory(uuid_obj)
        
        if not existing_memory:
            raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")
        
        # Create memory response before deletion
        memory_response = MemoryResponse(
            id=str(existing_memory.id),
            name=existing_memory.name,
            description=existing_memory.description,
            content=existing_memory.content,
            session_id=str(existing_memory.session_id) if existing_memory.session_id else None,
            user_id=existing_memory.user_id,
            agent_id=existing_memory.agent_id,
            read_mode=existing_memory.read_mode,
            access=existing_memory.access,
            metadata=existing_memory.metadata,
            created_at=existing_memory.created_at,
            updated_at=existing_memory.updated_at
        )
        
        # Delete the memory using repository function
        success = repo_delete_memory(uuid_obj)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete memory")
        
        # Return the deleted memory details
        return memory_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting memory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting memory: {str(e)}")
