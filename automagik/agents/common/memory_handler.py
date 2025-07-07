"""Memory handler for agents.

This module handles memory operations, variable initialization, and substitution.
"""
import logging
from typing import Dict, List, Any, Optional

# Setup logging
logger = logging.getLogger(__name__)

class MemoryHandler:
    """Class for handling memory operations and initialization."""
    
    @staticmethod
    def initialize_memory_variables_sync(
        template_vars: List[str],
        agent_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """Initialize memory variables in the database.
        
        This ensures all template variables exist in memory with default values.
        Uses direct repository calls to avoid async/await issues.
        
        Args:
            template_vars: List of template variables to initialize
            agent_id: Agent ID to associate with memory variables
            user_id: Optional user ID to associate with memory variables
            
        Returns:
            True if initialization was successful, False otherwise
        """
        if not agent_id:
            logger.warning("Cannot initialize memory variables: No agent ID available")
            return False
            
        try:
            # Import the repository functions for direct database access
            from automagik.db.repository.memory import get_memory_by_name, create_memory
            from automagik.db.models import Memory
            
            # Create context
                
            # Extract all variables except run_id which is handled separately
            memory_vars = [var for var in template_vars if var != "run_id"]
            
            # Log the user_id we're using (if any)
            if user_id:
                logger.info(f"Initializing memory variables for user_id={user_id}")
            else:
                logger.warning("No user_id provided, memories will be created with NULL user_id")
            
            success = True
            for var_name in memory_vars:
                try:
                    # Check if memory already exists with direct repository call for this user
                    existing_memory = get_memory_by_name(var_name, agent_id=agent_id, user_id=user_id)
                    
                    # If not found, create it with default value
                    if not existing_memory:
                        logger.debug(f"Creating missing memory variable: {var_name} for user: {user_id}")
                        
                        # Prepare a proper description based on the variable name
                        description = "Auto-created template variable for SimpleAgent"
                        if var_name == "personal_attributes":
                            description = "Personal attributes and preferences for the agent"
                            content = "None stored yet. You can update this by asking the agent to remember personal details."
                        elif var_name == "technical_knowledge":
                            description = "Technical knowledge and capabilities for the agent"
                            content = "None stored yet. You can update this by asking the agent to remember technical information."
                        elif var_name == "user_preferences":
                            description = "User preferences and settings for the agent"
                            content = "None stored yet. You can update this by asking the agent to remember your preferences."
                        else:
                            content = "None stored yet"
                        
                        # Create the memory directly using repository function
                        memory = Memory(
                            name=var_name,
                            content=content,
                            description=description,
                            agent_id=agent_id,
                            user_id=user_id,  # Include the user_id here
                            read_mode="system_prompt",
                            access="read_write"  # Ensure it can be written to
                        )
                        
                        memory_id = create_memory(memory)
                        if memory_id:
                            logger.debug(f"Created memory variable: {var_name} with ID: {memory_id} for user: {user_id}")
                        else:
                            logger.error(f"Failed to create memory variable: {var_name}")
                            success = False
                    else:
                        logger.info(f"Memory variable already exists: {var_name}")
                        
                except Exception as e:
                    logger.error(f"Error initializing memory variable {var_name}: {str(e)}")
                    success = False
                    
            return success
                    
        except Exception as e:
            logger.error(f"Error in initialize_memory_variables_sync: {str(e)}")
            return False
    
    @staticmethod
    def store_memory_sync(
        name: str,
        content: str,
        agent_id: int,
        user_id: Optional[int] = None,
        description: Optional[str] = None,
        read_mode: str = "system_prompt",
        access: str = "read_write"
    ) -> bool:
        """Store or update a memory variable in the database.
        
        Uses direct repository calls to avoid async/await issues.
        
        Args:
            name: Name of the memory variable
            content: Content to store
            agent_id: Agent ID to associate with memory variable
            user_id: Optional user ID to associate with memory variable
            description: Optional description of the memory variable
            read_mode: How the memory should be read (default: system_prompt)
            access: Access permissions for the memory (default: read_write)
            
        Returns:
            True if storage was successful, False otherwise
        """
        if not agent_id:
            logger.warning("Cannot store memory: No agent ID available")
            return False
            
        try:
            # Import the repository functions for direct database access
            from automagik.db.repository.memory import get_memory_by_name, create_memory, update_memory
            from automagik.db.models import Memory
            
            # Check if memory already exists
            existing_memory = get_memory_by_name(name, agent_id=agent_id, user_id=user_id)
            
            if existing_memory:
                # Update existing memory
                logger.info(f"Updating existing memory: {name} for user: {user_id}")
                existing_memory.content = content
                
                if description:
                    existing_memory.description = description
                
                success = update_memory(existing_memory)
                if success:
                    logger.info(f"Updated memory: {name} for user: {user_id}")
                    return True
                else:
                    logger.error(f"Failed to update memory: {name}")
                    return False
            else:
                # Create new memory
                logger.info(f"Creating new memory: {name} for user: {user_id}")
                
                if not description:
                    description = "Memory variable created for agent"
                
                memory = Memory(
                    name=name,
                    content=content,
                    description=description,
                    agent_id=agent_id,
                    user_id=user_id,
                    read_mode=read_mode,
                    access=access
                )
                
                memory_id = create_memory(memory)
                if memory_id:
                    logger.info(f"Created memory: {name} with ID: {memory_id} for user: {user_id}")
                    return True
                else:
                    logger.error(f"Failed to create memory: {name}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error in store_memory_sync: {str(e)}")
            return False
    
    @staticmethod
    def check_and_ensure_memory_variables(
        template_vars: List[str], 
        agent_id: int, 
        user_id: Optional[int] = None
    ) -> bool:
        """Check if memory variables are properly initialized and initialize if needed.
        
        Args:
            template_vars: List of template variables to check
            agent_id: Agent ID to associate with memory variables
            user_id: Optional user ID to associate with memory variables
            
        Returns:
            True if all memory variables are properly initialized, False otherwise
        """
        if not agent_id:
            logger.warning("Cannot check memory variables: No agent ID available")
            return False
            
        try:
            from automagik.db.repository.memory import get_memory_by_name
            
            # Create a context dict for memory operations
            
            # Extract all variables except run_id which is handled separately
            memory_vars = [var for var in template_vars if var != "run_id"]
            missing_vars = []
            
            for var_name in memory_vars:
                # Check if memory exists for this user
                existing_memory = get_memory_by_name(var_name, agent_id=agent_id, user_id=user_id)
                
                if not existing_memory:
                    missing_vars.append(var_name)
            
            # If we found missing variables, try to initialize them
            if missing_vars:
                logger.warning(f"Found {len(missing_vars)} uninitialized memory variables: {', '.join(missing_vars)}")
                # Initialize missing variables
                return MemoryHandler.initialize_memory_variables_sync(template_vars, agent_id, user_id)
                
            return True
        except Exception as e:
            logger.error(f"Error checking memory variables: {str(e)}")
            return False
            
    @staticmethod
    async def fetch_memory_vars(
        template_vars: List[str], 
        agent_id: int, 
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Fetch memory variables for system prompt filling.
        
        Args:
            template_vars: List of template variables to fetch
            agent_id: Agent ID to associate with memory variables 
            user_id: Optional user ID to associate with memory variables
            
        Returns:
            Dictionary of memory variables and their contents
        """
        memory_vars = {}
        
        try:
            # Import memory functions
            from automagik.tools.memory.tool import read_memory
            
            # Create context - convert UUID to string if needed
            context = {
                "agent_id": agent_id,
                "user_id": str(user_id) if user_id else None
            }
            
            # Fetch each memory variable
            for var_name in template_vars:
                if var_name == "run_id":
                    # Skip run_id as it's handled separately
                    continue
                    
                try:
                    # Fetch memory content
                    logger.debug(f"Fetching memory variable: {var_name} with context {context}")
                    memory_result = await read_memory(context, name=var_name)
                    
                    if isinstance(memory_result, dict):
                        # Check if we have success and content
                        if memory_result.get("success", False) and "content" in memory_result:
                            memory_vars[var_name] = memory_result["content"]
                            logger.debug(f"Successfully fetched memory variable: {var_name}")
                        else:
                            # If not successful or no content, use a default value
                            memory_vars[var_name] = "No data available"
                            logger.warning(f"Memory variable {var_name} retrieval unsuccessful: {memory_result.get('message', 'Unknown error')}")
                    else:
                        # For backward compatibility with string responses
                        memory_vars[var_name] = memory_result
                        logger.info(f"Fetched memory variable as string: {var_name}")
                        
                except Exception as e:
                    logger.error(f"Error fetching memory variable {var_name}: {str(e)}")
                    memory_vars[var_name] = "No data available"
                    
            return memory_vars
                
        except Exception as e:
            logger.error(f"Error fetching memory variables: {str(e)}")
            # Return empty values for all variables
            return {var: "No data available" for var in template_vars if var != "run_id"} 