"""Unit tests for Omie API tools.

This module contains unit tests for the Omie API tools.
These tests mock the API calls to test the functionality without making real requests.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from automagik.tools.omie.tool import (
    search_clients,
    search_client_by_cnpj
)
from automagik.tools.omie.schema import (
    ClientSearchInput,
    ClientSearchResult,
    ClientSimplifiedResult
)

# Sample test data
SAMPLE_CLIENT = {
    "codigo_cliente_omie": 123456,
    "codigo_cliente_integracao": "TEST123",
    "cnpj_cpf": "12.345.678/0001-90",
    "razao_social": "Test Company",
    "nome_fantasia": "Test",
    "email": "test@example.com",
    "endereco": "Test Street",
    "endereco_numero": "123",
    "complemento": "Suite 1",
    "bairro": "Test District",
    "cidade": "Test City",
    "estado": "TS",
    "cep": "12345-678",
    "contato": "Test Contact",
    "inativo": "N",
    "data_cadastro": datetime.now().isoformat()
}

@pytest.mark.asyncio
async def test_search_clients_success():
    """Test successful client search."""
    # Create mock context
    ctx = MagicMock()
    
    # Create search input
    search_input = ClientSearchInput(
        email="test@example.com",
        pagina=1,
        registros_por_pagina=10
    )
    
    # Mock provider response
    mock_result = ClientSearchResult(
        success=True,
        data={
            "total_de_registros": 1,
            "total_de_paginas": 1,
            "pagina": 1,
            "registros_por_pagina": 10,
            "clients": [SAMPLE_CLIENT]
        }
    )
    
    # Mock provider
    with patch('automagik.tools.omie.tool.OmieProvider') as mock_provider:
        mock_instance = mock_provider.return_value
        mock_instance.search_clients = AsyncMock(return_value=mock_result)
        
        # Call function
        result = await search_clients(ctx, search_input)
        
        # Verify result
        assert result["success"] is True
        assert result["data"]["total_de_registros"] == 1
        assert len(result["data"]["clients"]) == 1
        assert result["data"]["clients"][0]["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_search_clients_error():
    """Test client search with error."""
    # Create mock context
    ctx = MagicMock()
    
    # Create search input
    search_input = ClientSearchInput(
        email="test@example.com",
        pagina=1,
        registros_por_pagina=10
    )
    
    # Mock provider error
    with patch('automagik.tools.omie.tool.OmieProvider') as mock_provider:
        mock_instance = mock_provider.return_value
        mock_instance.search_clients = AsyncMock(side_effect=Exception("API Error"))
        
        # Call function
        result = await search_clients(ctx, search_input)
        
        # Verify error result
        assert result["success"] is False
        assert "Error searching clients" in result["error"]

@pytest.mark.asyncio
async def test_search_client_by_cnpj_success():
    """Test successful client search by CNPJ."""
    # Create mock context
    ctx = MagicMock()
    
    # Mock provider response
    mock_result = ClientSimplifiedResult(
        success=True,
        client=SAMPLE_CLIENT
    )
    
    # Mock provider
    with patch('automagik.tools.omie.tool.OmieProvider') as mock_provider:
        mock_instance = mock_provider.return_value
        mock_instance.search_client_by_cnpj = AsyncMock(return_value=mock_result)
        
        # Call function
        result = await search_client_by_cnpj(ctx, "12.345.678/0001-90")
        
        # Verify result
        assert result["success"] is True
        assert result["client"]["cnpj_cpf"] == "12.345.678/0001-90"
        assert result["client"]["razao_social"] == "Test Company"

@pytest.mark.asyncio
async def test_search_client_by_cnpj_error():
    """Test client search by CNPJ with error."""
    # Create mock context
    ctx = MagicMock()
    
    # Mock provider error
    with patch('automagik.tools.omie.tool.OmieProvider') as mock_provider:
        mock_instance = mock_provider.return_value
        mock_instance.search_client_by_cnpj = AsyncMock(side_effect=Exception("API Error"))
        
        # Call function
        result = await search_client_by_cnpj(ctx, "12.345.678/0001-90")
        
        # Verify error result
        assert result["success"] is False
        assert "Error searching client by CNPJ" in result["error"] 