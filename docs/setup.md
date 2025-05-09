# Setup Guide

This guide provides step-by-step instructions for setting up your local development environment for the Automagik Agents project.

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Python:** Version 3.10, 3.11, or 3.12 (check with `python --version`). You can use tools like `pyenv` to manage multiple Python versions.
*   **Docker & Docker Compose:** Required for running the PostgreSQL database. Visit the [Docker website](https://docs.docker.com/get-docker/) for installation instructions.
*   **Git:** For cloning the repository.
*   **`uv`:** The Python package installer and virtual environment manager used by this project. Install it via pip or your preferred method:
    ```bash
    pip install uv
    # or: pipx install uv
    ```

## Installation Steps

1.  **Clone the Repository:**
    Open your terminal and clone the project repository:
    ```bash
    git clone https://github.com/namastexlabs/automagik-agents.git
    cd automagik-agents
    ```

2.  **Create a Virtual Environment:**
    It's highly recommended to use a virtual environment to manage project dependencies. Create and activate one using `uv`:
    ```bash
    uv venv
    source .venv/bin/activate  # On Linux/macOS
    # .venv\Scripts\activate    # On Windows (Command Prompt/PowerShell)
    ```
    Your terminal prompt should now indicate that you are in the `.venv` environment.

3.  **Install Dependencies:**
    Install all required Python packages using `uv`:
    ```bash
    uv pip install -r requirements.txt  # Or potentially: uv pip sync pyproject.toml
    # Note: Verify the correct command based on project conventions (requirements.txt or pyproject.toml)
    ```
    *Self-correction: The `pyproject.toml` file seems to define dependencies directly. The command should likely be:* 
    ```bash
    uv pip sync pyproject.toml
    ```

4.  **Set Up Environment Variables:**
    Copy the example environment file (if one exists) or create a new file named `.env` in the project root directory.
    ```bash
    # If an example exists (e.g., .env.example):
    cp .env.example .env 
    # Otherwise, create an empty file:
    touch .env
    ```
    Open the `.env` file in your text editor and add the following **essential** variables:
    ```dotenv
    # Essential Variables
    AM_API_KEY="your_internal_api_key_here" # Define a secure key for internal API authentication
    OPENAI_API_KEY="sk-your_openai_api_key_here"
    DISCORD_BOT_TOKEN="your_discord_bot_token_here"
    
    # Database Configuration (Choose ONE method)
    # Method 1: Using DATABASE_URL (Recommended if running Postgres via Docker Compose)
    DATABASE_URL="postgresql://automagik:automagik@localhost:5438/automagik_agents" 
    
    # Method 2: Using individual variables (If DATABASE_URL is not set)
    # POSTGRES_HOST=localhost
    # POSTGRES_PORT=5438 # Note: Port 5438 is mapped from the container's 5432
    # POSTGRES_USER=automagik
    # POSTGRES_PASSWORD=automagik
    # POSTGRES_DB=automagik_agents
    
    # Optional Variables (Add as needed for specific features)
    # NOTION_TOKEN=
    # BLACKPEARL_TOKEN=
    # OMIE_TOKEN=
    # GOOGLE_DRIVE_TOKEN=
    # EVOLUTION_API_KEY=
    # EVOLUTION_API_URL=
    # EVOLUTION_INSTANCE=agent
    # BLACKPEARL_API_URL=
    # BLACKPEARL_DB_URI=
    # SUPABASE_URL=
    # SUPABASE_SERVICE_ROLE_KEY=
    # LOGFIRE_TOKEN=
    
    # Development Settings (Defaults are usually fine)
    # AM_PORT=8881
    # AM_HOST=0.0.0.0
    # AM_ENV=development
    # AM_LOG_LEVEL=INFO
    # AM_TIMEZONE=UTC
    ```
    **Notes:**
    *   Replace placeholder values (`your_..._here`) with your actual keys and tokens.
    *   The `DATABASE_URL` provided assumes you are using the Docker Compose setup below, which maps the container's port 5432 to your host machine's port 5438. Adjust the port if you change the mapping in `docker-compose.yml`.
    *   If you are *not* using the provided Docker Compose (e.g., connecting to an external Postgres instance), adjust the `DATABASE_URL` or individual `POSTGRES_*` variables accordingly.
    *   Refer to `src/config.py` for descriptions of all possible environment variables.

5.  **Start the Database:**
    Use Docker Compose to start the PostgreSQL database container defined in `docker-compose.yml`:
    ```bash
    docker compose up -d
    ```
    The `-d` flag runs the container in detached mode (in the background).

## Verification

To verify that your setup is complete and the application can connect to the database:

1.  **Check Docker Container:** Ensure the PostgreSQL container is running:
    ```bash
    docker compose ps
    ```
    You should see a service named `postgres` (or similar, based on `docker-compose.yml`) with `State` as `running`.

2.  **Run Database Migrations (if applicable):** If the project uses a migration tool (like Alembic - check `src/db/` or `pyproject.toml`), run the migrations. (Example command, actual command may vary):
    ```bash
    # Example: alembic upgrade head 
    # Check project documentation or code for the correct migration command.
    echo "Note: Check if database migrations are needed and how to run them."
    ```

3.  **Run the Application (Briefly):** Try running the API server or a simple CLI command to see if it starts without immediate configuration or database connection errors. See the [Running the Project](./running.md) guide for specific commands.

## Troubleshooting

*   **`uv` command not found:** Ensure `uv` is installed and its installation directory is in your system's PATH.
*   **Dependency Installation Errors:** Make sure you are inside the activated virtual environment (`.venv`). Check your Python version compatibility. Delete the `.venv` directory and try steps 2 and 3 again.
*   **Database Connection Errors:**
    *   Verify the PostgreSQL container is running (`docker compose ps`).
    *   Double-check the `DATABASE_URL` or `POSTGRES_*` variables in your `.env` file... See [Configuration](./configuration.md) for variable details.
    *   Ensure the database name, user, and password match those defined in `docker-compose.yml` and your `.env` file.
    *   Check firewall settings if connecting to a non-local database.
*   **`.env` file not loaded:** Ensure the file is named exactly `.env`... See [Configuration](./configuration.md). 