# API Documentation

This document provides an overview of the FastAPI application programming interface (API) for the Automagik Agents project. See [Architecture](./architecture.md) for context.

## Accessing the API Documentation (Recommended)

The most up-to-date and detailed documentation for the API is **automatically generated** using FastAPI's built-in features and can be accessed interactively through your web browser when the server is running (see [Running the Project](./running.md)).

*   **Swagger UI:** `http://localhost:8881/docs`
    *   Provides a detailed view of all endpoints, their parameters, request bodies, response models, and allows you to directly test API calls.
*   **ReDoc:** `http://localhost:8881/redoc`
    *   Offers an alternative, often cleaner, view of the API specification.

**We strongly recommend using the Swagger UI or ReDoc interfaces as the primary source for detailed API information.** This manual documentation provides a higher-level overview.

## Authentication

API requests are authenticated using an API key.

*   **Mechanism:** The client must include the API key in the `Authorization` header of each request, typically prefixed with `Bearer `, or in the `X-API-Key` header for MCP endpoints.
*   **Configuration:** The required API key is set via the `AM_API_KEY` environment variable in your `.env` file.
*   **Implementation:** Authentication logic is likely handled by middleware defined in `src/api/middleware.py` and potentially parts of `src/auth.py`.

**Example `curl` Request with Authorization Header:**

```bash
curl -X GET "http://localhost:8881/api/v1/some_endpoint" \
     -H "accept: application/json" \
     -H "Authorization: Bearer your_secret_internal_api_key"
```

**Example `curl` Request with X-API-Key Header (MCP endpoints):**

```bash
curl -X GET "http://localhost:8881/api/v1/mcp/servers" \
     -H "accept: application/json" \
     -H "X-API-Key: your_secret_internal_api_key"
```

Replace `your_secret_internal_api_key` with the value set for `AM_API_KEY` in your `.env` file.

## API Endpoint Groups

The API endpoints are logically grouped based on the resources they manage. You can explore the specifics of each endpoint within these groups using the Swagger UI.

*   **Agent Routes (`src/api/routes/agent_routes.py`):**
    *   Endpoints related to managing agents... See [Agent System Overview](./agents_overview.md). Likely available under a path like `/api/v1/agents/`.
*   **Session Routes (`src/api/routes/session_routes.py`):**
    *   Endpoints for managing interaction sessions (creating, retrieving, listing sessions, etc.). Likely available under `/api/v1/sessions/`.
*   **User Routes (`src/api/routes/user_routes.py`):**
    *   Endpoints for managing user information (if applicable). Likely available under `/api/v1/users/`.
*   **Memory Routes (`src/api/memory_routes.py`):**
    *   Endpoints specifically for interacting with agent memory (conversation history or structured memory). Paths might vary, potentially under sessions or agents.
*   **MCP Routes (`src/api/routes/mcp_routes.py`):** ✨ **NEW**
    *   Endpoints for Model Context Protocol (MCP) server and tool management. Available under `/api/v1/mcp/`. See [MCP Integration Documentation](./mcp_integration.md) for detailed information about MCP functionality, testing results, and troubleshooting.

Refer to the Swagger UI (`/docs`) for the exact paths, methods, request/response details, and parameters for all endpoints within these groups.

## Error Handling

Standard HTTP status codes are used to indicate success or failure:

*   `2xx`: Success (e.g., `200 OK`, `201 Created`)
*   `4xx`: Client Errors (e.g., `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `422 Unprocessable Entity` for validation errors)
*   `5xx`: Server Errors (e.g., `500 Internal Server Error`)

Error responses typically include a JSON body with a `detail` field explaining the error. 