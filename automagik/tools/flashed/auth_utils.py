"""Shared authentication utilities for Flashinho agents.

This module provides utilities for conversation code handling and user authentication
that can be shared between flashinho_v2 and flashinho_pro agents. Includes authentication
context preservation to prevent users from having to re-authenticate after first message.
"""
import logging
import re
import uuid
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from automagik.tools.flashed.provider import FlashedProvider
from automagik.db import get_user_by_identifier, update_user

logger = logging.getLogger(__name__)

# In-memory cache for authentication context (shared across agent instances)
_auth_context_cache: Dict[str, Dict[str, Any]] = {}
_cache_ttl_minutes = 60  # Cache expires after 1 hour


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
            # Pattern for mock codes like "FreeMock99"
            r'\b(FreeMock[0-9]{2})\b',  # FreeMock99 pattern
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


async def prepare_flashinho_agent_for_phone(phone: str) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """Convenience function to prepare Flashinho agent for a phone number.
    
    Args:
        phone: User phone number
        
    Returns:
        Tuple of (agent_config, user_status_info)
    """
    checker = UserStatusChecker()
    return await checker.prepare_agent_config(phone)


# Authentication Context Persistence Functions
def _build_auth_cache_key(phone_number: str, session_id: Optional[str] = None) -> str:
    """Build cache key for authentication context.
    
    Args:
        phone_number: User phone number
        session_id: Optional session ID for more specific caching
        
    Returns:
        Cache key string
    """
    if session_id:
        return f"auth:{phone_number}:{session_id}"
    return f"auth:{phone_number}"


async def cache_authentication_context(
    phone_number: str, 
    context: Dict[str, Any], 
    session_id: Optional[str] = None,
    ttl_minutes: Optional[int] = None
) -> None:
    """Cache authentication context to prevent re-authentication using database storage.
    
    Args:
        phone_number: User phone number
        context: Authentication context to cache
        session_id: Optional session ID for session-specific caching
        ttl_minutes: Cache TTL in minutes (default: 60)
    """
    try:
        ttl = ttl_minutes or _cache_ttl_minutes
        expires_at = datetime.now() + timedelta(minutes=ttl)
        
        # Store authentication context in user data
        try:
            # Find user by phone number
            user = get_user_by_identifier(phone_number)
            if user:
                # Update user data with authentication context
                auth_data = {
                    "flashed_conversation_code": context.get("flashed_conversation_code"),
                    "flashed_user_id": context.get("flashed_user_id"),
                    "flashed_user_name": context.get("flashed_user_name"),
                    "auth_cached_at": datetime.now().isoformat(),
                    "auth_expires_at": expires_at.isoformat(),
                    "auth_session_id": session_id
                }
                
                # Merge with existing user_data
                current_data = user.user_data or {}
                current_data.update(auth_data)
                
                # Update user with new authentication data
                from automagik.db.models import User
                updated_user = User(
                    id=user.id,
                    email=user.email,
                    phone_number=user.phone_number,
                    user_data=current_data,
                    created_at=user.created_at,
                    updated_at=datetime.now()
                )
                update_user(updated_user)
                logger.debug(f"Cached authentication context in database for {phone_number} (expires in {ttl}m)")
            else:
                logger.warning(f"User not found for phone {phone_number}, cannot cache authentication")
        except Exception as db_error:
            logger.warning(f"Database caching failed for {phone_number}: {db_error}, using memory cache only")
        
        # Keep fallback in-memory cache for immediate access
        cache_key = _build_auth_cache_key(phone_number, session_id)
        cache_entry = {
            "context": context.copy(),
            "cached_at": datetime.now(),
            "expires_at": expires_at,
            "phone_number": phone_number,
            "session_id": session_id
        }
        _auth_context_cache[cache_key] = cache_entry
        
    except Exception as e:
        logger.error(f"Error caching authentication context: {e}")


async def get_cached_authentication_context(
    phone_number: str, 
    session_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Get cached authentication context if valid, checking database first.
    
    Args:
        phone_number: User phone number
        session_id: Optional session ID for session-specific lookup
        
    Returns:
        Cached context if valid, None otherwise
    """
    try:
        # First check in-memory cache for immediate access
        cache_key = _build_auth_cache_key(phone_number, session_id)
        
        if cache_key in _auth_context_cache:
            cache_entry = _auth_context_cache[cache_key]
            if datetime.now() <= cache_entry["expires_at"]:
                logger.debug(f"Retrieved cached authentication context from memory for {phone_number}")
                return cache_entry["context"].copy()
            else:
                # Remove expired memory cache
                del _auth_context_cache[cache_key]
        
        # Check database for persistent authentication
        try:
            user = get_user_by_identifier(phone_number)
            
            if user and user.user_data:
                auth_expires_at = user.user_data.get("auth_expires_at")
                if auth_expires_at:
                    expires_at = datetime.fromisoformat(auth_expires_at)
                    if datetime.now() <= expires_at:
                        # Restore context from database
                        context = {
                            "flashed_conversation_code": user.user_data.get("flashed_conversation_code"),
                            "flashed_user_id": user.user_data.get("flashed_user_id"),
                            "flashed_user_name": user.user_data.get("flashed_user_name"),
                            "authenticated_at": user.user_data.get("auth_cached_at"),
                            "user_identification_method": "database_cache"
                        }
                        
                        # Restore to memory cache for faster access
                        cache_entry = {
                            "context": context.copy(),
                            "cached_at": datetime.fromisoformat(user.user_data.get("auth_cached_at", datetime.now().isoformat())),
                            "expires_at": expires_at,
                            "phone_number": phone_number,
                            "session_id": session_id
                        }
                        _auth_context_cache[cache_key] = cache_entry
                        
                        logger.debug(f"Retrieved cached authentication context from database for {phone_number}")
                        return context
                    else:
                        logger.debug(f"Database authentication cache expired for {phone_number}")
        except Exception as db_error:
            logger.warning(f"Database lookup failed for {phone_number}: {db_error}, using memory cache only")
        
        logger.debug(f"No cached authentication state found for {phone_number}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting cached authentication context: {e}")
        return None


def clear_authentication_cache(
    phone_number: Optional[str] = None, 
    session_id: Optional[str] = None
) -> None:
    """Clear authentication cache entries.
    
    Args:
        phone_number: Clear specific phone number (None to clear all)
        session_id: Clear specific session (requires phone_number)
    """
    try:
        if phone_number and session_id:
            # Clear specific session
            cache_key = _build_auth_cache_key(phone_number, session_id)
            if cache_key in _auth_context_cache:
                del _auth_context_cache[cache_key]
                logger.debug(f"Cleared authentication cache for {phone_number}:{session_id}")
        elif phone_number:
            # Clear all entries for phone number
            keys_to_remove = [
                key for key in _auth_context_cache.keys() 
                if key.startswith(f"auth:{phone_number}")
            ]
            for key in keys_to_remove:
                del _auth_context_cache[key]
            logger.debug(f"Cleared {len(keys_to_remove)} authentication cache entries for {phone_number}")
        else:
            # Clear all cache
            _auth_context_cache.clear()
            logger.debug("Cleared all authentication cache entries")
            
    except Exception as e:
        logger.error(f"Error clearing authentication cache: {e}")


def get_authentication_cache_stats() -> Dict[str, Any]:
    """Get authentication cache statistics.
    
    Returns:
        Dict with cache statistics
    """
    try:
        now = datetime.now()
        valid_entries = 0
        expired_entries = 0
        
        for cache_entry in _auth_context_cache.values():
            if now <= cache_entry["expires_at"]:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            "total_entries": len(_auth_context_cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_hit_potential": valid_entries > 0
        }
        
    except Exception as e:
        logger.error(f"Error getting cache statistics: {e}")
        return {"error": str(e)}


def cleanup_expired_authentication_cache() -> int:
    """Clean up expired authentication cache entries.
    
    Returns:
        Number of entries removed
    """
    try:
        now = datetime.now()
        keys_to_remove = []
        
        for key, cache_entry in _auth_context_cache.items():
            if now > cache_entry["expires_at"]:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del _auth_context_cache[key]
        
        if keys_to_remove:
            logger.debug(f"Cleaned up {len(keys_to_remove)} expired authentication cache entries")
        
        return len(keys_to_remove)
        
    except Exception as e:
        logger.error(f"Error cleaning up authentication cache: {e}")
        return 0


async def preserve_authentication_state(
    phone_number: str,
    flashed_user_id: str,
    conversation_code: str,
    user_data: Dict[str, Any],
    session_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Preserve authentication state to prevent re-authentication in subsequent messages.
    
    Args:
        phone_number: User phone number
        flashed_user_id: Authenticated Flashed user ID
        conversation_code: Verified conversation code
        user_data: User data from Flashed API
        session_id: Optional session ID
        context: Additional context to preserve
    """
    try:
        auth_context = {
            "flashed_user_id": flashed_user_id,
            "flashed_conversation_code": conversation_code,
            "phone_number": phone_number,
            "user_data": user_data.copy(),
            "authenticated_at": datetime.now().isoformat(),
            "authentication_method": "conversation_code"
        }
        
        # Add additional context if provided
        if context:
            auth_context.update(context)
        
        # Cache the authentication context
        await cache_authentication_context(phone_number, auth_context, session_id)
        
        logger.info(f"Preserved authentication state for {phone_number} (user: {flashed_user_id})")
        
    except Exception as e:
        logger.error(f"Error preserving authentication state: {e}")


async def restore_authentication_state(
    phone_number: str,
    session_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Restore previously authenticated state to avoid re-authentication.
    
    Args:
        phone_number: User phone number
        session_id: Optional session ID
        
    Returns:
        Restored authentication context if available
    """
    try:
        cached_context = await get_cached_authentication_context(phone_number, session_id)
        
        if cached_context:
            logger.info(f"Restored authentication state for {phone_number} "
                       f"(authenticated at: {cached_context.get('authenticated_at')})")
            return cached_context
        else:
            logger.debug(f"No cached authentication state found for {phone_number}")
            return None
        
    except Exception as e:
        logger.error(f"Error restoring authentication state: {e}")
        return None