"""Configuration management for Claude SDK Executor.

This module handles configuration loading with priority system and file-based configuration.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ConfigPriority:
    """Configuration loading priority system."""
    
    @staticmethod
    def load_with_priority(
        workspace: Path,
        explicit_value: Optional[Any],
        file_name: str,
        default: Any = None
    ) -> Any:
        """
        Load configuration with priority:
        1. Explicit parameter (if provided)
        2. File in workspace (if exists)
        3. Default value
        """
        if explicit_value is not None:
            return explicit_value
            
        file_path = workspace / file_name
        if file_path.exists():
            try:
                if file_name.endswith('.json'):
                    with open(file_path) as f:
                        return json.load(f)
                else:
                    return file_path.read_text().strip()
            except Exception as e:
                logger.error(f"Failed to load {file_name}: {e}")
                
        return default


class SDKConfigManager:
    """Manages SDK configuration building with file-based loading."""
    
    @staticmethod
    def build_options(workspace: Path, **kwargs):
        """Build options with file-based configuration loading.
        
        Args:
            workspace: The workspace directory path
            **kwargs: Additional options that override file-based configs
            
        Returns:
            Configured ClaudeCodeOptions instance
        """
        from claude_code_sdk import ClaudeCodeOptions
        
        options = ClaudeCodeOptions()
        
        # Set working directory (SDK uses cwd, not workspace)
        options.cwd = str(workspace)
        
        # Load system prompt from prompt.md (NOT append_system_prompt)
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
        
        # Load allowed tools if file exists and not explicitly provided
        if 'allowed_tools' not in kwargs:
            allowed_tools_file = workspace / "allowed_tools.json"
            if allowed_tools_file.exists():
                try:
                    with open(allowed_tools_file) as f:
                        tools_list = json.load(f)
                        if isinstance(tools_list, list):
                            options.allowed_tools = tools_list
                            logger.info(f"Loaded {len(tools_list)} allowed tools from file")
                        else:
                            logger.warning("allowed_tools.json must contain a JSON array")
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid allowed_tools.json: {e}")
                except Exception as e:
                    logger.error(f"Failed to load allowed_tools.json: {e}")
        
        # Load disallowed tools if file exists and not explicitly provided
        if 'disallowed_tools' not in kwargs:
            disallowed_tools_file = workspace / "disallowed_tools.json"
            if disallowed_tools_file.exists():
                try:
                    with open(disallowed_tools_file) as f:
                        tools_list = json.load(f)
                        if isinstance(tools_list, list):
                            options.disallowed_tools = tools_list
                            logger.info(f"Loaded {len(tools_list)} disallowed tools from file")
                        else:
                            logger.warning("disallowed_tools.json must contain a JSON array")
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid disallowed_tools.json: {e}")
                except Exception as e:
                    logger.error(f"Failed to load disallowed_tools.json: {e}")
        
        # Load MCP configuration
        mcp_config_file = workspace / ".mcp.json"
        if mcp_config_file.exists():
            try:
                with open(mcp_config_file) as f:
                    mcp_data = json.load(f)
                    
                # SDK expects mcp_servers dict
                if 'mcpServers' in mcp_data and isinstance(mcp_data['mcpServers'], dict):
                    options.mcp_servers = mcp_data['mcpServers']
                    logger.info(f"Loaded {len(mcp_data['mcpServers'])} MCP servers from config")
                else:
                    logger.warning(".mcp.json must contain 'mcpServers' object")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid .mcp.json: {e}")
            except Exception as e:
                logger.error(f"Failed to load .mcp.json: {e}")
        
        # Apply explicit kwargs (highest priority)
        for key, value in kwargs.items():
            if hasattr(options, key) and value is not None:
                setattr(options, key, value)
        
        # Handle model parameter specifically
        if 'model' in kwargs and kwargs['model']:
            options.model = kwargs['model']
        
        # Handle max_thinking_tokens if provided
        if 'max_thinking_tokens' in kwargs and kwargs['max_thinking_tokens'] is not None:
            options.max_thinking_tokens = kwargs['max_thinking_tokens']
            logger.info(f"Set max_thinking_tokens to {kwargs['max_thinking_tokens']}")
        
        # Handle session resumption - only use resume with correct Claude session ID
        if 'session_id' in kwargs and kwargs['session_id']:
            options.resume = kwargs['session_id']
            logger.info(f"Setting session resumption with Claude session ID: {kwargs['session_id']}")
        
        # Set permission mode to bypass tool permission prompts for automated workflows
        options.permission_mode = "bypassPermissions"
        logger.info("Set permission_mode to bypassPermissions for automated workflow execution")
        
        return options