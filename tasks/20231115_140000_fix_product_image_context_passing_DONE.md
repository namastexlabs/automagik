# Task: Fix Product Image Context Passing
**Status**: Completed

## Analysis
- [x] **Requirements**
  - [x] Fix the issue where `evolution_payload` was not being correctly passed to the product agent
  - [x] Ensure the `send_multiple_product_images` tool can reliably access the user's WhatsApp information
  - [x] Implement robust error handling and fallback mechanisms
  - [x] Add detailed logging to help diagnose context issues in production
  - [x] Prevent agents from sharing direct image URLs with users
  - [x] Fix handling of numeric product IDs in API calls
- [x] **Problem Identification**
  - [x] Error message: `Tool 'send_multiple_product_images': Evolution payload not found in any context`
  - [x] When the main agent's `product_agent_wrapper` was delegating to the product agent, the `evolution_payload` was not properly preserved
  - [x] The `ctx.deps.set_context(agent_context)` call was not reliably passing all required context data
  - [x] The error only manifested with the newly added `send_multiple_product_images` tool
  - [x] API errors were occurring with numeric string product IDs like "6975763145197"
  - [x] Main agent was occasionally sharing direct image URLs instead of using the product image tools

## Plan
- [x] **Step 1: Fix context passing in main agent's product_agent_wrapper**
  - [x] Modify the wrapper to specifically ensure the `evolution_payload` is included in the context
  - [x] Preserve existing context data while adding the evolution_payload
  - [x] Add warning logs if evolution_payload cannot be found

- [x] **Step 2: Enhance error handling in send_multiple_product_images tool**
  - [x] Add additional methods to retrieve the evolution_payload from various possible locations
  - [x] Add detailed logging to show what context is available when the error occurs
  - [x] Implement a fallback mechanism using config values when available
  - [x] Add helper method for handling fallback sending
  
- [x] **Step 3: Fix product ID handling and API errors**
  - [x] Update the `get_product_images` function to better handle numeric ID strings
  - [x] Add proper integer conversion for product IDs in `send_product_image_to_user`
  - [x] Add robust error handling for invalid product IDs in `send_multiple_product_images`

- [x] **Step 4: Prevent sharing direct image URLs**
  - [x] Update the product agent system prompt to explicitly prohibit sharing direct image URLs
  - [x] Add clear instructions to force using image sending tools instead
  - [x] Remove problematic product IDs from the example catalog that were causing errors

## Execution
- [x] **Fixed context passing in StanAgent**
  - [x] Modified `_create_product_agent_wrapper` in `agent.py` to specifically check for and handle evolution_payload
  - [x] Added code to create a new context dictionary that preserves existing context while adding evolution_payload
  - [x] Added warning logs when the evolution_payload is not available

- [x] **Enhanced error handling in Product Agent**
  - [x] Added additional lookup methods in `send_multiple_product_images` to find evolution_payload:
    - Added check for `ctx.deps.get_context()` method
    - Added check for `ctx.parent_context` attribute
  - [x] Added detailed debug logging showing context structure when the payload is missing
  - [x] Added fallback mechanism using `src.config.settings` values when available
  - [x] Created a helper function `_send_product_images_with_fallback` to handle fallback scenarios

- [x] **Fixed product ID handling**
  - [x] Updated `get_product_images` to properly validate and convert string product IDs
  - [x] Added robust error handling to return helpful error messages on invalid product IDs
  - [x] Updated `send_product_image_to_user` and `send_multiple_product_images` to handle numeric string IDs
  - [x] Added input sanitization to ensure all product IDs are properly processed

- [x] **Prevented sharing direct image URLs**
  - [x] Updated the product agent's system prompt with stronger directives about image security
  - [x] Added explicit instructions to NEVER share direct image URLs with users
  - [x] Removed problematic product IDs (like 6975763145197) from the example catalog
  - [x] Emphasized using the proper image sending tools in all cases

## Summary
- [x] **Files modified**: 
  - `src/agents/simple/stan_agent/agent.py` (modified `_create_product_agent_wrapper` method)
  - `src/agents/simple/stan_agent/specialized/product.py` (enhanced multiple functions and system prompt)
- [x] **Edge cases considered**:
  - Missing evolution_payload in various context locations
  - Configuration for fallback values might be missing
  - Different types of context objects with varying structures
  - Invalid or malformed product IDs
  - Large numeric product IDs that might cause type conversion issues
- [x] **Known limitations**:
  - Fallback mechanism requires DEFAULT_EVOLUTION_INSTANCE and DEFAULT_WHATSAPP_NUMBER to be defined in settings
  - Complex nested context structures might still occasionally fail to pass all data
  - Very long numeric product IDs may still cause issues with some API endpoints
- [x] **Future impact points**:
  - Similar context passing issues might exist in other specialized agents (order, backoffice)
  - Changes to context structure in AutomagikAgentsDependencies might require updates to these fixes 
  - API changes to BlackPearl product endpoints might require adjusting ID handling logic 