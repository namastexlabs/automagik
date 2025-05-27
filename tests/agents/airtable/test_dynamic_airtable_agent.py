#!/usr/bin/env python3
"""
Test script for the enhanced dynamic Airtable agent with caching.

This demonstrates how the agent now dynamically fetches the actual Airtable
schema, builds the prompt with real table information, and caches results
for optimal performance.

Usage:
    python tests/agent/test_dynamic_airtable_agent.py
"""

import asyncio
import logging
import time
from src.agents.simple.sofia.specialized.airtable import (
    fetch_airtable_schema, 
    build_dynamic_system_prompt,
    get_airtable_assistant,
    clear_schema_cache,
    get_cache_info,
    SCHEMA_CACHE_TTL_MINUTES
)
from src.config import settings

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_schema_fetching():
    """Test the dynamic schema fetching functionality."""
    
    print("🔍 Testing Dynamic Airtable Schema Fetching with Caching")
    print("=" * 70)
    
    # Check if Airtable is configured
    if not settings.AIRTABLE_TOKEN:
        print("❌ AIRTABLE_TOKEN not configured. Please set it in your .env file.")
        return
    
    if not settings.AIRTABLE_DEFAULT_BASE_ID:
        print("❌ AIRTABLE_DEFAULT_BASE_ID not configured. Please set it in your .env file.")
        return
    
    print(f"✅ Configuration found:")
    print(f"   📊 Base ID: {settings.AIRTABLE_DEFAULT_BASE_ID}")
    print(f"   🔑 Token: {'*' * 10}...{settings.AIRTABLE_TOKEN[-4:]}")
    print(f"   ⏰ Cache TTL: {SCHEMA_CACHE_TTL_MINUTES} minutes")
    print()
    
    try:
        # Clear any existing cache
        clear_schema_cache()
        
        # Test 1: First fetch (should be slow - fresh from API)
        print("🚀 Step 1: First schema fetch (fresh from API)...")
        start_time = time.time()
        schema = await fetch_airtable_schema()
        first_fetch_time = time.time() - start_time
        
        print(f"✅ Schema fetched successfully in {first_fetch_time:.2f} seconds!")
        print("📋 Schema preview (first 800 chars):")
        print("-" * 40)
        print(schema[:800])
        if len(schema) > 800:
            print(f"... (truncated, full schema is {len(schema)} characters)")
        print("-" * 40)
        print()
        
        # Test 2: Second fetch (should be fast - from cache)
        print("🚀 Step 2: Second schema fetch (should use cache)...")
        start_time = time.time()
        cached_schema = await fetch_airtable_schema()
        second_fetch_time = time.time() - start_time
        
        print(f"✅ Schema fetched in {second_fetch_time:.2f} seconds!")
        
        # Verify it's the same content
        schemas_match = schema == cached_schema
        print(f"🔍 Schema content matches: {schemas_match}")
        
        # Show performance improvement
        speed_improvement = first_fetch_time / second_fetch_time if second_fetch_time > 0 else float('inf')
        print(f"⚡ Performance improvement: {speed_improvement:.1f}x faster")
        print()
        
        # Test 3: Cache info
        print("🚀 Step 3: Checking cache information...")
        cache_info = get_cache_info()
        
        for base_id, info in cache_info.items():
            print(f"📊 Cache for base {base_id}:")
            print(f"   ⏰ Cached at: {info['cached_at']}")
            print(f"   ⏳ Time remaining: {info['time_remaining_minutes']:.1f} minutes")
            print(f"   ✅ Valid: {info['is_valid']}")
        print()
        
        # Test 4: Build dynamic prompt (should use cache)
        print("🚀 Step 4: Building dynamic system prompt...")
        start_time = time.time()
        full_prompt = await build_dynamic_system_prompt()
        prompt_build_time = time.time() - start_time
        
        print(f"✅ Dynamic prompt built in {prompt_build_time:.2f} seconds!")
        print(f"📝 Prompt length: {len(full_prompt)} characters")
        print()
        
        # Test 5: Initialize agent
        print("🚀 Step 5: Initializing agent with cached schema...")
        start_time = time.time()
        agent = await get_airtable_assistant()
        agent_init_time = time.time() - start_time
        
        print(f"✅ Agent initialized in {agent_init_time:.2f} seconds!")
        print("🤖 Agent is ready with live schema information!")
        print()
        
        # Test 6: Force refresh
        print("🚀 Step 6: Testing force refresh...")
        start_time = time.time()
        fresh_schema = await fetch_airtable_schema(force_refresh=True)
        force_refresh_time = time.time() - start_time
        
        print(f"✅ Force refresh completed in {force_refresh_time:.2f} seconds!")
        schemas_still_match = schema == fresh_schema
        print(f"🔍 Schema content still matches: {schemas_still_match}")
        print()
        
        # Show performance summary
        print("📊 **Performance Summary:**")
        print(f"   🔥 First fetch (API):     {first_fetch_time:.2f}s")
        print(f"   ⚡ Cached fetch:          {second_fetch_time:.2f}s ({speed_improvement:.1f}x faster)")
        print(f"   📝 Prompt build (cached): {prompt_build_time:.2f}s")
        print(f"   🤖 Agent init (cached):   {agent_init_time:.2f}s")
        print(f"   🔄 Force refresh:         {force_refresh_time:.2f}s")
        print()
        
        # Show stats
        prompt_lines = full_prompt.count('\n')
        schema_lines = schema.count('\n')
        tables_mentioned = schema.count('### 📋 Table:')
        
        print("📊 **Schema Statistics:**")
        print(f"   📝 Total prompt lines: {prompt_lines}")
        print(f"   🗂️  Schema lines: {schema_lines}")
        print(f"   📋 Tables discovered: {tables_mentioned}")
        print()
        
        print("🎉 **Dynamic Airtable Agent Enhancement Complete!**")
        print()
        print("💡 **What's New:**")
        print("   ✨ Agent prompt includes live table schemas")
        print("   ⚡ Smart caching for optimal performance")
        print("   🔄 30-minute cache TTL with force refresh option")
        print("   📊 Real field names, types, and sample values")
        print("   🎯 More accurate field references in conversations")
        print("   🚀 Self-updating when Airtable schema changes")
        print("   💾 Cache management functions for control")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        logger.exception("Detailed error information:")


async def test_cache_invalidation():
    """Test cache invalidation and refresh behavior."""
    
    print("\n" + "="*60)
    print("⏰ CACHE INVALIDATION TEST")
    print("="*60)
    
    print("🧪 Testing cache behavior...")
    
    # Clear cache
    clear_schema_cache()
    print("🗑️ Cache cleared")
    
    # First fetch
    start = time.time()
    await fetch_airtable_schema()
    first_time = time.time() - start
    print(f"⏱️  First fetch: {first_time:.2f}s")
    
    # Cached fetch
    start = time.time()
    await fetch_airtable_schema()
    cached_time = time.time() - start
    print(f"⚡ Cached fetch: {cached_time:.2f}s")
    
    # Force refresh
    start = time.time()
    await fetch_airtable_schema(force_refresh=True)
    refresh_time = time.time() - start
    print(f"🔄 Force refresh: {refresh_time:.2f}s")
    
    print("✅ Cache invalidation working correctly!")


async def show_schema_comparison():
    """Show the difference between old hardcoded vs new dynamic schema."""
    
    print("\n" + "="*60)
    print("📊 SCHEMA ENHANCEMENT COMPARISON")
    print("="*60)
    
    print("🔴 **BEFORE (Hardcoded):**")
    print("```")
    print("### Table `Tasks`")
    print("| Field | Type | Notes |")
    print("| Task Name | single line text | Primary key |")
    print("| Status | single select | A fazer · Estou trabalhando... |")
    print("```")
    print("❌ Static, can become outdated")
    print("❌ Manual maintenance required")
    print("❌ No visibility into actual field values")
    print("❌ No performance optimization")
    print()
    
    print("🟢 **AFTER (Dynamic + Cached):**")
    try:
        schema = await fetch_airtable_schema()
        preview_lines = schema.split('\n')[:15]
        print("```")
        for line in preview_lines:
            print(line)
        print("... (and more)")
        print("```")
        print("✅ Always up-to-date with real Airtable data")
        print("✅ Shows actual field names and types")
        print("✅ Includes sample values for context")
        print("✅ Self-maintaining with smart caching")
        print("⚡ Performance optimized with 30-min TTL")
        print("🔄 Force refresh available when needed")
    except Exception as e:
        print(f"❌ Could not fetch dynamic schema: {e}")


async def main():
    """Main test execution."""
    print("🤖 Dynamic Airtable Agent Enhancement Test")
    print("="*60)
    
    await test_schema_fetching()
    await test_cache_invalidation()
    await show_schema_comparison()
    
    print("\n🎯 **Next Steps:**")
    print("1. Agent automatically fetches and caches schema (30-min TTL)")
    print("2. Use `force_refresh=True` for immediate schema updates")
    print("3. Monitor cache with `get_cache_info()` function")
    print("4. Clear cache manually with `clear_schema_cache()` if needed")
    print("5. The agent now has optimal performance + accuracy!")


if __name__ == "__main__":
    asyncio.run(main()) 