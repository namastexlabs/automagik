#!/usr/bin/env python

"""
This script directly tests the current implementation of memory tool descriptions
by initializing the SimpleAgent and printing the exact descriptions used.
"""

import os
import sys
from pprint import pprint

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Configure logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Import necessary modules
from src.agents.simple.simple_agent.agent import SimpleAgent
from src.tools.memory.tool import read_memory, create_memory

def main():
    """Create a SimpleAgent instance and extract the exact tool descriptions directly."""
    print("\n===== DIRECT TOOL DESCRIPTION TEST =====\n")
    
    # Initialize the SimpleAgent with proper config
    print("Initializing SimpleAgent...")
    config = {
        "agent_id": "direct-test",
        "model": "gpt-3.5-turbo",  # Default model
        "retries": 1
    }
    agent = SimpleAgent(config=config)
    
    # We need to directly access the tool descriptions being generated
    print("\nDIRECTLY ACCESSING MEMORY TOOL DESCRIPTIONS FROM AGENT CODE:")
    print("Importing necessary modules to directly access descriptions...")

    
    # To directly access tool descriptions, let's use the same code from agent.py
    from src.tools.memory.tool import read_memory, create_memory
    from src.db import list_memories
    import inspect
    
    # Get all available memories using repository function
    memories = list_memories()
    
    # Convert memory models to dictionaries for consistent access
    memory_dicts = []
    for memory in memories:
        if hasattr(memory, 'model_dump'):
            # For Pydantic v2 models
            memory_dicts.append(memory.model_dump())
        elif hasattr(memory, 'dict'):
            # For Pydantic v1 models
            memory_dicts.append(memory.dict())
        elif isinstance(memory, dict):
            # Already a dict
            memory_dicts.append(memory)
        else:
            # Extract attributes directly
            memory_dicts.append({
                'id': getattr(memory, 'id', None),
                'name': getattr(memory, 'name', 'Unknown'),
                'description': getattr(memory, 'description', None)
            })
    
    memory_count = len(memory_dicts)
    
    print(f"Found {memory_count} memories in database")
    
    # Extract memory names for reference
    memory_names = [memory.get('name', 'Unknown') for memory in memory_dicts]
    print(f"Memory names: {', '.join(memory_names)}")

    
    # Create read_memory description using same code from SimpleAgent
    print("Creating read_memory description directly using SimpleAgent code:")

    read_desc = "This tool allows retrieving memories stored in the database. It can return a "
    read_desc += "specific memory based on ID or name. Available parameters:\n\n"
    read_desc += "- **memory_id**: Optional ID of the specific memory to retrieve\n"
    read_desc += "- **name**: Optional memory name (or partial name) to search for\n"
    read_desc += "- **list_all**: If True, returns all memories available to this agent/user\n\n"
    
    # Add memory names section
    if memory_count > 0:
        read_desc += "Memories available to this agent/user:\n"
        
        max_desc_length = 950  # Limit to stay within API constraints
        memories_added = 0
        memory_names_str = ""
        
        for memory in memory_dicts:
            mem_name = memory.get('name', 'Unknown')
            memory_entry = f"- {mem_name}\n"
            
            # Check if adding this would exceed our limit
            if len(read_desc) + len(memory_entry) + 30 > max_desc_length:
                remaining = memory_count - memories_added
                if remaining > 0:
                    memory_names_str += f"...and {remaining} more."
                break
            
            memory_names_str += memory_entry
            memories_added += 1
        
        read_desc += memory_names_str
    else:
        read_desc += "No memories are currently available to this agent/user."
    
    print(read_desc)
    print(f"Character count: {len(read_desc)}")
    
    # Create write_memory description using same code from SimpleAgent
    print("Creating write_memory description directly using SimpleAgent code:")

    write_desc = "This tool has two distinct uses:\n\n"
        
    # 1. Creating new memories
    write_desc += "1. CREATING A NEW MEMORY:\n"
    write_desc += "   Required parameters:\n"
    write_desc += "   - **name**: The name of the new memory to create\n"
    write_desc += "   - **content**: The content to store (string or dictionary format)\n"
    write_desc += "   - **description**: A description of what this memory contains or is used for\n"
    write_desc += "   - **read_mode**: Controls how this memory is used (e.g., tool_call, system_prompt)\n"
    write_desc += "   - **access**: The access permissions for this memory (e.g., read, write)\n\n"
    
    # 2. Updating existing memories
    write_desc += "2. UPDATING AN EXISTING MEMORY:\n"
    write_desc += "   Required parameters:\n"
    write_desc += "   - **memory_id** OR **name**: ID or name of the existing memory to update\n"
    write_desc += "   - **content**: The new content to store\n\n"
    
    # Add memory names section
    if memory_count > 0:
        write_desc += "Memories available for updating (that belong to this agent/user):\n"
        
        max_desc_length = 900  # Limit to stay within API constraints
        memories_added = 0
        memory_names_str = ""
        
        for memory in memory_dicts:
            mem_name = memory.get('name', 'Unknown')
            memory_entry = f"- {mem_name}\n"
            
            # Check if adding this would exceed our limit
            if len(write_desc) + len(memory_entry) + 30 > max_desc_length:
                remaining = memory_count - memories_added
                if remaining > 0:
                    memory_names_str += f"...and {remaining} more."
                break
            
            memory_names_str += memory_entry
            memories_added += 1
        
        write_desc += memory_names_str
    else:
        write_desc += "No existing memories are available for updating."
    
    print(write_desc)
    print(f"Character count: {len(write_desc)}")
    
    # Save these descriptions to files
    with open("direct_read_memory_desc.txt", "w") as f:
        f.write(read_desc)
    
    with open("direct_write_memory_desc.txt", "w") as f:
        f.write(write_desc)
    
    print("Direct descriptions saved to:\n- direct_read_memory_desc.txt\n- direct_write_memory_desc.txt")

    
    # Now try to access the actual pydantic-ai Agent instance and its tools
    pydantic_agent = agent.agent
    
    # Find the memory tools in the agent's tools
    memory_tools = {}
    if hasattr(pydantic_agent, 'tools'):
        for tool in pydantic_agent.tools:
            if tool.name in ["read_memory", "write_memory"]:
                memory_tools[tool.name] = tool
        
        print(f"Found {len(memory_tools)} memory tools in agent.tools")
    else:
        print("Warning: Agent does not have 'tools' attribute. Accessing through __dict__...")
        if hasattr(pydantic_agent, '__dict__'):
            print(f"Agent __dict__ keys: {list(pydantic_agent.__dict__.keys())}")
    
    # Print the actual tool descriptions being used
    print("\n===== ACTUAL TOOL DESCRIPTIONS IN AGENT =====\n")
    
    if "read_memory" in memory_tools:
        print("READ_MEMORY DESCRIPTION:")
        print("-" * 80)
        read_desc = memory_tools["read_memory"].description
        print(read_desc)
        print(f"Character count: {len(read_desc)}")
        print("-" * 80)
    else:
        print("READ_MEMORY tool not found in agent!")
    
    if "write_memory" in memory_tools:
        print("\nWRITE_MEMORY DESCRIPTION:")
        print("-" * 80)
        write_desc = memory_tools["write_memory"].description
        print(write_desc)
        print(f"Character count: {len(write_desc)}")
        print("-" * 80)
    else:
        print("WRITE_MEMORY tool not found in agent!")
    
    # Save descriptions to files for easy comparison
    with open("actual_read_memory_desc.txt", "w") as f:
        if "read_memory" in memory_tools:
            f.write(memory_tools["read_memory"].description)
    
    with open("actual_write_memory_desc.txt", "w") as f:
        if "write_memory" in memory_tools:
            f.write(memory_tools["write_memory"].description)
    
    print("\nTool descriptions saved to:")
    print("- actual_read_memory_desc.txt")
    print("- actual_write_memory_desc.txt")
    
    # Print original docstrings for comparison
    print("\n===== ORIGINAL DOCSTRINGS FROM MEMORY_TOOLS =====\n")
    print("READ_MEMORY ORIGINAL DOCSTRING:")
    print("-" * 80)
    print(read_memory.__doc__)
    print("-" * 80)
    
    print("\nWRITE_MEMORY ORIGINAL DOCSTRING:")
    print("-" * 80)
    print(write_memory.__doc__)
    print("-" * 80)
    
    print("\n===== TEST COMPLETE =====\n")

if __name__ == "__main__":
    main()
