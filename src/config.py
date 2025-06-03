import os
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
import urllib.parse
from pathlib import Path
import logging
import subprocess

try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: python-dotenv is not installed. Environment variables may not be loaded from .env file.")
    def load_dotenv():
        return None

logger = logging.getLogger(__name__)

def detect_environment_file() -> str:
    """
    Detect which environment file to use based on the same logic as env_loader.sh
    Returns the path to the appropriate .env file.
    """
    env_file = ".env"
    prod_env_file = ".env.prod"
    
    # Check if development mode is forced (e.g., from make dev)
    if os.environ.get('AM_FORCE_DEV_ENV') == '1':
        return env_file
    
    # Check if .env.prod exists
    if not Path(prod_env_file).exists():
        return env_file
    
    # Check AM_ENV in both files
    def get_am_env_from_file(file_path: str) -> str:
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip().startswith('AM_ENV='):
                        value = line.split('=', 1)[1].strip().strip('"').strip("'")
                        return value.lower()
        except (FileNotFoundError, IOError):
            pass
        return ""
    
    # Get AM_ENV from both files
    current_env = get_am_env_from_file(env_file)
    prod_env = get_am_env_from_file(prod_env_file)
    
    # Get production port for container detection
    def get_port_from_file(file_path: str) -> str:
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip().startswith('AM_PORT='):
                        value = line.split('=', 1)[1].strip().strip('"').strip("'")
                        return value
        except (FileNotFoundError, IOError):
            pass
        return ""
    
    prod_port = get_port_from_file(prod_env_file) or "18881"
    
    # Check if production containers are running
    try:
        result = subprocess.run(
            ["docker", "ps"], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        if result.returncode == 0:
            docker_output = result.stdout
            if (f"automagik-agents-prod" in docker_output or 
                f"automagik_agent" in docker_output and prod_port in docker_output):
                return prod_env_file
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # Docker not available or error - continue with file-based detection
        pass
    
    # Check if environment is explicitly set to production
    if current_env == "production" or prod_env == "production":
        return prod_env_file
    
    # Default to development
    return env_file

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"

class Settings(BaseSettings):
    # Authentication
    AM_API_KEY: str = Field(..., description="API key for authenticating requests")

    # OpenAI
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key for agent operations")

    # Google Gemini (Optional)
    GEMINI_API_KEY: Optional[str] = Field(None, description="Google Gemini API key for agent operations")

    # Notion (Optional)
    NOTION_TOKEN: Optional[str] = Field(None, description="Notion integration token")

    # BlackPearl, Omie, Google Drive, Evolution (Optional)
    BLACKPEARL_TOKEN: Optional[str] = Field(None, description="BlackPearl API token")
    OMIE_TOKEN: Optional[str] = Field(None, description="Omie API token")
    GOOGLE_DRIVE_TOKEN: Optional[str] = Field(None, description="Google Drive API token")
    
    # Evolution
    EVOLUTION_API_KEY: Optional[str] = Field(None, description="Evolution API key")
    EVOLUTION_API_URL: Optional[str] = Field(None, description="Evolution API URL")
    EVOLUTION_INSTANCE: str = Field("agent", description="Evolution API instance name")

    # BlackPearl API URL and DB URI
    BLACKPEARL_API_URL: Optional[str] = Field(None, description="BlackPearl API URL")
    BLACKPEARL_DB_URI: Optional[str] = Field(None, description="BlackPearl database URI")

    FLASHED_API_KEY: Optional[str] = Field(None, description="Flashed API key")
    FLASHED_API_URL: Optional[str] = Field(None, description="Flashed API URL")

    # Discord
    DISCORD_BOT_TOKEN: str = Field(..., description="Discord bot token for authentication")

    # Meeting Bot
    MEETING_BOT_URL: Optional[str] = Field(None, description="Meeting bot webhook service URL for creating bots")

    # Database (PostgreSQL)
    DATABASE_URL: str = Field("postgresql://postgres:postgres@localhost:5432/automagik", 
                          description="PostgreSQL connection string")
    POSTGRES_HOST: str = Field("localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(5432, description="PostgreSQL port")
    POSTGRES_USER: str = Field("postgres", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field("postgres", description="PostgreSQL password")
    POSTGRES_DB: str = Field("automagik", description="PostgreSQL database name")
    POSTGRES_POOL_MIN: int = Field(10, description="Minimum connections in the pool")
    POSTGRES_POOL_MAX: int = Field(25, description="Maximum connections in the pool")

    # Server
    AM_PORT: int = Field(8881, description="Port to run the server on")
    AM_HOST: str = Field("0.0.0.0", description="Host to bind the server to")
    AM_ENV: Environment = Field(Environment.DEVELOPMENT, description="Environment (development, production, testing)")

    # Logging
    AM_LOG_LEVEL: LogLevel = Field(LogLevel.INFO, description="Logging level")
    AM_VERBOSE_LOGGING: bool = Field(False, description="Enable verbose logging with additional details")
    AM_LOG_TO_FILE: bool = Field(False, description="Enable logging to file for debugging")
    AM_LOG_FILE_PATH: str = Field("debug.log", description="Path to log file when file logging is enabled")
    LOGFIRE_TOKEN: Optional[str] = Field(None, description="Logfire token for logging service")
    LOGFIRE_IGNORE_NO_CONFIG: bool = Field(True, description="Suppress Logfire warning if no token")

    # Agent Settings
    AM_TIMEZONE: str = Field(
        default="UTC", 
        description="Timezone for the agent to operate in (e.g., 'UTC', 'America/New_York')"
    )
    AM_AGENTS_NAMES: Optional[str] = Field(
        default=None,
        description="Comma-separated list of agent names to pre-instantiate at startup (e.g., 'simple,stan')"
    )
    AM_ENABLE_CLAUDE_CODE: bool = Field(
        default=False,
        description="Enable Claude-Code agent (experimental containerized Claude CLI execution)"
    )

    # Supabase
    SUPABASE_URL: Optional[str] = Field(None, description="Supabase project URL")
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = Field(None, description="Supabase service role key for authentication")

    # Suppress warnings from dependency conflict resolution (Poetry related)
    PYTHONWARNINGS: Optional[str] = Field(None, description="Python warnings configuration")

    # Fallback settings for WhatsApp
    DEFAULT_EVOLUTION_INSTANCE: str = Field(
        default="default",
        description="Default Evolution API instance to use if none is provided in the context"
    )
    
    DEFAULT_WHATSAPP_NUMBER: str = Field(
        default="5511999999999@s.whatsapp.net",
        description="Default WhatsApp number to use if none is provided in the context"
    )

    # Graphiti / Neo4j (Optional)
    GRAPHITI_ENABLED: bool = Field(
        default=True,
        description="Master switch to enable/disable all Graphiti functionality"
    )
    NEO4J_URI: Optional[str] = Field(None, description="Neo4j connection URI (e.g., bolt://localhost:7687 or neo4j://localhost:7687)")
    NEO4J_USERNAME: Optional[str] = Field(None, description="Neo4j username")
    NEO4J_PASSWORD: Optional[str] = Field(None, description="Neo4j password")
    GRAPHITI_NAMESPACE_ID: str = Field("automagik", description="Project namespace ID for Graphiti, used as a prefix for agent IDs")
    GRAPHITI_ENV: str = Field("default", description="Environment for Graphiti, e.g., 'development', 'production'")

    # Graphiti Queue Configuration
    GRAPHITI_QUEUE_ENABLED: bool = Field(
        default=True,
        description="Enable asynchronous Graphiti queue processing"
    )
    GRAPHITI_QUEUE_MAX_WORKERS: int = Field(
        default=10,
        description="Maximum number of Graphiti background workers"
    )
    GRAPHITI_QUEUE_MAX_SIZE: int = Field(
        default=1000,
        description="Maximum queue size for pending Graphiti operations"
    )
    GRAPHITI_QUEUE_RETRY_ATTEMPTS: int = Field(
        default=3,
        description="Maximum retry attempts for failed Graphiti operations"
    )
    GRAPHITI_QUEUE_RETRY_DELAY: int = Field(
        default=5,
        description="Delay in seconds between retry attempts"
    )
    GRAPHITI_BACKGROUND_MODE: bool = Field(
        default=True,
        description="Process Graphiti operations in background (non-blocking)"
    )
    GRAPHITI_MOCK_ENABLED: bool = Field(
        default=False,
        description="Use fast mock processing for Graphiti operations instead of real API calls"
    )

    # LLM Concurrency / Retry
    LLM_MAX_CONCURRENT_REQUESTS: int = Field(
        default=15,
        description="Maximum number of concurrent requests to the LLM provider (OpenAI) per API instance"
    )
    LLM_RETRY_ATTEMPTS: int = Field(
        default=3,
        description="Number of retry attempts for LLM calls on transient errors (rate limits, 5xx)"
    )

    # Airtable (Optional)
    AIRTABLE_TOKEN: Optional[str] = Field(None, description="Airtable personal access token (PAT)")
    AIRTABLE_DEFAULT_BASE_ID: Optional[str] = Field(None, description="Default Airtable base ID for tools if not provided explicitly")
    AIRTABLE_TEST_BASE_ID: Optional[str] = Field(None, description="Airtable base ID specifically for integration testing (separate from production)")
    AIRTABLE_TEST_TABLE: Optional[str] = Field(None, description="Airtable table ID/name for integration testing")

    # Uvicorn request handling limits
    UVICORN_LIMIT_CONCURRENCY: int = Field(
        default=100,
        description="Maximum number of concurrent in-process requests Uvicorn should allow before back-pressure kicks in"
    )
    UVICORN_LIMIT_MAX_REQUESTS: int = Field(
        default=1000,
        description="Maximum number of requests to handle before the worker is recycled (helps avoid memory bloat)"
    )

    model_config = ConfigDict(
        # Dynamic env_file will be set in load_settings()
        case_sensitive=True,
        extra="ignore"  # Allow extra fields in environment variables
    )

def load_settings() -> Settings:
    """Load and validate settings from environment variables and .env file."""
    # Detect which environment file to use
    env_file = detect_environment_file()
    
    # Check if we're in debug mode (AM_LOG_LEVEL set to DEBUG)
    debug_mode = os.environ.get('AM_LOG_LEVEL', '').upper() == 'DEBUG'
    
    # Load environment variables from the detected env file
    try:
        load_dotenv(dotenv_path=env_file, override=True)
        print(f"📝 Environment file loaded from: {Path(env_file).absolute()}")
    except Exception as e:
        print(f"⚠️ Error loading {env_file} file: {str(e)}")

    # Debug DATABASE_URL only if in debug mode
    if debug_mode:
        print(f"🔍 DATABASE_URL from environment after dotenv: {os.environ.get('DATABASE_URL', 'Not set')}")

    # Strip comments from environment variables
    for key in os.environ:
        if isinstance(os.environ[key], str) and '#' in os.environ[key]:
            os.environ[key] = os.environ[key].split('#')[0].strip()
            if debug_mode:
                print(f"📝 Stripped comments from environment variable: {key}")

    try:
        # Create settings with the detected env file
        settings = Settings(_env_file=env_file, _env_file_encoding='utf-8')
        
        # Debug DATABASE_URL after loading settings - only in debug mode
        if debug_mode:
            print(f"🔍 DATABASE_URL after loading settings: {settings.DATABASE_URL}")
        
        # Final check - if there's a mismatch, use the environment value
        env_db_url = os.environ.get('DATABASE_URL')
        if env_db_url and env_db_url != settings.DATABASE_URL:
            if debug_mode:
                print("⚠️ Overriding settings.DATABASE_URL with environment value")
            # This is a bit hacky but necessary to fix mismatches
            settings.DATABASE_URL = env_db_url
            if debug_mode:
                print(f"📝 Final DATABASE_URL: {settings.DATABASE_URL}")
                
        # We no longer print the detailed configuration here
        # This is now handled by the CLI's debug flag handler in src/cli/__init__.py
        
        return settings
    except Exception as e:
        print("❌ Error loading configuration:")
        print(f"   {str(e)}")
        raise

def mask_connection_string(conn_string: str) -> str:
    """Mask sensitive information in a connection string."""
    try:
        # Parse the connection string
        parsed = urllib.parse.urlparse(conn_string)
        
        # Create a masked version
        if parsed.password:
            # Replace password with asterisks
            masked_netloc = f"{parsed.username}:****@{parsed.hostname}"
            if parsed.port:
                masked_netloc += f":{parsed.port}"
                
            # Reconstruct the URL with masked password
            masked_url = urllib.parse.urlunparse((
                parsed.scheme,
                masked_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            return masked_url
        
        return conn_string  # No password to mask
    except Exception:
        # If parsing fails, just show the first and last few characters
        return f"{conn_string[:10]}...{conn_string[-10:]}"

# Create a global settings instance
settings = load_settings()

def get_model_settings(model_name: str) -> Dict[str, Any]:
    """Get model settings from environment variables.
    
    Args:
        model_name: Model name
        
    Returns:
        Dict with model settings
    """
    # Default settings
    settings_dict = {
        "temperature": 0.7,
        "max_tokens": 4096
    }
    
    # Override with environment variables
    model_prefix = model_name.replace("-", "_").replace(":", "_").upper()
    
    # Check for temperature override
    temp_var = f"{model_prefix}_TEMPERATURE"
    if temp_var in os.environ:
        try:
            settings_dict["temperature"] = float(os.environ[temp_var])
        except ValueError:
            pass
    
    # Check for max tokens override
    tokens_var = f"{model_prefix}_MAX_TOKENS"
    if tokens_var in os.environ:
        try:
            settings_dict["max_tokens"] = int(os.environ[tokens_var])
        except ValueError:
            pass
    
    return settings_dict