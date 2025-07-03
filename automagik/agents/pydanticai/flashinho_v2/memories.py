"""User-memory helpers used by Flashinho V2.

This module is only a thin façade above the existing `memory_manager`
convenience functions, so that `agent.py` can stay declarative and new
contributors can immediately see where memory logic lives without
scrolling a thousand lines.
"""
from __future__ import annotations

from typing import Dict, Optional
from datetime import datetime
import uuid
import logging

from automagik.db.models import Memory
from automagik.db import create_memory

logger = logging.getLogger(__name__)

# Default fallback values for all prompt variables
DEFAULT_VALUES = {
    "name": "Estudante",
    "levelOfEducation": "Ensino Médio",
    "preferredSubject": "",
    "createdAt": "",
    "has_opted_in": "false",
    "onboardingCompleted": "false",
    "dailyProgress": "0",
    "sequence": "0",
    "flashinhoEnergy": "100",
    "starsBalance": "0",
    "roadmap": "Comece criando sua primeira revisão!",
    "lastActivity": "",
    "last_cardPlay_result": "",
    "last_cardPlay_category": "",
    "last_cardPlay_topic": "",
    "last_cardPlay_date": "",
    "last_objectiveCreated_type": "",
    "last_objectiveCreated_topics": "",
    "last_objectiveCreated_duedate": "",
    "interesses_detectados": "",
}

class FlashinhoMemories:
    """Helper class responsible for creating and updating all prompt memories."""

    # ------------------------------------------------------------------
    # 1. Initial default creation (called once per run to ensure variables
    #    always exist even before the first successful API fetch).
    # ------------------------------------------------------------------
    @staticmethod
    async def init_defaults(agent_id: int, user_id: Optional[str] = None) -> bool:
        user_uuid = uuid.UUID(str(user_id)) if user_id else None

        ok = True
        for key, val in DEFAULT_VALUES.items():
            mem = Memory(
                id=uuid.uuid4(),
                name=key,
                content=str(val),
                description=f"Flashinho var {key} (default)",
                user_id=user_uuid,
                agent_id=agent_id,
                read_mode="system_prompt",
                access="read_write",
                metadata={"source": "default", "updated_at": datetime.now().isoformat()},
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            if not create_memory(mem):
                ok = False
                logger.warning("Failed to create default memory %s", key)

        return ok

    @staticmethod
    async def refresh_from_api(agent_id: int, user_id: str, api_data: Dict[str, Dict]) -> bool:
        """Upsert memories using data returned by FlashinhoAPI.fetch_all()."""
        vars_: Dict[str, str] = DEFAULT_VALUES.copy()

        def fmt_date(iso: str | None) -> str:
            if not iso:
                return ""
            try:
                return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%d/%m/%Y")
            except Exception:
                return iso or ""

        # user_data
        user = api_data.get("user_data", {}).get("user", {})
        if user:
            vars_["name"] = user.get("name", vars_["name"])
            vars_["createdAt"] = fmt_date(user.get("createdAt"))
            meta = user.get("metadata", {}) or {}
            vars_["levelOfEducation"] = meta.get("levelOfEducation", vars_["levelOfEducation"])
            vars_["preferredSubject"] = meta.get("preferredSubject", vars_["preferredSubject"])

        # user_score
        score = api_data.get("user_score", {}).get("score", {})
        if score:
            vars_["flashinhoEnergy"] = score.get("flashinhoEnergy", vars_["flashinhoEnergy"])
            vars_["sequence"] = score.get("sequence", vars_["sequence"])
            vars_["dailyProgress"] = score.get("dailyProgress", vars_["dailyProgress"])
            vars_["starsBalance"] = score.get("starsBalance", vars_["starsBalance"])

        # user_energy may override
        energy = api_data.get("user_energy", {})
        if "energyLeft" in energy:
            vars_["flashinhoEnergy"] = energy["energyLeft"]

        # roadmap
        road_root = api_data.get("user_roadmap", {})
        next_subject = (
            road_root.get("roadmap", {})
            .get("roadmap", {})
            .get("nextSubjectToStudy", {})
        )
        if next_subject:
            vars_["roadmap"] = next_subject.get("name", vars_["roadmap"])

        # last card round
        last_round = api_data.get("last_card_round", {}).get("lastRoundPlayed", {})
        if last_round:
            vars_["lastActivity"] = fmt_date(last_round.get("completedAt"))
            plays = last_round.get("cardPlays", [])
            if plays:
                last_play = plays[-1]
                res = str(last_play.get("result", "")).lower()
                vars_["last_cardPlay_result"] = "certo" if res in {"right", "correct", "certo", "true", "verdadeiro"} else "errado"
                vars_["last_cardPlay_category"] = last_round.get("subcategory", {}).get("name", "")
                vars_["last_cardPlay_topic"] = last_play.get("card", {}).get("topic", "")
                vars_["last_cardPlay_date"] = fmt_date(last_round.get("completedAt"))

        # objectives
        objectives = api_data.get("user_objectives", {}).get("objectives", [])
        if objectives:
            last_obj = objectives[-1]
            vars_["last_objectiveCreated_type"] = last_obj.get("type", "")
            topics = [t.get("name", "") for t in last_obj.get("topics", [])]
            vars_["last_objectiveCreated_topics"] = ", ".join(topics)
            vars_["last_objectiveCreated_duedate"] = fmt_date(last_obj.get("dueDate"))

        # ------------------------------------------------------------------
        user_uuid = uuid.UUID(user_id) if user_id else None
        ok = True
        for key, val in vars_.items():
            mem = Memory(
                id=uuid.uuid4(),
                name=key,
                content=str(val),
                description=f"Flashinho var {key}",
                user_id=user_uuid,
                agent_id=agent_id,
                read_mode="system_prompt",
                access="read_write",
                metadata={"source": "flashed_api", "updated_at": datetime.now().isoformat()},
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            if not create_memory(mem):
                logger.warning("Failed to upsert memory %s", key)
                ok = False

        logger.debug("FlashinhoMemories.refresh_from_api → %s/%s upserts ok", sum(1 for _ in vars_), len(vars_))
        return ok

    # Backwards-compat name: not used by agent anymore but kept for clarity
    refresh = refresh_from_api  # type: ignore[misc] 