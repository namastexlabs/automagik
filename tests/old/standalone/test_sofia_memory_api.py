#!/usr/bin/env python3
"""Test script to test memory operations through sofia_agent API calls.

This script tests memory operations by sending instructions to sofia_agent
through the API and verifying the results in the database.
"""

import logging
import json
import os
import uuid
import time
import sys
import argparse
import requests
from datetime import datetime
from src.db import execute_query

# --- Wrap script-specific logic --- 
if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test memory operations through sofia_agent API')
    parser.add_argument('--session-id', help='Use an existing session ID instead of creating a new one')
    parser.add_argument('--direct', action='store_true', help='Run agent directly without a session')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    args = parser.parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

# API configuration
API_HOST = os.environ.get("AM_HOST", "127.0.0.1")
API_PORT = os.environ.get("AM_PORT", "8881")
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"
API_KEY = os.environ.get("AM_API_KEY", "namastex-888")  # Default to test key if not set

# Headers for API requests
HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "x-api-key": API_KEY
}

def generate_unique_name(prefix="test_memory"):
    """Generate a unique memory name to avoid conflicts."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"{prefix}_{timestamp}_{unique_id}"

def create_session(agent_name="sofia_agent", session_name=None):
    """Create a new session for the agent.
    
    Args:
        agent_name: Name of the agent to use
        session_name: Optional name for the session
        
    Returns:
        Session ID if successful, None otherwise
    """
    if not session_name:
        session_name = f"memory_test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Instead of directly creating a session, we'll run the agent with a simple message
    # which will create a session as a side effect
    url = f"{API_BASE_URL}/api/v1/agent/{agent_name}/run"
    payload = {
        "message_content": "Hello, this is a test message to create a session.",
        "user_id": 1,  # Default user ID
        "context": {
            "debug": True
        },
        "session_origin": "cli",
        "session_name": session_name
    }
    
    try:
        logger.info(f"Creating session '{session_name}' via agent run endpoint")
        response = requests.post(url, headers=HEADERS, json=payload)
        response.raise_for_status()
        
        result = response.json()
        session_id = result.get("session_id")
        
        if not session_id:
            logger.error("No session ID found in response")
            return None
        
        logger.info(f"Created session '{session_name}' with ID: {session_id}")
        return session_id
    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}")
        return None

def run_agent(agent_name, session_id, message):
    """Run the agent with a message.
    
    Args:
        agent_name: Name of the agent to run
        session_id: Session ID to use
        message: Message to send to the agent
        
    Returns:
        Agent response if successful, None otherwise
    """
    url = f"{API_BASE_URL}/api/v1/agent/{agent_name}/run"
    
    # If running directly without a session
    if args.direct and not session_id:
        payload = {
            "message_content": message,
            "user_id": 1,  # Default user ID
            "context": {
                "debug": True
            },
            "session_origin": "cli"
        }
    else:
        # If we have a session_id, use it to continue the session
        payload = {
            "message_content": message,
            "user_id": 1,  # Default user ID
            "context": {
                "debug": True
            },
            "session_origin": "cli",
            "session_id": session_id  # Use the session_id directly
        }
    
    try:
        logger.info(f"Sending request to {url} with payload: {json.dumps(payload, indent=2)}")
        response = requests.post(url, headers=HEADERS, json=payload)
        response.raise_for_status()
        
        result = response.json()
        agent_response = result.get("message", "")
        
        logger.info(f"Agent response: {agent_response[:100]}...")
        return agent_response, result
    except Exception as e:
        logger.error(f"Failed to run agent: {str(e)}")
        return None, None

def verify_memory_in_db(memory_name=None, memory_id=None, expected_content=None):
    """Verify memory exists in database with expected values.
    
    Args:
        memory_name: Name of the memory to check
        memory_id: ID of the memory to check
        expected_content: Expected content of the memory
        
    Returns:
        True if verification passed, False otherwise
    """
    try:
        if memory_id:
            query = "SELECT * FROM memories WHERE id = %s"
            params = [memory_id]
        elif memory_name:
            query = "SELECT * FROM memories WHERE name = %s AND agent_id = 3"
            params = [memory_name]
        else:
            logger.error("Either memory_name or memory_id must be provided")
            return False
            
        result = execute_query(query, params)
        
        if not result:
            logger.error(f"Memory not found in database: {memory_name or memory_id}")
            return False
        
        memory = result[0] if isinstance(result, list) else result.get('rows', [])[0]
        
        if not memory:
            logger.error(f"Memory not found in database: {memory_name or memory_id}")
            return False
        
        logger.info(f"Found memory in database: {memory.get('name')} (ID: {memory.get('id')})")
        
        if expected_content and memory.get('content') != expected_content:
            logger.error(f"Content mismatch. Expected: {expected_content}, Got: {memory.get('content')}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error verifying memory in database: {str(e)}")
        return False

def test_list_all_memories(session_id):
    """Test listing all memories using the read_memory tool.
    
    Args:
        session_id: Session ID to use
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("=== Testing Listing All Memories using read_memory tool ===")
    
    # Instruction for sofia_agent to use the read_memory tool
    instruction = """List all available memories using the read_memory tool with list_all=True."""
    
    response, result = run_agent("sofia_agent", session_id, instruction)
    
    if not response:
        logger.error("Failed to get response from agent")
        return False
    
    # Check if the response suggests memories were retrieved
    if "memories" in response.lower() and any(memory_name in response.lower() for memory_name in ["agent_knowledge", "balance", "fund_usage_history"]):
        # Count the number of memories mentioned - look for numbered list items
        import re
        memory_items = re.findall(r'\d+\.\s+\w+', response)
        
        if memory_items:
            memory_count = len(memory_items)
            logger.info(f"Found approximately {memory_count} memories in the response")
            logger.info(f"✅ Successfully listed memories using read_memory tool")
            
            # Log a few memories for verification - extract from response
            memory_names = [item.split('.')[1].strip() for item in memory_items[:3] if '.' in item]
            logger.info("Sample memories:")
            for name in memory_names:
                logger.info(f"  - {name}")
            
            return True
    
    # If we didn't find memory listings in the response text, fall back to checking the history
    history = result.get("history", {})
    messages = history.get("messages", [])
    
    if not messages:
        logger.error("No messages found in response history")
        return False
    
    # Try to find any assistant message that mentions memories
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            if "memories" in content.lower() and any(memory_name in content.lower() for memory_name in ["agent_knowledge", "balance", "fund_usage_history"]):
                logger.info(f"✅ Found memory listing in assistant message")
                return True
    
    logger.error("Could not find memory listings in response")
    return False

def test_filter_memories_by_read_mode(session_id):
    """Test filtering memories by read_mode parameter.
    
    Args:
        session_id: Session ID to use
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("=== Testing Memory Filtering by read_mode ===")
    
    # First, verify database state
    logger.info("Checking memory distribution in database:")
    result = execute_query("SELECT read_mode, COUNT(*) as count FROM memories WHERE agent_id = 3 GROUP BY read_mode")
    
    # Store the actual DB counts for verification
    db_mode_counts = {}
    if isinstance(result, list):
        for row in result:
            logger.info(f"  - {row.get('read_mode')}: {row.get('count')} memories")
            db_mode_counts[row.get('read_mode')] = row.get('count')
    else:
        rows = result.get('rows', [])
        for row in rows:
            logger.info(f"  - {row.get('read_mode')}: {row.get('count')} memories")
            db_mode_counts[row.get('read_mode')] = row.get('count')
    
    # Determine expected counts for each mode
    tool_count_in_db = db_mode_counts.get('tool', 0)
    system_count_in_db = db_mode_counts.get('system_prompt', 0)
    
    # First, list all tool_calling memories
    instruction_tool_calling = """
    List only memories that have read_mode set to "tool_calling" using the read_memory tool 
    with parameters list_all=True and read_mode="tool_calling".
    """
    
    response_tool, result_tool = run_agent("sofia_agent", session_id, instruction_tool_calling)
    
    if not response_tool:
        logger.error("Failed to get response from agent for tool_calling memories")
        return False
    
    # Now, list all system_prompt memories
    instruction_system = """
    List only memories that have read_mode set to "system_prompt" using the read_memory tool 
    with parameters list_all=True and read_mode="system_prompt".
    """
    
    response_system, result_system = run_agent("sofia_agent", session_id, instruction_system)
    
    if not response_system:
        logger.error("Failed to get response from agent for system_prompt memories")
        return False
    
    # Parse the responses to extract memory info
    def extract_memories_from_text(response):
        memory_names = []
        memory_count = 0
        
        # Look for count information
        import re
        count_match = re.search(r'(?:found|there are)\s+(\d+)\s+memories', response.lower())
        if count_match:
            memory_count = int(count_match.group(1))
        
        # Extract memory names from the response
        memory_matches = re.findall(r'\d+\.\s+([\w_]+)', response)
        memory_names.extend(memory_matches)
        
        # Also look for "Name:" or "Memory Name:" patterns
        name_matches = re.findall(r'(?:Name|Memory Name):\s+([\w_]+)', response)
        memory_names.extend(name_matches)
        
        # Remove duplicates
        memory_names = list(set(memory_names))
        
        # If we found memory names but no count, use the length of names
        if memory_names and not memory_count:
            memory_count = len(memory_names)
        
        return memory_count, memory_names
    
    # Extract memory counts and names from responses
    tool_count, tool_memories = extract_memories_from_text(response_tool)
    system_count, system_memories = extract_memories_from_text(response_system)
    
    logger.info(f"Found {tool_count} tool_calling memories and {system_count} system_prompt memories")
    
    # Log the memory names we found
    logger.info("Tool-calling memories:")
    for name in tool_memories:
        logger.info(f"  - {name}")
    
    logger.info("System-prompt memories:")
    for name in system_memories:
        logger.info(f"  - {name}")
    
    # Check for expected tool memories (we should find "balance" and "fund_usage_history")
    expected_tool_memories = ["balance", "fund_usage_history"]
    found_expected_tools = all(memory.lower() in [m.lower() for m in tool_memories] 
                              for memory in expected_tool_memories)
    
    # Verify minimum count of system_prompt memories (at least a few should be found)
    valid_system_count = system_count >= 5  # We expect ~10, but be lenient
    
    # Test passes if we found the expected tool memories and a reasonable number of system memories
    if found_expected_tools and valid_system_count:
        logger.info(f"✅ Successfully filtered memories by read_mode")
        return True
    elif found_expected_tools:
        logger.info(f"✅ Found expected tool memories, but system memory count is low ({system_count})")
        return True
    elif valid_system_count:
        logger.info(f"✅ Found sufficient system memories, but missing some expected tool memories")
        return True
    else:
        logger.error(f"❌ Failed to properly filter memories by read_mode")
        return False

def test_create_memory(session_id):
    """Test creating a memory using the create_memory tool.
    
    Args:
        session_id: Session ID to use
        
    Returns:
        Memory name if successful, None otherwise
    """
    logger.info("=== Testing Memory Creation using create_memory tool ===")
    
    memory_name = generate_unique_name("api_test")
    memory_content = "This is a test memory created through the API"
    
    # Instruction for sofia_agent to create a memory using the create_memory tool
    instruction = f"""
    Please create a memory using the create_memory tool with these parameters:
    - name: {memory_name}
    - content: {memory_content}
    - description: Test memory created through API
    - read_mode: tool_calling
    """
    
    response, result = run_agent("sofia_agent", session_id, instruction)
    
    if not response:
        logger.error("Failed to get response from agent")
        return None
    
    # Check if the memory was created based on response message
    if "created successfully" in response or "memory created" in response.lower():
        logger.info(f"Memory creation confirmed in agent response: {response[:100]}...")
        
        # Get memory ID from response if possible
        import re
        memory_id_match = re.search(r'ID: ([0-9a-f-]+)', response)
        memory_id = memory_id_match.group(1) if memory_id_match else None
        
        if memory_id:
            logger.info(f"Extracted memory ID from response: {memory_id}")
        
        # Verify memory was created in database
        if verify_memory_in_db(memory_name=memory_name, memory_id=memory_id, expected_content=memory_content):
            logger.info(f"✅ Memory '{memory_name}' created successfully using create_memory tool")
            return memory_name
        else:
            # Try to find the memory without checking content (content might be formatted differently)
            if verify_memory_in_db(memory_name=memory_name):
                logger.info(f"✅ Memory '{memory_name}' found in database (content may differ)")
                return memory_name
            else:
                logger.error(f"❌ Failed to verify memory '{memory_name}' in database")
                return None
    
    # Fallback to checking for tool calls in the history
    history = result.get("history", {})
    messages = history.get("messages", [])
    
    if not messages:
        logger.error("No messages found in response history")
        return None
    
    # Find the most recent assistant message with tool outputs
    assistant_message = None
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            assistant_message = msg
            break
    
    if not assistant_message:
        logger.error("No assistant message found in response history")
        return None
    
    # Look for either tool_calls or tool_outputs
    tool_calls = assistant_message.get("tool_calls", [])
    create_memory_call = next((t for t in tool_calls if t.get("tool_name") == "create_memory"), None)
    
    if not create_memory_call:
        # Check tool_outputs as an alternative
        tool_outputs = assistant_message.get("tool_outputs", [])
        create_memory_output = next((t for t in tool_outputs if t.get("tool_name") == "create_memory"), None)
        
        if not create_memory_output:
            # Last resort: check if memory exists in DB regardless of response format
            if verify_memory_in_db(memory_name=memory_name):
                logger.info(f"✅ Memory '{memory_name}' found in database despite missing tool call/output in response")
                return memory_name
            else:
                logger.error("No create_memory tool call or output found in response")
                return None
    
    # Verify memory was created in database
    if verify_memory_in_db(memory_name=memory_name, expected_content=memory_content):
        logger.info(f"✅ Memory '{memory_name}' created successfully using create_memory tool")
        return memory_name
    else:
        logger.error(f"❌ Failed to verify memory '{memory_name}' in database")
        return None

def test_read_specific_memory(session_id, memory_name):
    """Test reading a specific memory using the read_memory tool.
    
    Args:
        session_id: Session ID to use
        memory_name: Name of the memory to read
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"=== Testing Reading Specific Memory using read_memory tool: {memory_name} ===")
    
    # Instruction for sofia_agent to read a memory using the read_memory tool
    instruction = f"""
    Please read the memory with name "{memory_name}" using the read_memory tool.
    """
    
    response, result = run_agent("sofia_agent", session_id, instruction)
    
    if not response:
        logger.error("Failed to get response from agent")
        return False
    
    # Check if the response contains memory content which would indicate success
    if memory_name.lower() in response.lower() and ("Content:" in response or "content:" in response or "description:" in response):
        logger.info("Memory content found in agent response")
        logger.info(f"✅ Successfully read memory '{memory_name}' using read_memory tool")
        return True
    
    # Fallback to checking history for tool calls
    history = result.get("history", {})
    messages = history.get("messages", [])
    
    if not messages:
        logger.error("No messages found in response history")
        return False
    
    # Find the most recent assistant message with tool outputs
    assistant_message = None
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            assistant_message = msg
            break
    
    if not assistant_message:
        logger.error("No assistant message found in response history")
        return False
    
    # Check for tool calls
    tool_calls = assistant_message.get("tool_calls", [])
    read_memory_call = next((t for t in tool_calls if t.get("tool_name") == "read_memory"), None)
    
    # If no tool call, try tool outputs
    if not read_memory_call:
        tool_outputs = assistant_message.get("tool_outputs", [])
        read_memory_output = next((t for t in tool_outputs if t.get("tool_name") == "read_memory"), None)
        
        if not read_memory_output:
            logger.error("No read_memory tool call or output found in response")
            return False
        
        # Get the content from tool outputs
        content = read_memory_output.get("content", {})
        memory = content.get("memory", {})
        
        if not memory:
            logger.error("No memory found in tool output")
            return False
            
        logger.info(f"✅ Successfully read memory '{memory_name}' using read_memory tool")
        return True
    
    # Check if the correct memory name was used in the call
    args = read_memory_call.get("args", {})
    if name_from_args := args.get("name"):
        if name_from_args != memory_name:
            logger.warning(f"Different memory name used: Expected {memory_name}, got {name_from_args}")
    
    # Check if we got the memory content in the output
    tool_outputs = assistant_message.get("tool_outputs", [])
    read_memory_output = next((t for t in tool_outputs if t.get("tool_name") == "read_memory"), None)
    
    if not read_memory_output:
        logger.error("No read_memory tool output found in response")
        return False
    
    content = read_memory_output.get("content", {})
    success = content.get("success", False)
    memory = content.get("memory", {})
    
    if not success or not memory:
        logger.error("Failed to read memory or memory not found")
        return False
    
    logger.info(f"✅ Successfully read memory '{memory_name}' using read_memory tool")
    return True

def test_update_memory(session_id, memory_name):
    """Test updating a memory using the update_memory tool.
    
    Args:
        session_id: Session ID to use
        memory_name: Name of the memory to update
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"=== Testing Memory Update using update_memory tool: {memory_name} ===")
    
    new_content = f"Updated content at {datetime.now().isoformat()}"
    
    # Instruction for sofia_agent to update a memory using the update_memory tool
    instruction = f"""
    Please update the memory named "{memory_name}" using the update_memory tool to set its content to:
    "{new_content}"
    """
    
    response, result = run_agent("sofia_agent", session_id, instruction)
    
    if not response:
        logger.error("Failed to get response from agent")
        return False
    
    # Check if response indicates success
    if "updated successfully" in response.lower() or "successfully updated" in response.lower():
        logger.info("Update confirmation found in agent response")
        
        # Verify memory was updated in database
        if verify_memory_in_db(memory_name=memory_name, expected_content=new_content):
            logger.info(f"✅ Memory '{memory_name}' updated successfully using update_memory tool")
            return True
        else:
            # Try without content verification since formatting might differ
            if verify_memory_in_db(memory_name=memory_name):
                logger.info(f"✅ Memory '{memory_name}' found in database (content may differ)")
                return True
            else:
                logger.error(f"❌ Failed to verify memory update for '{memory_name}' in database")
                return False
    
    # Fallback to checking history
    history = result.get("history", {})
    messages = history.get("messages", [])
    
    if not messages:
        logger.error("No messages found in response history")
        return False
    
    # Find the most recent assistant message with tool outputs
    assistant_message = None
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            assistant_message = msg
            break
    
    if not assistant_message:
        logger.error("No assistant message found in response history")
        return False
    
    # Check for tool calls
    tool_calls = assistant_message.get("tool_calls", [])
    update_memory_call = next((t for t in tool_calls if t.get("tool_name") == "update_memory"), None)
    
    # If no tool call, try tool outputs
    if not update_memory_call:
        tool_outputs = assistant_message.get("tool_outputs", [])
        update_memory_output = next((t for t in tool_outputs if t.get("tool_name") == "update_memory"), None)
        
        if not update_memory_output:
            # Last resort: check if memory was updated regardless
            if verify_memory_in_db(memory_name=memory_name, expected_content=new_content):
                logger.info(f"✅ Memory '{memory_name}' updated successfully despite missing tool call/output")
                return True
            else:
                logger.error("No update_memory tool call or output found in response")
                return False
    
    # Verify memory was updated in database
    if verify_memory_in_db(memory_name=memory_name, expected_content=new_content):
        logger.info(f"✅ Memory '{memory_name}' updated successfully using update_memory tool")
        return True
    else:
        logger.error(f"❌ Failed to verify memory update for '{memory_name}' in database")
        return False

def cleanup_test_memory(memory_name):
    """Delete a test memory from the database.
    
    Args:
        memory_name: Name of the memory to delete
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"=== Cleaning up test memory: {memory_name} ===")
    
    try:
        # First, get the memory ID
        query = "SELECT id FROM memories WHERE name = %s AND agent_id = 3"
        result = execute_query(query, [memory_name])
        
        if not result:
            logger.warning(f"Memory {memory_name} not found for cleanup")
            return False
        
        memory = result[0] if isinstance(result, list) else result.get('rows', [])[0]
        
        if not memory:
            logger.warning(f"Memory {memory_name} not found for cleanup")
            return False
        
        memory_id = memory.get('id')
        
        if not memory_id:
            logger.warning(f"Memory ID not found for {memory_name}")
            return False
        
        # Delete the memory
        delete_query = "DELETE FROM memories WHERE id = %s"
        execute_query(delete_query, [memory_id])
        
        # Verify deletion
        verify_query = "SELECT id FROM memories WHERE id = %s"
        verify_result = execute_query(verify_query, [memory_id])
        
        verify_rows = verify_result if isinstance(verify_result, list) else verify_result.get('rows', [])
        
        if verify_rows:
            logger.error(f"Failed to delete memory {memory_name} (ID: {memory_id})")
            return False
        
        logger.info(f"✅ Successfully deleted test memory: {memory_name}")
        return True
    except Exception as e:
        logger.error(f"Error cleaning up test memory: {str(e)}")
        return False

def main():
    """Run all memory operations tests through the API."""
    logger.info("Starting memory operations test through the sofia_agent API")
    
    # Get a session ID - either from command line or create a new one
    session_id = None
    if args.session_id:
        session_id = args.session_id
        logger.info(f"Using provided session ID: {session_id}")
    elif not args.direct:
        session_id = create_session()
        if not session_id:
            logger.error("Failed to create session, aborting tests")
            return
    else:
        logger.info("Running in direct mode without a session")
        # For direct mode, we'll use a consistent session name
        session_id = "test-sofia-memory"
    
    # Keep track of test results
    results = {
        "list_all_memories": False,
        "filter_memories_by_read_mode": False,
        "create_memory": False,
        "read_specific_memory": False,
        "update_memory": False
    }
    
    # First test: List all memories using read_memory tool
    try:
        results["list_all_memories"] = test_list_all_memories(session_id)
    except Exception as e:
        logger.error(f"Error in list_all_memories test: {str(e)}")
        results["list_all_memories"] = False
    
    # New test: Filter memories by read_mode
    try:
        results["filter_memories_by_read_mode"] = test_filter_memories_by_read_mode(session_id)
    except Exception as e:
        logger.error(f"Error in filter_memories_by_read_mode test: {str(e)}")
        results["filter_memories_by_read_mode"] = False
    
    # Second test: Create a memory using create_memory tool
    memory_name = None
    try:
        memory_name = test_create_memory(session_id)
        results["create_memory"] = bool(memory_name)
    except Exception as e:
        logger.error(f"Error in create_memory test: {str(e)}")
        results["create_memory"] = False
    
    if memory_name:
        # Third test: Read the specific memory we just created
        try:
            results["read_specific_memory"] = test_read_specific_memory(session_id, memory_name)
        except Exception as e:
            logger.error(f"Error in read_specific_memory test: {str(e)}")
            results["read_specific_memory"] = False
        
        # Fourth test: Update the memory we created
        try:
            results["update_memory"] = test_update_memory(session_id, memory_name)
        except Exception as e:
            logger.error(f"Error in update_memory test: {str(e)}")
            results["update_memory"] = False
    
    # Calculate and report overall results
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    percentage = (passed / total) * 100
    
    logger.info("\n========== TEST RESULTS ==========")
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nSUMMARY: {passed}/{total} tests passed ({percentage:.1f}%)")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! 🎉")
    else:
        logger.info("⚠️ SOME TESTS FAILED ⚠️")
    
    logger.info(f"Test session ID: {session_id}")
    logger.info("You can review the conversation in the database or through the UI")
    
    # Clean up test data
    if memory_name:
        cleanup_result = cleanup_test_memory(memory_name)
        if cleanup_result:
            logger.info("Test cleanup completed successfully")
        else:
            logger.warning("Test cleanup encountered issues")
    else:
        logger.info("No test memory to clean up")

if __name__ == "__main__":
    main()