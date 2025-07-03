"""Session-history utilities for Flashinho V2.

These helpers are MOVED verbatim from the original `agent.py` so that the
agent file can be simplified.  They expect the same parameters as the
old private methods but are now **stand-alone**, making them reusable and
unit-testable.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from automagik.memory.message_history import MessageHistory
from automagik.db.repository.message import update_message, create_message
from automagik.db.repository.session import (
    update_session,
    get_session,
    create_session,
)
from automagik.db.models import Session, Message
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# update_message_history_user_id
# ---------------------------------------------------------------------------
async def update_message_history_user_id(
    message_history_obj: MessageHistory,
    new_user_id: str,
) -> None:
    """Update all messages in *message_history_obj* to the new_user_id."""
    try:
        old_user_id = message_history_obj.user_id
        new_user_uuid = uuid.UUID(new_user_id)

        logger.info("🔄 Updating MessageHistory user_id from %s to %s", old_user_id, new_user_id)

        # Update the MessageHistory object itself
        message_history_obj.user_id = new_user_uuid

        # Update existing messages in the database directly
        # We need to work with database Message objects, not PydanticAI messages
        from automagik.db.repository.message import list_messages
        session_uuid = uuid.UUID(message_history_obj.session_id)
        
        # Get all database messages for this session
        db_messages = list_messages(session_uuid, sort_desc=False)
        updated = 0
        
        for db_msg in db_messages:
            # Update messages that either have the old_user_id or None (unassigned messages)
            if db_msg.user_id == old_user_id or (old_user_id is None and db_msg.user_id is None):
                db_msg.user_id = new_user_uuid
                if update_message(db_msg):
                    updated += 1
        logger.info("✅ Updated %s database messages to new user_id %s", updated, new_user_id)

        # Also update the session row if needed
        session = get_session(session_uuid)
        if session and session.user_id == old_user_id:
            session.user_id = new_user_uuid
            update_session(session)
            logger.info("✅ Updated session %s user_id to %s", session_uuid, new_user_id)

    except Exception as exc:
        logger.error("❌ Error in update_message_history_user_id: %s", exc)


# ---------------------------------------------------------------------------
# update_session_user_id
# ---------------------------------------------------------------------------
async def update_session_user_id(
    message_history_obj: Optional[MessageHistory],
    new_user_id: str,
) -> None:
    if not message_history_obj or not new_user_id:
        return
    try:
        session_uuid = uuid.UUID(message_history_obj.session_id)
        new_user_uuid = uuid.UUID(new_user_id)
        
        # Get the existing session from database
        session = get_session(session_uuid)
        if not session:
            logger.warning(f"Session {session_uuid} not found in database")
            return
            
        # Update the session's user_id
        session.user_id = new_user_uuid
        update_session(session)
        logger.info("✅ Updated session %s to user_id %s", session_uuid, new_user_id)
    except Exception as exc:
        logger.error("❌ Error updating session user_id: %s", exc)


# ---------------------------------------------------------------------------
# make_session_persistent
# ---------------------------------------------------------------------------
async def make_session_persistent(
    agent,  # FlashinhoV2 instance – needed for context & db_id
    message_history_obj: Optional[MessageHistory],
    user_id: str,
    force_user_update: bool = False,
) -> None:
    """Persist a previously local MessageHistory into the database with improved user conversion support.
    
    Args:
        agent: Agent instance for context and db_id
        message_history_obj: MessageHistory object to persist
        user_id: User ID to link session to
        force_user_update: If True, always update session user_id even if session exists
    """
    if not message_history_obj or not user_id:
        return
    try:
        session_uuid = uuid.UUID(message_history_obj.session_id)
        user_uuid = uuid.UUID(user_id)

        # Check if session exists in database regardless of local_only flag
        existing_session = get_session(session_uuid)
        
        # Skip if session exists and is properly linked to this user (unless forced update)
        if existing_session and existing_session.user_id == user_uuid and not force_user_update:
            # Update the MessageHistory object to mark as persistent if needed
            if getattr(message_history_obj, "_local_only", False):
                message_history_obj._local_only = False
            logger.debug("Session already exists and properly linked, skipping")
            return

        # Handle session creation or user migration
        if not existing_session:
            # Create new session
            session_name = _build_session_name(agent, session_uuid)
            # Get the correct agent ID from database if needed
            agent_db_id = getattr(agent, 'db_id', None)
            if not agent_db_id and hasattr(agent, '__class__'):
                # Try to get agent ID by name
                try:
                    from automagik.db.repository.agent import get_agent_by_name
                    agent_name = agent.__class__.__name__.lower().replace('agent', '').replace('flashinho', 'flashinho_pro')
                    db_agent = get_agent_by_name(agent_name)
                    if db_agent:
                        agent_db_id = db_agent.id
                        # Also set it on the agent for future use
                        agent.db_id = agent_db_id
                        logger.info(f"Found agent {agent_name} with ID {agent_db_id}")
                except Exception as e:
                    logger.warning(f"Could not find agent in database: {e}")
            
            session_row = Session(
                id=session_uuid,
                user_id=user_uuid,
                name=session_name,
                platform="automagik",
                agent_id=agent_db_id,  # This can be None if agent not found
            )
            created_session_id = create_session(session_row)
            if created_session_id:
                logger.info("✅ Created session %s in DB with name: %s", session_uuid, session_name)
                # Verify session was actually created
                verification_session = get_session(session_uuid)
                if not verification_session:
                    logger.error("❌ Session creation verification failed for %s", session_uuid)
                    raise Exception(f"Session {session_uuid} was not properly created in database")
            else:
                logger.error("❌ Failed to create session %s", session_uuid)
                raise Exception(f"Failed to create session {session_uuid}")
            
        elif existing_session.user_id != user_uuid or force_user_update:
            # Session exists but needs user migration or forced update
            old_user_id = existing_session.user_id
            logger.info("🔄 Updating session %s user_id from %s to %s (force=%s)", 
                       session_uuid, old_user_id, user_uuid, force_user_update)
            
            # Migrate all related data for this session
            await _migrate_session_data(session_uuid, old_user_id, user_uuid)
            
            # Update session record
            updated_session = Session(
                id=session_uuid,
                user_id=user_uuid,
                name=existing_session.name,
                platform=existing_session.platform,
                agent_id=getattr(agent, 'db_id', None),
                created_at=existing_session.created_at,
            )
            update_session(updated_session)
            logger.info("✅ Session user migration completed: %s → %s", old_user_id, user_uuid)

        # Save local messages to DB, avoiding duplicates  
        await _save_local_messages_to_db(message_history_obj, session_uuid, user_uuid, agent)

        # Mark session as persistent and update message history
        message_history_obj._local_only = False
        message_history_obj.user_id = user_uuid
        message_history_obj._local_messages.clear()

    except Exception as exc:
        logger.error("Error persisting session: %s", exc)


def _build_session_name(agent, session_uuid: uuid.UUID) -> str:
    """Build appropriate session name from agent context."""
    session_name = None
    
    if hasattr(agent, 'context'):
        # Try multiple ways to get the session name
        session_name = (
            agent.context.get("session_name") or
            agent.context.get("whatsapp_session_name")
        )
        
        # If no session name, only then build it from phone number as fallback
        # IMPORTANT: Agents should respect session names from API, not override them
        if not session_name:
            phone = (
                agent.context.get("whatsapp_user_number") or 
                agent.context.get("user_phone_number")
            )
            if phone:
                # Clean phone number (remove + and other chars)
                clean_phone = phone.replace("+", "").replace("-", "").replace(" ", "")
                # FALLBACK ONLY: Create session name only if API didn't provide one
                # This should match the API controller pattern for consistency
                session_name = f"whatsapp-fallback-{clean_phone}"
    
    # Fallback to UUID-based name if no session name found
    return session_name or f"Session-{session_uuid}"


async def _migrate_session_data(session_uuid: uuid.UUID, old_user_id: uuid.UUID, new_user_id: uuid.UUID) -> None:
    """Migrate all session-related data from old user to new user."""
    try:
        from automagik.db.repository.message import list_messages, update_message
        
        # Get all messages for this session
        messages = list_messages(session_uuid, sort_desc=False)
        updated_count = 0
        
        for message in messages:
            if message.user_id == old_user_id:
                # Update message user_id
                message.user_id = new_user_id
                if update_message(message):
                    updated_count += 1
                    
        logger.info("Migrated %d messages for session %s: %s → %s", 
                   updated_count, session_uuid, old_user_id, new_user_id)
                   
    except Exception as e:
        logger.error("Error migrating session data for %s: %s", session_uuid, e)


async def _save_local_messages_to_db(
    message_history_obj: MessageHistory, 
    session_uuid: uuid.UUID, 
    user_uuid: uuid.UUID, 
    agent
) -> None:
    """Save local messages to database, avoiding duplicates."""
    try:
        local_msgs = getattr(message_history_obj, "_local_messages", [])
        
        # Get existing messages to avoid duplicates
        from automagik.db.repository.message import list_messages
        existing_messages = list_messages(session_uuid, sort_desc=False)
        existing_content = {(msg.role, msg.text_content.strip()) for msg in existing_messages}
        
        saved = 0
        for local_msg in local_msgs:
            role = "user"
            content = ""
            if isinstance(local_msg, ModelRequest):
                role = "user"
                for part in local_msg.parts:
                    if isinstance(part, UserPromptPart):
                        content = part.content; break
            elif isinstance(local_msg, ModelResponse):
                role = "assistant"
                for part in local_msg.parts:
                    if isinstance(part, TextPart):
                        content = part.content; break
            
            if content:
                # Check if this message already exists
                content_key = (role, content.strip())
                if content_key in existing_content:
                    logger.debug(f"Skipping duplicate message: {role} - {content[:50]}...")
                    continue
                
                msg_row = Message(
                    id=uuid.uuid4(),
                    session_id=session_uuid,
                    user_id=user_uuid,
                    agent_id=agent.db_id,
                    role=role,
                    text_content=content,
                    message_type="text",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                if create_message(msg_row):
                    saved += 1
                    existing_content.add(content_key)  # Add to set to prevent further duplicates
                    
        logger.info("💾 Saved %s local messages for session %s (skipped duplicates)", saved, session_uuid)
        
    except Exception as e:
        logger.error("Error saving local messages: %s", e)


# ---------------------------------------------------------------------------
# ensure_session_row
# ---------------------------------------------------------------------------
def ensure_session_row(session_id: uuid.UUID, user_id: uuid.UUID | None = None) -> None:
    """Idempotently create a *session* row so that FK constraints on
    *message* inserts never fail.

    This is a thin wrapper used by agents that construct `MessageHistory`
    objects in *local* mode first and only later persist them.
    """
    try:
        if get_session(session_id):
            return
        session_row = Session(
            id=session_id,
            user_id=user_id,
            name=f"Session-{session_id}",
            platform="automagik",
        )
        create_session(session_row)
        logger.info("✅ ensure_session_row created session %s", session_id)
    except Exception as exc:
        logger.error("❌ ensure_session_row failed: %s", exc) 