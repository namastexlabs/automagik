# Task: Enhance Product Image Capabilities
**Status**: Completed

## Analysis
- [x] **Requirements**
  - [x] Add support for sending multiple product images to users at once.
  - [x] Update system prompts to better instruct the main agent on when to show product images.
  - [x] Ensure the main agent knows to use the product sub-agent for handling product queries and image sending.
  - [x] Improve guidelines on when to proactively offer to show product images to users.
  - [x] Make agent delegation seamless so users don't see the "behind the scenes" process.
- [x] **Challenges**
  - [x] Maintaining consistent context passing between the main agent and sub-agent.
  - [x] Ensuring robust error handling when dealing with multiple product IDs.
  - [x] Providing clear instructions in the prompts about when to use single vs. multiple image tools.
  - [x] Creating seamless interactions without mentioning delegation to specialists.
- [x] **Dependencies**
  - [x] `src/agents/simple/stan_agent/specialized/product.py`
  - [x] `src/agents/simple/stan_agent/prompts/approved.py`
  - [x] `src/agents/simple/stan_agent/prompts/not_registered.py`
  - [x] `src/tools/evolution/api.py` (for image sending)

## Plan
- [x] **Step 1: Add multiple product image sending tool in product.py**
  - [x] Create `send_multiple_product_images` function that accepts a list of product IDs.
  - [x] Add ability to override captions for each product using an optional dictionary parameter.
  - [x] Implement robust error handling and tracking of success/failure per product.
  - [x] Ensure proper context retrieval for evolution_payload and user_jid.
  - [x] Create a summary response that properly communicates results to the user.

- [x] **Step 2: Update system prompts to emphasize image capabilities**
  - [x] Enhance the `approved.py` prompt:
    - [x] Add a dedicated section for product image instructions.
    - [x] Clarify when to use single vs. multiple image sending.
    - [x] Add guidance on proactively offering to show images.
    - [x] Include example phrasing for image offers.
  - [x] Update the `not_registered.py` prompt:
    - [x] Add instructions about product images while maintaining focus on registration.
    - [x] Include image demonstration in the example interactions.

- [x] **Step 3: Make the delegation process seamless**
  - [x] Remove all references to "specialist" or "expert" agents in user-facing responses
  - [x] Update the `approved.py` prompt to hide the delegation process:
    - [x] Mark delegation guidelines as internal instructions only
    - [x] Remove phrases like "vou solicitar ao nosso especialista"
    - [x] Change examples to present information directly
  - [x] Update the `not_registered.py` prompt similarly:
    - [x] Make delegation invisible to users
    - [x] Update examples to remove mentions of specialists
    - [x] Provide direct alternatives to delegation language

## Execution
- [x] **Adding multi-image tool**
  - [x] Implemented `send_multiple_product_images` in `product.py` that:
    - Takes a list of product IDs and optional caption overrides
    - Uses the same context retrieval approach as the single image tool
    - Processes each product ID in a loop, with try/except blocks
    - Tracks successful and failed image sendings
    - Returns a summary with success/failure counts
  
- [x] **Updating prompts for image capabilities**
  - [x] Enhanced `approved.py`:
    - Added explicit instructions for the agent to proactively offer product images
    - Created a dedicated section specifically for product image handling
    - Added guidance on using different tools for single vs multiple products
    - Included specific trigger phrases to watch for ("como é", "ver", etc.)
  - [x] Updated `not_registered.py`:
    - Added product image instructions while maintaining priority on registration
    - Updated example interactions to include image handling
    - Added specific tool references and when to use them

- [x] **Making delegation seamless**
  - [x] Updated both prompts to mark delegation sections as internal instructions only
  - [x] Removed all phrases like "vou solicitar ao especialista" or "nosso especialista em produtos"
  - [x] Modified examples to show direct responses like "Aqui está uma imagem" instead of "Vou solicitar uma imagem"
  - [x] Added explicit warnings not to mention delegation or specialist agents to the user
  - [x] Added alternative phrasings that present information directly

## Summary
- [x] **Files modified**: 
  - `src/agents/simple/stan_agent/specialized/product.py` (added send_multiple_product_images tool)
  - `src/agents/simple/stan_agent/prompts/approved.py` (enhanced image instructions and made delegation seamless)
  - `src/agents/simple/stan_agent/prompts/not_registered.py` (added image instructions and made delegation seamless)
- [x] **Dependencies added/changed**: None (used existing dependencies)
- [x] **Edge cases considered**:
  - Empty product ID list
  - Products without images
  - Missing evolution_payload in context
  - Missing JID or instance name
  - Large numbers of products (special handling for summaries)
- [x] **Known limitations**:
  - Processing many products sequentially may take time
  - WhatsApp may have rate limits for multiple media messages
- [x] **Future impact points**:
  - Any changes to EvolutionMessagePayload would affect this functionality
  - Additional image formats or sources could be supported
  - Performance optimization for multiple image handling 