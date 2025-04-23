"""Integration tests for Omie API tools.

These tests make real API calls to Omie and require valid credentials in environment variables:
- OMIE_APP_KEY
- OMIE_APP_SECRET
"""
import os
import pytest

from src.tools.omie.tool import search_clients, search_client_by_cnpj
from src.tools.omie.schema import ClientSearchInput

# Skip all tests if credentials are not set
pytestmark = pytest.mark.skipif(
    not os.getenv("OMIE_APP_KEY") or not os.getenv("OMIE_APP_SECRET"),
    reason="Omie credentials not set in environment variables"
)

@pytest.mark.asyncio
async def test_search_clients_integration():
    """Test searching clients with real API call."""
    # Create context
    ctx = {"agent_id": "test_agent"}
    
    # Create search input with email filter
    search_input = ClientSearchInput(
        email="nfe@kabum.com.br",  # Using a real email from the response
        pagina=1,
        registros_por_pagina=10
    )
    
    # Perform search
    result = await search_clients(ctx, search_input)
    
    # Verify basic response structure
    assert result["success"] is True
    assert "clients" in result["data"]
    assert "pagination" in result["data"]
    assert result["data"]["pagination"]["page"] == 1
    assert len(result["data"]["clients"]) > 0

@pytest.mark.asyncio
async def test_search_client_by_cnpj_integration():
    """Test searching client by CNPJ with real API call."""
    # Create context
    ctx = {"agent_id": "test_agent"}
    
    # Use a real CNPJ that exists in your Omie account
    cnpj = "05.570.714/0008-25"  # Using a real CNPJ from the response
    
    # Perform search
    result = await search_client_by_cnpj(ctx, cnpj)
    
    # Verify basic response structure
    assert result["success"] is True
    assert "client" in result
    assert result["client"]["cnpj_cpf"] == cnpj

@pytest.mark.asyncio
async def test_search_clients_pagination():
    """Test client search pagination."""
    # Create context
    ctx = {"agent_id": "test_agent"}
    
    # Search first page
    search_input_page1 = ClientSearchInput(
        pagina=1,
        registros_por_pagina=10,
        email="nfe@kabum.com.br"  # Adding a filter to ensure we get results
    )
    result_page1 = await search_clients(ctx, search_input_page1)
    
    # Search second page
    search_input_page2 = ClientSearchInput(
        pagina=2,
        registros_por_pagina=10,
        email="nfe@kabum.com.br"  # Same filter for consistency
    )
    result_page2 = await search_clients(ctx, search_input_page2)
    
    # Verify pagination
    assert result_page1["success"] is True
    assert result_page2["success"] is True
    assert result_page1["data"]["pagination"]["page"] == 1
    assert result_page2["data"]["pagination"]["page"] == 2
    
    # Verify different results if we have multiple pages
    if result_page1["data"]["pagination"]["total_pages"] > 1:
        page1_ids = [c["codigo_cliente_omie"] for c in result_page1["data"]["clients"]]
        page2_ids = [c["codigo_cliente_omie"] for c in result_page2["data"]["clients"]]
        assert not set(page1_ids).intersection(set(page2_ids))

@pytest.mark.asyncio
async def test_search_clients_filters():
    """Test different search filters."""
    # Create context
    ctx = {"agent_id": "test_agent"}
    
    # Test searching by company name
    search_by_name = ClientSearchInput(
        razao_social="KABUM",  # Using a real company name from the response
        pagina=1,
        registros_por_pagina=10
    )
    result_name = await search_clients(ctx, search_by_name)
    
    # Test searching by trade name
    search_by_trade = ClientSearchInput(
        nome_fantasia="KABUM",  # Using a real trade name from the response
        pagina=1,
        registros_por_pagina=10
    )
    result_trade = await search_clients(ctx, search_by_trade)
    
    # Verify both searches work
    assert result_name["success"] is True
    assert result_trade["success"] is True
    
    # Verify results contain the search terms if we got any results
    if result_name["data"]["pagination"]["total_records"] > 0:
        assert any(
            "KABUM".lower() in client["razao_social"].lower() 
            for client in result_name["data"]["clients"]
        )
    
    if result_trade["data"]["pagination"]["total_records"] > 0:
        assert any(
            "KABUM".lower() in client["nome_fantasia"].lower() 
            for client in result_trade["data"]["clients"]
        ) 