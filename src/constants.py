"""Constants for the Automagik Agents project.

This module defines constants that are used throughout the project.
Centralizing these values makes it easier to maintain and update the codebase.
"""

# Default model settings
# DEFAULT_MODEL is now handled by AUTOMAGIK_DEFAULT_MODEL env var
DEFAULT_TEMPERATURE = 0.1  # Default temperature setting
DEFAULT_MAX_TOKENS = 4000  # Default max tokens for responses
DEFAULT_RETRIES = 3  # Default number of retries for API calls

# API settings
DEFAULT_API_TIMEOUT = 30  # Default timeout for API calls in seconds
DEFAULT_REQUEST_LIMIT = 5  # Default limit on number of API requests

# Session settings
DEFAULT_SESSION_PLATFORM = "automagik"  # Default platform for sessions 