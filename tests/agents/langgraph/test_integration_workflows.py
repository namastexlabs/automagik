"""Integration tests for LangGraph orchestration workflows.

This module contained tests for the legacy LangGraph implementation.
All tests have been removed as part of NMSTX-230 cleanup.
The PydanticAI Genie implementation has its own test suite.
"""

import pytest

@pytest.mark.skip(reason="Legacy LangGraph implementation removed - replaced by PydanticAI Genie")
class TestIntegrationWorkflows:
    """Integration tests for orchestration workflows (DISABLED)."""
    
    def test_placeholder(self):
        """Placeholder test - legacy tests removed."""
        pass