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

        # Update existing messages already in memory
        updated = 0
        for msg in message_history_obj.all_messages():
            if msg.user_id == old_user_id:
                msg.user_id = new_user_uuid
                if update_message(msg):
                    updated += 1
        logger.info("✅ Updated %s messages to new user_id %s", updated, new_user_id)

        # Also update the session row if needed
        session_uuid = uuid.UUID(message_history_obj.session_id)
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
        session_info = message_history_obj.get_session_info()
        if not session_info:
            return
        session = Session(id=session_info.id, user_id=uuid.UUID(new_user_id))
        update_session(session)
        logger.info("✅ Updated session %s to user_id %s", session_info.id, new_user_id)
    except Exception as exc:
        logger.error("Error updating session user_id: %s", exc)


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
        # Skip if already persistent
        if not getattr(message_history_obj, "_local_only", False):
            return

        session_uuid = uuid.UUID(message_history_obj.session_id)
        user_uuid = uuid.UUID(user_id)

        # Save session row if missing
        if not get_session(session_uuid):
            session_row = Session(
                id=session_uuid,
                user_id=user_uuid,
                name=f"Session-{session_uuid}",
                platform="automagik",
            )
            create_session(session_row)
            logger.info("✅ Created session %s in DB", session_uuid)

        # Save local messages to DB
        local_msgs = getattr(message_history_obj, "_local_messages", [])
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
        logger.info("💾 Saved %s local messages for session %s", saved, session_uuid)

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