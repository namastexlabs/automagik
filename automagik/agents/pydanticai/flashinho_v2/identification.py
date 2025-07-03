"""Unified identification utilities for Flashinho V2.

This thin wrapper consolidates the two former modules
`user_identification.py` and `user_status_checker.py` so that new
contributors only have to import from a single place.

Keeping the original implementations untouched avoids a risky refactor
right now; we just re-export the public classes.
"""

from __future__ import annotations

# Re-export the original classes for compatibility
from .user_identification import FlashinhoProUserMatcher as FlashinhoIdentifier  # noqa: F401
from .user_status_checker import UserStatusChecker  # noqa: F401

import uuid
from typing import Dict, Any
import logging
from automagik.db.repository.user import list_users

__all__ = [
    "FlashinhoIdentifier",
    "UserStatusChecker",
    "build_external_key",
    "attach_user_by_external_key",
    "attach_user_by_flashed_id_lookup",
    "normalize_phone",
    "find_user_by_whatsapp_id",
    "user_has_conversation_code",
]


def build_external_key(context: Dict[str, Any]) -> str | None:
    """Generate stable external key <session_name>|<normalized_phone>."""
    session_name = context.get("session_name")
    phone = (
        context.get("whatsapp_user_number")
        or context.get("user_phone_number")
        or context.get("whatsapp_id")
    )
    if not session_name or not phone:
        return None
    normalized = str(phone).replace("+", "").replace("-", "").replace("@s.whatsapp.net", "")
    return f"{session_name}|{normalized}"


async def attach_user_by_external_key(context: Dict[str, Any], external_key: str) -> bool:
    """Lookup user by external_key and update *context* if found."""
    if not external_key or context.get("user_id"):
        return False
    users, _ = list_users(page=1, page_size=1000)
    for u in users:
        if u.user_data and u.user_data.get("external_key") == external_key:
            context.update(
                {
                    "user_id": str(u.id),
                    "flashed_user_id": u.user_data.get("flashed_user_id"),
                    "flashed_conversation_code": u.user_data.get("flashed_conversation_code"),
                    "flashed_user_name": u.user_data.get("flashed_user_name"),
                    "user_identification_method": "external_key",
                }
            )
            return True
    return False


async def attach_user_by_flashed_id_lookup(context: Dict[str, Any]) -> bool:
    """Fallback user identification by searching for any user with a
    stored ``flashed_user_id``. The first match **with a conversation
    code** wins.

    This mirrors the old ``_attach_user_by_flashed_id_lookup`` method that
    lived inside ``agent.py`` but is now a standalone utility so it can be
    reused by other components without importing the full agent.

    Args:
        context: Mutable per-request context dict coming from the agent.

    Returns:
        ``True`` if a user was found and the context has been updated,
        ``False`` otherwise.
    """
    if context.get("user_id"):
        return False

    logger = logging.getLogger(__name__)

    try:
        logger.info("🔍 Searching for any user with flashed_user_id (fallback lookup)")

        users, _ = list_users(page=1, page_size=1000)

        for user in users:
            user_data = user.user_data or {}
            flashed_user_id = user_data.get("flashed_user_id")
            conversation_code = user_data.get("flashed_conversation_code")

            if flashed_user_id and conversation_code:
                logger.info(
                    "🔍 Found user %s with flashed_user_id %s", user.id, flashed_user_id
                )

                context.update(
                    {
                        "user_id": str(user.id),
                        "flashed_user_id": flashed_user_id,
                        "flashed_conversation_code": conversation_code,
                        "flashed_user_name": user_data.get("flashed_user_name"),
                        "user_identification_method": "flashed_id_lookup",
                    }
                )

                return True

        logger.info("🔍 No user found with flashed_user_id")
        return False

    except Exception as e:
        logger.error("Error in flashed_id lookup: %s", e)
        return False


def normalize_phone(phone: str | None) -> str | None:
    """Return a normalized phone string suitable for comparison."""
    if not phone:
        return None
    return str(phone).replace("+", "").replace("-", "").replace("@s.whatsapp.net", "")


async def find_user_by_whatsapp_id(whatsapp_id: str | None):
    """Return the *first* user whose stored ``whatsapp_id`` matches ``whatsapp_id``.

    It still uses the simple *list all users* approach for now to keep behaviour
    identical to the original code. Optimisation can happen later under a
    dedicated task.
    """
    if not whatsapp_id:
        return None

    norm_target = normalize_phone(whatsapp_id)
    users, _ = list_users(page=1, page_size=1000)
    for user in users:
        stored_phone = user.user_data.get("whatsapp_id") if user.user_data else None
        if stored_phone and normalize_phone(stored_phone) == norm_target:
            return user
    return None


def user_has_conversation_code(user) -> bool:
    """Return *True* if the user already stored a Flashed conversation code."""
    if not user or not user.user_data:
        return False
    return bool(user.user_data.get("flashed_conversation_code")) 