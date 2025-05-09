# Running the Project

This guide explains how to run the Automagik Agents application, both the FastAPI web server and the Typer command-line interface (CLI).

**Prerequisite:** Ensure you have completed the steps in the [Setup Guide](./setup.md) and have your virtual environment activated (`source .venv/bin/activate`).

## Running the FastAPI Web Server

The web server provides an API interface to the application.

1.  **Start the Server:**
    From the project root directory (`automagik-agents`), run the following command:
    ```bash
    uvicorn src.main:app --host 0.0.0.0 --port 8881 --reload
    ```
    *   `src.main:app`: Points to the FastAPI application instance (`app`) inside the `src/main.py` file.
    *   `--host 0.0.0.0`: Makes the server accessible from other devices on your network (use `127.0.0.1` or `localhost` to restrict access to your machine only).
    *   `--port 8881`: Specifies the port to run the server on (default is 8881, configurable via `AM_PORT` in `.env` - see [Configuration](./configuration.md)).
    *   `--reload`: Enables auto-reloading. The server will automatically restart when you make changes to the code. **Only use this for development.** For production, remove this flag.

2.  **Accessing the API:**
    Once the server is running, you can access:
    *   **API Endpoints:** Directly via tools like `curl` or Postman at `http://localhost:8881/`. Specific endpoint paths depend on the routes defined in `src/api/`.
    *   **Interactive Documentation (Swagger UI):** Open your web browser and navigate to `http://localhost:8881/docs`. See [API Documentation](./api.md) for more.
    *   **Alternative Documentation (ReDoc):** Navigate to `http://localhost:8881/redoc`.

3.  **Stopping the Server:**
    Press `Ctrl+C` in the terminal where `uvicorn` is running.

## Running the Typer CLI

The CLI provides commands for specific tasks or interactions.

1.  **Base Command:**
    The primary way to invoke the CLI is:
    ```bash
    python -m src.cli [COMMAND] [OPTIONS]
    ```
    Alternatively, if the `[project.scripts]` entry in `pyproject.toml` is set up correctly during installation, you might be able to use:
    ```bash
    automagik-agents [COMMAND] [OPTIONS]
    ```

2.  **Available Commands (Examples - Needs Verification):**
    *The specific commands available depend on the implementation in `src/cli/`. You can usually find out by running the help command:* 
    ```bash
    python -m src.cli --help
    # or
    automagik-agents --help
    ```
    Common command patterns might include:
    ```bash
    # Example: Run a specific agent task
    # python -m src.cli run-agent simple_agent --input "Some text"
    
    # Example: Manage configurations
    # python -m src.cli config show
    
    # Example: Database operations (if implemented)
    # python -m src.cli db migrate
    ```
    *(Note: These are illustrative examples. Check the `--help` output or `src/cli/` code for actual commands.)*

## Environment Differences

*   **Development:** Use the `--reload` flag with `uvicorn` for automatic code reloading.
*   **Production:**
    *   Do **not** use the `--reload` flag with `uvicorn`.
    *   Consider using a process manager like `systemd` or `supervisor` to manage the `uvicorn` process.
    *   You might run `uvicorn` with multiple workers for better performance (e.g., `uvicorn src.main:app --workers 4 ...`).
    *   Ensure `AM_ENV` in `.env` is set to `production`. See [Configuration](./configuration.md).
    *   Set `AM_LOG_LEVEL` appropriately (e.g., `INFO` or `WARNING`). See [Configuration](./configuration.md). 