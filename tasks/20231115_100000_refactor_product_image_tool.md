# Task: Refactor Product Image Sending Tool
**Status**: Completed

## Analysis
- [x] **Requirements**
  - [x] Centralize the `send_product_image_to_user` logic within the specialized agent in `src/agents/simple/stan_agent/specialized/product.py`.
  - [x] Remove the duplicate tool definition from the main agent in `src/agents/simple/stan_agent/agent.py`.
  - [x] Ensure the necessary context (`evolution_payload` containing user JID and instance name) is correctly passed from `StanAgent` to `product_agent` and accessed within the tool in `product.py`.
  - [x] Use the `evolution_payload` from the live interaction context rather than relying on potentially stale database lookups for the user's contact info.
- [x] **Challenges**
  - [x] Ensuring the `evolution_payload` object is consistently available within `ctx.deps` when the `product_agent`'s internal tool is called.
  - [x] Handling cases where the payload might be missing or improperly formatted.
- [x] **Dependencies**
  - [x] `src/agents/simple/stan_agent/agent.py`
  - [x] `src/agents/simple/stan_agent/specialized/product.py`
  - [x] `src/agents/simple/stan_agent/models/EvolutionMessagePayload` (potentially needed for type hints/access)
  - [x] `src/tools/evolution/api.py` (`send_evolution_media_logic`)
  - [x] `src/tools/blackpearl/api.py` (`fetch_blackpearl_product_details`)

## Plan
- [x] **Step 1: Modify `send_product_image_to_user` tool in `src/agents/simple/stan_agent/specialized/product.py`**
  - [x] Subtask 1.1: Remove the existing logic that uses `get_user` to retrieve `whatsapp_id` from the database.
  - [x] Subtask 1.2: Implement logic to safely access the `evolution_payload` object from the `ctx.deps`. This might involve checking `ctx.deps.get("evolution_payload")` or similar, depending on how it's passed.
  - [x] Subtask 1.3: Extract the user's JID using `evolution_payload.get_user_jid()` if the payload is available.
  - [x] Subtask 1.4: Extract the Evolution instance name, likely from `evolution_payload.instance` or a similar attribute. Provide a fallback mechanism (e.g., from environment variables or config) if not present in the payload.
  - [x] Subtask 1.5: Add robust error handling: return informative error messages if `evolution_payload`, user JID, or instance name cannot be determined.
  - [x] Subtask 1.6: Verify and add necessary imports at the top of `product.py` (e.g., `send_evolution_media_logic`, `fetch_blackpearl_product_details`).
  - [x] Subtask 1.7: Update the tool's docstring (`send_product_image_to_user` in `product.py`) to accurately reflect its new context requirements and logic.
- [x] **Step 2: Remove `send_blackpearl_product_image_to_user` tool from `src/agents/simple/stan_agent/agent.py`**
  - [x] Subtask 2.1: Delete the entire `async def send_blackpearl_product_image_to_user(...) -> str:` function definition (approximately lines 141-221) within the `_initialize_pydantic_agent` method.

## Execution
- [x] Discovered that the `send_product_image_to_user` method in `product.py` was already properly implemented to use the `evolution_payload` approach. The tool appropriately:
  - Gets the evolution_payload from ctx.deps.context or ctx.deps directly.
  - Extracts the user_jid using get_user_jid() method.
  - Gets the instance name from evolution_payload.instance with fallback to environment variables.
  - Includes proper error handling for missing information.
- [x] Removed the redundant `send_blackpearl_product_image_to_user` tool from `agent.py` as it's now handled by the specialized agent.

## Summary
- [x] Files modified: 
  - `src/agents/simple/stan_agent/agent.py` (lines 141-221, removed tool function)
- [x] Dependencies added/changed: None
- [x] Edge cases considered: 
  - Missing evolution_payload in context
  - Missing user JID in payload  
  - Missing instance name (with fallback to env vars)
  - Product image not found in main data (with fallback to get_imagens_de_produto)
- [x] Known limitations: 
  - Tool relies on proper context passing from StanAgent to product_agent
  - If evolution_payload or JID is missing, image sending will fail
- [x] Future impact points: 
  - Any changes to EvolutionMessagePayload.get_user_jid() would affect this tool
  - Any changes to context passing between agents would need to ensure evolution_payload continues to be available 