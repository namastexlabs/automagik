# Test Cleanup Analysis

## Summary
After analyzing the test folder structure against the current codebase, most tests are still relevant but need updates rather than removal. The codebase has evolved significantly, but the test structure has been maintained reasonably well.

## Analysis by Directory

### ✅ Agent Tests (`tests/agents/`)

#### Keep All - Current and Active
- **airtable/** - Tests specialized airtable functionality within Sofia agent
- **sofia/** - Active agent with MCP integration, all tests relevant
- **simple/** - Current agent with multimodal support
- **stan/** - Agent exists but test implementation incomplete (missing `test_api_integration.py`)
- **claude_code/** - Core workflow system, comprehensive test suite

#### Action Required
- **stan/**: Either implement the missing `test_api_integration.py` or update README.md

### ✅ API Tests (`tests/api/`)

#### Keep - Routes Still Exist
- test_agent_routes.py
- test_analytics_routes.py
- test_mcp_routes.py, test_mcp_routes_new.py, test_mcp_routes_simple.py
- test_session_routes.py
- test_tool_routes.py
- test_user_routes.py
- test_memory_routes.py
- test_system_endpoints.py
- test_auth_middleware.py
- test_message_routes.py

#### Need Review/Update
- test_agent_active_status.py
- test_agent_api_usage_integration.py
- test_agent_crud.py
- test_agent_response_usage_simple.py
- test_session_controller_analytics.py
- test_virtual_agent_prompts.py

### ✅ Tool Tests (`tests/tools/`)

#### Keep All - Tools Still Exist
- **airtable/** - Full test suite for airtable integration
- **blackpearl/** - API integration tests
- **gmail/** - Email integration tests
- **omie/** - ERP integration tests

### ❓ Tests Requiring Investigation

#### Database Tests (`tests/db/`)
- Need to verify against current schema migrations
- Check if repository patterns match current implementation
- Validate SQLite parameter binding tests still relevant

#### Integration Tests (`tests/integration/`)
- test_discord_agent_api.py - Check if Discord agent API still works the same
- test_stan_agent_api.py - Verify Stan agent API compatibility
- test_mcp_integration.py - Ensure MCP integration patterns current

#### Framework Tests (`tests/frameworks/`)
- test_agno_*.py - Verify Agno framework is still in use

#### Performance Tests (`tests/perf/`)
- Contains benchmark data from May 2025
- Need to verify if benchmark suite still compatible

### 🗑️ Potentially Obsolete Tests

1. **tests/preferences/** - Empty directory with only __init__.py
2. **tests/conftest_token_analytics.py** - Separate conftest may be redundant
3. **tests/test_no_legacy.py** - Depends on what "legacy" refers to
4. **tests/test_product_agent.py** - No product agent found in src/agents/
5. **tests/perf/benchmarks/benchmark/** - Old benchmark data from May 2025

### 📋 Recommended Cleanup Strategy

1. **Phase 1: Run All Tests**
   ```bash
   pytest tests/ -v --tb=short
   ```
   Document which tests fail and why.

2. **Phase 2: Update Import Paths**
   - Fix imports from old module structures
   - Update database model imports
   - Align with current package structure

3. **Phase 3: Fix Schema Mismatches**
   - Update test fixtures to match current DB schema
   - Align test models with migration changes
   - Update API request/response models

4. **Phase 4: Remove True Obsoletes**
   Only remove tests that:
   - Test non-existent functionality
   - Reference removed components
   - Have no path to update

5. **Phase 5: Add Missing Tests**
   - New agents: flashinho, flashinho_pro, flashinho_v2, discord, summary
   - New workflows in claude_code
   - New API endpoints
   - MCP server functionality

## Key Findings

1. **Good Test Coverage**: Most core functionality has tests
2. **Maintenance Debt**: Tests need updates for API/schema changes
3. **No Mass Deletion**: Very few tests are truly obsolete
4. **Missing Coverage**: New agents and features lack tests

## Priority Actions

1. **High Priority**
   - Run full test suite to identify actual failures
   - Update database model imports
   - Fix API authentication patterns

2. **Medium Priority**
   - Add tests for new agents
   - Update benchmark suite
   - Clean up empty directories

3. **Low Priority**
   - Archive old benchmark data
   - Consolidate conftest files
   - Update test documentation

## Conclusion

The test suite is in better shape than expected. Rather than mass deletion, focus on:
- Running tests to find actual issues
- Updating imports and schemas
- Adding tests for new functionality
- Removing only truly obsolete tests after verification