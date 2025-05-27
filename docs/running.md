# Running the Project

This guide explains how to run the Automagik Agents application using the unified CLI commands.

**Prerequisite:** Ensure you have completed the steps in the [Setup Guide](./setup.md). The installation provides a bash wrapper that automatically handles virtual environment activation.

## Unified CLI Commands

The automagik CLI provides a unified interface for running and managing the application:

```bash
# Start the server
automagik agents start      # Start web server (development/production mode)
automagik agents dev        # Start with auto-reload (development only)

# Manage the service
automagik agents stop       # Stop the server
automagik agents restart    # Restart the server
automagik agents status     # Show service status
automagik agents logs       # View logs with colors

# Optional: Install shorter alias
automagik install-alias     # Install 'agent' alias for convenience
# After alias installation:
agent start                 # Same as 'automagik agents start'
agent dev                   # Same as 'automagik agents dev'
```

## Manual Server Startup (Development)

If you need to run the server manually with specific options:

1.  **Activate Virtual Environment:**
    ```bash
    source .venv/bin/activate
    ```

2.  **Start the Server:**
    ```bash
    uvicorn src.main:app --host 0.0.0.0 --port 8881 --reload
    ```
    *   `src.main:app`: Points to the FastAPI application instance (`app`) inside the `src/main.py` file.
    *   `--host 0.0.0.0`: Makes the server accessible from other devices on your network (use `127.0.0.1` or `localhost` to restrict access to your machine only).
    *   `--port 8881`: Specifies the port to run the server on (default is 8881, configurable via `AM_PORT` in `.env` - see [Configuration](./configuration.md)).
    *   `--reload`: Enables auto-reloading. The server will automatically restart when you make changes to the code. **Only use this for development.** For production, remove this flag.

3.  **Stopping the Server:**
    Press `Ctrl+C` in the terminal where `uvicorn` is running.

## Accessing the API

Once the server is running, you can access:
*   **API Endpoints:** Directly via tools like `curl` or Postman at `http://localhost:8881/`. Specific endpoint paths depend on the routes defined in `src/api/`.
*   **Interactive Documentation (Swagger UI):** Open your web browser and navigate to `http://localhost:8881/docs`. See [API Documentation](./api.md) for more.
*   **Alternative Documentation (ReDoc):** Navigate to `http://localhost:8881/redoc`.

## CLI Commands

The CLI provides additional commands for specific tasks:

1.  **Available Commands:**
    ```bash
    automagik agents --help     # Show all available commands
    automagik --help            # Show all CLI commands
    
    # Database operations (if available)
    automagik agents db init    # Initialize database schema
    automagik agents db check   # Check database connectivity
    
    # Agent management (if available)  
    automagik agents create     # Create new agent
    automagik agents list       # List available agents
    ```

## Environment Differences

*   **Development:** 
    *   Use `automagik agents dev` for automatic code reloading
    *   Use the `--reload` flag with manual `uvicorn` commands
*   **Production:**
    *   Use `automagik agents start` for production mode
    *   Do **not** use the `--reload` flag with manual `uvicorn` commands
    *   Consider using the systemd service installation: `automagik agents start` with service mode
    *   Ensure `AM_ENV` in `.env` is set to `production`. See [Configuration](./configuration.md).
    *   Set `AM_LOG_LEVEL` appropriately (e.g., `INFO` or `WARNING`). See [Configuration](./configuration.md). 