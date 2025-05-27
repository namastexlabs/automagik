# Configuration

This document explains how project configuration is managed in Automagik Agents, primarily using environment variables and the `src/config.py` module.

## Overview

The project utilizes the [`pydantic-settings`](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) library to manage configuration. This approach provides:

*   **Centralized Definition:** All configuration parameters are defined as typed fields within the `Settings` class in `src/config.py`.
*   **Environment Variable Loading:** Settings are primarily loaded from environment variables.
*   **.env File Support:** A `.env` file in the project root can be used to set environment variables locally during development (using `python-dotenv`).
*   **Type Validation:** Pydantic automatically validates the types of loaded configuration values.
*   **Default Values:** Default values can be specified directly in the `Settings` class.

Refer to the [config-rules](../rules/config-rules.md) for best practices when adding or modifying configuration.

## Configuration Loading

1.  **Environment Variables:** The system first checks for environment variables matching the fields defined in the `Settings` class (case-sensitive).
2.  **.env File:** If `python-dotenv` is installed, the system attempts to load variables from a `.env` file located in the project root directory.
3.  **Default Values:** If a variable is not found in the environment or the `.env` file, the default value defined in the `Settings` class is used.

**Precedence:** Environment variables set directly in the shell/system take precedence over values defined in the `.env` file. Values from either source take precedence over the default values in `src/config.py`.

The global `settings` object, imported from `src.config`, holds the loaded configuration values.

## Configuration Variables

Below is a list of the main configuration variables defined in `src/config.py`, along with their corresponding environment variable names, types, and descriptions. Refer to the `Settings` class in `src/config.py` for the most up-to-date list and default values.

**Essential:**

*   `AM_API_KEY` (str): API key for authenticating internal requests. (Required)
*   `OPENAI_API_KEY` (str): OpenAI API key. (Required)
*   `DISCORD_BOT_TOKEN` (str): Discord bot token. (Required)
*   `DATABASE_URL` (str): Full PostgreSQL connection string. Takes precedence over individual `POSTGRES_*` variables if set.
    *   *Alternatively:* `POSTGRES_HOST` (str), `POSTGRES_PORT` (int), `POSTGRES_USER` (str), `POSTGRES_PASSWORD` (str), `POSTGRES_DB` (str): Individual database connection parameters.

**Optional Integrations:**

*   `NOTION_TOKEN` (Optional[str]): Notion integration token.
*   `BLACKPEARL_TOKEN` (Optional[str]): BlackPearl API token.
*   `OMIE_TOKEN` (Optional[str]): Omie API token.
*   `GOOGLE_DRIVE_TOKEN` (Optional[str]): Google Drive API token.
*   `EVOLUTION_API_KEY` (Optional[str]): Evolution API key.
*   `EVOLUTION_API_URL` (Optional[str]): Evolution API URL.
*   `EVOLUTION_INSTANCE` (str, default: "agent"): Evolution API instance name.
*   `BLACKPEARL_API_URL` (Optional[str]): BlackPearl API URL.
*   `BLACKPEARL_DB_URI` (Optional[str]): BlackPearl database URI.
*   `SUPABASE_URL` (Optional[str]): Supabase project URL.
*   `SUPABASE_SERVICE_ROLE_KEY` (Optional[str]): Supabase service role key.
*   `LOGFIRE_TOKEN` (Optional[str]): Logfire token for logging service.

**Server & Application:**

*   `AM_PORT` (int, default: 8881): Port for the FastAPI server.
*   `AM_HOST` (str, default: "0.0.0.0"): Host for the FastAPI server.
*   `AM_ENV` (Enum: "development", "production", "testing", default: "development"): Application environment.
*   `AM_LOG_LEVEL` (Enum: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", default: "INFO"): Logging level.
*   `AM_VERBOSE_LOGGING` (bool, default: False): Enable verbose logging.
*   `LOGFIRE_IGNORE_NO_CONFIG` (bool, default: True): Suppress Logfire warning if no token.
*   `AM_TIMEZONE` (str, default: "UTC"): Timezone for agents.
*   `AM_AGENTS_NAMES` (Optional[str]): Comma-separated list of agent names to pre-instantiate.
*   `DEFAULT_EVOLUTION_INSTANCE` (str, default: "default"): Default Evolution instance if none provided.
*   `DEFAULT_WHATSAPP_NUMBER` (str, default: "5511999999999@s.whatsapp.net"): Default WhatsApp number.

**Database Pool:**

*   `POSTGRES_POOL_MIN` (int, default: 1): Minimum connections in the pool.
*   `POSTGRES_POOL_MAX` (int, default: 10): Maximum connections in the pool.

**Other:**

*   `PYTHONWARNINGS` (Optional[str]): Python warnings configuration.

## Example `.env` File

Create a file named `.env` in the project root directory. **Do not commit this file to Git.** See [Setup Guide](./setup.md) for initial setup.

```dotenv
# .env - Local Development Environment Variables
# Ensure this file is listed in .gitignore

# --- Essential Variables ---
# Internal API Key (generate a secure random string)
AM_API_KEY="your_secret_internal_api_key"

# OpenAI API Key
OPENAI_API_KEY="sk-replace_with_your_openai_key"

# Discord Bot Token
DISCORD_BOT_TOKEN="replace_with_your_discord_bot_token"

# --- Database Configuration ---
# Using DATABASE_URL is recommended with the provided Docker Compose setup.
# The port 5438 on the host maps to 5432 inside the container.
DATABASE_URL="postgresql://automagik:automagik@localhost:5438/automagik_agents"

# If NOT using DATABASE_URL, uncomment and configure these:
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5438
# POSTGRES_USER=automagik
# POSTGRES_PASSWORD=automagik
# POSTGRES_DB=automagik_agents

# --- Optional Integrations (Add API keys/tokens as needed) ---
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

# --- Server & Application Settings (Defaults are often suitable for development) ---
AM_PORT=8881
AM_HOST=0.0.0.0
AM_ENV=development
AM_LOG_LEVEL=DEBUG # Use DEBUG for more verbose logs during development
AM_VERBOSE_LOGGING=True
# AM_TIMEZONE=America/Sao_Paulo # Example: Set a specific timezone
# AM_AGENTS_NAMES=simple # Example: Pre-load 'simple'

# --- Database Pool (Defaults are usually fine) ---
# POSTGRES_POOL_MIN=1
# POSTGRES_POOL_MAX=10

# --- Other ---
# PYTHONWARNINGS=
```

## Managing Sensitive Information

*   **Never commit `.env` files or files containing secrets** (like API keys, passwords) to version control (Git). Ensure `.env` is listed in your `.gitignore` file.
*   For production environments, use secure methods for managing environment variables (e.g., secrets management tools provided by your cloud provider or deployment platform).
*   Avoid hardcoding secrets directly in the source code (`src/config.py` or elsewhere). 