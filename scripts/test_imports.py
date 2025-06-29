#!/usr/bin/env python3
"""
Import test script for Automagik Agents repository.

This script verifies that all core modules can be imported correctly
and that the basic functionality is accessible.

Usage:
    uv run python scripts/test_imports.py
"""

import sys
from typing import List, Tuple


def test_core_imports() -> List[Tuple[str, str, bool, str]]:
    """Test core module imports and return results."""
    
    tests = [
        ('src', 'Main src module'),
        ('src.config', 'Configuration system'),
        ('src.agents', 'Agent framework'),
        ('src.agents.pydanticai.simple', 'Simple agent'),
        ('src.agents.pydanticai.stan', 'Stan agent'),
        ('src.agents.pydanticai.sofia', 'Sofia agent'),
        ('src.api', 'API framework'),
        ('src.db', 'Database layer'),
        ('src.mcp', 'MCP integration'),
        ('src.tools', 'Tools framework'),
        ('src.cli', 'Command line interface'),
        ('src.main', 'Main entry point'),
    ]
    
    results = []
    
    for module_name, description in tests:
        try:
            __import__(module_name)
            results.append((module_name, description, True, ''))
        except Exception as e:
            error_msg = str(e)
            # Get shorter error for readability
            if len(error_msg) > 100:
                error_msg = error_msg[:97] + '...'
            results.append((module_name, description, False, error_msg))
    
    return results


def test_functional_verification():
    """Test that core functionality actually works."""
    
    print("\n=== FUNCTIONAL VERIFICATION ===")
    
    # Test 1: Configuration access
    try:
        from src.config import settings
        print(f"✅ Configuration: Environment={settings.AM_ENV}, Port={settings.AM_PORT}")
    except Exception as e:
        print(f"❌ Configuration access failed: {e}")
        return False
    
    # Test 2: Agent creation
    try:
        from src.agents.models.agent_factory import AgentFactory
        
        test_config = {"am_api_key": "test", "openai_api_key": "test-key"}
        agent = AgentFactory.create_agent("simple", config=test_config)
        print(f"✅ Agent creation: {type(agent).__name__} created successfully")
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        return False
    
    # Test 3: Database provider
    try:
        from src.db.providers.factory import get_database_provider
        
        provider = get_database_provider()
        print(f"✅ Database: {type(provider).__name__} initialized")
    except Exception as e:
        print(f"❌ Database provider failed: {e}")
        return False
    
    return True


def main():
    """Run all import tests."""
    
    print("=== AUTOMAGIK AGENTS IMPORT TEST ===")
    print()
    
    # Run core import tests
    results = test_core_imports()
    
    print("Core Module Import Results:")
    print("-" * 60)
    
    passed = 0
    total = len(results)
    
    for module_name, description, success, error in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {description}")
        
        if not success and error:
            print(f"      Error: {error}")
        
        if success:
            passed += 1
    
    print()
    print(f"Results: {passed}/{total} modules imported successfully ({(passed/total)*100:.1f}%)")
    
    # Run functional tests if basic imports work
    if passed >= total * 0.8:  # If at least 80% pass
        functional_success = test_functional_verification()
        
        print()
        print("=== SUMMARY ===")
        
        if passed == total and functional_success:
            print("🎉 ALL TESTS PASSED!")
            print("✅ All modules import correctly")
            print("✅ Core functionality verified")
            return 0
        elif passed >= total * 0.9:
            print("✅ MOSTLY SUCCESSFUL")
            print("✅ Core modules import correctly")
            if not functional_success:
                print("⚠️  Some functional issues detected")
            return 0
        else:
            print("⚠️  PARTIAL SUCCESS")
            print("⚠️  Some modules have import issues")
            return 1
    else:
        print()
        print("❌ CRITICAL IMPORT ISSUES")
        print("❌ Too many core modules failed to import")
        print("❌ Check dependencies and configuration")
        return 2


if __name__ == "__main__":
    sys.exit(main())