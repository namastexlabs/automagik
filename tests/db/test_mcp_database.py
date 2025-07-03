#!/usr/bin/env python3
"""Database tests for MCP tables and repository - NAM-15"""

from automagik.db.repository.mcp import (
    list_mcp_configs, get_mcp_config_by_name, create_mcp_config, 
    update_mcp_config_by_name, delete_mcp_config_by_name
)
from automagik.db.models import MCPConfig, MCPConfigCreate

def test_database_tables():
    """Test that MCP database tables exist."""
    # Use SQLite-compatible table existence check
    # New architecture uses single mcp_configs table (NMSTX-253)
    
    # Check mcp_configs table exists using database-agnostic method
    from automagik.db.connection import table_exists
    mcp_configs_exists = table_exists('mcp_configs')
    
    print(f"✅ MCP Table exists - mcp_configs: {mcp_configs_exists}")
            
    assert mcp_configs_exists, "MCP configs table is missing"
    
    # Check table structure using database-agnostic method
    from automagik.db.connection import get_table_columns
    columns = get_table_columns('mcp_configs')
    expected_columns = ['id', 'name', 'config', 'created_at', 'updated_at']
    
    missing_columns = [col for col in expected_columns if col not in columns]
    assert not missing_columns, f"Missing columns in mcp_configs: {missing_columns}"
    
    print("✅ MCP table structure verified")

def test_repository_functions():
    """Test MCP repository CRUD operations."""
    # Test list configs (should work even if empty)
    configs = list_mcp_configs()
    print(f"✅ list_mcp_configs() works - found {len(configs)} configs")
    
    # Test creating a test config
    test_config = MCPConfigCreate(
        name="test_db_server",
        config={
            "server_type": "stdio",
            "description": "Test server for database verification",
            "command": ["echo", "test"],
            "env": {},
            "auto_start": False,
            "max_retries": 3,
            "timeout": 30000,
            "agents": ["test"],
            "enabled": True
        }
    )
    
    # Try to create config
    config_id = create_mcp_config(test_config)
    assert config_id is not None, "create_mcp_config() failed"
    print(f"✅ create_mcp_config() works - created config with ID {config_id}")
    
    try:
        # Test get by name
        retrieved_config = get_mcp_config_by_name("test_db_server")
        assert retrieved_config is not None, "get_mcp_config_by_name() returned None"
        assert retrieved_config.name == "test_db_server", "get_mcp_config_by_name() returned wrong config"
        print("✅ get_mcp_config_by_name() works")
        
        # Test update
        updated_config = test_config.model_copy()
        updated_config.config["description"] = "Updated test server"
        update_success = update_mcp_config_by_name("test_db_server", updated_config)
        assert update_success, "update_mcp_config_by_name() failed"
        print("✅ update_mcp_config_by_name() works")
            
    finally:
        # Clean up - delete test config
        delete_success = delete_mcp_config_by_name("test_db_server")
        assert delete_success, "delete_mcp_config_by_name() failed"
        print("✅ delete_mcp_config_by_name() works")

def test_existing_functionality():
    """Test that existing functionality still works with MCP integration."""
    # Test that the server can still start (already tested in NAM-14, but verify here)
    print("✅ Server startup already verified in NAM-14")
    
    # Test that existing database functionality works
    from automagik.db.repository.agent import list_agents
    agents = list_agents()
    print(f"✅ Existing agent repository still works - found {len(agents)} agents")
    
    # Test that authentication still works (already verified in NAM-14)
    print("✅ Authentication already verified in NAM-14")

def main():
    """Run all MCP database tests."""
    print("🧪 Starting MCP Database Tests (NAM-15)")
    print("=" * 50)
    
    tests = [
        ("Database Tables", test_database_tables),
        ("Repository Functions", test_repository_functions), 
        ("Existing Functionality", test_existing_functionality),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        try:
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
        print("🎉 All MCP database tests PASSED!")
        return True
    else:
        print("💥 Some MCP database tests FAILED!")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 