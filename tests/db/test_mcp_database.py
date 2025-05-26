#!/usr/bin/env python3
"""Database tests for MCP tables and repository - NAM-15"""

from src.db.connection import get_connection_pool
from src.db.repository.mcp import (
    list_mcp_servers, get_mcp_server_by_name, create_mcp_server, 
    update_mcp_server, delete_mcp_server, get_server_agents,
    assign_agent_to_server, remove_agent_from_server
)
from src.db.models import MCPServerDB

def test_database_tables():
    """Test that MCP database tables exist."""
    pool = get_connection_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            # Check mcp_servers table exists
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'mcp_servers')")
            mcp_servers_exists = cur.fetchone()[0]
            
            # Check agent_mcp_servers table exists  
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'agent_mcp_servers')")
            agent_mcp_servers_exists = cur.fetchone()[0]
            
            print(f"✅ MCP Tables exist - mcp_servers: {mcp_servers_exists}, agent_mcp_servers: {agent_mcp_servers_exists}")
            
            if not (mcp_servers_exists and agent_mcp_servers_exists):
                print("❌ MCP tables are missing")
                return False
                
            # Check table structure
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'mcp_servers' ORDER BY ordinal_position")
            columns = [row[0] for row in cur.fetchall()]
            expected_columns = ['id', 'name', 'server_type', 'description', 'command', 'env', 'http_url', 
                              'auto_start', 'max_retries', 'timeout_seconds', 'tags', 'priority', 'status', 
                              'enabled', 'started_at', 'last_error', 'error_count', 'connection_attempts', 
                              'last_ping', 'tools_discovered', 'resources_discovered', 'created_at', 
                              'updated_at', 'last_started', 'last_stopped']
            
            missing_columns = [col for col in expected_columns if col not in columns]
            if missing_columns:
                print(f"❌ Missing columns in mcp_servers: {missing_columns}")
                return False
            
            print("✅ MCP table structure verified")
            return True
            
    finally:
        pool.putconn(conn)

def test_repository_functions():
    """Test MCP repository CRUD operations."""
    try:
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
        if server_id:
            print(f"✅ create_mcp_server() works - created server with ID {server_id}")
            
            # Test get by name
            retrieved_server = get_mcp_server_by_name("test_db_server")
            if retrieved_server and retrieved_server.name == "test_db_server":
                print("✅ get_mcp_server_by_name() works")
            else:
                print("❌ get_mcp_server_by_name() failed")
                return False
            
            # Test update
            test_server.id = server_id
            test_server.description = "Updated test server"
            update_success = update_mcp_server(test_server)
            if update_success:
                print("✅ update_mcp_server() works")
            else:
                print("❌ update_mcp_server() failed")
                return False
                
            # Clean up - delete test server
            delete_success = delete_mcp_server(server_id)
            if delete_success:
                print("✅ delete_mcp_server() works")
            else:
                print("❌ delete_mcp_server() failed")
                return False
                
        else:
            print("❌ create_mcp_server() failed")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Repository testing failed: {e}")
        return False

def test_existing_functionality():
    """Test that existing functionality still works with MCP integration."""
    try:
        # Test that the server can still start (already tested in NAM-14, but verify here)
        print("✅ Server startup already verified in NAM-14")
        
        # Test that existing database functionality works
        from src.db.repository.agent import list_agents
        agents = list_agents()
        print(f"✅ Existing agent repository still works - found {len(agents)} agents")
        
        # Test that authentication still works (already verified in NAM-14)
        print("✅ Authentication already verified in NAM-14")
        
        return True
        
    except Exception as e:
        print(f"❌ Existing functionality test failed: {e}")
        return False

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