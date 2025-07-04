"""Tools for external agents.

This module provides common tools that can be used by multiple external agents,
avoiding code duplication and making maintenance easier.
"""

# Export Flashed tools
from .flashed.tool import (
    get_user_data,
    get_user_score,
    get_user_roadmap,
    get_user_objectives,
    get_last_card_round,
    get_user_energy,
    get_user_by_pretty_id,
)

from .flashed.provider import FlashedProvider
from .flashed.user_identification import (
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
from .flashed.auth_utils import (
    UserStatusChecker,
    preserve_authentication_state,
    restore_authentication_state,
)
from .flashed.workflow_runner import analyze_student_problem
from .flashed.message_generator import (
    generate_math_processing_message,
    generate_pro_feature_message,
    generate_error_message,
)

# Export Evolution tools if available
try:
    from .evolution.api import send_text_message
except ImportError:
    # Evolution tools might not be available for all agents
    pass

__all__ = [
    # Flashed tools
    "get_user_data",
    "get_user_score",
    "get_user_roadmap",
    "get_user_objectives",
    "get_last_card_round",
    "get_user_energy",
    "get_user_by_pretty_id",
    "FlashedProvider",
    "identify_user_comprehensive",
    "UserIdentificationResult",
    "ensure_user_uuid_matches_flashed_id",
    "make_session_persistent",
    "UserStatusChecker",
    "preserve_authentication_state",
    "restore_authentication_state",
    "analyze_student_problem",
    "generate_math_processing_message",
    "generate_pro_feature_message",
    "generate_error_message",
    # Evolution tools
    "send_text_message",
]