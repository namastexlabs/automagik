"""Service version and metadata information."""

import tomllib
from pathlib import Path

def _get_version():
    """Get version from pyproject.toml"""
    try:
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except Exception:
        return "unknown"

__version__ = _get_version()

SERVICE_NAME = "automagik-agents"
SERVICE_DESCRIPTION = "Automagik agents templates and API"

# Service information dictionary for reuse
SERVICE_INFO = {
    "name": SERVICE_NAME,
    "description": SERVICE_DESCRIPTION,
    "version": __version__,
}