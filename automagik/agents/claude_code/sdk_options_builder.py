"""SDK Options Builder for Claude Code execution.

This module handles building ClaudeCodeOptions with proper configuration loading.
"""

import json
import logging
from pathlib import Path
from claude_code_sdk import ClaudeCodeOptions

logger = logging.getLogger(__name__)


class SDKOptionsBuilder:
    """Builds ClaudeCodeOptions with file-based configuration loading."""
    
    def build_options(self, workspace: Path, **kwargs) -> ClaudeCodeOptions:
        """Build options with file-based configuration loading.
        
        Args:
            workspace: Path to the workflow workspace
            **kwargs: Additional options to override defaults
            
        Returns:
            Configured ClaudeCodeOptions instance
        """
        options = ClaudeCodeOptions()
        
        # Set working directory (SDK uses cwd, not workspace)
        options.cwd = str(workspace)
        
        # Load system prompt from prompt.md
        self._load_system_prompt(workspace, options)
        
        # Load allowed tools
        if 'allowed_tools' not in kwargs:
            self._load_allowed_tools(workspace, options)
        
        # Load disallowed tools
        if 'disallowed_tools' not in kwargs:
            self._load_disallowed_tools(workspace, options)
        
        # Load MCP configuration
        self._load_mcp_config(workspace, options)
        
        # Apply explicit kwargs (highest priority)
        for key, value in kwargs.items():
            if hasattr(options, key) and value is not None:
                setattr(options, key, value)
        
        # Handle session resumption
        if 'session_id' in kwargs and kwargs['session_id']:
            options.resume = kwargs['session_id']
            logger.info(f"Setting session resumption with Claude session ID: {kwargs['session_id']}")
        
        # Set permission mode to bypass tool permission prompts
        options.permission_mode = "bypassPermissions"
        logger.info("Set permission_mode to bypassPermissions for automated workflow execution")
        
        return options
    
    def _load_system_prompt(self, workspace: Path, options: ClaudeCodeOptions) -> None:
        """Load system prompt from prompt.md file."""
        prompt_file = workspace / "prompt.md"
        if prompt_file.exists():
            try:
                prompt_content = prompt_file.read_text().strip()
                if prompt_content:
                    options.system_prompt = prompt_content
                    logger.info(f"Loaded system prompt from {prompt_file} ({len(prompt_content)} chars)")
                else:
                    logger.debug("prompt.md is empty, using default Claude Code behavior")
            except Exception as e:
                logger.error(f"Failed to load prompt.md: {e}")
        else:
            logger.debug("No prompt.md found, using vanilla Claude Code")
    
    def _load_allowed_tools(self, workspace: Path, options: ClaudeCodeOptions) -> None:
        """Load allowed tools from allowed_tools.json file."""
        allowed_tools_file = workspace / "allowed_tools.json"
        if allowed_tools_file.exists():
            try:
                with open(allowed_tools_file) as f:
                    tools_list = json.load(f)
                    if isinstance(tools_list, list):
                        options.allowed_tools = tools_list
                        logger.info(f"Loaded {len(tools_list)} allowed tools from file")
            except Exception as e:
                logger.error(f"Failed to load allowed_tools.json: {e}")
    
    def _load_disallowed_tools(self, workspace: Path, options: ClaudeCodeOptions) -> None:
        """Load disallowed tools from disallowed_tools.json file."""
        disallowed_tools_file = workspace / "disallowed_tools.json"
        if disallowed_tools_file.exists():
            try:
                with open(disallowed_tools_file) as f:
                    tools_list = json.load(f)
                    if isinstance(tools_list, list):
                        options.disallowed_tools = tools_list
                        logger.info(f"Loaded {len(tools_list)} disallowed tools from file")
            except Exception as e:
                logger.error(f"Failed to load disallowed_tools.json: {e}")
    
    def _load_mcp_config(self, workspace: Path, options: ClaudeCodeOptions) -> None:
        """Load MCP configuration from .mcp.json file."""
        mcp_config_file = workspace / ".mcp.json"
        if mcp_config_file.exists():
            try:
                with open(mcp_config_file) as f:
                    mcp_data = json.load(f)
                    
                if 'mcpServers' in mcp_data and isinstance(mcp_data['mcpServers'], dict):
                    options.mcp_servers = mcp_data['mcpServers']
                    logger.info(f"Loaded {len(mcp_data['mcpServers'])} MCP servers from config")
                else:
                    logger.warning(".mcp.json must contain 'mcpServers' object")
                    
            except Exception as e:
                logger.error(f"Failed to load .mcp.json: {e}")