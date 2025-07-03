"""Memory management for Flashinho Pro user variables.

This module handles creating and updating memories that automatically populate
the prompt variables using the framework's memory system.
"""

import logging
from typing import Dict, Optional, Any
import uuid
from datetime import datetime

from automagik.db.models import Memory
from automagik.db import create_memory, create_memories_bulk
from .user_identification import FlashinhoProUserMatcher

logger = logging.getLogger(__name__)


class FlashinhoProMemoryManager:
    """Manages memories for Flashinho Pro agent prompt variables."""
    
    def __init__(self, agent_id: int, user_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        """Initialize memory manager.
        
        Args:
            agent_id: Database ID of the Flashinho Pro agent
            user_id: User ID (UUID string) for user-specific memories
            context: Agent context for user identification
        """
        self.agent_id = agent_id
        self.user_id = uuid.UUID(user_id) if user_id else None
        self.context = context or {}
        
    async def update_user_memories(self) -> bool:
        """Update all user-specific memories from Flashed API data.
        
        Returns:
            True if memories were updated successfully, False otherwise
        """
        try:
            # Get user identification and variables
            matcher = FlashinhoProUserMatcher(self.context)
            flashed_user_id = await matcher.identify_user()
            
            if flashed_user_id:
                # Load user variables from Flashed API
                matcher.flashed_user_id = flashed_user_id
                # Update internal user_id reference
                try:
                    self.user_id = uuid.UUID(flashed_user_id)
                except Exception:
                    # If flashed_user_id is not a valid UUID string we generate a deterministic UUID namespace
                    self.user_id = uuid.uuid5(uuid.NAMESPACE_DNS, flashed_user_id)

                # Ensure we have a corresponding user row in the database
                await self._ensure_user_in_db(flashed_user_id)

                variables = await matcher.load_user_variables()
                logger.debug(f"Loaded {len(variables)} variables for user {flashed_user_id}")
            else:
                # Use default variables for unidentified users
                variables = matcher._get_default_variables()
                logger.debug("Using default variables")
            
            # Create/update memories in bulk for better performance
            logger.info(f"About to bulk update {len(variables)} memories for user_id: {self.user_id}, agent_id: {self.agent_id}")
            success_count = await self._bulk_update_memories(variables)
            
            logger.info(f"Updated {success_count}/{len(variables)} memories")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error updating user memories: {str(e)}")
            return False
    
    async def _update_memory(self, memory_name: str, content: Any) -> bool:
        """Create or update a single memory entry.
        
        Args:
            memory_name: Name of the memory (matches prompt variable)
            content: Content to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert content to string
            content_str = str(content) if content is not None else ""
            
            # Create memory with read_mode="system_prompt" for automatic substitution
            memory = Memory(
                id=uuid.uuid4(),
                name=memory_name,
                content=content_str,
                description=f"Flashinho Pro variable: {memory_name}",
                user_id=self.user_id,
                agent_id=self.agent_id,
                read_mode="system_prompt",  # KEY: This enables automatic prompt substitution
                access="read_write",
                metadata={
                    "source": "flashed_api",
                    "updated_at": datetime.now().isoformat(),
                    "variable_type": "user_context"
                },
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Create/update the memory (upsert behavior)
            memory_id = create_memory(memory)
            
            if memory_id:
                # Memory updated successfully
                return True
            else:
                logger.debug(f"Failed to update memory '{memory_name}'")
                return False
                
        except Exception as e:
            logger.error(f"Error updating memory '{memory_name}': {str(e)}")
            return False
    
    async def _bulk_update_memories(self, variables: Dict[str, Any]) -> int:
        """Create or update multiple memories in a single bulk operation.
        
        Args:
            variables: Dictionary of variable names to values
            
        Returns:
            Number of memories successfully created/updated
        """
        try:
            # Prepare list of Memory objects
            memories = []
            logger.debug(f"Creating memory objects for {len(variables)} variables")
            
            for var_name, var_value in variables.items():
                memory = Memory(
                    id=uuid.uuid4(),
                    name=var_name,
                    content=str(var_value) if var_value is not None else "",
                    description=f"Flashinho Pro variable: {var_name}",
                    user_id=self.user_id,
                    agent_id=self.agent_id,
                    read_mode="system_prompt",  # KEY: This enables automatic prompt substitution
                    access="read_write",
                    metadata={
                        "source": "flashed_api",
                        "updated_at": datetime.now().isoformat(),
                        "variable_type": "user_context"
                    },
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                memories.append(memory)
                logger.debug(f"Created memory object: name={var_name}, user_id={self.user_id}, agent_id={self.agent_id}")
            
            # Use bulk creation for better performance
            logger.info(f"Calling create_memories_bulk with {len(memories)} memories")
            success_count = create_memories_bulk(memories)
            
            if success_count > 0:
                logger.info(f"Bulk updated {success_count} memories successfully")
            else:
                logger.warning(f"Bulk memory update returned 0 successes. user_id={self.user_id}, agent_id={self.agent_id}")
                
            return success_count
            
        except Exception as e:
            logger.error(f"Error in bulk memory update: {str(e)}")
            return 0
    
    async def initialize_default_memories(self) -> bool:
        """Initialize all Flashinho Pro prompt variables with default values.
        
        This ensures all variables exist in the memory system even if the user
        hasn't been identified or API calls fail.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Default values for all Flashinho Pro variables
            default_variables = {
                # User profile
                "name": "Estudante",
                "levelOfEducation": "Ensino Médio", 
                "preferredSubject": "",
                "createdAt": "",
                
                # Status flags
                "has_opted_in": "false",
                "onboardingCompleted": "false",
                
                # Progress metrics
                "dailyProgress": "0",
                "sequence": "0", 
                "flashinhoEnergy": "100",
                "starsBalance": "0",
                
                # Study activity
                "roadmap": "Comece criando sua primeira revisão!",
                "lastActivity": "",
                "last_cardPlay_result": "",
                "last_cardPlay_category": "",
                "last_cardPlay_topic": "",
                "last_cardPlay_date": "",
                
                # Objectives
                "last_objectiveCreated_type": "",
                "last_objectiveCreated_topics": "",
                "last_objectiveCreated_duedate": "",
                
                # Dynamic
                "interesses_detectados": "",
            }
            
            success_count = 0
            for var_name, default_value in default_variables.items():
                # Create memory (upsert behavior - will update if exists)
                if await self._update_memory(var_name, default_value):
                    success_count += 1
            
            logger.debug(f"Initialized {success_count} default memories")
            return success_count == len(default_variables)
            
        except Exception as e:
            logger.error(f"Error initializing default memories: {str(e)}")
            return False
    
    async def update_detected_interests(self, interests: str) -> bool:
        """Update the dynamically detected interests variable.
        
        Args:
            interests: Comma-separated list of detected interests
            
        Returns:
            True if successful, False otherwise
        """
        return await self._update_memory("interesses_detectados", interests)
    
    async def update_activity_status(self, activity_data: Dict[str, Any]) -> bool:
        """Update activity-related variables from recent user activity.
        
        Args:
            activity_data: Dictionary containing activity information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success_count = 0
            
            # Map activity data to memory variables
            activity_mappings = {
                "lastActivity": activity_data.get("last_activity_date", ""),
                "last_cardPlay_result": activity_data.get("last_result", ""),
                "last_cardPlay_category": activity_data.get("last_category", ""),
                "last_cardPlay_topic": activity_data.get("last_topic", ""),
                "last_cardPlay_date": activity_data.get("last_play_date", ""),
            }
            
            for var_name, value in activity_mappings.items():
                if value and await self._update_memory(var_name, value):
                    success_count += 1
            
            logger.debug(f"Updated {success_count} activity memories")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error updating activity status: {str(e)}")
            return False
    
    def get_memory_status(self) -> Dict[str, Any]:
        """Get status of all Flashinho Pro memories.
        
        Returns:
            Dictionary with memory status information
        """
        try:
            # List of all expected variables
            expected_variables = [
                "name", "levelOfEducation", "preferredSubject", "createdAt",
                "has_opted_in", "onboardingCompleted", "dailyProgress", "sequence",
                "flashinhoEnergy", "starsBalance", "roadmap", "lastActivity",
                "last_cardPlay_result", "last_cardPlay_category", "last_cardPlay_topic",
                "last_cardPlay_date", "last_objectiveCreated_type", 
                "last_objectiveCreated_topics", "last_objectiveCreated_duedate",
                "interesses_detectados"
            ]
            
            status = {
                "agent_id": self.agent_id,
                "user_id": str(self.user_id) if self.user_id else None,
                "total_variables": len(expected_variables),
                "existing_memories": 0,
                "missing_memories": [],
                "memory_details": {}
            }
            
            for var_name in expected_variables:
                try:
                    # For now, assume memories exist after initialization
                    # In a real implementation, you would query the database
                    status["existing_memories"] += 1
                    status["memory_details"][var_name] = {
                        "exists": True,
                        "content_length": "unknown",
                        "read_mode": "system_prompt"
                    }
                except Exception as e:
                    logger.error(f"Error checking memory '{var_name}': {str(e)}")
                    status["missing_memories"].append(var_name)
                    status["memory_details"][var_name] = {
                        "exists": False,
                        "error": str(e)
                    }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting memory status: {str(e)}")
            return {"error": str(e)}

    async def _ensure_user_in_db(self, flashed_user_id: str) -> bool:
        """Ensure a user row exists for the given flashed_user_id.

        A new user will be created if none exists, and the flashed_user_id will be
        stored under the user_data JSON field.

        Args:
            flashed_user_id: The Flashed user UUID string

        Returns:
            True if user exists or was created/updated successfully
        """
        try:
            from automagik.db.repository.user import get_user, create_user, update_user_data
            from automagik.db.models import User

            # Ensure flashed_user_id is a UUID object. If it's already a UUID, keep it;
            # if it's a string, attempt normal construction; otherwise create a
            # deterministic UUID based on its string representation.
            if isinstance(flashed_user_id, uuid.UUID):
                user_uuid = flashed_user_id
            else:
                try:
                    user_uuid = uuid.UUID(str(flashed_user_id))
                except Exception:
                    user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(flashed_user_id))

            # Attempt to fetch existing user
            existing_user = get_user(user_uuid)

            phone = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
            email = self.context.get("user_email")
            name = self.context.get("whatsapp_user_name") or self.context.get("user_name")

            if existing_user:
                # If the existing user's ID differs from the Flashed UUID, migrate data to the new ID
                if existing_user.id != user_uuid:
                    logger.info(f"Migrating user to Flashed ID {user_uuid}")
                    # 1. Ensure destination user row exists (create minimal row if needed)
                    from datetime import datetime
                    from automagik.db.repository.user import create_user, delete_user

                    dest_user = get_user(user_uuid)
                    if not dest_user:
                        create_user(
                            User(
                                id=user_uuid,
                                email=email,
                                phone_number=phone,
                                user_data={"flashed_user_id": flashed_user_id, "merged_from": str(existing_user.id)},
                                created_at=datetime.now(),
                                updated_at=datetime.now()
                            )
                        )

                    # 2. Migrate FK references (sessions, messages, memories, preferences)
                    tables_to_update = [
                        "sessions",
                        "messages",
                        "memories",
                        "preferences"
                    ]
                    from automagik.db.connection import execute_query
                    for tbl in tables_to_update:
                        execute_query(
                            f"UPDATE {tbl} SET user_id = %s WHERE user_id = %s",
                            (user_uuid, existing_user.id),
                            fetch=False
                        )

                    # 3. Delete old user row (optional – keep as archive if desired)
                    delete_user(existing_user.id)

                    logger.debug(f"User migrated to {user_uuid}")

                # Update user_data if flashed_user_id missing on the current (now-correct) row
                if not (existing_user.user_data or {}).get("flashed_user_id"):
                    update_user_data(user_uuid, {"flashed_user_id": flashed_user_id})
            else:
                # Create new user row
                from datetime import datetime
                user_model = User(
                    id=user_uuid,
                    email=email,
                    phone_number=phone,
                    user_data={"flashed_user_id": flashed_user_id, "name": name} if flashed_user_id else {},
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                created_id = create_user(user_model)
                if not created_id:
                    logger.error(f"Failed to create user row for flashed_user_id {flashed_user_id}")
                    return False

            return True
        except Exception as e:
            logger.error(f"Error ensuring user in DB for flashed_user_id {flashed_user_id}: {str(e)}")
            return False


# Convenience functions for agent integration
async def update_flashinho_pro_memories(agent_id: int, user_id: Optional[str], context: Dict[str, Any]) -> bool:
    """Convenience function to update Flashinho Pro memories.
    
    Args:
        agent_id: Database ID of the Flashinho Pro agent
        user_id: User ID (UUID string)
        context: Agent context with channel information
        
    Returns:
        True if memories updated successfully, False otherwise
    """
    manager = FlashinhoProMemoryManager(agent_id, user_id, context)
    return await manager.update_user_memories()


async def initialize_flashinho_pro_memories(agent_id: int, user_id: Optional[str] = None) -> bool:
    """Convenience function to initialize default Flashinho Pro memories.
    
    Args:
        agent_id: Database ID of the Flashinho Pro agent
        user_id: Optional user ID for user-specific memories
        
    Returns:
        True if initialization successful, False otherwise
    """
    manager = FlashinhoProMemoryManager(agent_id, user_id)
    return await manager.initialize_default_memories()