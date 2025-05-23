import importlib
import sys
from scripts import rules_enforcer

# Re-import to ensure latest code if modified during test run
importlib.reload(rules_enforcer)


def test_no_getenv_violation():
    """check_getenv_usage should complete without raising Violation."""
    # Should not raise
    rules_enforcer.check_getenv_usage()


def test_tool_signatures_valid():
    """All tool async functions must take ctx as first argument."""
    rules_enforcer.check_tool_signatures()


def test_rules_index_complete():
    """00_index.mdc must list every README under rules/*/*."""
    rules_enforcer.check_rules_index() 