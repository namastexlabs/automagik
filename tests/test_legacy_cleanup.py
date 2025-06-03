"""Regression tests for NMSTX-230 legacy cleanup.

Ensures that the legacy LangGraph implementation remains removed
and that the PydanticAI Genie implementation is properly available.
"""

import pytest
from pathlib import Path
import importlib
import sys


class TestNMSTX230LegacyCleanup:
    """Tests for NMSTX-230 legacy cleanup regression."""
    
    def test_legacy_langgraph_directory_removed(self):
        """Ensure legacy LangGraph directory has been removed."""
        legacy_path = Path(__file__).parent.parent / "src" / "agents" / "langgraph"
        
        # Should not exist anymore
        assert not legacy_path.exists(), f"Legacy LangGraph directory still exists at {legacy_path}"
    
    def test_pydanticai_genie_exists(self):
        """Ensure PydanticAI Genie implementation exists."""
        genie_path = Path(__file__).parent.parent / "src" / "agents" / "pydanticai" / "genie"
        
        # Should exist
        assert genie_path.exists(), f"PydanticAI Genie directory missing at {genie_path}"
        assert (genie_path / "agent.py").exists(), "Genie agent.py missing"
        assert (genie_path / "models.py").exists(), "Genie models.py missing"
    
    def test_no_legacy_imports_in_agent_factory(self):
        """Ensure agent factory doesn't import legacy LangGraph code."""
        # Read the agent factory file
        factory_path = Path(__file__).parent.parent / "src" / "agents" / "models" / "agent_factory.py"
        factory_content = factory_path.read_text()
        
        # Should not contain any uncommented imports from langgraph
        lines = factory_content.split('\n')
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('from src.agents.langgraph') and not stripped.startswith('#'):
                pytest.fail(f"Found uncommented legacy import: {line}")
            if stripped.startswith('import src.agents.langgraph') and not stripped.startswith('#'):
                pytest.fail(f"Found uncommented legacy import: {line}")
    
    def test_genie_agent_importable(self):
        """Ensure the PydanticAI Genie agent can be imported."""
        try:
            from src.agents.pydanticai.genie import create_agent
            # Should be able to create an agent
            agent = create_agent({})
            assert agent is not None, "Failed to create Genie agent"
        except ImportError as e:
            pytest.fail(f"Failed to import PydanticAI Genie: {e}")
    
    def test_no_langgraph_references_in_scripts(self):
        """Ensure scripts don't have uncommented references to legacy LangGraph."""
        scripts_dir = Path(__file__).parent.parent / "scripts"
        
        for script_file in scripts_dir.glob("*.py"):
            content = script_file.read_text()
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                stripped = line.strip()
                # Check for uncommented imports
                if (stripped.startswith('from src.agents.langgraph') or 
                    stripped.startswith('import src.agents.langgraph')) and not stripped.startswith('#'):
                    pytest.fail(f"Found uncommented legacy import in {script_file}:{line_num}: {line}")