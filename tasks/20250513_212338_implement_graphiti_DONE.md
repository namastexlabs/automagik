# Task: Implement Graphiti in AutomagikAgent

**Objective:** Integrate the Graphiti knowledge graph framework into the `AutomagikAgent` base class to process and store information from each user message and agent response as episodes in the knowledge graph.

## Requirements
- [x] Integrate the `graphiti-core` library.
- [x] Initialize Graphiti with Neo4j connection parameters and other relevant configurations (e.g., agent ID, environment).
- [x] Modify the agent's message processing methods (`run` and/or `process_message`) to add episodes to Graphiti for each interaction.
- [x] Ensure Neo4j credentials and other sensitive information are handled securely via configuration settings.
- [x] Implement proper error handling and logging for Graphiti operations.
- [x] Ensure the Graphiti client is gracefully closed during agent cleanup.

## Key Considerations & Challenges
- [x] **Configuration Management:** How to best manage Neo4j URI, username, password, and Graphiti-specific settings (like agent ID for namespacing, environment tag).
- [x] **Asynchronous Operations:** Graphiti operations (like `add_episode`) are typically asynchronous. Ensure they are correctly awaited and integrated into the agent's async workflow.
- [x] **Neo4j Availability:** Handle potential connection issues with the Neo4j instance gracefully.
- [x] **Performance:** Assess and mitigate any performance impact of adding an episode for every message.
- [x] **Data Model for Episodes:** Decide on the structure and content of the episodes (e.g., what metadata from the user message, agent response, context, and tool calls should be included).
- [x] **One-time Setup:** `graphiti.build_indices_and_constraints()` should ideally be called once at application startup. Determine the best place for this (e.g., in `main.py` during `lifespan` events or a global agent setup routine).

## Dependencies
- [x] `graphiti-core` library (add to `pyproject.toml` or `requirements.txt`).
- [x] `neo4j` Python driver (usually a dependency of `graphiti-core`, but confirm).
- [x] A running Neo4j instance.

## Detailed Implementation Plan

### Step 1: Add Dependencies and Configuration

- [x] **Add `graphiti-core` to Project Dependencies:**
  - Modify `pyproject.toml` (if using Poetry) or `requirements.txt` to include `graphiti-core`.
    ```toml
    # Example for pyproject.toml
    # graphiti-core = "^0.x.y" # Replace with the latest appropriate version
    ```
- [x] **Define Configuration in `src/config.py`:**
  - Add the following fields to the `Settings` class in `src/config.py`:
    ```python
    # Inside class Settings(BaseSettings):
    # ... (other settings)

    # Graphiti / Neo4j (Optional)
    NEO4J_URI: Optional[str] = Field(None, description="Neo4j connection URI (e.g., bolt://localhost:7687 or neo4j://localhost:7687)")
    NEO4J_USERNAME: Optional[str] = Field(None, description="Neo4j username")
    NEO4J_PASSWORD: Optional[str] = Field(None, description="Neo4j password")
    GRAPHITI_AGENT_ID: str = Field("automagik_agent", description="Default Agent ID for Graphiti, used as a namespace for nodes/episodes")
    GRAPHITI_ENV: str = Field("default", description="Environment for Graphiti, e.g., 'development', 'production'")
    # OPENAI_API_KEY is already present and will be used by Graphiti if configured for LLM inference.
    ```
  - Ensure these settings can be loaded from environment variables or a `.env` file.

### Step 2: Initialize Graphiti Client in `AutomagikAgent`

- [x] **Import necessary modules in `src/agents/models/automagik_agent.py`:**
  ```python
  from graphiti import Graphiti
  from src.config import settings # Assuming 'settings' is the global config instance
  import asyncio # For one-time setup
  ```
- [x] **Modify `AutomagikAgent.__init__`:**
  - Add a `self.graphiti_client: Optional[Graphiti] = None` attribute.
  - Inside `__init__`, check if `settings.NEO4J_URI`, `settings.NEO4J_USERNAME`, and `settings.NEO4J_PASSWORD` are set.
  - If they are, initialize `self.graphiti_client`:
    ```python
    # Inside AutomagikAgent.__init__
    self.graphiti_client: Optional[Graphiti] = None
    if settings.NEO4J_URI and settings.NEO4J_USERNAME and settings.NEO4J_PASSWORD:
        try:
            self.graphiti_client = Graphiti(
                agent_id=settings.GRAPHITI_AGENT_ID, # Or use self.name or self.db_id if more specific
                env=settings.GRAPHITI_ENV,
                api_key=settings.OPENAI_API_KEY, # Graphiti uses this for its LLM features
                db_url=settings.NEO4J_URI,
                db_user=settings.NEO4J_USERNAME,
                db_pass=settings.NEO4J_PASSWORD,
                # verbose=True, # Optional: for debugging
                # llm_model_name="gpt-4-turbo-preview" # Optional: if you want to specify a model for Graphiti
            )
            logger.info(f"Graphiti client initialized for agent '{self.name}' using agent_id '{settings.GRAPHITI_AGENT_ID}' and env '{settings.GRAPHITI_ENV}'.")
            # Consider one-time setup for indices here or globally
        except Exception as e:
            logger.error(f"Failed to initialize Graphiti client for agent '{self.name}': {e}")
            self.graphiti_client = None # Ensure it's None if initialization fails
    else:
        logger.info("Graphiti/Neo4j settings not fully configured. Graphiti client will not be initialized.")
    ```
- [x] **Implement `graphiti.build_indices_and_constraints()` call (One-time Setup):**
  - This should be done once when the application starts. The best place is likely in `src/main.py` within an `async def lifespan(app: FastAPI):` context manager or similar global startup hook.
  - If it must be per-agent (less ideal for global indices), a lock mechanism (`asyncio.Lock`) could be used in `AutomagikAgent.__init__` to ensure it's called only by the first agent instance if multiple agents share the same Graphiti config. For now, assume a global setup is preferred.
    ```python
    # Example for main.py (conceptual)
    # async def lifespan(app: FastAPI):
    #     if settings.NEO4J_URI and settings.NEO4J_USERNAME and settings.NEO4J_PASSWORD:
    #         graphiti_temp = Graphiti(...)
    #         await graphiti_temp.build_indices_and_constraints()
    #         await graphiti_temp.close()
    #     yield
    ```

### Step 3: Integrate `add_episode` in Message Processing

- [x] **Create a helper method in `AutomagikAgent`:**
  - `async def _add_episode_to_graphiti(self, user_input: str, agent_response: str, metadata: Optional[Dict] = None):`
    ```python
    async def _add_episode_to_graphiti(self, user_input: str, agent_response: str, metadata: Optional[Dict] = None) -> None:
        if not self.graphiti_client:
            return

        try:
            # Construct episode details
            # You might want to include session_id, user_id, tool_calls, etc. in metadata
            episode_data = {
                "user_input": user_input,
                "llm_response": agent_response,
                # Add other relevant fields like 'tool_calls', 'tool_outputs', 'session_id', 'user_id'
            }
            if metadata:
                episode_data.update(metadata)

            # The `input` parameter for add_episode is usually the user's query.
            # The `output` is the agent's response.
            # `chunks_perex_episode` and `chunks_detail` relate to knowledge item creation, 
            # which might be a next step after basic episode logging.
            # For now, focus on logging the interaction.
            await self.graphiti_client.add_episode(
                input_text=user_input,
                output_text=agent_response,
                metadata=episode_data, # Pass structured data here
                # agent_id can be passed if different from the client's default
                # env can be passed if different from the client's default
            )
            logger.info(f"Added episode to Graphiti for agent '{self.name}'.")
        except Exception as e:
            logger.error(f"Failed to add episode to Graphiti for agent '{self.name}': {e}")
    ```
- [x] **Call `_add_episode_to_graphiti` from `AutomagikAgent.process_message` (or `run`):**
  - The `process_message` method seems suitable as it handles both user input and agent output formatting.
  - After the `response = await self.run(...)` call and before returning, call `_add_episode_to_graphiti`.
    ```python
    # Inside AutomagikAgent.process_message, after getting agent_response
    # ...
    # agent_response_text = response.text (or however you get the final text)
    # episode_metadata = { "session_id": self.context.get("session_id"), "user_id": str(self.dependencies.user_id) if self.dependencies.user_id else None, ... }
    # await self._add_episode_to_graphiti(user_input=content, agent_response=agent_response_text, metadata=episode_metadata)
    # ...
    # return response
    ```
  - Ensure you extract the raw user message (`content`) and the agent's final textual response.
  - Gather relevant metadata (e.g., `session_id`, `user_id`, `tool_calls` from `response.tool_calls`, `tool_outputs` from `response.tool_outputs`).

### Step 4: Implement Cleanup

- [x] **Modify `AutomagikAgent.cleanup`:**
  - If `self.graphiti_client` exists, call `await self.graphiti_client.close()`.
    ```python
    # Inside AutomagikAgent.cleanup
    async def cleanup(self) -> None:
        # ... (existing cleanup, e.g., for http_client)
        if self.graphiti_client:
            try:
                await self.graphiti_client.close()
                logger.info(f"Graphiti client closed for agent '{self.name}'.")
            except Exception as e:
                logger.error(f"Error closing Graphiti client for agent '{self.name}': {e}")
        # ...
    ```

### Step 5: Testing

- [x] **Unit Tests:**
  - Test `AutomagikAgent.__init__` to ensure `graphiti_client` is initialized (or not) based on configuration.
  - Mock `Graphiti` and test `_add_episode_to_graphiti` to verify it's called with correct parameters.
  - Test `cleanup` to ensure `graphiti_client.close()` is called.
- [x] **Integration Tests (Requires running Neo4j):**
  - Create a test that sends a message to an agent and verifies that an episode is actually created in the Neo4j database.
  - This will require querying Neo4j directly in the test or using Graphiti's retrieval methods if applicable.

### Step 6: Documentation

- [x] Update `README.md` or other relevant documentation to include:
  - New dependencies (`graphiti-core`).
  - Required environment variables for Neo4j and Graphiti (`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `GRAPHITI_AGENT_ID`, `GRAPHITI_ENV`).
  - A brief explanation of the Graphiti integration and its purpose.

## Next Steps (After Basic Episode Logging)
- [x] Explore using Graphiti for knowledge extraction from episodes (e.g., `graphiti.extract_knowledge(...)`).
- [x] Investigate how Graphiti's retrieval capabilities (`graphiti.search_similar_episodes(...)` or `graphiti.query_knowledge_graph(...)`) can be used to provide context to the agent.
