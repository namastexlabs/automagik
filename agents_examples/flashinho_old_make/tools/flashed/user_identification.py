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
        from automagik.db.repository.user import list_users
        
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
            
        from automagik.db.repository.user import list_users
        
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
        from automagik.db.repository.user import list_users
        
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
    flashed_user_data: Dict[str, Any],
    existing_sessions: Optional[list] = None
) -> str:
    """Ensure user UUID matches Flashed user ID and update user data.
    
    This is a critical function that ensures synchronization between
    our database and the Flashed system. It also handles session migration
    to prevent authentication persistence issues.
    
    Args:
        phone_number: User's phone number
        flashed_user_id: User ID from Flashed system
        flashed_user_data: User data from Flashed API
        existing_sessions: List of existing session IDs to migrate (optional)
        
    Returns:
        Final user ID that matches Flashed UUID
    """
    try:
        from automagik.db.repository.user_uuid_migration import ensure_user_uuid_matches_flashed_id as _ensure_uuid
        
        # Delegate to the existing implementation
        final_user_id = await _ensure_uuid(
            phone_number=phone_number,
            flashed_user_id=flashed_user_id,
            flashed_user_data=flashed_user_data
        )
        
        # If sessions were provided and user conversion happened, update sessions
        if existing_sessions and final_user_id == flashed_user_id:
            await _update_sessions_after_user_conversion(existing_sessions, final_user_id)
        
        logger.info(f"UUID synchronization complete for phone {phone_number}: {final_user_id}")
        return final_user_id
        
    except Exception as e:
        logger.error(f"Error in UUID synchronization: {e}")
        raise


async def _update_sessions_after_user_conversion(session_ids: list, new_user_id: str) -> None:
    """Update existing sessions after user conversion to maintain authentication.
    
    Args:
        session_ids: List of session IDs to update
        new_user_id: New user UUID to assign to sessions
    """
    try:
        import uuid as _uuid
        from automagik.db.repository.session import get_session, update_session
        from automagik.db.models import Session
        
        new_user_uuid = _uuid.UUID(new_user_id)
        updated_count = 0
        
        for session_id in session_ids:
            try:
                session_uuid = _uuid.UUID(str(session_id))
                existing_session = get_session(session_uuid)
                
                if existing_session and existing_session.user_id != new_user_uuid:
                    # Update session to use new user ID
                    updated_session = Session(
                        id=session_uuid,
                        user_id=new_user_uuid,
                        name=existing_session.name,
                        platform=existing_session.platform,
                        agent_id=existing_session.agent_id,
                        created_at=existing_session.created_at,
                    )
                    
                    if update_session(updated_session):
                        updated_count += 1
                        logger.info(f"✅ Updated session {session_uuid} to use new user_id {new_user_id}")
                    else:
                        logger.warning(f"❌ Failed to update session {session_uuid}")
                        
            except Exception as e:
                logger.error(f"Error updating session {session_id}: {e}")
                continue
        
        logger.info(f"Updated {updated_count} sessions for user conversion to {new_user_id}")
        
    except Exception as e:
        logger.error(f"Error updating sessions after user conversion: {e}")


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
        from automagik.agents.pydanticai.flashinho_v2.session_utils import update_session_user_id as _update_session
        
        await _update_session(message_history_obj, user_id)
        logger.debug(f"Updated session user_id to: {user_id}")
        
    except Exception as e:
        logger.error(f"Error updating session user_id: {e}")


async def make_session_persistent(agent: Any, message_history_obj: Any, user_id: str, force_user_update: bool = False) -> None:
    """Make session persistent with user ID and optional forced user update.
    
    Args:
        agent: Agent instance
        message_history_obj: MessageHistory object
        user_id: User ID for persistence
        force_user_update: Force session user_id update even if session exists
    """
    try:
        # Import session utilities
        from automagik.agents.pydanticai.flashinho_v2.session_utils import make_session_persistent as _make_persistent
        
        await _make_persistent(agent, message_history_obj, user_id, force_user_update)
        logger.debug(f"Made session persistent for user: {user_id} (force_update={force_user_update})")
        
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
        from automagik.agents.pydanticai.flashinho_v2.session_utils import ensure_session_row as _ensure_session
        
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
    """Comprehensive user identification process with session persistence support.
    
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
    session_id = context.get("session_id")
    
    logger.info(f"User identification starting - Context: {initial_user_id}, History: {history_user_id}, Session: {session_id}")
    
    # Check for existing authenticated user by flashed_user_id first
    flashed_user_id = context.get("flashed_user_id")
    if flashed_user_id and not context.get("user_id"):
        found_by_flashed_id = await attach_user_by_flashed_id_lookup(context)
        if found_by_flashed_id:
            logger.info(f"User identified via flashed_id_lookup: {context.get('user_id')}")
            # If we found a user by flashed_id, ensure session is properly linked
            await _sync_message_history_if_needed(context, message_history_obj, history_user_id, update_session=True)
    
    # Priority: Use user_id from message history if available and no flashed_user_id conflict
    if history_user_id and not context.get("user_id"):
        context["user_id"] = str(history_user_id)
        logger.info(f"Using user_id from session history: {history_user_id}")
    
    # Try external key identification
    external_key = build_external_key(context)
    if external_key and not context.get("user_id"):
        found_by_key = await attach_user_by_external_key(context, external_key)
        if found_by_key:
            logger.info(f"User identified via external_key: {context.get('user_id')}")
            await _sync_message_history_if_needed(context, message_history_obj, history_user_id)
    
    # Final fallback: Try Flashed ID identification if still not found
    if not context.get("user_id"):
        found_by_flashed_id = await attach_user_by_flashed_id_lookup(context)
        if found_by_flashed_id:
            logger.info(f"User identified via flashed_id_lookup (fallback): {context.get('user_id')}")
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
    history_user_id: Optional[str],
    update_session: bool = False
) -> None:
    """Sync message history with new user ID if needed."""
    new_user_id = context.get("user_id")
    session_id = context.get("session_id")
    
    if message_history_obj and new_user_id and new_user_id != str(history_user_id):
        logger.info(f"🔄 Syncing message history: {history_user_id} → {new_user_id}")
        await update_message_history_user_id(message_history_obj, new_user_id)
        await update_session_user_id(message_history_obj, new_user_id)
        
        # If session update is explicitly requested, also update session directly
        if update_session and session_id:
            try:
                import uuid as _uuid
                from automagik.db.repository.session import get_session, update_session as _update_session
                from automagik.db.models import Session
                
                session_uuid = _uuid.UUID(str(session_id))
                new_user_uuid = _uuid.UUID(new_user_id)
                existing_session = get_session(session_uuid)
                
                if existing_session and existing_session.user_id != new_user_uuid:
                    updated_session = Session(
                        id=session_uuid,
                        user_id=new_user_uuid,
                        name=existing_session.name,
                        platform=existing_session.platform,
                        agent_id=existing_session.agent_id,
                        created_at=existing_session.created_at,
                    )
                    
                    if _update_session(updated_session):
                        logger.info(f"✅ Updated session {session_uuid} user_id: {history_user_id} → {new_user_id}")
                    else:
                        logger.warning(f"❌ Failed to update session {session_uuid}")
                        
            except Exception as e:
                logger.error(f"Error updating session during sync: {e}")


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
        
        from automagik.db.repository.user import get_user
        import uuid as _uuid
        
        db_user = get_user(_uuid.UUID(str(user_id)))
        if not db_user:
            return True
        
        return not user_has_conversation_code(db_user)
        
    except Exception as e:
        logger.error("Error checking conversation code requirement: %s", e)
        return True  # Safe default


# Database Consistency Validation Functions
async def validate_session_user_consistency(
    phone_number: Optional[str] = None,
    session_id: Optional[str] = None,
    fix_inconsistencies: bool = False
) -> Dict[str, Any]:
    """Validate and optionally fix session-user relationship consistency.
    
    Args:
        phone_number: Check specific phone number (None for all)
        session_id: Check specific session (None for all)
        fix_inconsistencies: Whether to fix found inconsistencies
        
    Returns:
        Dict with validation results and fixes applied
    """
    try:
        import uuid as _uuid
        from automagik.db.repository.session import list_sessions, get_session, update_session
        from automagik.db.repository.user import list_users, get_user
        from automagik.db.repository.message import list_messages
        from automagik.db.models import Session
        
        results = {
            "sessions_checked": 0,
            "inconsistencies_found": 0,
            "fixes_applied": 0,
            "errors": [],
            "details": []
        }
        
        # Get sessions to check
        if session_id:
            session_uuid = _uuid.UUID(str(session_id))
            session = get_session(session_uuid)
            sessions_to_check = [session] if session else []
        else:
            # Get all sessions (or filter by phone number if provided)
            sessions_to_check, _ = list_sessions(page=1, page_size=1000)
            
            # Filter by phone number if provided
            if phone_number:
                filtered_sessions = []
                for session in sessions_to_check:
                    if session.name and phone_number.replace("+", "").replace("-", "").replace(" ", "") in session.name:
                        filtered_sessions.append(session)
                sessions_to_check = filtered_sessions
        
        # Check each session
        for session in sessions_to_check:
            results["sessions_checked"] += 1
            
            try:
                # Check if user exists
                if session.user_id:
                    user = get_user(session.user_id)
                    if not user:
                        # Orphaned session - user doesn't exist
                        inconsistency = {
                            "type": "orphaned_session",
                            "session_id": str(session.id),
                            "user_id": str(session.user_id),
                            "session_name": session.name,
                            "issue": "Session references non-existent user"
                        }
                        
                        results["inconsistencies_found"] += 1
                        results["details"].append(inconsistency)
                        
                        if fix_inconsistencies:
                            # Option 1: Try to find correct user by phone number
                            if session.name and any(char.isdigit() for char in session.name):
                                # Extract phone number from session name
                                import re
                                phone_match = re.search(r'(\d{10,15})', session.name)
                                if phone_match:
                                    phone = phone_match.group(1)
                                    correct_user = await find_user_by_whatsapp_id(phone)
                                    if correct_user:
                                        # Update session to correct user
                                        updated_session = Session(
                                            id=session.id,
                                            user_id=correct_user.id,
                                            name=session.name,
                                            platform=session.platform,
                                            agent_id=session.agent_id,
                                            created_at=session.created_at,
                                        )
                                        update_session(updated_session)
                                        results["fixes_applied"] += 1
                                        inconsistency["fixed"] = True
                                        inconsistency["fix_action"] = f"Updated to correct user {correct_user.id}"
                
                # Check messages consistency
                if session.user_id:
                    messages = list_messages(session.id, sort_desc=False)
                    for message in messages:
                        if message.user_id != session.user_id:
                            inconsistency = {
                                "type": "message_user_mismatch",
                                "session_id": str(session.id),
                                "session_user_id": str(session.user_id),
                                "message_id": str(message.id),
                                "message_user_id": str(message.user_id),
                                "issue": "Message user_id doesn't match session user_id"
                            }
                            
                            results["inconsistencies_found"] += 1
                            results["details"].append(inconsistency)
                            
                            if fix_inconsistencies:
                                # Update message to match session user_id
                                message.user_id = session.user_id
                                from automagik.db.repository.message import update_message
                                if update_message(message):
                                    results["fixes_applied"] += 1
                                    inconsistency["fixed"] = True
                                    inconsistency["fix_action"] = f"Updated message user_id to {session.user_id}"
                
            except Exception as e:
                error_msg = f"Error checking session {session.id}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
        
        logger.info(f"Session consistency check complete: {results['sessions_checked']} sessions, "
                   f"{results['inconsistencies_found']} issues, {results['fixes_applied']} fixes")
        
        return results
        
    except Exception as e:
        error_msg = f"Error in session consistency validation: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}


async def cleanup_authentication_orphans(dry_run: bool = True) -> Dict[str, Any]:
    """Clean up orphaned authentication data and sessions.
    
    Args:
        dry_run: If True, only report what would be cleaned up
        
    Returns:
        Dict with cleanup results
    """
    try:
        from automagik.db.repository.session import list_sessions
        from automagik.db.repository.message import list_messages
        from automagik.db.repository.user import get_user
        
        results = {
            "orphaned_sessions": 0,
            "orphaned_messages": 0,
            "cleaned_up": 0,
            "dry_run": dry_run,
            "details": []
        }
        
        # Get all sessions
        sessions, _ = list_sessions(page=1, page_size=1000)
        
        for session in sessions:
            if session.user_id:
                # Check if user exists
                user = get_user(session.user_id)
                if not user:
                    results["orphaned_sessions"] += 1
                    
                    # Check for orphaned messages
                    messages = list_messages(session.id, sort_desc=False)
                    message_count = len(messages)
                    
                    detail = {
                        "session_id": str(session.id),
                        "user_id": str(session.user_id),
                        "session_name": session.name,
                        "message_count": message_count,
                        "created_at": session.created_at.isoformat() if session.created_at else None
                    }
                    
                    if not dry_run:
                        # Delete orphaned messages first
                        for message in messages:
                            from automagik.db.repository.message import delete_message
                            delete_message(message.id)
                        
                        # Delete orphaned session
                        from automagik.db.repository.session import delete_session
                        delete_session(session.id)
                        
                        results["cleaned_up"] += 1
                        detail["cleaned"] = True
                    
                    results["details"].append(detail)
        
        logger.info(f"Authentication cleanup {'simulation' if dry_run else 'complete'}: "
                   f"{results['orphaned_sessions']} orphaned sessions, "
                   f"{results['cleaned_up']} cleaned up")
        
        return results
        
    except Exception as e:
        error_msg = f"Error in authentication cleanup: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}