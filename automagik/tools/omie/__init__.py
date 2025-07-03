"""Omie API tools for Automagik Agents.

Provides tools for interacting with Omie API.
"""

# Import from tool module
from automagik.tools.omie.tool import (
    search_clients,
    search_client_by_cnpj,
    get_search_clients_description,
    get_search_client_by_cnpj_description,
)

# Import schema models
from automagik.tools.omie.schema import (
    ClientSearchInput,
    ClientSearchResult,
    ClientSimplifiedResult
)

# Import interface
from automagik.tools.omie.interface import (
    OmieTools,
    omie_tools
)

# Export public API
__all__ = [
    # Tool functions
    'search_clients',
    'search_client_by_cnpj',
    
    # Description functions
    'get_search_clients_description',
    'get_search_client_by_cnpj_description',
    
    # Schema models
    'ClientSearchInput',
    'ClientSearchResult',
    'ClientSimplifiedResult',
    
    # Interface
    'OmieTools',
    'omie_tools'
] 