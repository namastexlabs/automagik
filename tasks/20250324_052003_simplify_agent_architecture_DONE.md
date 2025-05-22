## Analysis
The current `simple_agent/agent.py` implementation still contains significant complexity despite previous refactoring efforts. The agent handles numerous responsibilities:

1. Message parsing and extraction
2. Tool call/output handling 
3. Session/context management
4. Memory variable handling
5. Multimodal content processing

Our recent refactoring separated some concerns into modules like `prompt_builder.py`, `memory_handler.py`, and `tool_registry.py`. However, these modules remain within the simple_agent folder, limiting their reusability for other agent implementations.

Additionally, there are still several helper methods and utilities embedded within the agent class that could be extracted to create a cleaner, more maintainable codebase.

## Plan

### Step 1: Move Common Components to Parent Directory
Move these components from `src/agents/simple/simple_agent/` up to `src/agents/common/` to make them available to all agent implementations:

1. `prompt_builder.py` → `src/agents/common/prompt_builder.py`
2. `memory_handler.py` → `src/agents/common/memory_handler.py`
3. `tool_registry.py` → `src/agents/common/tool_registry.py`

### Step 2: Create New Utility Modules
Extract additional helper functionality into new utility files:

1. `src/agents/common/message_parser.py`
   - Functions for parsing messages
   - Tool call extraction
   - Tool output processing
   - Message history formatting

2. `src/agents/common/session_manager.py`
   - Functions for managing user/agent sessions
   - Context handling
   - ID management (user_id, agent_id)

3. `src/agents/common/dependencies_helper.py`
   - Utilities for configuring dependencies
   - Model settings management
   - Usage limits handling

### Step 3: Simplify SimpleAgent Implementation
Rewrite `simple_agent/agent.py` to:
   - Focus only on core agent functionality
   - Use composition over inheritance where possible
   - Delegate all parsing/extraction to the new utilities
   - Reduce method sizes and complexity
   - Minimize duplicated code

### Step 4: Update Import Paths
1. Update all import statements throughout the codebase
2. Ensure backward compatibility
3. Fix any circular dependencies

### Step 5: Comprehensive Testing
1. Create unit tests for new utility modules
2. Verify existing tests pass with refactored code
3. Add integration tests for simplified agent

### Step 6: Documentation
1. Update docstrings and comments
2. Add usage examples for new utility files

### Step 7: Enhance Base Agent Class
1. Rename BaseAgent to AutomagikAgent
2. Move common functionality from SimpleAgent to AutomagikAgent
3. Make SimpleAgent inherit from AutomagikAgent
4. Ensure backward compatibility

## Execution

### Step 1: Set Up Directory Structure ✅
1. Created a dedicated `src/agents/common` directory for shared utilities
2. Created an `__init__.py` file with proper exports for the new package

### Step 2: Implement Message Parser ✅
- Implemented `message_parser.py` to handle tool call/output extraction
- Added functions for message formatting and history management
- Added user message parsing utilities

### Step 3: Implement Session Manager ✅
- Implemented `session_manager.py` to handle session management
- Added functions for ID validation, context creation, and multimodal content extraction
- Included utilities for generating session and run IDs

### Step 4: Implement Dependencies Helper ✅
- Implemented `dependencies_helper.py` to handle dependency configuration
- Added functions for model settings, usage limits, and HTTP client management
- Included utilities for message history formatting

### Step 5: Move Common Components ✅
- Moved `memory_handler.py` to common directory
- Moved `prompt_builder.py` to common directory 
- Moved `tool_registry.py` to common directory
- Updated docstrings to reflect their broader usage across all agents

### Step 6: Simplify SimpleAgent ✅
- Simplified SimpleAgent to use the new common utilities
- Removed redundant helper methods that are now in common utilities
- Reduced code complexity by delegating operations to specialized utilities
- Improved error handling and logging
- Created a cleaner, more maintainable implementation

### Step 7: Update Import Paths ✅
- Updated imports in the SimpleAgent module to use the new common utilities
- No other files directly imported the moved modules, so no further changes needed
- Created test file for the common utilities to verify functionality

### Step 8: Testing ✅
- Created a comprehensive test file (test_agent_common_utils.py) for the new utilities
- The tests verify the functionality of each utility module
- Future work could include expanding integration tests

### Step 9: Create Enhanced Base Agent ✅
- Created new `AutomagikAgent` base class with improved functionality
- Moved common functionality from SimpleAgent to AutomagikAgent:
  - Context management
  - Memory variable initialization and fetching
  - Tool registration
  - System prompt filling
- Updated SimpleAgent to inherit from AutomagikAgent
- Added backward compatibility by re-exporting AutomagikAgent as BaseAgent

## Testing
1. Unit tests for new utility modules ✅
   - Created comprehensive tests for message parsing, session management, dependencies helpers, etc.
   - Tests verify basic functionality of all moved and new utilities

2. Integration tests (Future work)
   - Future iterations should include more comprehensive integration tests

## Summary
We have successfully refactored the agent architecture by:

1. Creating a dedicated `src/agents/common` directory for shared utilities
2. Implementing core utilities for:
   - Message parsing
   - Session management
   - Dependencies configuration
   - Memory handling
   - Prompt building
   - Tool registration

3. Dramatically simplifying the SimpleAgent implementation:
   - Reduced code size by removing redundant helper methods
   - Improved maintainability by delegating to specialized utilities
   - Enhanced readability by clearly separating concerns
   - Reduced complexity through consistent patterns

4. Created enhanced AutomagikAgent base class:
   - Moved common functionality from SimpleAgent to AutomagikAgent
   - Made SimpleAgent implementation much cleaner
   - Ensured backward compatibility with BaseAgent

These changes promote code reuse and ensure consistent behavior across different agent implementations. The architecture is now more modular, making it easier to:

1. Create new agent implementations that leverage the same utilities
2. Extend existing functionality without duplicating code
3. Maintain and debug the system with clear separation of concerns
4. Test components in isolation

Future improvements could include:
1. Further refactoring of agent implementations to better utilize AutomagikAgent
2. More comprehensive integration testing
3. Adding documentation for how to create new agents with these utilities

Key files modified:
- Created: `src/agents/common/message_parser.py`
- Created: `src/agents/common/session_manager.py`
- Created: `src/agents/common/dependencies_helper.py`
- Created: `src/agents/common/__init__.py`
- Created: `tests/test_agent_common_utils.py`
- Created: `src/agents/models/automagik_agent.py`
- Moved: `src/agents/common/prompt_builder.py`
- Moved: `src/agents/common/memory_handler.py`
- Moved: `src/agents/common/tool_registry.py`
- Simplified: `src/agents/simple/simple_agent/agent.py`
- Updated: `src/agents/simple/simple_agent/__init__.py`
- Updated: `src/agents/models/base_agent.py` (for backward compatibility) 