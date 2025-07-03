"""Common helpers for working with Evolution (WhatsApp-webhook) payloads.

This module re-exports the `EvolutionMessagePayload` model from the centralized
src.channels.models location, providing a stable import path for agents that
need to work with Evolution webhook payloads.

Example
-------
    from automagik.agents.common.evolution import EvolutionMessagePayload

    payload = EvolutionMessagePayload(**incoming_dict)
    user_number = payload.get_user_number()

This module provides backward compatibility while channeling imports to the
centralized channel models location.
"""

from __future__ import annotations

# Re-export the model from the centralized channels location. Keeping a local alias makes
# the public symbol independent of the module path, so callers only
# ever need to import *here*.
from automagik.channels.models import (
    EvolutionMessagePayload as _EvolutionMessagePayload,
)

# Public API
EvolutionMessagePayload = _EvolutionMessagePayload

__all__ = [
    "EvolutionMessagePayload",
] 