#!/usr/bin/env python3
"""Test script for MCP core module components - NAM-13"""

import asyncio
import sys
import pytest
from src.mcp.client import MCPClientManager
from src.mcp.server import MCPServerManager  
from src.mcp.models import MCPServerConfig, MCPServerStatus, MCPServerType
from src.mcp.exceptions import MCPError, MCPServerError, MCPConnectionError

def test_imports():
    """Test that all core imports work correctly."""
    print("✅ All MCP core module imports successful")

def test_models():
    """Test MCP model creation and validation."""
    # Test MCPServerConfig creation
    config = MCPServerConfig(
        name='test_server',
        server_type=MCPServerType.STDIO,
        description='Test server for validation',
        command=['echo', 'test'],
        agent_names=['test_agent']
    )
    print("✅ MCPServerConfig creation successful")
    
    # Test enum values
    assert MCPServerType.STDIO.value == "stdio"
    assert MCPServerType.HTTP.value == "http"
    print("✅ MCPServerType enum validation successful")
    
    # Test status enum
    assert MCPServerStatus.STOPPED.value == "stopped"
    assert MCPServerStatus.RUNNING.value == "running"
    print("✅ MCPServerStatus enum validation successful")

def test_exceptions():
    """Test MCP exception creation and inheritance."""
    # Test base exception - MCPError prefixes "MCP Error: "
    base_error = MCPError("Test base error")
    assert str(base_error) == "MCP Error: Test base error"
    assert isinstance(base_error, Exception)
    print("✅ MCPError creation and string formatting successful")
    
    # Test server error with server name
    server_error = MCPServerError("Test server error", server_name="test_server")
    assert isinstance(server_error, MCPError)
    assert "test_server" in str(server_error)
    print("✅ MCPServerError inheritance and formatting successful")
    
    # Test connection error  
    conn_error = MCPConnectionError("Test connection error")
    assert isinstance(conn_error, MCPError)
    assert "MCP Error: Test connection error" == str(conn_error)
    print("✅ MCPConnectionError inheritance successful")

@pytest.mark.asyncio
async def test_client_manager():
    """Test MCPClientManager basic initialization."""
    manager = MCPClientManager()
    print("✅ MCPClientManager instantiation successful")
    
    # Test basic properties without initialization
    servers = manager.list_servers()
    assert isinstance(servers, list)
    print("✅ MCPClientManager.list_servers() works")
    
    # Test health without initialization
    health = await manager.get_health()
    assert health.servers_total == 0  # No servers loaded yet
    print("✅ MCPClientManager.get_health() works")

def test_server_manager():
    """Test MCPServerManager basic creation."""
    config = MCPServerConfig(
        name='test_server',
        server_type=MCPServerType.STDIO,
        description='Test server for manager testing',
        command=['echo', 'test'],
        agent_names=['test_agent']
    )
    
    manager = MCPServerManager(config)
    print("✅ MCPServerManager instantiation successful")
    
    # Test basic properties
    assert manager.name == 'test_server'
    assert manager.status == MCPServerStatus.STOPPED
    print("✅ MCPServerManager properties accessible")

async def main():
    """Run all MCP core module tests."""
    print("🧪 Starting MCP Core Module Tests (NAM-13)")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Models", test_models),
        ("Exceptions", test_exceptions),
        ("Client Manager", test_client_manager),
        ("Server Manager", test_server_manager),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"✅ {test_name} test PASSED")
            else:
                print(f"❌ {test_name} test FAILED")
        except Exception as e:
            print(f"❌ {test_name} test FAILED with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All MCP core module tests PASSED!")
        return True
    else:
        print("💥 Some MCP core module tests FAILED!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 