"""Common helpers for working with Evolution (WhatsApp-webhook) payloads.

Currently this module simply re-exports the `EvolutionMessagePayload` model
originally defined for `stan_agent`, so that every agent can import it from a
single, shared location without depending on the Stan package layout.

Example
-------
    from src.agents.common.evolution import EvolutionMessagePayload

    payload = EvolutionMessagePayload(**incoming_dict)
    user_number = payload.get_user_number()

In the future we can move or extend additional utilities (e.g. media-sending
helpers) into this module while keeping backward compatibility for existing
imports.
"""

from __future__ import annotations

# Re-export the model from its original location.  Keeping a local alias makes
# the public symbol independent of the original module path, so callers only
# ever need to import *here*.
from src.agents.simple.stan_agent.models import (
    EvolutionMessagePayload as _EvolutionMessagePayload,
)

# Public API
EvolutionMessagePayload = _EvolutionMessagePayload

__all__ = [
    "EvolutionMessagePayload",
] 