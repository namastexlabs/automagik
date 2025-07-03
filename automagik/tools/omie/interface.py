"""Omie tools interface.

This module provides a compatibility layer for Omie API tools.
"""
import logging
import os
from typing import List, Dict, Any, Optional

from pydantic_ai import RunContext
from pydantic_ai.tools import Tool

from .tool import (
    search_clients,
    search_client_by_cnpj,
    get_search_clients_description,
    get_search_client_by_cnpj_description,
    
)
from .provider import OmieProvider
from .schema import ClientSearchInput

logger = logging.getLogger(__name__)

class OmieTools:
    """Tools for interacting with Omie API."""

    def __init__(self, app_key: Optional[str] = None, app_secret: Optional[str] = None):
        """Initialize with Omie API credentials.
        
        Args:
            app_key: Omie App Key (if None, will try to get from OMIE_APP_KEY env var)
            app_secret: Omie App Secret (if None, will try to get from OMIE_APP_SECRET env var)
        """
        self.app_key = app_key or os.environ.get("OMIE_APP_KEY")
        self.app_secret = app_secret or os.environ.get("OMIE_APP_SECRET")
        self.provider = OmieProvider(app_key=self.app_key, app_secret=self.app_secret)
        
        if not self.app_key or not self.app_secret:
            logger.warning("Omie credentials not provided and not found in environment variables")
        else:
            logger.info("Initialized OmieTools with credentials")

    def get_tools(self) -> List[Any]:
        """Get tools for the agent."""
        return []
        
    def get_host_tools(self) -> List[Any]:
        """Get tools for the host agent."""
        return [
            self.search_clients,
            self.search_client_by_cnpj,
            self.get_curl_example
        ]
        
    def get_backoffice_tools(self) -> List[Any]:
        """Get tools for the backoffice agent."""
        return [
            self.search_clients,
            self.search_client_by_cnpj,
            self.get_curl_example
        ]

    async def search_clients(self, input: ClientSearchInput) -> Dict[str, Any]:
        """Search clients from Omie API with various search options.

        Args:
            input: Search parameters

        Returns:
            Dictionary with search results
        """
        # Create a mock RunContext
        ctx = RunContext({})
        
        # Call the actual implementation
        result = await search_clients(ctx, input)
        
        return result

    async def search_client_by_cnpj(self, cnpj: str) -> Dict[str, Any]:
        """Search for a client by CNPJ.

        Args:
            cnpj: The CNPJ to search for

        Returns:
            Dictionary with client information
        """
        # Create a mock RunContext
        ctx = RunContext({})
        
        # Call the actual implementation
        result = await search_client_by_cnpj(ctx, cnpj)
        
        return result

# Create Omie tool instances
omie_search_clients_tool = Tool(
    name="omie_search_clients",
    description=get_search_clients_description(),
    function=search_clients
)

omie_search_client_by_cnpj_tool = Tool(
    name="omie_search_client_by_cnpj",
    description=get_search_client_by_cnpj_description(),
    function=search_client_by_cnpj
)

# Group all Omie tools
omie_tools = [
    omie_search_clients_tool,
    omie_search_client_by_cnpj_tool
] 