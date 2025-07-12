"""SDK CLI Manager for Claude Code execution.

This module handles Claude CLI detection and environment setup.
"""

import os
import glob
import shutil
import logging
from typing import Optional

from ...utils.nodejs_detection import ensure_node_in_path

logger = logging.getLogger(__name__)


class SDKCLIManager:
    """Manages Claude CLI detection and environment setup."""
    
    # Common Claude CLI installation paths
    CLAUDE_CLI_PATHS = [
        os.path.expanduser('~/.nvm/versions/node/*/bin/claude'),
        '/usr/local/bin/claude',
        os.path.expanduser('~/.volta/bin/claude'),
        os.path.expanduser('~/.fnm/node-versions/*/installation/bin/claude'),
        os.path.expanduser('~/n/bin/claude'),
        '/opt/homebrew/bin/claude',
        '/usr/bin/claude',
        # Windows paths
        os.path.expanduser('~/AppData/Roaming/npm/claude.cmd'),
        os.path.expanduser('~/AppData/Roaming/npm/node_modules/.bin/claude.cmd'),
    ]
    
    def __init__(self):
        self.claude_cli_path = None
    
    def ensure_claude_cli_available(self) -> str:
        """Ensure Claude CLI is available and return its path.
        
        Returns:
            Path to Claude CLI executable
            
        Raises:
            RuntimeError: If Claude CLI cannot be found
        """
        # First ensure Node.js is in PATH
        ensure_node_in_path()
        
        # Check if Claude CLI is already in PATH
        claude_cli = shutil.which('claude')
        if claude_cli:
            logger.info(f"Claude CLI found at: {claude_cli}")
            self.claude_cli_path = claude_cli
            return claude_cli
        
        # Search common locations
        logger.warning("Claude CLI not found in PATH, searching common locations...")
        claude_cli = self._search_claude_cli()
        
        if not claude_cli:
            self._log_environment_debug()
            raise RuntimeError(
                "Claude CLI is required but not found. "
                "Please ensure Claude Code is installed: npm install -g claude-code"
            )
        
        self.claude_cli_path = claude_cli
        return claude_cli
    
    def _search_claude_cli(self) -> Optional[str]:
        """Search for Claude CLI in common locations.
        
        Returns:
            Path to Claude CLI if found, None otherwise
        """
        for pattern in self.CLAUDE_CLI_PATHS:
            try:
                matches = glob.glob(pattern)
                # Sort matches to get the latest version if multiple exist
                matches.sort(reverse=True)
                
                for match in matches:
                    if os.path.isfile(match) and os.access(match, os.X_OK):
                        # Add Claude's directory to PATH
                        claude_dir = os.path.dirname(match)
                        self._add_to_path(claude_dir)
                        
                        # Check if it's now available via which
                        claude_cli = shutil.which('claude')
                        if claude_cli:
                            logger.info(f"Claude CLI now available at: {claude_cli}")
                            return claude_cli
                        else:
                            # Return the direct path
                            logger.info(f"Claude CLI found at: {match}")
                            return match
                            
            except Exception as e:
                logger.debug(f"Error checking pattern {pattern}: {e}")
        
        return None
    
    def _add_to_path(self, directory: str) -> None:
        """Add a directory to PATH if not already present."""
        current_path = os.environ.get('PATH', '')
        if directory not in current_path:
            os.environ['PATH'] = f"{directory}:{current_path}"
            logger.info(f"Added directory to PATH: {directory}")
    
    def _log_environment_debug(self) -> None:
        """Log environment information for debugging."""
        logger.error("Claude CLI not found after searching all common locations!")
        logger.error(f"Current PATH: {os.environ.get('PATH', 'NOT SET')}")
        logger.error(f"NODE_PATH: {os.environ.get('NODE_PATH', 'NOT SET')}")
        logger.error(f"NPM_CONFIG_PREFIX: {os.environ.get('NPM_CONFIG_PREFIX', 'NOT SET')}")
        
        # Log PM2 specific environment
        if os.environ.get('PM2_HOME'):
            logger.error(f"PM2_HOME: {os.environ.get('PM2_HOME')}")
            logger.error("Running under PM2 - check PM2 environment configuration")
    
    def get_claude_version(self) -> Optional[str]:
        """Get Claude CLI version if available."""
        if not self.claude_cli_path:
            self.ensure_claude_cli_available()
        
        try:
            import subprocess
            result = subprocess.run(
                [self.claude_cli_path, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.error(f"Failed to get Claude CLI version: {e}")
        
        return None
    
    def validate_claude_sdk_import(self) -> bool:
        """Validate that claude_code_sdk can be imported."""
        try:
            import claude_code_sdk  # noqa: F401
            logger.info("claude_code_sdk module loaded successfully")
            return True
        except ImportError as e:
            logger.error(f"Failed to import claude_code_sdk: {e}")
            logger.error("Ensure claude-code Python SDK is installed: pip install claude-code-sdk")
            return False
    
    def get_environment_info(self) -> dict:
        """Get environment information for debugging."""
        return {
            "claude_cli_path": self.claude_cli_path,
            "claude_in_path": bool(shutil.which('claude')),
            "node_path": shutil.which('node'),
            "npm_path": shutil.which('npm'),
            "python_executable": os.sys.executable,
            "working_directory": os.getcwd(),
            "path_env": os.environ.get('PATH', ''),
            "pm2_home": os.environ.get('PM2_HOME'),
            "claude_code_entrypoint": os.environ.get('CLAUDE_CODE_ENTRYPOINT'),
            "claudecode_env": os.environ.get('CLAUDECODE')
        }