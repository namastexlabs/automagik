"""User status checker for Flashinho V2 agent.

This module provides utilities to check user Pro status and identify users
BEFORE agent execution to determine the appropriate model and prompt to use.
"""
import logging
import re
from typing import Dict, Any, Optional, Tuple
from automagik.tools.flashed.provider import FlashedProvider

logger = logging.getLogger(__name__)


class UserStatusChecker:
    """Utility class for checking user Pro status and identification before agent execution."""
    
    def __init__(self):
        """Initialize the status checker."""
        self.flashed_provider = FlashedProvider()
    
    def extract_conversation_code_from_message(self, message: str) -> Optional[str]:
        """Extract conversation code from user message.
        
        Args:
            message: User message text
            
        Returns:
            Conversation code if found, None otherwise
        """
        # Pattern to match conversation codes like "KixVoBT59N"
        # More specific patterns first, then generic as fallback
        patterns = [
            # Specific conversation code patterns with context
            r'código de conversa[:\s]*([A-Za-z0-9]{10})',
            r'codigo de conversa[:\s]*([A-Za-z0-9]{10})',
            r'meu código[:\s]*([A-Za-z0-9]{10})',
            r'código[:\s]*([A-Za-z0-9]{10})',
            r'codigo[:\s]*([A-Za-z0-9]{10})',
            # Pattern for the specific test format: "KixVoBT59N"
            r'\b([A-Z][a-z]{2}[A-Z][a-z]{1}[A-Z][a-z]{1}[0-9]{2}[A-Z])\b',  # KixVoBT59N pattern
            # Generic pattern but exclude common Portuguese words
            r'(?<![a-záàâãéêíóôõúç])\b([A-Za-z0-9]{10})(?![a-záàâãéêíóôõúç])\b'
        ]
        
        # Common Portuguese words to exclude (that might be 10 chars)
        excluded_words = [
            'linguagens', 'programação', 'desenvolvimento', 'javascript', 'typescript',
            'conversação', 'flashinho', 'mensagem', 'whatsapp', 'conversar'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                code = match.group(1)
                # Check if it's not an excluded word
                if code.lower() not in excluded_words:
                    logger.info(f"Extracted conversation code: {code}")
                    return code
                else:
                    logger.debug(f"Skipped excluded word: {code}")
        
        return None
    
    async def get_user_by_conversation_code(self, conversation_code: str) -> Dict[str, Any]:
        """Get user data by conversation code.
        
        Args:
            conversation_code: User conversation code
            
        Returns:
            Dict containing:
            - success: Boolean indicating if user was found
            - user_data: User information if found
            - error: Error message if failed
        """
        try:
            async with self.flashed_provider:
                result = await self.flashed_provider.get_user_by_pretty_id(conversation_code)
                return {
                    "success": True,
                    "user_data": result,
                    "conversation_code": conversation_code
                }
        except Exception as e:
            logger.error(f"Error getting user by conversation code {conversation_code}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "user_data": None,
                "conversation_code": conversation_code
            }
    
    async def check_user_pro_status_by_phone(self, phone: str) -> Dict[str, Any]:
        """Check user Pro status by phone number.
        
        Args:
            phone: User phone number
            
        Returns:
            Dict containing:
            - userId: User UUID
            - isWhatsappProAvailable: Boolean indicating Pro availability
            - llmModel: Recommended model ("light" or "pro")
            - userFeedbackMessage: Message for user (optional)
            - success: Boolean indicating if check was successful
            - error: Error message if check failed
        """
        try:
            async with self.flashed_provider:
                result = await self.flashed_provider.check_user_pro_status_by_phone(phone)
                result["success"] = True
                return result
        except Exception as e:
            logger.error(f"Error checking Pro status for phone {phone}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "userId": None,
                "isWhatsappProAvailable": False,
                "llmModel": "light",  # Default to light model on error
                "userFeedbackMessage": None
            }
    
    def get_model_config_for_status(self, is_pro: bool) -> Dict[str, str]:
        """Get model configuration based on Pro status.
        
        Args:
            is_pro: Whether user has Pro status
            
        Returns:
            Dict with model configuration
        """
        if is_pro:
            return {
                "model": "google-gla:gemini-2.5-pro-preview-05-06",
                "vision_model": "google-gla:gemini-2.5-pro-preview-05-06",
                "prompt_type": "pro"
            }
        else:
            return {
                "model": "google-gla:gemini-2.5-flash-preview-05-20", 
                "vision_model": "google-gla:gemini-2.5-flash-preview-05-20",
                "prompt_type": "free"
            }
    
    def generate_conversation_code_request_message(self) -> str:
        """Generate a message requesting the conversation code in Flashinho's style.
        
        Returns:
            Message requesting conversation code
        """
        return ("E aí! 👋 Pra eu conseguir te dar aquela força nos estudos de forma "
                "personalizada, preciso do seu código de conversa! 🔑\n\n"
                "Manda aí seu código pra gente começar com tudo! 🚀✨")
    
    async def prepare_agent_config(self, phone: str) -> Tuple[Dict[str, str], Dict[str, Any]]:
        """Prepare agent configuration based on user phone status.
        
        Args:
            phone: User phone number
            
        Returns:
            Tuple of (agent_config, user_status_info)
        """
        # Check user status
        status_result = await self.check_user_pro_status_by_phone(phone)
        
        # Determine if user is Pro
        is_pro = status_result.get("isWhatsappProAvailable", False)
        
        # Get model configuration
        model_config = self.get_model_config_for_status(is_pro)
        
        # Prepare agent config
        agent_config = {
            "model": model_config["model"],
            "vision_model": model_config["vision_model"],
            "supported_media": ["image", "audio", "document"],
            "auto_enhance_prompts": True,
            "enable_multi_prompt": True
        }
        
        # Add user status info
        user_status_info = {
            "user_id": status_result.get("userId"),
            "is_pro": is_pro,
            "llm_model": status_result.get("llmModel", "light"),
            "prompt_type": model_config["prompt_type"],
            "user_feedback_message": status_result.get("userFeedbackMessage"),
            "status_check_success": status_result.get("success", False)
        }
        
        logger.info(f"Prepared config for phone {phone}: Pro={is_pro}, Model={model_config['model']}")
        
        return agent_config, user_status_info
    
    async def handle_user_identification_workflow(self, message: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the complete user identification workflow before agent run.
        
        Args:
            message: User message
            user_data: Current user data from database
            
        Returns:
            Dict containing:
            - needs_conversation_code: Boolean indicating if code is needed
            - conversation_code_request_message: Message to send if code is needed
            - user_identified: Boolean indicating if user was identified
            - flashed_user_data: User data from Flashed API if identified
            - updated_user_data: Updated user_data dict to save
            - error: Error message if any
        """
        try:
            # Check if user already has flashed_conversation_code
            existing_code = user_data.get("flashed_conversation_code")
            
            if existing_code:
                logger.info(f"User already has conversation code: {existing_code}")
                return {
                    "needs_conversation_code": False,
                    "user_identified": True,
                    "flashed_conversation_code": existing_code
                }
            
            # Extract conversation code from message
            conversation_code = self.extract_conversation_code_from_message(message)
            
            if not conversation_code:
                logger.info("No conversation code found in message and user doesn't have one stored")
                return {
                    "needs_conversation_code": True,
                    "conversation_code_request_message": self.generate_conversation_code_request_message(),
                    "user_identified": False
                }
            
            # Get user data by conversation code
            user_result = await self.get_user_by_conversation_code(conversation_code)
            
            if not user_result["success"]:
                logger.error(f"Failed to get user by conversation code: {user_result['error']}")
                return {
                    "needs_conversation_code": True,
                    "conversation_code_request_message": self.generate_conversation_code_request_message(),
                    "user_identified": False,
                    "error": user_result["error"]
                }
            
            # Extract user information
            flashed_user_data = user_result["user_data"]
            user_info = flashed_user_data.get("user", {})
            flashed_user_id = user_info.get("id")
            
            # Update user_data with conversation code and flashed info
            updated_user_data = user_data.copy()
            updated_user_data.update({
                "flashed_conversation_code": conversation_code,
                "flashed_user_id": flashed_user_id,
                "flashed_user_name": user_info.get("name"),
                "flashed_user_phone": user_info.get("phone"),
                "flashed_user_email": user_info.get("email")
            })
            
            logger.info(f"Successfully identified user via conversation code: {flashed_user_id}")
            
            return {
                "needs_conversation_code": False,
                "user_identified": True,
                "flashed_user_data": flashed_user_data,
                "updated_user_data": updated_user_data,
                "flashed_conversation_code": conversation_code,
                "flashed_user_id": flashed_user_id
            }
            
        except Exception as e:
            logger.error(f"Error in user identification workflow: {str(e)}")
            return {
                "needs_conversation_code": True,
                "conversation_code_request_message": self.generate_conversation_code_request_message(),
                "user_identified": False,
                "error": str(e)
            }


# Convenience functions for direct use
async def check_user_pro_status_by_phone(phone: str) -> Dict[str, Any]:
    """Convenience function to check user Pro status by phone.
    
    Args:
        phone: User phone number
        
    Returns:
        User status information
    """
    checker = UserStatusChecker()
    return await checker.check_user_pro_status_by_phone(phone)


async def handle_user_identification(message: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to handle user identification workflow.
    
    Args:
        message: User message
        user_data: Current user data from database
        
    Returns:
        User identification result
    """
    checker = UserStatusChecker()
    return await checker.handle_user_identification_workflow(message, user_data)


async def prepare_flashinho_v2_for_phone(phone: str) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """Convenience function to prepare Flashinho V2 agent for a phone number.
    
    Args:
        phone: User phone number
        
    Returns:
        Tuple of (agent_config, user_status_info)
    """
    checker = UserStatusChecker()
    return await checker.prepare_agent_config(phone) 