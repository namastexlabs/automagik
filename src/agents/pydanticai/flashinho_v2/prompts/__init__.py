"""Flashinho V2 agent prompts module."""

from pathlib import Path
import logging

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parent  # prompts folder


def _load(name: str) -> str:
    """Load prompt markdown by base filename without extension."""
    md_path = _BASE_DIR / f"{name}.md"
    if md_path.exists():
        try:
            return md_path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.error("Failed reading %s: %s", md_path, exc)

    # Fallback to old python constants in prompts.prompt if they still exist
    try:
        from .prompt import AGENT_PROMPT as _OLD_FULL, AGENT_FREE as _OLD_FREE
        return _OLD_FULL if "pro" in name else _OLD_FREE
    except ModuleNotFoundError:
        logger.warning("Prompt file %s.md not found and legacy constants missing", name)
        return ""


AGENT_PROMPT: str = _load("prompt_pro") or _load("default")
AGENT_FREE: str = _load("prompt_default") or _load("free")