"""Memory management utilities for Flashinho Pro."""
import logging
from typing import Dict, Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


async def initialize_flashinho_pro_memories(agent_id: int, user_id: Optional[str] = None) -> None:
    """Initialize default memories for Flashinho Pro agent.
    
    Args:
        agent_id: Agent database ID
        user_id: User ID for user-specific memories
    """
    try:
        # Import here to avoid circular dependencies
        from automagik.db import get_memory_by_name, create_memory
        from automagik.db.models import Memory
        
        # Default memories to create
        default_memories = {
            "user_name": {"content": "Estudante", "is_global": False},
            "recent_context": {"content": "Nenhum contexto recente", "is_global": False},
            "user_preferences": {"content": "Padrão", "is_global": False},
            "last_topic": {"content": "Geral", "is_global": False},
            "study_progress": {"content": "0%", "is_global": False}
        }
        
        for name, config in default_memories.items():
            # Check if memory already exists
            existing = get_memory_by_name(
                agent_id=agent_id,
                name=name,
                user_id=UUID(user_id) if user_id and not config["is_global"] else None
            )
            
            if not existing:
                # Create new memory
                memory = Memory(
                    agent_id=agent_id,
                    user_id=UUID(user_id) if user_id and not config["is_global"] else None,
                    name=name,
                    content=config["content"]
                )
                create_memory(memory)
                logger.debug(f"Created memory '{name}' for agent {agent_id}")
        
    except Exception as e:
        logger.error(f"Error initializing Flashinho Pro memories: {e}")


async def update_flashinho_pro_memories(agent_id: int, user_id: Optional[str], context: Dict[str, Any]) -> bool:
    """Update Flashinho Pro memories with current context data.
    
    Args:
        agent_id: Agent database ID
        user_id: User ID
        context: Current context dictionary
        
    Returns:
        True if all updates successful
    """
    try:
        # Import here to avoid circular dependencies
        from automagik.db import get_memory_by_name, create_memory
        from automagik.db.models import Memory
        
        success = True
        
        # Update user name if available
        user_name = context.get("flashed_user_name") or context.get("user_name")
        if user_name:
            memory = Memory(
                agent_id=agent_id,
                user_id=UUID(user_id) if user_id else None,
                name="user_name",
                content=user_name
            )
            create_memory(memory)  # This is an upsert
        
        # Update recent context
        if context.get("last_message"):
            memory = Memory(
                agent_id=agent_id,
                user_id=UUID(user_id) if user_id else None,
                name="recent_context",
                content=context["last_message"][:200]  # Limit length
            )
            create_memory(memory)
        
        # Update study progress if available
        if context.get("study_progress"):
            memory = Memory(
                agent_id=agent_id,
                user_id=UUID(user_id) if user_id else None,
                name="study_progress",
                content=str(context["study_progress"])
            )
            create_memory(memory)
        
        return success
        
    except Exception as e:
        logger.error(f"Error updating Flashinho Pro memories: {e}")
        return False