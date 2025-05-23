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
from src.agents.simple.sofia_agent.specialized.airtable import get_airtable_assistant
from src.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_cezar_tasks():
    """Test querying tasks for Cezar Vasconcelos."""
    
    print("🧪 Testing Airtable Agent - Cezar Vasconcelos Tasks")
    print("=" * 60)
    
    # Check configuration
    if not settings.AIRTABLE_TOKEN:
        print("❌ AIRTABLE_TOKEN not configured. Please set it in your .env file.")
        return
    
    if not settings.AIRTABLE_DEFAULT_BASE_ID:
        print("❌ AIRTABLE_DEFAULT_BASE_ID not configured. Please set it in your .env file.")
        return
    
    print(f"✅ Configuration found:")
    print(f"   📊 Base ID: {settings.AIRTABLE_DEFAULT_BASE_ID}")
    print(f"   🔑 Token: {'*' * 10}...{settings.AIRTABLE_TOKEN[-4:]}")
    print()
    
    try:
        # Initialize the agent with fresh schema
        print("🔄 Initializing Airtable agent with fresh schema...")
        agent = await get_airtable_assistant(force_refresh=True)
        print("✅ Agent initialized successfully!")
        print()
        
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
                # Create a mock context for the agent
                class MockDeps:
                    def __init__(self):
                        self.context = {}
                
                class MockCtx:
                    def __init__(self):
                        self.deps = MockDeps()
                
                # Run the query
                result = await agent.run(query, deps=MockCtx().deps)
                
                print("✅ Response:")
                print(result.output)
                print()
                
            except Exception as e:
                print(f"❌ Error: {e}")
                print()
            
            # Wait a bit between queries to avoid rate limiting
            await asyncio.sleep(1)
    
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        logger.exception("Detailed error:")


async def test_improved_queries():
    """Test more specific and improved query patterns."""
    
    print("🔧 Testing Improved Query Patterns")
    print("=" * 60)
    
    try:
        agent = await get_airtable_assistant()
        
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
                
                class MockCtx:
                    def __init__(self):
                        self.deps = MockDeps()
                
                result = await agent.run(query, deps=MockCtx().deps)
                
                print("✅ Response:")
                print(result.output)
                print()
                
            except Exception as e:
                print(f"❌ Error: {e}")
                print()
            
            await asyncio.sleep(1)
    
    except Exception as e:
        print(f"❌ Failed in improved queries: {e}")


async def analyze_agent_capabilities():
    """Analyze the current agent's capabilities and suggest improvements."""
    
    print("🔍 Analyzing Current Agent Capabilities")
    print("=" * 60)
    
    try:
        agent = await get_airtable_assistant()
        
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
                
                class MockCtx:
                    def __init__(self):
                        self.deps = MockCtx().deps
                
                result = await agent.run(query, deps=MockCtx().deps)
                print("💭 Agent Response:")
                print(result.output)
                print()
                
            except Exception as e:
                print(f"❌ Error: {e}")
                print()
    
    except Exception as e:
        print(f"❌ Failed in analysis: {e}")


async def main():
    """Run all tests."""
    print("🤖 Airtable Agent Testing - Focus: Cezar Vasconcelos Tasks")
    print("=" * 70)
    print()
    
    await test_cezar_tasks()
    await test_improved_queries()
    await analyze_agent_capabilities()
    
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


if __name__ == "__main__":
    asyncio.run(main()) 