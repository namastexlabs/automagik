"""
Automagik - AI Agent Framework

A powerful framework for building and deploying AI agents with memory,
tools, and orchestration capabilities.
"""

__version__ = "0.4.7"

# Export key components for easier imports
from automagik.agents.models.agent_factory import AgentFactory
from automagik.agents.models.automagik_agent import AutomagikAgent

__all__ = ['AgentFactory', 'AutomagikAgent', '__version__']
