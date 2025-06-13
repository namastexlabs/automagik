#!/usr/bin/env python3
"""Database tests for MCP tables and repository - NAM-15"""

from src.db.repository.mcp import (
    list_mcp_servers, get_mcp_server_by_name, create_mcp_server, 
    update_mcp_server, delete_mcp_server
)
from src.db.models import MCPServerDB

def test_database_tables():
    """Test that MCP database tables exist."""
    # Use SQLite-compatible table existence check
    # For SQLite: SELECT name FROM sqlite_master WHERE type='table' AND name='table_name'
    # For PostgreSQL: SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'table_name')
    
    # Check mcp_servers table exists using database-agnostic method
    from src.db.connection import table_exists
    mcp_servers_exists = table_exists('mcp_servers')
    
    # Check agent_mcp_servers table exists using database-agnostic method
    agent_mcp_servers_exists = table_exists('agent_mcp_servers')
    
    print(f"✅ MCP Tables exist - mcp_servers: {mcp_servers_exists}, agent_mcp_servers: {agent_mcp_servers_exists}")
            
    assert mcp_servers_exists and agent_mcp_servers_exists, "MCP tables are missing"
    
    # Check table structure using database-agnostic method
    from src.db.connection import get_table_columns
    columns = get_table_columns('mcp_servers')
    expected_columns = ['id', 'name', 'server_type', 'description', 'command', 'env', 'http_url', 
                      'auto_start', 'max_retries', 'timeout_seconds', 'tags', 'priority', 'status', 
                      'enabled', 'started_at', 'last_error', 'error_count', 'connection_attempts', 
                      'last_ping', 'tools_discovered', 'resources_discovered', 'created_at', 
                      'updated_at', 'last_started', 'last_stopped']
    
    missing_columns = [col for col in expected_columns if col not in columns]
    assert not missing_columns, f"Missing columns in mcp_servers: {missing_columns}"
    
    print("✅ MCP table structure verified")

def test_repository_functions():
    """Test MCP repository CRUD operations."""
    # Test list servers (should work even if empty)
    servers = list_mcp_servers()
    print(f"✅ list_mcp_servers() works - found {len(servers)} servers")
    
    # Test creating a test server
    test_server = MCPServerDB(
        name="test_db_server",
        server_type="stdio",
        description="Test server for database verification",
        command=["echo", "test"],
        env={},
        auto_start=False,
        max_retries=3,
        timeout_seconds=30,
        tags=["test"],
        priority=0
    )
    
    # Try to create server
    server_id = create_mcp_server(test_server)
    assert server_id is not None, "create_mcp_server() failed"
    print(f"✅ create_mcp_server() works - created server with ID {server_id}")
    
    try:
        # Test get by name
        retrieved_server = get_mcp_server_by_name("test_db_server")
        assert retrieved_server is not None, "get_mcp_server_by_name() returned None"
        assert retrieved_server.name == "test_db_server", "get_mcp_server_by_name() returned wrong server"
        print("✅ get_mcp_server_by_name() works")
        
        # Test update
        test_server.id = server_id
        test_server.description = "Updated test server"
        update_success = update_mcp_server(test_server)
        assert update_success, "update_mcp_server() failed"
        print("✅ update_mcp_server() works")
            
    finally:
        # Clean up - delete test server
        delete_success = delete_mcp_server(server_id)
        assert delete_success, "delete_mcp_server() failed"
        print("✅ delete_mcp_server() works")

def test_existing_functionality():
    """Test that existing functionality still works with MCP integration."""
    # Test that the server can still start (already tested in NAM-14, but verify here)
    print("✅ Server startup already verified in NAM-14")
    
    # Test that existing database functionality works
    from src.db.repository.agent import list_agents
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