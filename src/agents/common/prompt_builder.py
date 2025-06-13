"""Prompt builder for agent implementations.

This module handles system prompt building and template variable substitution
for all agent implementations.
"""
import logging
import re
from typing import Dict, List, Any, Optional

# Setup logging
logger = logging.getLogger(__name__)

class PromptBuilder:
    """Class for building and filling system prompts with template variables."""
    
    @staticmethod
    def extract_template_variables(template: str) -> List[str]:
        """Extract all template variables from a string.
        
        Args:
            template: Template string with {{variable}} placeholders
            
        Returns:
            List of variable names without braces
        """
        pattern = r'\{\{([a-zA-Z_]+)\}\}'
        matches = re.findall(pattern, template)
        return list(set(matches))  # Remove duplicates

    @staticmethod
    def create_base_system_prompt(prompt_template: str) -> str:
        """Create the base system prompt.
        
        Args:
            prompt_template: The template string to use
            
        Returns:
            Base system prompt template
        """
        return prompt_template

    @staticmethod
    async def get_filled_system_prompt(
        prompt_template: str, 
        memory_vars: Dict[str, Any], 
        run_id: Optional[str] = None,
        agent_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> str:
        """Fill the system prompt template with memory variables.
        
        Args:
            prompt_template: The template to fill
            memory_vars: Dictionary of memory variables
            run_id: Optional run ID to include in the prompt
            agent_id: Optional agent ID for context
            user_id: Optional user ID for context
            
        Returns:
            Filled system prompt
        """
        # Start with the template
        filled_prompt = prompt_template
        
        # Fill in memory variables
        for var_name, content in memory_vars.items():
            placeholder = f"{{{{{var_name}}}}}"
            if placeholder in filled_prompt:
                if content is None:
                    content = f"No {var_name} data available"
                elif isinstance(content, dict):
                    try:
                        import json
                        content = json.dumps(content, indent=2)
                    except Exception as e:
                        logger.error(f"Error serializing {var_name} to JSON: {str(e)}")
                        content = f"Error: could not process {var_name} data"
                
                filled_prompt = filled_prompt.replace(placeholder, str(content))
                logger.debug(f"Filled template variable: {var_name}")
        
        # Fill in run_id if provided and placeholder exists
        if run_id and "{{run_id}}" in filled_prompt:
            filled_prompt = filled_prompt.replace("{{run_id}}", str(run_id))
            logger.info(f"Filled run_id: {run_id}")
            
        # Check for any unfilled variables
        remaining_vars = PromptBuilder.extract_template_variables(filled_prompt)
        if remaining_vars:
            logger.warning(f"Some template variables could not be filled: {', '.join(remaining_vars)}")
            
            # Replace unfilled variables with placeholders
            for var in remaining_vars:
                placeholder = f"{{{{{var}}}}}"
                filled_prompt = filled_prompt.replace(placeholder, f"[No data for {var}]")
        
        return filled_prompt 