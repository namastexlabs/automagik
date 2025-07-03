"""Multi-Prompt Manager for PydanticAI agents.

This module provides utilities to simplify multi-prompt management
for agents like Stan that need different prompts based on status.
"""
import logging
import glob
import os
from typing import Dict, Any, Optional, List
from importlib import import_module

logger = logging.getLogger(__name__)


class MultiPromptManager:
    """Manager for handling multiple prompts in status-based agents."""
    
    def __init__(self, agent_instance, prompts_directory: str, package_name: str):
        """Initialize the multi-prompt manager.
        
        Args:
            agent_instance: The agent instance
            prompts_directory: Path to the prompts directory
            package_name: Package name for importing prompts
        """
        self.agent = agent_instance
        self.prompts_dir = prompts_directory
        self.package_name = package_name
        self._prompts_registered = False
        self._registered_prompts = {}
    
    async def register_all_prompts(self) -> Dict[str, str]:
        """Register all prompts from the prompts directory.
        
        Returns:
            Dictionary mapping status keys to prompt IDs
        """
        if self._prompts_registered:
            return self._registered_prompts
        
        # Find all prompt files
        prompt_files = glob.glob(os.path.join(self.prompts_dir, "*.py"))
        
        primary_default_prompt_id = None
        not_registered_prompt_id = None
        
        for prompt_file in prompt_files:
            filename = os.path.basename(prompt_file)
            status_key = os.path.splitext(filename)[0].upper()
            
            # Skip non-prompt files
            if status_key.startswith("__") or status_key == "PROMPT":
                continue
            
            try:
                # Import the prompt
                module_name = f".prompts.{status_key.lower()}"
                module = import_module(module_name, package=self.package_name)
                prompt_text = getattr(module, "PROMPT")
                
                # Register the prompt
                is_primary_default = (status_key == "NOT_REGISTERED")
                
                self.agent._code_prompt_text = prompt_text
                prompt_id = await self.agent._register_code_defined_prompt(
                    prompt_text,
                    status_key=status_key,
                    prompt_name=f"{self.agent.__class__.__name__} {status_key} Prompt",
                    is_primary_default=is_primary_default
                )
                
                self._registered_prompts[status_key] = prompt_id
                
                # Track special prompts
                if status_key == "NOT_REGISTERED" and prompt_id:
                    not_registered_prompt_id = prompt_id
                elif status_key == "DEFAULT" and prompt_id:
                    primary_default_prompt_id = prompt_id
                
                logger.info(f"Registered prompt for status key: {status_key} with ID: {prompt_id}")
                
            except (ImportError, AttributeError) as e:
                logger.error(f"Failed to import prompt from {module_name}: {str(e)}")
        
        # Handle default prompt setup
        await self._setup_default_prompt(primary_default_prompt_id, not_registered_prompt_id)
        
        self._prompts_registered = True
        logger.info("All prompts registered successfully")
        return self._registered_prompts
    
    async def _setup_default_prompt(
        self, 
        primary_default_prompt_id: Optional[str],
        not_registered_prompt_id: Optional[str]
    ) -> None:
        """Set up the default prompt if needed."""
        if not primary_default_prompt_id and not_registered_prompt_id and self.agent.db_id:
            try:
                from automagik.db.repository.prompt import (
                    get_prompts_by_agent_id, get_prompt_by_id, 
                    create_prompt, set_prompt_active
                )
                from automagik.db.models import PromptCreate
                from automagik.db.repository.agent import update_agent_active_prompt_id
                
                # Check if default prompt exists
                default_prompts = get_prompts_by_agent_id(self.agent.db_id, status_key="default")
                
                if not default_prompts:
                    # Get NOT_REGISTERED prompt text
                    not_registered_prompt = get_prompt_by_id(not_registered_prompt_id)
                    
                    if not_registered_prompt:
                        # Create default prompt
                        default_prompt_data = PromptCreate(
                            agent_id=self.agent.db_id,
                            prompt_text=not_registered_prompt.prompt_text,
                            version=1,
                            is_active=True,
                            is_default_from_code=True,
                            status_key="default",
                            name=f"{self.agent.__class__.__name__} Default Prompt (maps to NOT_REGISTERED)"
                        )
                        
                        default_prompt_id = create_prompt(default_prompt_data)
                        self._registered_prompts["default"] = default_prompt_id
                        logger.info(f"Created default status prompt with ID {default_prompt_id}")
                else:
                    # Use existing default prompt
                    default_prompt_id = default_prompts[0].id
                    set_prompt_active(default_prompt_id, True)
                    self._registered_prompts["default"] = default_prompt_id
                    logger.info(f"Set existing default prompt {default_prompt_id} as active")
                
                # Update agent record
                if default_prompt_id or not_registered_prompt_id:
                    prompt_id_to_use = default_prompt_id or not_registered_prompt_id
                    success = update_agent_active_prompt_id(self.agent.db_id, prompt_id_to_use)
                    if success:
                        logger.info(f"Updated agent {self.agent.db_id} with active_default_prompt_id {prompt_id_to_use}")
                    else:
                        logger.error(f"Failed to update agent {self.agent.db_id} with active_default_prompt_id")
                        
            except Exception as e:
                logger.error(f"Error setting up default prompt: {str(e)}")
    
    async def load_prompt_by_status(self, status: str) -> bool:
        """Load a prompt based on status.
        
        Args:
            status: The status key to load prompt for
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Loading prompt for status {status}")
        
        # Convert status to string if it's an enum
        status_key = str(status)
        
        # Try to load the specific prompt
        result = await self.agent.load_active_prompt_template(status_key=status_key)
        
        if not result:
            # Fallback to NOT_REGISTERED
            logger.warning(f"No prompt found for status {status_key}, falling back to NOT_REGISTERED")
            result = await self.agent.load_active_prompt_template(status_key="NOT_REGISTERED")
            
            if not result:
                logger.error(f"Failed to load any prompt for status {status}")
                return False
        
        return True
    
    def get_registered_prompts(self) -> Dict[str, str]:
        """Get all registered prompt IDs.
        
        Returns:
            Dictionary mapping status keys to prompt IDs
        """
        return self._registered_prompts.copy()
    
    def is_registered(self) -> bool:
        """Check if prompts have been registered.
        
        Returns:
            True if prompts are registered, False otherwise
        """
        return self._prompts_registered


class PromptDiscovery:
    """Utility for automatic prompt discovery and validation."""
    
    @staticmethod
    def discover_prompt_files(prompts_directory: str) -> List[str]:
        """Discover all prompt files in a directory.
        
        Args:
            prompts_directory: Path to the prompts directory
            
        Returns:
            List of prompt file paths
        """
        if not os.path.exists(prompts_directory):
            logger.warning(f"Prompts directory not found: {prompts_directory}")
            return []
        
        prompt_files = glob.glob(os.path.join(prompts_directory, "*.py"))
        valid_files = []
        
        for file_path in prompt_files:
            filename = os.path.basename(file_path)
            if not filename.startswith("__") and filename != "prompt.py":
                valid_files.append(file_path)
        
        logger.debug(f"Discovered {len(valid_files)} prompt files in {prompts_directory}")
        return valid_files
    
    @staticmethod
    def validate_prompt_file(file_path: str, package_name: str) -> bool:
        """Validate that a prompt file contains the required PROMPT constant.
        
        Args:
            file_path: Path to the prompt file
            package_name: Package name for importing
            
        Returns:
            True if valid, False otherwise
        """
        filename = os.path.basename(file_path)
        module_name = os.path.splitext(filename)[0]
        
        try:
            import_path = f".prompts.{module_name}"
            module = import_module(import_path, package=package_name)
            prompt_text = getattr(module, "PROMPT", None)
            
            if not prompt_text:
                logger.error(f"Prompt file {file_path} missing PROMPT constant")
                return False
            
            if not isinstance(prompt_text, str) or len(prompt_text.strip()) == 0:
                logger.error(f"Invalid PROMPT constant in {file_path}")
                return False
            
            return True
            
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to validate prompt file {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def get_status_key_from_filename(filename: str) -> str:
        """Extract status key from prompt filename.
        
        Args:
            filename: The prompt filename
            
        Returns:
            Status key (uppercase)
        """
        base_name = os.path.splitext(filename)[0]
        return base_name.upper()


class PromptTemplateRenderer:
    """Utility for rendering prompt templates with variables."""
    
    @staticmethod
    def render_prompt_with_context(
        prompt_template: str, 
        context: Dict[str, Any]
    ) -> str:
        """Render a prompt template with context variables.
        
        Args:
            prompt_template: The prompt template with {{variable}} placeholders
            context: Dictionary of variables to substitute
            
        Returns:
            Rendered prompt text
        """
        rendered = prompt_template
        
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in rendered:
                rendered = rendered.replace(placeholder, str(value))
        
        return rendered
    
    @staticmethod
    def extract_template_variables(prompt_template: str) -> List[str]:
        """Extract variable names from a prompt template.
        
        Args:
            prompt_template: The prompt template
            
        Returns:
            List of variable names found in the template
        """
        import re
        pattern = r'\{\{(\w+)\}\}'
        matches = re.findall(pattern, prompt_template)
        return list(set(matches))  # Remove duplicates