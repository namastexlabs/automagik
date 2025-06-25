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

from src.memory.message_history import MessageHistory
from src.db.repository.message import update_message, create_message
from src.db.repository.session import (
    update_session,
    get_session,
    create_session,
)
from src.db.models import Session, Message
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
        from src.db.repository.message import list_messages
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
) -> None:
    """Persist a previously local MessageHistory into the database."""
    if not message_history_obj or not user_id:
        return
    try:
        session_uuid = uuid.UUID(message_history_obj.session_id)
        user_uuid = uuid.UUID(user_id)

        # Check if session exists in database regardless of local_only flag
        existing_session = get_session(session_uuid)
        
        # Skip if session exists and is properly linked to this user
        if existing_session and existing_session.user_id == user_uuid:
            # Update the MessageHistory object to mark as persistent if needed
            if getattr(message_history_obj, "_local_only", False):
                message_history_obj._local_only = False
            logger.debug("Session already exists and properly linked, skipping")
            return

        # Create session row if missing or incorrectly linked
        if not existing_session:
            # Try to get the original session name from agent context
            session_name = None
            if hasattr(agent, 'context'):
                # Try multiple ways to get the session name
                session_name = (
                    agent.context.get("session_name") or
                    agent.context.get("whatsapp_session_name")
                )
                
                # If no session name, build it from phone number (flashinho pattern)
                if not session_name:
                    phone = (
                        agent.context.get("whatsapp_user_number") or 
                        agent.context.get("user_phone_number")
                    )
                    if phone:
                        # Clean phone number (remove + and other chars)
                        clean_phone = phone.replace("+", "").replace("-", "").replace(" ", "")
                        session_name = f"flashinho-v2-{clean_phone}"
            
            # Fallback to UUID-based name if no session name found
            if not session_name:
                session_name = f"Session-{session_uuid}"
                
            session_row = Session(
                id=session_uuid,
                user_id=user_uuid,
                name=session_name,
                platform="automagik",
                agent_id=getattr(agent, 'db_id', None),
            )
            create_session(session_row)
            logger.info("✅ Created session %s in DB with name: %s", session_uuid, session_name)
        elif existing_session.user_id != user_uuid:
            # Session exists but linked to different user - update it
            logger.info("🔄 Updating session %s user_id from %s to %s", session_uuid, existing_session.user_id, user_uuid)
            updated_session = Session(
                id=session_uuid,
                user_id=user_uuid,
                name=existing_session.name,
                platform=existing_session.platform,
                agent_id=getattr(agent, 'db_id', None),
                created_at=existing_session.created_at,
            )
            update_session(updated_session)

        # Save local messages to DB, avoiding duplicates
        local_msgs = getattr(message_history_obj, "_local_messages", [])
        
        # Get existing messages to avoid duplicates
        from src.db.repository.message import list_messages
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

        # Mark session as persistent and reload
        message_history_obj._local_only = False
        message_history_obj.user_id = user_uuid
        message_history_obj._local_messages.clear()

    except Exception as exc:
        logger.error("Error persisting session: %s", exc)


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