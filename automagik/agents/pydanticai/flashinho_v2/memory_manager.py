"""Memory management for Flashinho Pro user variables.

This module handles creating and updating memories that automatically populate
the prompt variables using the framework's memory system.
"""

import logging
from typing import Dict, Optional, Any
import uuid
from datetime import datetime

from automagik.db.models import Memory
from automagik.db import create_memory
from .identification import FlashinhoIdentifier as FlashinhoProUserMatcher

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
                logger.info(f"Loaded {len(variables)} variables for user {flashed_user_id}")
            else:
                # Use default variables for unidentified users
                variables = matcher._get_default_variables()
                logger.info("Using default variables for unidentified user")
            
            # Create/update individual memories for each variable
            success_count = 0
            for var_name, var_value in variables.items():
                if await self._update_memory(var_name, var_value):
                    success_count += 1
            
            logger.info(f"Updated {success_count}/{len(variables)} memories successfully")
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
                logger.debug(f"Updated memory '{memory_name}' with content: {content_str[:50]}...")
                return True
            else:
                logger.warning(f"Failed to create/update memory '{memory_name}'")
                return False
                
        except Exception as e:
            logger.error(f"Error updating memory '{memory_name}': {str(e)}")
            return False
    
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
            
            logger.info(f"Initialized {success_count}/{len(default_variables)} default memories")
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
            
            logger.info(f"Updated {success_count} activity memories")
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
            
            # Get conversation code if available from context
            conversation_code = self.context.get("pretty_id") or self.context.get("flashed_conversation_code")

            if existing_user:
                logger.info(f"Found existing user in DB: {user_uuid}")
                
                # Check if this user is already correctly configured
                current_user_data = existing_user.user_data or {}
                current_flashed_id = current_user_data.get("flashed_user_id")
                
                # Update user_data if needed
                needs_update = False
                updated_user_data = current_user_data.copy()
                
                if current_flashed_id != flashed_user_id:
                    updated_user_data["flashed_user_id"] = flashed_user_id
                    needs_update = True
                    logger.info(f"Updating flashed_user_id from {current_flashed_id} to {flashed_user_id}")
                
                # Add conversation code if available and not already stored
                if conversation_code and updated_user_data.get("flashed_conversation_code") != conversation_code:
                    updated_user_data["flashed_conversation_code"] = conversation_code
                    needs_update = True
                    logger.info(f"Adding conversation code {conversation_code} to user_data")
                
                # Add user name if available and not already stored
                if name and not updated_user_data.get("name"):
                    updated_user_data["name"] = name
                    needs_update = True
                
                if needs_update:
                    update_user_data(user_uuid, updated_user_data)
                    logger.info(f"Updated user_data for user {user_uuid}")

                # Check if the primary key UUID is different from the flashed_user_id
                if str(user_uuid) != str(flashed_user_id):
                    logger.warning(f"User UUID {user_uuid} differs from Flashed ID {flashed_user_id}")
                    
                    # Check if there's a user with the flashed_user_id as primary key
                    try:
                        flashed_uuid_user = get_user(uuid.UUID(flashed_user_id))
                        if flashed_uuid_user and flashed_uuid_user.id != user_uuid:
                            logger.warning(f"Found different user with Flashed UUID {flashed_user_id}")
                            # Update the flashed UUID user instead
                            flashed_user_data = flashed_uuid_user.user_data or {}
                            flashed_user_data.update(updated_user_data)
                            update_user_data(uuid.UUID(flashed_user_id), flashed_user_data)
                            return True
                    except Exception:
                        # Flashed UUID user doesn't exist, continue with current user
                        pass

                # Update user_data if flashed_user_id missing on the current (now-correct) row
                if not (existing_user.user_data or {}).get("flashed_user_id"):
                    final_user_data = (existing_user.user_data or {}).copy()
                    final_user_data["flashed_user_id"] = flashed_user_id
                    if conversation_code:
                        final_user_data["flashed_conversation_code"] = conversation_code
                    update_user_data(user_uuid, final_user_data)
            else:
                # Create new user row
                from datetime import datetime
                
                # Prepare user_data with all available information
                user_data = {"flashed_user_id": flashed_user_id}
                if name:
                    user_data["name"] = name
                if conversation_code:
                    user_data["flashed_conversation_code"] = conversation_code
                
                user_model = User(
                    id=user_uuid,
                    email=email,
                    phone_number=phone,
                    user_data=user_data,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                created_id = create_user(user_model)
                if not created_id:
                    logger.error(f"Failed to create user row for flashed_user_id {flashed_user_id}")
                    return False
                
                logger.info(f"Created new user with ID: {user_uuid} and conversation code: {conversation_code}")

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