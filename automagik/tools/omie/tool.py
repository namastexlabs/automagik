"""Omie API tool implementation.

This module provides the core functionality for Omie API tools.
"""
import logging
from typing import Dict, Any
from pydantic_ai import RunContext

from .schema import ClientSearchInput, ClientSearchResult, ClientSimplifiedResult
from .provider import OmieProvider

logger = logging.getLogger(__name__)

def get_search_clients_description() -> str:
    """Get description for the search_clients function."""
    return "Search for clients in Omie with various search options."

def get_search_client_by_cnpj_description() -> str:
    """Get description for the search_client_by_cnpj function."""
    return "Search for a client by CNPJ in Omie."

def get_curl_example_description() -> str:
    """Get description for the get_curl_example function."""
    return "Get a cURL example for the Omie API."

async def search_clients(ctx: RunContext[Dict], input: ClientSearchInput) -> Dict[str, Any]:
    """Search for clients in Omie API.
    
    Args:
        ctx: The run context
        input: Search parameters
        
    Returns:
        Dict with search results
    """
    logger.info(f"Searching clients in Omie: {input}")
    
    try:
        # Create provider instance
        provider = OmieProvider()
        
        # Use provider to search clients
        result = await provider.search_clients(input)
        
        # Return the result as a dictionary
        return result.model_dump()
    except Exception as e:
        error_msg = f"Error searching clients: {str(e)}"
        logger.error(error_msg)
        
        response = ClientSearchResult(
            success=False,
            error=error_msg
        )
        return response.model_dump()

async def search_client_by_cnpj(ctx: RunContext[Dict], cnpj: str) -> Dict[str, Any]:
    """Search for a client by CNPJ in Omie API.
    
    Args:
        ctx: The run context
        cnpj: The CNPJ to search for
        
    Returns:
        Dict with client information
    """
    logger.info(f"Searching client by CNPJ in Omie: {cnpj}")
    
    try:
        # Create provider instance
        provider = OmieProvider()
        
        # Use provider to search client by CNPJ
        result = await provider.search_client_by_cnpj(cnpj)
        
        # Return the result as a dictionary
        return result.model_dump()
    except Exception as e:
        error_msg = f"Error searching client by CNPJ: {str(e)}"
        logger.error(error_msg)
        
        response = ClientSimplifiedResult(
            success=False,
            error=error_msg
        )
        return response.model_dump()

def get_curl_example() -> Dict[str, Any]:
    """Provides a curl example for the Omie API.
    
    Returns:
        Dictionary with curl request and response examples
    """
    # Example request
    request_example = '''
curl --location 'https://app.omie.com.br/api/v1/geral/clientes/' \\
--header 'Content-Type: application/json' \\
--data-raw '{
  "call": "ListarClientes",
  "app_key": 1123855542810,
  "app_secret": "5e75b85418f326158d712fb7a543cb95",
  "param": [
    {
      "pagina": 1,
      "registros_por_pagina": 50,
      "apenas_importado_api": "N",
      "clientesFiltro": {
        "email": "marcosjsh@gmail.com"
      }
    }
  ]
}'
'''

    # Example response (truncated for brevity)
    response_example = '''
{
    "pagina": 1,
    "total_de_paginas": 174,
    "registros": 50,
    "total_de_registros": 8698,
    "clientes_cadastro": [
        {
            "bairro": "FAZENDA VELHA",
            "bloquear_faturamento": "N",
            "cep": "83704580",
            "cidade": "ARAUCARIA (PR)",
            "cidade_ibge": "4101804",
            "cnpj_cpf": "12.513.084/0001-46",
            "codigo_cliente_integracao": "44",
            "codigo_cliente_omie": 1128334562,
            "codigo_pais": "1058",
            "complemento": "SALA 01",
            "contato": "Bruno",
            "contribuinte": "S",
            "email": "boletos@shopb.com.br,bruno@shopb.com.br",
            "endereco": "IRMA ELIZABETH WERKA",
            "endereco_numero": "176",
            "estado": "PR",
            "exterior": "N",
            "inativo": "N",
            "inscricao_estadual": "90532588-48",
            "nome_fantasia": "SHOP B ARACAURIA PR",
            "optante_simples_nacional": "N",
            "pessoa_fisica": "N",
            "razao_social": "SHOP B COMERCIO VIRTUAL LTDA"
        }
        // ... more clients would be listed here
    ]
}
'''

    # Example of how to use the tool
    tool_usage_example = '''
# Example of using the Omie tools:

from automagik.tools.omie import search_clients
from automagik.tools.omie.schema import ClientSearchInput

# Create search input
search_input = ClientSearchInput(
    email="example@example.com",
    pagina=1,
    registros_por_pagina=50
)

# Perform search
result = await search_clients(ctx, search_input)

# Check results
if result["success"]:
    clients = result["data"]["clients"]
    print(f"Found {len(clients)} clients")
else:
    print(f"Error: {result['error']}")
'''

    # Return all examples
    return {
        "curl_request": request_example,
        "curl_response": response_example,
        "tool_usage": tool_usage_example,
        "api_endpoint": "https://app.omie.com.br/api/v1/geral/clientes/",
        "common_search_filters": {
            "codigo_cliente_omie": "Search by Omie client code",
            "codigo_cliente_integracao": "Search by integration client code",
            "cnpj_cpf": "Search by CNPJ/CPF",
            "email": "Search by email",
            "razao_social": "Search by company name",
            "nome_fantasia": "Search by trade name"
        }
    } 