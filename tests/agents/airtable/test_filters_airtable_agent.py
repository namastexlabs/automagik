#!/usr/bin/env python3
"""
Test script for Airtable agent - Query tasks for Cezar Vasconcelos

This test will help us improve the Airtable agent by testing its ability to:
1. Query specific records based on user names
2. Filter tasks by assignee
3. Present results in a user-friendly format
"""

import asyncio
import logging
import sys
from src.agents.simple.sofia.specialized.airtable import get_airtable_assistant
from src.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_configuration():
    """Check if required configuration is available."""
    print("🔧 Checking Configuration")
    print("=" * 40)
    
    config_status = {
        "airtable_token": bool(settings.AIRTABLE_TOKEN),
        "airtable_base_id": bool(settings.AIRTABLE_DEFAULT_BASE_ID),
        "openai_api_key": bool(settings.OPENAI_API_KEY),
    }
    
    for key, status in config_status.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {key.upper()}: {'Configured' if status else 'Missing'}")
    
    print()
    
    if not all(config_status.values()):
        print("⚠️  Some configuration is missing. The test may not work properly.")
        print("💡 To fix this:")
        if not config_status["airtable_token"]:
            print("   - Set AIRTABLE_TOKEN in your .env file")
        if not config_status["airtable_base_id"]:
            print("   - Set AIRTABLE_DEFAULT_BASE_ID in your .env file")
        if not config_status["openai_api_key"]:
            print("   - Set OPENAI_API_KEY in your .env file")
        print()
        return False
    
    print("✅ All required configuration found!")
    if settings.AIRTABLE_DEFAULT_BASE_ID:
        print(f"   📊 Base ID: {settings.AIRTABLE_DEFAULT_BASE_ID}")
    if settings.AIRTABLE_TOKEN:
        print(f"   🔑 Token: {'*' * 10}...{settings.AIRTABLE_TOKEN[-4:]}")
    print()
    return True


async def test_agent_initialization():
    """Test basic agent initialization."""
    print("🤖 Testing Agent Initialization")
    print("=" * 40)
    
    try:
        print("🔄 Initializing Airtable agent...")
        agent = await get_airtable_assistant(force_refresh=True)
        print("✅ Agent initialized successfully!")
        return agent
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        logger.exception("Detailed error:")
        return None


async def test_basic_queries(agent):
    """Test basic query functionality."""
    if not agent:
        print("⏭️  Skipping basic queries - agent not available")
        return
    
    print("🧪 Testing Basic Queries")
    print("=" * 40)
    
    # Simple test queries that should work even without data
    basic_queries = [
        "What tools and capabilities do you have available?",
        "How can you help me with Airtable?",
        "What is your purpose?",
    ]
    
    for i, query in enumerate(basic_queries, 1):
        print(f"🚀 Basic Test {i}: {query}")
        print("-" * 30)
        
        try:
            class MockDeps:
                def __init__(self):
                    self.context = {}
            
            result = await agent.run(query, deps=MockDeps())
            
            print("✅ Response:")
            print(result.output[:200] + "..." if len(result.output) > 200 else result.output)
            print()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print()
        
        # Wait a bit between queries
        await asyncio.sleep(0.5)


async def test_cezar_tasks(agent):
    """Test querying tasks for Cezar Vasconcelos."""
    if not agent:
        print("⏭️  Skipping Cezar tasks test - agent not available")
        return
    
    print("🧪 Testing Cezar Vasconcelos Tasks")
    print("=" * 40)
    
    # Test different query variations for Cezar's tasks
    test_queries = [
        "Show me all Milestones",
        "Show me all tasks assigned to Cezar Vasconcelos",
        "Show me all tasks assigned to Cezar Vasconcelos that are not completed",
        "What tasks does Cezar Vasconcelos have in the Automagik - Plataforma Milestone?",
        "Show Cezar Vasconcelos's current tasks and their status"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"🚀 Test {i}: {query}")
        print("-" * 40)
        
        try:
            class MockDeps:
                def __init__(self):
                    self.context = {}
            
            # Run the query
            result = await agent.run(query, deps=MockDeps())
            
            print("✅ Response:")
            print(result.output)
            print()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print()
        
        # Wait a bit between queries to avoid rate limiting
        await asyncio.sleep(1)


async def test_improved_queries(agent):
    """Test more specific and improved query patterns."""
    if not agent:
        print("⏭️  Skipping improved queries - agent not available")
        return
    
    print("🔧 Testing Improved Query Patterns")
    print("=" * 40)
    
    # More specific queries that might work better
    improved_queries = [
        # Direct table queries
        "List all records from the Tasks table",
        "Show me the structure of the Tasks table",
        
        # Filtered queries
        "From the Tasks table, find records where any field contains 'Cezar'",
        "Query the Tasks table and filter by assignee or responsible person matching 'Cezar Vasconcelos'",
        
        # Status-focused queries
        "Show all tasks that are currently 'A fazer' (to do)",
        "List tasks with status 'Estou trabalhando' (working on)",
        
        # Exploratory queries
        "What fields are available in the Tasks table?",
        "Show me a sample of 3 records from the Tasks table",
    ]
    
    for i, query in enumerate(improved_queries, 1):
        print(f"🧪 Improved Test {i}: {query}")
        print("-" * 50)
        
        try:
            class MockDeps:
                def __init__(self):
                    self.context = {}
            
            result = await agent.run(query, deps=MockDeps())
            
            print("✅ Response:")
            print(result.output)
            print()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print()
        
        await asyncio.sleep(1)


async def analyze_agent_capabilities(agent):
    """Analyze the current agent's capabilities and suggest improvements."""
    if not agent:
        print("⏭️  Skipping capability analysis - agent not available")
        return
    
    print("🔍 Analyzing Current Agent Capabilities")
    print("=" * 40)
    
    # Test the agent's self-awareness
    analysis_queries = [
        "What tools and capabilities do you have available?",
        "How can you help me find specific tasks in Airtable?",
        "What is the structure of our Airtable base?",
        "Explain your workflow for filtering records by assignee",
    ]
    
    for query in analysis_queries:
        print(f"🤔 Analysis: {query}")
        print("-" * 40)
        
        try:
            class MockDeps:
                def __init__(self):
                    self.context = {}
            
            result = await agent.run(query, deps=MockDeps())
            print("💭 Agent Response:")
            print(result.output)
            print()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print()


async def main():
    """Run all tests."""
    print("🤖 Airtable Agent Testing - Focus: Cezar Vasconcelos Tasks")
    print("=" * 70)
    print()
    
    # Check configuration first
    config_ok = check_configuration()
    
    if not config_ok:
        print("🛑 Cannot proceed with full testing due to missing configuration.")
        print("   Running basic tests only...")
        print()
    
    # Try to initialize agent
    agent = await test_agent_initialization()
    
    # Run tests based on what's available
    await test_basic_queries(agent)
    
    if config_ok and agent:
        await test_cezar_tasks(agent)
        await test_improved_queries(agent)
        await analyze_agent_capabilities(agent)
    else:
        print("⏭️  Skipping advanced tests due to configuration or initialization issues")
    
    print("🎯 **Test Summary & Improvement Suggestions:**")
    print()
    print("Based on the test results, consider these improvements:")
    print("1. 🔍 Better field name recognition for assignee/responsible person")
    print("2. 🎯 More intelligent filtering based on partial name matches")
    print("3. 📋 Enhanced presentation of task lists with status, priority, dates")
    print("4. 🔗 Better handling of linked record fields (Team Members table)")
    print("5. 💬 More conversational and user-friendly response formatting")
    print("6. 🚀 Caching of common queries for better performance")
    print()
    
    if not config_ok:
        print("💡 **Next Steps:**")
        print("1. Configure missing environment variables in .env file")
        print("2. Re-run the test to see full functionality")
        print("3. Check Airtable permissions and API access")


if __name__ == "__main__":
    asyncio.run(main()) 