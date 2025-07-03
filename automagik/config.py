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

# REMOVED: .env.prod detection logic - using single .env file only

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
    AUTOMAGIK_API_KEY: str = Field("namastex888", description="API key for authenticating requests")

    # OpenAI
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key for agent operations")

    # Google Gemini (Optional)
    GEMINI_API_KEY: Optional[str] = Field(None, description="Google Gemini API key for agent operations")

    # Notion (Optional)
    NOTION_TOKEN: Optional[str] = Field(None, description="Notion integration token")

    # BlackPearl, Omie, Google Drive, Evolution (Optional)
    BLACKPEARL_TOKEN: Optional[str] = Field(None, description="BlackPearl API token")
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
    DISCORD_BOT_TOKEN: Optional[str] = Field(None, description="Discord bot token for authentication")

    # Meeting Bot
    MEETING_BOT_URL: Optional[str] = Field(None, description="Meeting bot webhook service URL for creating bots")

    # Database Configuration
    AUTOMAGIK_DATABASE_TYPE: str = Field("sqlite", description="Database type (sqlite or postgresql)")
    
    # SQLite Configuration  
    AUTOMAGIK_SQLITE_DATABASE_PATH: Optional[str] = Field(None, description="Path to SQLite database file (defaults to data/automagik.db)")
    
    # PostgreSQL Configuration
    AUTOMAGIK_DATABASE_URL: Optional[str] = Field(None, description="Database connection string (PostgreSQL or SQLite)")
    
    # PostgreSQL Connection Pool Settings
    AUTOMAGIK_POSTGRES_POOL_MIN: int = Field(10, description="Minimum connections in the pool")
    AUTOMAGIK_POSTGRES_POOL_MAX: int = Field(25, description="Maximum connections in the pool")

    # Server
    AUTOMAGIK_API_PORT: int = Field(8881, description="Port to run the server on")
    AUTOMAGIK_API_HOST: str = Field("0.0.0.0", description="Host to bind the server to")
    AUTOMAGIK_ENV: Environment = Field(Environment.DEVELOPMENT, description="Environment (development, production, testing)")

    # Logging
    AUTOMAGIK_LOG_LEVEL: LogLevel = Field(LogLevel.INFO, description="Logging level")
    AUTOMAGIK_VERBOSE_LOGGING: bool = Field(False, description="Enable verbose logging with additional details")
    AUTOMAGIK_LOG_TO_FILE: bool = Field(False, description="Enable logging to file for debugging")
    AUTOMAGIK_LOG_FILE_PATH: str = Field("debug.log", description="Path to log file when file logging is enabled")
    AUTOMAGIK_LOGFIRE_TOKEN: Optional[str] = Field(None, description="Logfire token for logging service")
    AUTOMAGIK_LOGFIRE_IGNORE_NO_CONFIG: bool = Field(True, description="Suppress Logfire warning if no token")

    # Agent Settings
    AUTOMAGIK_TIMEZONE: str = Field(
        default="UTC", 
        description="Timezone for the agent to operate in (e.g., 'UTC', 'America/New_York', 'America/Sao_Paulo')"
    )
    AUTOMAGIK_AGENT_NAMES: Optional[str] = Field(
        default=None,
        description="Comma-separated list of agent names to pre-instantiate at startup (e.g., 'simple,stan')"
    )

    # Claude Code Integration
    AUTOMAGIK_CLAUDE_LOCAL_WORKSPACE: str = Field(
        default="/tmp/claude-workspace",
        description="Local workspace directory for Claude Code operations"
    )
    AUTOMAGIK_CLAUDE_LOCAL_CLEANUP: bool = Field(
        default=True,
        description="Whether to cleanup Claude Code workspace after operations"
    )

    # Logging and File Storage
    AUTOMAGIK_LOG_DIRECTORY: str = Field(
        default="./logs",
        description="Directory for storing log files and workflow outputs"
    )



    # Fallback settings for WhatsApp
    DEFAULT_EVOLUTION_INSTANCE: str = Field(
        default="default",
        description="Default Evolution API instance to use if none is provided in the context"
    )
    
    DEFAULT_WHATSAPP_NUMBER: str = Field(
        default="5511999999999@s.whatsapp.net",
        description="Default WhatsApp number to use if none is provided in the context"
    )


    # LLM Concurrency / Retry
    AUTOMAGIK_LLM_MAX_CONCURRENT_REQUESTS: int = Field(
        default=15,
        description="Maximum number of concurrent requests to the LLM provider (OpenAI) per API instance"
    )
    AUTOMAGIK_LLM_RETRY_ATTEMPTS: int = Field(
        default=3,
        description="Number of retry attempts for LLM calls on transient errors (rate limits, 5xx)"
    )

    # Airtable (Optional)
    AIRTABLE_TOKEN: Optional[str] = Field(None, description="Airtable personal access token (PAT)")
    AIRTABLE_DEFAULT_BASE_ID: Optional[str] = Field(None, description="Default Airtable base ID for tools if not provided explicitly")
    AIRTABLE_TEST_BASE_ID: Optional[str] = Field(None, description="Airtable base ID specifically for integration testing (separate from production)")
    AIRTABLE_TEST_TABLE: Optional[str] = Field(None, description="Airtable table ID/name for integration testing")

    # Uvicorn request handling limits
    AUTOMAGIK_UVICORN_LIMIT_CONCURRENCY: int = Field(
        default=100,
        description="Maximum number of concurrent in-process requests Uvicorn should allow before back-pressure kicks in"
    )
    AUTOMAGIK_UVICORN_LIMIT_MAX_REQUESTS: int = Field(
        default=1000,
        description="Maximum number of requests to handle before the worker is recycled (helps avoid memory bloat)"
    )

    model_config = ConfigDict(
        # Dynamic env_file will be set in load_settings()
        case_sensitive=True,
        extra="ignore"  # Allow extra fields in environment variables
    )
    
    # Backward compatibility properties for legacy variable names
    @property
    def AM_LOG_LEVEL(self):
        """Backward compatibility for AM_LOG_LEVEL -> AUTOMAGIK_LOG_LEVEL"""
        return self.AUTOMAGIK_LOG_LEVEL
    
    @property
    def AM_PORT(self):
        """Backward compatibility for AM_PORT -> AUTOMAGIK_API_PORT"""
        return self.AUTOMAGIK_API_PORT
    

def load_settings() -> Settings:
    """Load and validate settings from environment variables and .env file."""
    # Use single .env file only (simplified approach)
    env_file = ".env"
    
    # Check if we're in debug mode
    debug_mode = os.environ.get('AUTOMAGIK_LOG_LEVEL', '').upper() == 'DEBUG'
    
    # Load environment variables from .env file
    try:
        load_dotenv(dotenv_path=env_file, override=True)
        print(f"📝 Environment file loaded from: {Path(env_file).absolute()}")
    except Exception as e:
        print(f"⚠️ Error loading {env_file} file: {str(e)}")

    # Debug database configuration
    if debug_mode:
        db_type = os.environ.get('AUTOMAGIK_DATABASE_TYPE', 'sqlite').lower()
        if db_type == 'postgresql':
            db_url = os.environ.get('AUTOMAGIK_DATABASE_URL', 'Not set')
            print(f"🔍 PostgreSQL mode - DATABASE_URL: {db_url}")

    # Strip comments from environment variables
    for key in os.environ:
        if isinstance(os.environ[key], str) and '#' in os.environ[key]:
            os.environ[key] = os.environ[key].split('#')[0].strip()
            if debug_mode:
                print(f"📝 Stripped comments from environment variable: {key}")

    try:
        # Create settings with the .env file
        settings = Settings(_env_file=env_file, _env_file_encoding='utf-8')
        
        # Debug database configuration after loading settings
        if debug_mode:
            if settings.AUTOMAGIK_DATABASE_TYPE.lower() == 'postgresql':
                print(f"✅ PostgreSQL configured - URL: {settings.AUTOMAGIK_DATABASE_URL}")
            else:
                sqlite_path = settings.AUTOMAGIK_SQLITE_DATABASE_PATH or './data/automagik.db'
                print(f"✅ SQLite configured - Path: {sqlite_path}")
        
        # Final check - if there's a mismatch, use the environment value
        env_db_url = os.environ.get('AUTOMAGIK_DATABASE_URL')
        if env_db_url and env_db_url != settings.AUTOMAGIK_DATABASE_URL:
            if debug_mode:
                print("⚠️ Overriding settings.AUTOMAGIK_DATABASE_URL with environment value")
            # This is a bit hacky but necessary to fix mismatches
            settings.AUTOMAGIK_DATABASE_URL = env_db_url
            if debug_mode:
                print(f"📝 Final AUTOMAGIK_DATABASE_URL: {settings.AUTOMAGIK_DATABASE_URL}")
                
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