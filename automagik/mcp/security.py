"""
MCP Security Module - Input Validation and Command Sanitization

This module provides comprehensive security functions to prevent:
- Command injection attacks
- Path traversal vulnerabilities  
- Environment variable injection
- Input validation bypasses

All MCP command execution MUST use these security functions.
"""

import shlex
import re
import os
import fnmatch
import shutil
from typing import List, Dict, Any
from urllib.parse import urlparse
import logging

from ..utils.nodejs_detection import get_security_paths

logger = logging.getLogger(__name__)

class SecurityError(Exception):
    """Security validation error"""
    pass

class ValidationError(Exception):
    """Input validation error"""
    pass

# =============================================================================
# DYNAMIC NODE.JS PATH DETECTION
# =============================================================================

def _get_nodejs_paths():
    """Get Node.js paths dynamically for security allowlist"""
    nodejs_paths = get_security_paths()
    if not nodejs_paths:
        logger.warning("Node.js not found - MCP servers using Node.js will not work")
        return {
            "npx_path": None,
            "node_path": None
        }
    
    return {
        "npx_path": nodejs_paths['npx_path'],
        "node_path": nodejs_paths['node_path']
    }

# =============================================================================
# COMMAND ALLOWLISTING CONFIGURATION
# =============================================================================

def _build_allowed_commands():
    """Build allowed commands with dynamic Node.js paths"""
    nodejs_paths = _get_nodejs_paths()
    
    commands = {
        # Python package runner (uvx for MCP servers) - dynamically detected
        "uvx": {
            "path": _detect_uvx_path(),
            "allowed_args": [
                "mcp-server-*", "@modelcontextprotocol/server-*",
                "--python", "--with", "--from",  # UV arguments
                "/tmp", "/var/tmp", "/opt/mcp", "/tmp/*", "/var/tmp/*", "/opt/mcp/*"
            ],
            "description": "UV package runner for Python MCP servers"
        },
        # Python MCP servers  
        "python3": {
            "path": "/usr/bin/python3",
            "allowed_args": ["-m", "mcp_server_*", "/tmp", "/var/tmp", "/opt/mcp", "/tmp/*", "/var/tmp/*", "/opt/mcp/*"],
            "description": "Python MCP servers"
        }
    }
    
    # Add Node.js commands if available
    if nodejs_paths["npx_path"]:
        commands["npx"] = {
            "path": nodejs_paths["npx_path"],
            "allowed_args": [
                "-y", "--yes",  # Auto-confirm package installation
                "@modelcontextprotocol/server-*", "mcp-server-*", 
                "/tmp", "/var/tmp", "/opt/mcp", "/tmp/*", "/var/tmp/*", "/opt/mcp/*"
            ],
            "description": "NPM package runner for MCP servers"
        }
    
    if nodejs_paths["node_path"]:
        commands["node"] = {
            "path": nodejs_paths["node_path"],
            "allowed_args": ["server.js", "**/server*.js", "weather-server.js", "/tmp/*", "/var/tmp/*", "/opt/mcp/*"],
            "description": "Node.js runtime"
        }
    
    return commands

def _detect_uvx_path():
    """Dynamically detect uvx executable location"""
    # Try PATH resolution first
    uvx_path = shutil.which("uvx")
    if uvx_path:
        logger.debug(f"Found uvx via PATH: {uvx_path}")
        return uvx_path
    
    # Static fallbacks as last resort
    fallbacks = [
        "/usr/local/bin/uvx",
        "/usr/bin/uvx",
        os.path.expanduser("~/.local/bin/uvx")
    ]
    
    for path in fallbacks:
        if os.path.exists(path) and os.access(path, os.X_OK):
            logger.debug(f"Found uvx at fallback: {path}")
            return path
    
    logger.warning("uvx not found - MCP servers using uvx will fail")
    return "/usr/local/bin/uvx"  # Keep original default for safety

# Build allowed commands dynamically
ALLOWED_COMMANDS = _build_allowed_commands()


# =============================================================================
# ENVIRONMENT VARIABLE FILTERING
# =============================================================================

ALLOWED_ENV_VARS = {
    # Safe environment variables
    "LANG", "LC_ALL", "LC_CTYPE", "LC_MESSAGES",
    "TZ", "USER", "LOGNAME",
    # MCP-specific variables (controlled)
    "MCP_SERVER_ROOT", "MCP_CONFIG_PATH",
    # Node.js variables (minimal set)
    "NODE_ENV", "NPM_CONFIG_REGISTRY",
    # Python variables (minimal set) 
    "PYTHONPATH", "PYTHONHOME"
}

DANGEROUS_ENV_VARS = {
    # System security
    "PATH", "LD_PRELOAD", "LD_LIBRARY_PATH",
    "DYLD_INSERT_LIBRARIES", "DYLD_FORCE_FLAT_NAMESPACE",
    # Shell and execution
    "SHELL", "IFS", "PS1", "PS2", "PS4", "PROMPT_COMMAND",
    # Process behavior
    "MALLOC_OPTIONS", "MALLOC_CHECK_", "GLIBC_TUNABLES",
    # Network and system
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"
}

# =============================================================================
# INPUT VALIDATION PATTERNS
# =============================================================================

class MCPInputValidator:
    """Comprehensive input validation for MCP operations"""
    
    # Validation patterns
    SERVER_NAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]{0,63}$')
    TOOL_NAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{0,127}$')
    SAFE_PATH_PATTERN = re.compile(r'^[a-zA-Z0-9._/-]+$')
    
    # Dangerous patterns to block
    PATH_TRAVERSAL_PATTERNS = [
        '../', '../', '..\\', '..\\\\',
        '%2e%2e%2f', '%2e%2e/', '%252e%252e%252f'
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        ';', '&&', '||', '`', '$(',
        '|', '>', '<', '&', '\n', '\r'
    ]
    
    RESERVED_NAMES = {'system', 'admin', 'root', 'test', 'config'}

# =============================================================================
# COMMAND VALIDATION FUNCTIONS
# =============================================================================

def validate_command(command: str, args: List[str]) -> bool:
    """
    Validate command against allowlist and security policies.
    
    Args:
        command: Command executable path or name
        args: Command arguments
        
    Returns:
        True if valid
        
    Raises:
        SecurityError: If command or args are not allowed
    """
    # Resolve command to absolute path if it's just a name
    if not os.path.isabs(command):
        command = resolve_command_path(command)
    
    # Extract command name for allowlist check
    command_name = os.path.basename(command)
    
    if command_name not in ALLOWED_COMMANDS:
        raise SecurityError(f"Command not allowed: {command_name}")
    
    allowed_cmd = ALLOWED_COMMANDS[command_name]
    
    # Verify path matches expected or fallback paths
    valid_path = False
    if os.path.exists(allowed_cmd["path"]):
        try:
            if os.path.samefile(command, allowed_cmd["path"]):
                valid_path = True
        except OSError:
            pass
    
    # Check fallback paths if not found in primary
    if not valid_path and "fallback_paths" in allowed_cmd:
        import glob
        for path_pattern in allowed_cmd["fallback_paths"]:
            matching_paths = glob.glob(path_pattern)
            for path in matching_paths:
                try:
                    if os.path.exists(path) and os.path.samefile(command, path):
                        valid_path = True
                        break
                except OSError:
                    continue
            if valid_path:
                break
    
    if not valid_path:
        raise SecurityError(f"Command path mismatch: {command}")
    
    # Validate arguments against patterns
    for arg in args:
        if not any(fnmatch.fnmatch(arg, pattern) 
                  for pattern in allowed_cmd["allowed_args"]):
            raise SecurityError(f"Argument not allowed: {arg}")
    
    logger.info(f"Command validation passed: {command_name} with {len(args)} args")
    return True

def resolve_command_path(command_name: str) -> str:
    """
    Safely resolve command name to absolute path.
    
    Args:
        command_name: Name of command to resolve
        
    Returns:
        Absolute path to command
        
    Raises:
        SecurityError: If command not found or not in allowed directories
    """
    # Check allowlist first
    if command_name in ALLOWED_COMMANDS:
        config = ALLOWED_COMMANDS[command_name]
        expected_path = config["path"]
        if os.path.exists(expected_path):
            return expected_path
        
        # Check fallback paths if available
        if "fallback_paths" in config:
            import glob
            for path_pattern in config["fallback_paths"]:
                matching_paths = glob.glob(path_pattern)
                for path in matching_paths:
                    if os.path.exists(path) and os.access(path, os.X_OK):
                        return path
    
    # Fallback to which command (with restricted PATH)
    allowed_dirs = ['/usr/bin', '/bin', '/usr/local/bin']
    
    for directory in allowed_dirs:
        full_path = os.path.join(directory, command_name)
        if os.path.exists(full_path) and os.access(full_path, os.X_OK):
            return full_path
    
    raise SecurityError(f"Command not found in allowed directories: {command_name}")

def sanitize_command_arguments(args: List[str]) -> List[str]:
    """
    Sanitize command arguments using shlex.quote().
    
    Args:
        args: List of command arguments
        
    Returns:
        List of properly escaped arguments
        
    Raises:
        ValidationError: If arguments contain dangerous patterns
    """
    sanitized_args = []
    
    for arg in args:
        # Validate argument first
        validate_command_argument(arg)
        
        # Escape argument using shlex.quote
        safe_arg = shlex.quote(arg)
        sanitized_args.append(safe_arg)
    
    logger.debug(f"Sanitized {len(args)} command arguments")
    return sanitized_args

def validate_command_argument(arg: str) -> bool:
    """
    Validate a single command argument for security.
    
    Args:
        arg: Command argument to validate
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If argument contains dangerous patterns
    """
    # Check length
    if len(arg) > 2048:
        raise ValidationError("Argument too long")
    
    # Check for command injection patterns
    for pattern in MCPInputValidator.COMMAND_INJECTION_PATTERNS:
        if pattern in arg:
            raise ValidationError(f"Argument contains dangerous pattern: {pattern}")
    
    # Check for path traversal in file arguments
    if any(traversal in arg for traversal in MCPInputValidator.PATH_TRAVERSAL_PATTERNS):
        raise ValidationError("Argument contains path traversal")
    
    # Validate file paths if argument looks like a path
    if arg.startswith('/') or arg.startswith('./'):
        validate_file_path(arg)
    
    return True

# =============================================================================
# ENVIRONMENT VARIABLE FILTERING
# =============================================================================

def filter_environment(env_vars: Dict[str, str]) -> Dict[str, str]:
    """
    Filter environment variables for security.
    
    Args:
        env_vars: Dictionary of environment variables
        
    Returns:
        Filtered dictionary of safe environment variables
    """
    filtered_env = {}
    
    for key, value in env_vars.items():
        # Block dangerous variables
        if key in DANGEROUS_ENV_VARS:
            logger.warning(f"Blocked dangerous environment variable: {key}")
            continue
            
        # Allow only allowlisted variables
        if key not in ALLOWED_ENV_VARS:
            logger.warning(f"Blocked non-allowlisted environment variable: {key}")
            continue
            
        # Validate variable content
        if not validate_env_value(key, value):
            logger.warning(f"Blocked environment variable with invalid value: {key}={value}")
            continue
            
        filtered_env[key] = value
    
    logger.info(f"Environment filtering: {len(env_vars)} -> {len(filtered_env)} variables")
    return filtered_env

def validate_env_value(key: str, value: str) -> bool:
    """
    Validate environment variable value.
    
    Args:
        key: Environment variable name
        value: Environment variable value
        
    Returns:
        True if valid
    """
    # Check for shell metacharacters
    dangerous_chars = ['$', '`', ';', '&', '|', '>', '<', '(', ')', '{', '}']
    if any(char in value for char in dangerous_chars):
        return False
    
    # Check for null bytes
    if '\x00' in value:
        return False
        
    # Key-specific validation
    if key in ["PYTHONPATH", "MCP_CONFIG_PATH"]:
        # Validate paths
        return all(os.path.isabs(path) for path in value.split(":"))
    
    # General length limit
    if len(value) > 4096:
        return False
        
    return True

def get_minimal_environment() -> Dict[str, str]:
    """
    Get minimal required environment for MCP servers.
    
    Returns:
        Dictionary of minimal safe environment variables
    """
    return {
        "PATH": "/usr/bin:/bin",  # Restricted PATH
        "HOME": "/tmp/mcp",       # Isolated home
        "USER": "mcp",            # Non-privileged user
        "LANG": "C.UTF-8",        # Minimal locale
    }

# =============================================================================
# INPUT VALIDATION FUNCTIONS  
# =============================================================================

def validate_server_name(name: str) -> bool:
    """
    Validate MCP server name.
    
    Args:
        name: Server name to validate
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If name is invalid
    """
    if not name or len(name) > 64:
        raise ValidationError("Server name must be 1-64 characters")
    
    if not MCPInputValidator.SERVER_NAME_PATTERN.match(name):
        raise ValidationError("Server name contains invalid characters")
    
    # Block reserved names
    if name.lower() in MCPInputValidator.RESERVED_NAMES:
        raise ValidationError("Server name is reserved")
    
    return True

def validate_file_path(path: str) -> bool:
    """
    Validate file system paths.
    
    Args:
        path: File path to validate
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If path is invalid or dangerous
    """
    # Normalize and check for traversal
    normalized = os.path.normpath(path)
    if '..' in normalized.split(os.sep):
        raise ValidationError("Path contains directory traversal")
    
    # Must be within allowed directories
    allowed_roots = ['/tmp', '/var/tmp', '/opt/mcp']
    if not any(normalized.startswith(root) for root in allowed_roots):
        raise ValidationError("Path outside allowed directories")
    
    # Check for special files
    if normalized.startswith('/proc') or normalized.startswith('/sys'):
        raise ValidationError("Access to system files not allowed")
    
    return True

def validate_resource_uri(uri: str) -> bool:
    """
    Validate MCP resource URIs.
    
    Args:
        uri: Resource URI to validate
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If URI is invalid
    """
    try:
        parsed = urlparse(uri)
    except Exception:
        raise ValidationError("Invalid URI format")
    
    # Allow only specific schemes
    allowed_schemes = ['file', 'mcp']
    if parsed.scheme not in allowed_schemes:
        raise ValidationError(f"URI scheme not allowed: {parsed.scheme}")
    
    # For file URIs, validate path
    if parsed.scheme == 'file':
        validate_file_path(parsed.path)
    
    return True

def validate_mcp_config(config: Dict[str, Any]) -> bool:
    """
    Validate MCP server configuration.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If configuration is invalid
    """
    required_fields = ['command', 'args']
    for field in required_fields:
        if field not in config:
            raise ValidationError(f"Required field missing: {field}")
    
    # Validate command (first element if list, or the command itself)
    command = config['command']
    if isinstance(command, list):
        if not command:
            raise ValidationError("Command list cannot be empty")
        validate_command_path(command[0])
        # Validate arguments (rest of command list + separate args)
        all_args = command[1:] + config.get('args', [])
    else:
        validate_command_path(command)
        all_args = config.get('args', [])
    
    # Validate all arguments
    for arg in all_args:
        validate_command_argument(arg)
    
    # Validate environment variables
    if 'env' in config:
        validate_environment_config(config['env'])
    
    # Validate working directory
    if 'cwd' in config:
        validate_file_path(config['cwd'])
    
    return True

def validate_command_path(command: str) -> bool:
    """
    Validate command executable path.
    
    Args:
        command: Command path to validate
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If command path is invalid
    """
    # Must be absolute path or resolvable command name
    if not os.path.isabs(command):
        # Try to resolve it
        try:
            resolve_command_path(command)
        except SecurityError as e:
            raise ValidationError(str(e))
    else:
        # Check for path traversal
        normalized = os.path.normpath(command)
        if normalized != command:
            raise ValidationError("Path contains traversal sequences")
        
        # Must exist and be executable
        if not os.path.exists(command):
            raise ValidationError("Command does not exist")
        
        if not os.access(command, os.X_OK):
            raise ValidationError("Command is not executable")
        
        # Must be in allowed directories
        allowed_dirs = ['/usr/bin', '/bin', '/usr/local/bin']
        if not any(command.startswith(d) for d in allowed_dirs):
            raise ValidationError("Command not in allowed directories")
    
    return True

def validate_environment_config(env: Dict[str, str]) -> bool:
    """
    Validate environment configuration.
    
    Args:
        env: Environment variables dictionary
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If environment config is invalid
    """
    for key, value in env.items():
        # Environment key validation
        if not re.match(r'^[A-Z][A-Z0-9_]*$', key):
            raise ValidationError(f"Invalid environment variable name: {key}")
        
        # Value validation (will be filtered later)
        if len(value) > 1024:
            raise ValidationError(f"Environment value too long: {key}")
    
    return True

# =============================================================================
# SECURE COMMAND CONSTRUCTION
# =============================================================================

def build_secure_command(base_command: str, args: List[str], env: Dict[str, str] = None) -> tuple:
    """
    Build a secure command with proper validation and sanitization.
    
    Args:
        base_command: Base command to execute
        args: Command arguments
        env: Environment variables (optional)
        
    Returns:
        Tuple of (secure_command_list, filtered_env)
        
    Raises:
        SecurityError: If command validation fails
        ValidationError: If input validation fails
    """
    # Validate and resolve command
    if not os.path.isabs(base_command):
        secure_command = resolve_command_path(base_command)
    else:
        validate_command_path(base_command)
        secure_command = base_command
    
    # Validate arguments
    for arg in args:
        validate_command_argument(arg)
    
    # Validate command against allowlist
    validate_command(secure_command, args)
    
    # Sanitize arguments  
    safe_args = sanitize_command_arguments(args)
    
    # Build secure command list (no shell, direct execution)
    secure_command_list = [secure_command] + safe_args
    
    # Filter environment
    filtered_env = get_minimal_environment()
    if env:
        safe_env = filter_environment(env)
        filtered_env.update(safe_env)
    
    logger.info(f"Built secure command: {os.path.basename(secure_command)} with {len(safe_args)} args")
    return secure_command_list, filtered_env 