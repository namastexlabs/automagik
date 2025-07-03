"""Thin async wrapper around `FlashedProvider` to keep `agent.py` tidy.

Usage::

    api = FlashinhoAPI()
    data = await api.fetch_all(user_uuid)

The wrapper is intentionally minimal – it only groups the six
endpoints we already rely on so that new developers can see every
network call in one file instead of hunting through agent logic.
"""
from __future__ import annotations

from typing import Dict, Any
import logging

from automagik.tools.flashed.provider import FlashedProvider

logger = logging.getLogger(__name__)


class FlashinhoAPI:
    """Convenience async client used by Flashinho V2 internals."""

    async def fetch_all(self, user_id: str) -> Dict[str, Any]:
        """Fetch data from all supported Flashed endpoints for *user_id*.

        Returns a dictionary with one key per endpoint so callers can pick
        what they need without extra network round-trips.
        """
        results: Dict[str, Any] = {}
        async with FlashedProvider() as provider:
            # Each API call is wrapped so that a single failure does not
            # blow everything up.  We only log the error – caller decides
            # whether missing data is acceptable.
            async def _safe(name: str, coro):
                try:
                    results[name] = await coro
                except Exception as exc:  # pragma: no cover – network errors
                    logger.error("Flashed API %s failed: %s", name, exc)

            await _safe("user_data", provider.get_user_data(user_id))
            await _safe("user_score", provider.get_user_score(user_id))
            await _safe("user_roadmap", provider.get_user_roadmap(user_id))
            await _safe("user_objectives", provider.get_user_objectives(user_id))
            await _safe("last_card_round", provider.get_last_card_round(user_id))
            await _safe("user_energy", provider.get_user_energy(user_id))

        return results

    # Individual helpers in case future code only needs one endpoint
    async def user_data(self, user_id: str):
        async with FlashedProvider() as provider:
            return await provider.get_user_data(user_id)

    async def user_score(self, user_id: str):
        async with FlashedProvider() as provider:
            return await provider.get_user_score(user_id) 