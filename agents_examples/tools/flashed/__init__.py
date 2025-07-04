"""Flashed API integration tools.

This module provides tools for interacting with the Flashed educational platform.
"""

from .tool import (
    get_user_data,
    get_user_score,
    get_user_roadmap,
    get_user_objectives,
    get_last_card_round,
    get_user_energy,
    get_user_by_pretty_id,
)

from .provider import FlashedProvider

from .user_identification import (
    identify_user_comprehensive,
    UserIdentificationResult,
    ensure_user_uuid_matches_flashed_id,
    make_session_persistent,
    build_external_key,
    attach_user_by_external_key,
    attach_user_by_flashed_id_lookup,
    find_user_by_whatsapp_id,
    user_has_conversation_code,
    update_message_history_user_id,
    update_session_user_id,
    ensure_session_row,
)

from .auth_utils import (
    UserStatusChecker,
    preserve_authentication_state,
    restore_authentication_state,
)

from .workflow_runner import analyze_student_problem

from .message_generator import (
    generate_math_processing_message,
    generate_pro_feature_message,
    generate_error_message,
)

__all__ = [
    # Tools
    "get_user_data",
    "get_user_score",
    "get_user_roadmap",
    "get_user_objectives",
    "get_last_card_round",
    "get_user_energy",
    "get_user_by_pretty_id",
    # Provider
    "FlashedProvider",
    # User identification
    "identify_user_comprehensive",
    "UserIdentificationResult",
    "ensure_user_uuid_matches_flashed_id",
    "make_session_persistent",
    "build_external_key",
    "attach_user_by_external_key",
    "attach_user_by_flashed_id_lookup",
    "find_user_by_whatsapp_id",
    "user_has_conversation_code",
    "update_message_history_user_id",
    "update_session_user_id",
    "ensure_session_row",
    # Auth utils
    "UserStatusChecker",
    "preserve_authentication_state", 
    "restore_authentication_state",
    # Workflow runner
    "analyze_student_problem",
    # Message generator
    "generate_math_processing_message",
    "generate_pro_feature_message",
    "generate_error_message",
]