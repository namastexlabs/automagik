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

SERVICE_NAME = "Automagik API"
SERVICE_DESCRIPTION = """Automagik Agents is a sophisticated AI agent orchestration platform that enables semi-autonomous development through intelligent task decomposition and specialized workflow execution.

**Key Features:**
- **🧞 Genie Orchestrator**: Decomposes complex development epics into specialized workflow sequences
- **⚡ Specialized Workflows**: Dynamic Claude Code workflow orchestration system  
- **🧠 Persistent Memory**: Agent consciousness using MCP agent-memory integration
- **🔄 Multi-Agent System**: PydanticAI + LangGraph for structured AI interactions
- **🛠️ Tool Integration**: Comprehensive tool discovery and execution framework
- **📊 Session Management**: Persistent conversation context and branching
- **🔐 Enterprise Security**: API key authentication with multiple methods

**Use Cases:**
- Automated code generation and refactoring
- Intelligent project scaffolding and setup
- Complex development task orchestration
- AI-powered debugging and optimization
- Collaborative human-AI development workflows

This API provides programmatic access to all Automagik Agents capabilities, enabling integration with existing development tools and workflows."""

# Service information dictionary for reuse
SERVICE_INFO = {
    "name": SERVICE_NAME,
    "description": SERVICE_DESCRIPTION,
    "version": __version__,
}