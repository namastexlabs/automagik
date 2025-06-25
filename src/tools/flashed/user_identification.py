"""User identification utilities for Flashinho agents.

This module provides utilities for user identification and session management
that can be shared between flashinho_v2 and flashinho_pro agents.
"""
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UserIdentificationResult:
    """Result of user identification process."""
    user_id: Optional[str]
    method: Optional[str]
    requires_conversation_code: bool
    conversation_code_extracted: bool = False


def build_external_key(context: Dict[str, Any]) -> Optional[str]:
    """Build external key for user identification.
    
    Args:
        context: Context dictionary with user information
        
    Returns:
        External key string if available, None otherwise
    """
    try:
        # Build external key from context data
        session_name = context.get("session_name")
        whatsapp_id = context.get("whatsapp_user_number") or context.get("user_phone_number")
        
        if session_name and whatsapp_id:
            return f"{session_name}|{whatsapp_id}"
    except Exception as e:
        logger.error(f"Error building external key: {e}")
    return None


async def attach_user_by_external_key(context: Dict[str, Any], external_key: str) -> bool:
    """Attach user by external key lookup.
    
    Args:
        context: Context dictionary to update
        external_key: External key to search for
        
    Returns:
        True if user was found and attached, False otherwise
    """
    try:
        from src.db.repository.user import list_users
        
        users, _ = list_users(page=1, page_size=1000)
        for user in users:
            if user.user_data and user.user_data.get("external_key") == external_key:
                context["user_id"] = str(user.id)
                context["user_identification_method"] = "external_key"
                
                # Update context with user data if available
                if user.user_data:
                    if user.user_data.get("flashed_user_id"):
                        context["flashed_user_id"] = user.user_data["flashed_user_id"]
                    if user.user_data.get("flashed_user_name"):
                        context["flashed_user_name"] = user.user_data["flashed_user_name"]
                    if user.user_data.get("flashed_conversation_code"):
                        context["flashed_conversation_code"] = user.user_data["flashed_conversation_code"]
                
                logger.info(f"Attached user {user.id} via external_key: {external_key}")
                return True
                
    except Exception as e:
        logger.error(f"Error during external_key lookup: {e}")
    return False


async def attach_user_by_flashed_id_lookup(context: Dict[str, Any]) -> bool:
    """Attach user by Flashed ID lookup.
    
    Args:
        context: Context dictionary to update
        
    Returns:
        True if user was found and attached, False otherwise
    """
    try:
        flashed_user_id = context.get("flashed_user_id")
        if not flashed_user_id:
            return False
            
        from src.db.repository.user import list_users
        
        users, _ = list_users(page=1, page_size=1000)
        for user in users:
            if user.user_data and user.user_data.get("flashed_user_id") == flashed_user_id:
                context["user_id"] = str(user.id)
                context["user_identification_method"] = "flashed_id_lookup"
                
                # Update context with additional user data
                if user.user_data.get("flashed_user_name"):
                    context["flashed_user_name"] = user.user_data["flashed_user_name"]
                if user.user_data.get("flashed_conversation_code"):
                    context["flashed_conversation_code"] = user.user_data["flashed_conversation_code"]
                
                logger.info(f"Attached user {user.id} via flashed_id_lookup: {flashed_user_id}")
                return True
                
    except Exception as e:
        logger.error(f"Error during flashed_id_lookup: {e}")
    return False


async def find_user_by_whatsapp_id(whatsapp_id: str) -> Optional[Any]:
    """Find user by WhatsApp ID.
    
    Args:
        whatsapp_id: WhatsApp phone number
        
    Returns:
        User object if found, None otherwise
    """
    try:
        from src.db.repository.user import list_users
        
        users, _ = list_users(page=1, page_size=1000)
        for user in users:
            if user.user_data:
                # Check various phone number fields
                user_phone = (
                    user.user_data.get("whatsapp_user_number") or
                    user.user_data.get("user_phone_number") or
                    user.user_data.get("phone") or
                    user.user_data.get("flashed_user_phone")
                )
                
                if user_phone == str(whatsapp_id):
                    logger.info(f"Found user {user.id} by WhatsApp ID: {whatsapp_id}")
                    return user
                    
    except Exception as e:
        logger.error(f"Error finding user by WhatsApp ID {whatsapp_id}: {e}")
    return None


def user_has_conversation_code(user: Any) -> bool:
    """Check if user has a conversation code stored.
    
    Args:
        user: User object from database
        
    Returns:
        True if user has conversation code, False otherwise
    """
    try:
        if not user or not user.user_data:
            return False
            
        conversation_code = user.user_data.get("flashed_conversation_code")
        return bool(conversation_code and conversation_code.strip())
        
    except Exception as e:
        logger.error(f"Error checking conversation code for user: {e}")
        return False


async def ensure_user_uuid_matches_flashed_id(
    phone_number: str,
    flashed_user_id: str,
    flashed_user_data: Dict[str, Any]
) -> str:
    """Ensure user UUID matches Flashed user ID and update user data.
    
    This is a critical function that ensures synchronization between
    our database and the Flashed system.
    
    Args:
        phone_number: User's phone number
        flashed_user_id: User ID from Flashed system
        flashed_user_data: User data from Flashed API
        
    Returns:
        Final user ID that matches Flashed UUID
    """
    try:
        from src.db.repository.user_uuid_migration import ensure_user_uuid_matches_flashed_id as _ensure_uuid
        
        # Delegate to the existing implementation
        final_user_id = await _ensure_uuid(
            phone_number=phone_number,
            flashed_user_id=flashed_user_id,
            flashed_user_data=flashed_user_data
        )
        
        logger.info(f"UUID synchronization complete for phone {phone_number}: {final_user_id}")
        return final_user_id
        
    except Exception as e:
        logger.error(f"Error in UUID synchronization: {e}")
        raise


async def update_message_history_user_id(message_history_obj: Any, user_id: str) -> None:
    """Update message history with new user ID.
    
    Args:
        message_history_obj: MessageHistory object
        user_id: New user ID to set
    """
    try:
        if message_history_obj and hasattr(message_history_obj, 'user_id'):
            message_history_obj.user_id = user_id
            logger.debug(f"Updated message history user_id to: {user_id}")
    except Exception as e:
        logger.error(f"Error updating message history user_id: {e}")


async def update_session_user_id(message_history_obj: Any, user_id: str) -> None:
    """Update session with new user ID.
    
    Args:
        message_history_obj: MessageHistory object
        user_id: New user ID to set
    """
    try:
        # Import session utilities
        from src.agents.pydanticai.flashinho_v2.session_utils import update_session_user_id as _update_session
        
        await _update_session(message_history_obj, user_id)
        logger.debug(f"Updated session user_id to: {user_id}")
        
    except Exception as e:
        logger.error(f"Error updating session user_id: {e}")


async def make_session_persistent(agent: Any, message_history_obj: Any, user_id: str) -> None:
    """Make session persistent with user ID.
    
    Args:
        agent: Agent instance
        message_history_obj: MessageHistory object
        user_id: User ID for persistence
    """
    try:
        # Import session utilities
        from src.agents.pydanticai.flashinho_v2.session_utils import make_session_persistent as _make_persistent
        
        await _make_persistent(agent, message_history_obj, user_id)
        logger.debug(f"Made session persistent for user: {user_id}")
        
    except Exception as e:
        logger.error(f"Error making session persistent: {e}")


def ensure_session_row(session_id: Any, user_id: Optional[Any]) -> None:
    """Ensure session row exists in database.
    
    Args:
        session_id: Session UUID
        user_id: User UUID (optional)
    """
    try:
        # Import session utilities
        from src.agents.pydanticai.flashinho_v2.session_utils import ensure_session_row as _ensure_session
        
        _ensure_session(session_id, user_id)
        logger.debug(f"Ensured session row exists for session: {session_id}")
        
    except Exception as e:
        logger.error(f"Error ensuring session row: {e}")


# Convenience functions for comprehensive user identification
async def identify_user_comprehensive(
    context: Dict[str, Any],
    channel_payload: Optional[dict] = None,
    message_history_obj: Optional[Any] = None,
    current_message: Optional[str] = None
) -> UserIdentificationResult:
    """Comprehensive user identification process.
    
    Args:
        context: Context dictionary to update
        channel_payload: Optional channel payload
        message_history_obj: Optional message history object
        current_message: Optional current message for conversation code extraction
        
    Returns:
        UserIdentificationResult with identification details
    """
    # Store initial state
    initial_user_id = context.get("user_id")
    history_user_id = message_history_obj.user_id if message_history_obj else None
    
    logger.info(f"User identification starting - Context: {initial_user_id}, History: {history_user_id}")
    
    # Priority: Use user_id from message history if available
    if history_user_id and not initial_user_id:
        context["user_id"] = str(history_user_id)
        logger.info(f"Using user_id from session history: {history_user_id}")
    
    # Try external key identification
    external_key = build_external_key(context)
    if external_key and not context.get("user_id"):
        found_by_key = await attach_user_by_external_key(context, external_key)
        if found_by_key:
            logger.info(f"User identified via external_key: {context.get('user_id')}")
            await _sync_message_history_if_needed(context, message_history_obj, history_user_id)
    
    # Try Flashed ID identification
    if not context.get("user_id"):
        found_by_flashed_id = await attach_user_by_flashed_id_lookup(context)
        if found_by_flashed_id:
            logger.info(f"User identified via flashed_id_lookup: {context.get('user_id')}")
            await _sync_message_history_if_needed(context, message_history_obj, history_user_id)
    
    # Check conversation code requirement
    user_id = context.get("user_id")
    requires_conversation_code = await _check_conversation_code_requirement(context, user_id)
    
    return UserIdentificationResult(
        user_id=user_id,
        method=context.get("user_identification_method"),
        requires_conversation_code=requires_conversation_code
    )


async def _sync_message_history_if_needed(
    context: Dict[str, Any],
    message_history_obj: Optional[Any],
    history_user_id: Optional[str]
) -> None:
    """Sync message history with new user ID if needed."""
    new_user_id = context.get("user_id")
    if message_history_obj and new_user_id and new_user_id != str(history_user_id):
        await update_message_history_user_id(message_history_obj, new_user_id)
        await update_session_user_id(message_history_obj, new_user_id)


async def _check_conversation_code_requirement(context: Dict[str, Any], user_id: Optional[str]) -> bool:
    """Check if user still needs to supply a conversation code."""
    try:
        # Check WhatsApp-based identification first
        whatsapp_id = (
            context.get("whatsapp_user_number") or
            context.get("user_phone_number")
        )
        
        if whatsapp_id:
            user = await find_user_by_whatsapp_id(str(whatsapp_id))
            if user:
                # Update context with this user information
                context.update({
                    "user_id": str(user.id),
                    "flashed_user_id": user.user_data.get("flashed_user_id") if user.user_data else None,
                    "flashed_conversation_code": user.user_data.get("flashed_conversation_code") if user.user_data else None,
                    "flashed_user_name": user.user_data.get("flashed_user_name") if user.user_data else None,
                    "user_identification_method": "whatsapp_id_lookup",
                })
                return not user_has_conversation_code(user)
        
        # Fallback to supplied user_id from context
        if not user_id:
            return True
        
        from src.db.repository.user import get_user
        import uuid as _uuid
        
        db_user = get_user(_uuid.UUID(str(user_id)))
        if not db_user:
            return True
        
        return not user_has_conversation_code(db_user)
        
    except Exception as e:
        logger.error("Error checking conversation code requirement: %s", e)
        return True  # Safe default