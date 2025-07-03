"""Memory repository functions for database operations."""

import uuid
import json
import logging
from typing import List, Optional

from automagik.db.connection import execute_query
from automagik.db.models import Memory

# Configure logger
logger = logging.getLogger(__name__)


def get_memory(memory_id: uuid.UUID) -> Optional[Memory]:
    """Get a memory by ID.
    
    Args:
        memory_id: The memory ID
        
    Returns:
        Memory object if found, None otherwise
    """
    try:
        result = execute_query(
            """
            SELECT id, name, description, content, session_id, user_id, agent_id,
                   read_mode, access, metadata, created_at, updated_at
            FROM memories 
            WHERE id = %s
            """,
            (str(memory_id),)
        )
        return Memory.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting memory {memory_id}: {str(e)}")
        return None


def get_memory_by_name(name: str, agent_id: Optional[int] = None, 
                      user_id: Optional[uuid.UUID] = None, 
                      session_id: Optional[uuid.UUID] = None,
                      exact_user_match: bool = True) -> Optional[Memory]:
    """Get a memory by name with optional filters for agent, user, and session.
    
    Args:
        name: The memory name
        agent_id: Optional agent ID filter
        user_id: Optional user ID filter (UUID). If None and exact_user_match=True, will look for user_id IS NULL
        session_id: Optional session ID filter
        exact_user_match: If True, user_id=None will match records with user_id IS NULL. If False, user_id filter is ignored when None.
        
    Returns:
        Memory object if found, None otherwise
    """
    try:
        query = """
            SELECT id, name, description, content, session_id, user_id, agent_id,
                   read_mode, access, metadata, created_at, updated_at
            FROM memories 
            WHERE name = %s
        """
        params = [name]
        
        # Add optional filters
        if agent_id is not None:
            query += " AND agent_id = %s"
            params.append(agent_id)
        
        # Handle user_id filtering properly for agent global memory
        if exact_user_match:
            if user_id is not None:
                query += " AND user_id = %s"
                params.append(str(user_id) if isinstance(user_id, uuid.UUID) else user_id)
            else:
                # For agent global memory, explicitly look for NULL user_id
                query += " AND user_id IS NULL"
        else:
            # Legacy behavior: only filter if user_id is provided
            if user_id is not None:
                query += " AND user_id = %s"
                params.append(str(user_id) if isinstance(user_id, uuid.UUID) else user_id)
        
        if session_id is not None:
            query += " AND session_id = %s"
            params.append(str(session_id))
            
        query += " LIMIT 1"
        
        result = execute_query(query, params)
        return Memory.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting memory by name {name}: {str(e)}")
        return None


def list_memories(agent_id: Optional[int] = None, 
                 user_id: Optional[uuid.UUID] = None, 
                 session_id: Optional[uuid.UUID] = None,
                 read_mode: Optional[str] = None,
                 name_pattern: Optional[str] = None) -> List[Memory]:
    """List memories with optional filters.
    
    Args:
        agent_id: Optional agent ID filter
        user_id: Optional user ID filter (UUID)
        session_id: Optional session ID filter
        read_mode: Optional read mode filter
        name_pattern: Optional name pattern to match (using ILIKE)
        
    Returns:
        List of Memory objects
    """
    try:
        query = """
            SELECT id, name, description, content, session_id, user_id, agent_id,
                   read_mode, access, metadata, created_at, updated_at
            FROM memories 
            WHERE 1=1
        """
        params = []
        
        # Add optional filters
        if agent_id is not None:
            query += " AND agent_id = %s"
            params.append(agent_id)
        if user_id is not None:
            query += " AND user_id = %s"
            params.append(str(user_id) if isinstance(user_id, uuid.UUID) else user_id)
        if session_id is not None:
            query += " AND session_id = %s"
            params.append(str(session_id))
        if read_mode is not None:
            query += " AND read_mode = %s"
            params.append(read_mode)
        if name_pattern is not None:
            query += " AND name ILIKE %s"
            params.append(f"%{name_pattern}%")
            
        query += " ORDER BY name ASC"
        
        result = execute_query(query, params)
        return [Memory.from_db_row(row) for row in result] if result else []
    except Exception as e:
        logger.error(f"Error listing memories: {str(e)}")
        return []


def create_memory(memory: Memory) -> Optional[uuid.UUID]:
    """Create a new memory or update an existing one.
    
    Args:
        memory: The memory to create
        
    Returns:
        The memory ID if successful, None otherwise
    """
    try:
        # Add debug logging
        logger.info(f"Creating memory: name={memory.name}, user_id={memory.user_id}, agent_id={memory.agent_id}")
        
        # Check if a memory with this name already exists for the same context
        if memory.name:
            # Use the updated get_memory_by_name function with exact user matching
            existing_memory = get_memory_by_name(
                name=memory.name,
                agent_id=memory.agent_id,
                user_id=memory.user_id,
                session_id=memory.session_id,
                exact_user_match=True
            )
            
            if existing_memory:
                logger.info(f"Found existing memory with ID {existing_memory.id}, updating instead")
                # Update existing memory
                memory.id = existing_memory.id
                return update_memory(memory)
        
        # Generate a UUID for the memory if not provided
        if not memory.id:
            memory.id = uuid.uuid4()
            logger.debug(f"Generated new UUID for memory: {memory.id}")
        
        # Prepare memory data
        metadata_json = json.dumps(memory.metadata) if memory.metadata else None
        
        # Insert the memory
        logger.debug(f"Inserting new memory with ID {memory.id}")
        try:
            insert_query = """
                INSERT INTO memories (
                    id, name, description, content, session_id, user_id, agent_id,
                    read_mode, access, metadata, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, NOW(), NOW()
                ) RETURNING id
                """
            
            params = (
                str(memory.id),
                memory.name,
                memory.description,
                memory.content,
                str(memory.session_id) if memory.session_id else None,
                str(memory.user_id) if isinstance(memory.user_id, uuid.UUID) else memory.user_id,
                memory.agent_id,
                memory.read_mode,
                memory.access,
                metadata_json
            )
            
            logger.debug(f"Executing insert query with params: {params}")
            result = execute_query(insert_query, params)
            
            if not result:
                logger.error("Insert query returned no result")
                return None
                
            memory_id = uuid.UUID(result[0]["id"]) if result else None
            logger.info(f"Successfully created memory {memory.name} with ID {memory_id}")
            
            # Verify that the memory was actually created
            verification = execute_query("SELECT id FROM memories WHERE id = %s", (str(memory_id),))
            if not verification:
                logger.error(f"Memory verification failed: Memory with ID {memory_id} not found after creation")
            else:
                logger.debug(f"Memory verification successful: Memory with ID {memory_id} found in database")
                
            return memory_id
        except Exception as insert_error:
            logger.error(f"Database error during memory insertion: {str(insert_error)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    except Exception as e:
        logger.error(f"Error creating memory {getattr(memory, 'name', 'unknown')}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None


def update_memory(memory: Memory) -> Optional[uuid.UUID]:
    """Update an existing memory.
    
    Args:
        memory: The memory to update
        
    Returns:
        The updated memory ID if successful, None otherwise
    """
    try:
        if not memory.id:
            # Try to find by name and context using the updated function
            existing_memory = get_memory_by_name(
                name=memory.name,
                agent_id=memory.agent_id,
                user_id=memory.user_id,
                session_id=memory.session_id,
                exact_user_match=True
            )
            
            if existing_memory:
                memory.id = existing_memory.id
            else:
                return create_memory(memory)
        
        # Prepare memory data
        metadata_json = json.dumps(memory.metadata) if memory.metadata else None
        
        execute_query(
            """
            UPDATE memories SET 
                name = %s,
                description = %s,
                content = %s,
                session_id = %s,
                user_id = %s,
                agent_id = %s,
                read_mode = %s,
                access = %s,
                metadata = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                memory.name,
                memory.description,
                memory.content,
                str(memory.session_id) if memory.session_id else None,
                str(memory.user_id) if isinstance(memory.user_id, uuid.UUID) else memory.user_id,
                memory.agent_id,
                memory.read_mode,
                memory.access,
                metadata_json,
                str(memory.id)
            ),
            fetch=False
        )
        
        logger.info(f"Updated memory {memory.name} with ID {memory.id}")
        return memory.id
    except Exception as e:
        logger.error(f"Error updating memory {memory.id}: {str(e)}")
        return None


def delete_memory(memory_id: uuid.UUID) -> bool:
    """Delete a memory.
    
    Args:
        memory_id: The memory ID to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        execute_query(
            "DELETE FROM memories WHERE id = %s",
            (str(memory_id),),
            fetch=False
        )
        logger.info(f"Deleted memory with ID {memory_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting memory {memory_id}: {str(e)}")
        return False


def create_memories_bulk(memories: List[Memory]) -> int:
    """Create multiple memories in a single transaction with upsert behavior.
    
    Args:
        memories: List of Memory objects to create
        
    Returns:
        Number of memories successfully created/updated
    """
    if not memories:
        return 0
        
    try:
        # Prepare data for bulk insert
        values = []
        for memory in memories:
            # Generate UUID if not provided
            if not memory.id:
                memory.id = uuid.uuid4()
                
            metadata_json = json.dumps(memory.metadata) if memory.metadata else None
            
            values.append((
                str(memory.id),
                memory.name,
                memory.description,
                memory.content,
                str(memory.session_id) if memory.session_id else None,
                str(memory.user_id) if isinstance(memory.user_id, uuid.UUID) else memory.user_id,
                memory.agent_id,
                memory.read_mode,
                memory.access,
                metadata_json
            ))
        
        # Since there's no unique constraint, we'll use individual upsert approach
        # but in a more efficient way by checking existing memories first
        success_count = 0
        
        # First, check which memories already exist
        existing_memories = {}
        if values:
            # Get all existing memories for this user/agent combination
            user_id = values[0][5]  # user_id from first value tuple
            agent_id = values[0][6]  # agent_id from first value tuple
            
            logger.debug(f"Checking existing memories for user_id={user_id}, agent_id={agent_id}")
            
            if user_id is not None:
                existing_query = """
                    SELECT name, id FROM memories 
                    WHERE user_id = %s AND agent_id = %s
                """
                existing_result = execute_query(existing_query, (user_id, agent_id))
            else:
                # Handle case where user_id is None (agent global memories)
                existing_query = """
                    SELECT name, id FROM memories 
                    WHERE user_id IS NULL AND agent_id = %s
                """
                existing_result = execute_query(existing_query, (agent_id,))
            
            if existing_result:
                existing_memories = {row['name']: row['id'] for row in existing_result}
                logger.debug(f"Found {len(existing_memories)} existing memories")
        
        # Process each memory: update if exists, insert if new
        for memory_data in values:
            memory_id, name, description, content, session_id, user_id, agent_id, read_mode, access, metadata = memory_data
            
            try:
                if name in existing_memories:
                    # Update existing memory
                    update_query = """
                        UPDATE memories SET 
                            content = %s,
                            description = %s,
                            read_mode = %s,
                            access = %s,
                            metadata = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """
                    execute_query(
                        update_query, 
                        (content, description, read_mode, access, metadata, existing_memories[name]),
                        fetch=False
                    )
                    success_count += 1
                else:
                    # Insert new memory
                    insert_query = """
                        INSERT INTO memories (
                            id, name, description, content, session_id, user_id, agent_id,
                            read_mode, access, metadata, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """
                    execute_query(
                        insert_query, 
                        (memory_id, name, description, content, session_id, user_id, agent_id, read_mode, access, metadata),
                        fetch=False
                    )
                    success_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing memory '{name}': {str(e)}")
                continue
        
        logger.info(f"Bulk created/updated {success_count} memories")
        return success_count
        
    except Exception as e:
        logger.error(f"Error in bulk memory creation: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 0
