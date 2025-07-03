"""Prompt repository functions for database operations."""

import logging
from typing import List, Optional

from automagik.db.connection import execute_query
from automagik.db.models import Prompt, PromptCreate, PromptUpdate

# Configure logger
logger = logging.getLogger(__name__)


def get_prompt_by_id(prompt_id: int) -> Optional[Prompt]:
    """Get a prompt by ID.
    
    Args:
        prompt_id: The prompt ID
        
    Returns:
        Prompt object if found, None otherwise
    """
    try:
        result = execute_query(
            "SELECT * FROM prompts WHERE id = %s",
            (prompt_id,)
        )
        return Prompt.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting prompt {prompt_id}: {str(e)}")
        return None


def get_active_prompt(agent_id: int, status_key: str = "default") -> Optional[Prompt]:
    """Get the active prompt for an agent and status key.
    
    Args:
        agent_id: The agent ID
        status_key: The status key to look for (default: "default")
        
    Returns:
        Active Prompt object if found, None otherwise
    """
    try:
        result = execute_query(
            """
            SELECT * FROM prompts 
            WHERE agent_id = %s AND status_key = %s AND is_active = TRUE
            LIMIT 1
            """,
            (agent_id, status_key)
        )
        return Prompt.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting active prompt for agent {agent_id}, status {status_key}: {str(e)}")
        return None


def find_code_default_prompt(agent_id: int, status_key: str = "default") -> Optional[Prompt]:
    """Find the default prompt from code for an agent and status key.
    
    Args:
        agent_id: The agent ID
        status_key: The status key to look for (default: "default")
        
    Returns:
        Prompt object marked as default from code if found, None otherwise
    """
    try:
        result = execute_query(
            """
            SELECT * FROM prompts 
            WHERE agent_id = %s AND status_key = %s AND is_default_from_code = TRUE
            ORDER BY version DESC LIMIT 1
            """,
            (agent_id, status_key)
        )
        return Prompt.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error finding code default prompt for agent {agent_id}, status {status_key}: {str(e)}")
        return None


def get_latest_version_for_status(agent_id: int, status_key: str = "default") -> int:
    """Get the latest version number for a prompt with given agent ID and status key.
    
    Args:
        agent_id: The agent ID
        status_key: The status key to look for (default: "default")
        
    Returns:
        Latest version number, or 0 if no prompts exist yet
    """
    try:
        result = execute_query(
            """
            SELECT MAX(version) as max_version FROM prompts 
            WHERE agent_id = %s AND status_key = %s
            """,
            (agent_id, status_key)
        )
        return result[0]["max_version"] if result and result[0]["max_version"] is not None else 0
    except Exception as e:
        logger.error(f"Error getting latest version for agent {agent_id}, status {status_key}: {str(e)}")
        return 0


def create_prompt(prompt_data: PromptCreate) -> Optional[int]:
    """Create a new prompt.
    
    Args:
        prompt_data: The PromptCreate object with prompt data
        
    Returns:
        The created prompt ID if successful, None otherwise
    """
    try:
        # Get the latest version and increment
        if prompt_data.version == 1:  # If not explicitly set to another value
            latest_version = get_latest_version_for_status(
                prompt_data.agent_id, prompt_data.status_key
            )
            prompt_data.version = latest_version + 1
        
        # If this prompt is being set as active, deactivate other prompts with the same agent_id and status_key
        if prompt_data.is_active:
            execute_query(
                """
                UPDATE prompts SET is_active = FALSE, updated_at = NOW()
                WHERE agent_id = %s AND status_key = %s AND is_active = TRUE
                """,
                (prompt_data.agent_id, prompt_data.status_key),
                fetch=False
            )
        
        # Insert the new prompt
        result = execute_query(
            """
            INSERT INTO prompts (
                agent_id, prompt_text, version, is_active, 
                is_default_from_code, status_key, name,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, 
                %s, %s, %s,
                NOW(), NOW()
            ) RETURNING id
            """,
            (
                prompt_data.agent_id,
                prompt_data.prompt_text,
                prompt_data.version,
                prompt_data.is_active,
                prompt_data.is_default_from_code,
                prompt_data.status_key,
                prompt_data.name
            )
        )
        
        prompt_id = result[0]["id"] if result else None
        
        # If this is the active prompt for the default status, update the agent's active_default_prompt_id
        if prompt_data.is_active and prompt_data.status_key == "default":
            execute_query(
                """
                UPDATE agents SET 
                    active_default_prompt_id = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (prompt_id, prompt_data.agent_id),
                fetch=False
            )
            logger.info(f"Updated agent {prompt_data.agent_id} with active_default_prompt_id {prompt_id}")
        
        logger.info(f"Created prompt for agent {prompt_data.agent_id}, status {prompt_data.status_key}, version {prompt_data.version} with ID {prompt_id}")
        return prompt_id
    except Exception as e:
        logger.error(f"Error creating prompt for agent {prompt_data.agent_id}, status {prompt_data.status_key}: {str(e)}")
        return None


def update_prompt(prompt_id: int, update_data: PromptUpdate) -> bool:
    """Update an existing prompt.
    
    Args:
        prompt_id: The ID of the prompt to update
        update_data: The PromptUpdate object with fields to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Construct SET clause dynamically based on provided fields
        set_parts = []
        params = []
        
        if update_data.prompt_text is not None:
            set_parts.append("prompt_text = %s")
            params.append(update_data.prompt_text)
            
        if update_data.name is not None:
            set_parts.append("name = %s")
            params.append(update_data.name)
            
        # Always update the updated_at timestamp
        set_parts.append("updated_at = NOW()")
        
        # Don't process is_active here as it requires special handling
        
        # If nothing to update, return early
        if not set_parts:
            return True
            
        # Build and execute the update query
        query = f"""
            UPDATE prompts SET {', '.join(set_parts)}
            WHERE id = %s
        """
        params.append(prompt_id)
        
        execute_query(query, tuple(params), fetch=False)
        
        # Handle is_active separately if it was provided
        if update_data.is_active is not None:
            return set_prompt_active(prompt_id, update_data.is_active)
            
        logger.info(f"Updated prompt {prompt_id}")
        return True
    except Exception as e:
        logger.error(f"Error updating prompt {prompt_id}: {str(e)}")
        return False


def set_prompt_active(prompt_id: int, is_active: bool = True) -> bool:
    """Set a prompt as active or inactive.
    
    If setting to active, this will deactivate all other prompts for the same agent and status key.
    
    Args:
        prompt_id: The ID of the prompt to update
        is_active: Whether to set as active (True) or inactive (False)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get the prompt to get its agent_id and status_key
        prompt = get_prompt_by_id(prompt_id)
        if not prompt:
            logger.error(f"Cannot set active status for non-existent prompt {prompt_id}")
            return False
            
        if is_active:
            # First, deactivate all other prompts for this agent and status key
            execute_query(
                """
                UPDATE prompts SET 
                    is_active = FALSE, 
                    updated_at = NOW()
                WHERE agent_id = %s AND status_key = %s AND id != %s
                """,
                (prompt.agent_id, prompt.status_key, prompt_id),
                fetch=False
            )
            
            # Then activate this prompt
            execute_query(
                """
                UPDATE prompts SET 
                    is_active = TRUE, 
                    updated_at = NOW()
                WHERE id = %s
                """,
                (prompt_id,),
                fetch=False
            )
            
            # If this is a default status prompt, update the agent's active_default_prompt_id
            if prompt.status_key == "default":
                execute_query(
                    """
                    UPDATE agents SET 
                        active_default_prompt_id = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (prompt_id, prompt.agent_id),
                    fetch=False
                )
                logger.info(f"Updated agent {prompt.agent_id} with active_default_prompt_id {prompt_id}")
                
            logger.info(f"Set prompt {prompt_id} as active for agent {prompt.agent_id}, status {prompt.status_key}")
        else:
            # Just deactivate this prompt
            execute_query(
                """
                UPDATE prompts SET 
                    is_active = FALSE, 
                    updated_at = NOW()
                WHERE id = %s
                """,
                (prompt_id,),
                fetch=False
            )
            
            # If this is a default status prompt and was active, clear the agent's active_default_prompt_id
            if prompt.status_key == "default" and prompt.is_active:
                execute_query(
                    """
                    UPDATE agents SET 
                        active_default_prompt_id = NULL,
                        updated_at = NOW()
                    WHERE id = %s AND active_default_prompt_id = %s
                    """,
                    (prompt.agent_id, prompt_id),
                    fetch=False
                )
                logger.info(f"Cleared active_default_prompt_id for agent {prompt.agent_id}")
                
            logger.info(f"Set prompt {prompt_id} as inactive")
            
        return True
    except Exception as e:
        logger.error(f"Error setting active status for prompt {prompt_id}: {str(e)}")
        return False


def get_prompts_by_agent_id(agent_id: int, status_key: Optional[str] = None) -> List[Prompt]:
    """Get all prompts for an agent.
    
    Args:
        agent_id: The agent ID
        status_key: Optional status key to filter by
        
    Returns:
        List of Prompt objects
    """
    try:
        if status_key:
            result = execute_query(
                """
                SELECT * FROM prompts 
                WHERE agent_id = %s AND status_key = %s
                ORDER BY status_key, version DESC
                """,
                (agent_id, status_key)
            )
        else:
            result = execute_query(
                """
                SELECT * FROM prompts 
                WHERE agent_id = %s
                ORDER BY status_key, version DESC
                """,
                (agent_id,)
            )
            
        return [Prompt.from_db_row(row) for row in result]
    except Exception as e:
        logger.error(f"Error getting prompts for agent {agent_id}: {str(e)}")
        return []


def delete_prompt(prompt_id: int) -> bool:
    """Delete a prompt.
    
    Args:
        prompt_id: The prompt ID to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get the prompt first to check if it's active
        prompt = get_prompt_by_id(prompt_id)
        if not prompt:
            logger.warning(f"Cannot delete non-existent prompt {prompt_id}")
            return False
            
        # If this prompt is active and for the default status, update the agent's active_default_prompt_id
        if prompt.is_active and prompt.status_key == "default":
            execute_query(
                """
                UPDATE agents SET 
                    active_default_prompt_id = NULL,
                    updated_at = NOW()
                WHERE id = %s AND active_default_prompt_id = %s
                """,
                (prompt.agent_id, prompt_id),
                fetch=False
            )
            logger.info(f"Cleared active_default_prompt_id for agent {prompt.agent_id}")
        
        # Delete the prompt
        execute_query(
            "DELETE FROM prompts WHERE id = %s",
            (prompt_id,),
            fetch=False
        )
        
        logger.info(f"Deleted prompt {prompt_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting prompt {prompt_id}: {str(e)}")
        return False 