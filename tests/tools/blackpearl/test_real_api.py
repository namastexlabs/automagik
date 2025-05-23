"""Real API integration tests for Blackpearl API tools.

This script tests the Blackpearl API tools against a real API endpoint.
To run this test, make sure the BLACKPEARL_API_URL environment variable is set.

Example:
    BLACKPEARL_API_URL=http://api.example.com python -m pytest tests/tools/blackpearl/test_real_api.py -v
"""
import pytest
import os
import asyncio
import logging
from typing import Dict, Any

from src.tools.blackpearl import (
    get_clientes,
    get_cliente,
    get_contatos,
    get_contato,
    get_vendedores,
    get_vendedor,
    get_produtos,
    get_produto,
    get_pedidos,
    get_pedido,
    get_regras_frete,
    get_regra_frete,
    get_regras_negocio,
    get_regra_negocio
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sample context dictionary
ctx = {"agent_id": "test-agent"}

# Skip all tests if BLACKPEARL_API_URL is not set or if SKIP_REAL_API_TESTS is set
skip_real_api_tests = pytest.mark.skipif(
    not os.environ.get("BLACKPEARL_API_URL") or os.environ.get("SKIP_REAL_API_TESTS"),
    reason="BLACKPEARL_API_URL not set or SKIP_REAL_API_TESTS is set"
)

@skip_real_api_tests
@pytest.mark.asyncio
async def test_get_clientes():
    """Test get_clientes against real API."""
    logger.info("Testing get_clientes against real API")
    result = await get_clientes(ctx, limit=5)
    
    # Basic validation of response format
    assert isinstance(result, dict)
    assert "results" in result
    assert isinstance(result["results"], list)
    
    logger.info(f"Got {len(result['results'])} clients")
    return result

@skip_real_api_tests
@pytest.mark.asyncio
async def test_get_cliente():
    """Test get_cliente against real API."""
    # First get a list of clients to find an ID
    clients_result = await get_clientes(ctx, limit=1)
    
    if not clients_result["results"]:
        pytest.skip("No clients available to test get_cliente")
        
    client_id = clients_result["results"][0]["id"]
    logger.info(f"Testing get_cliente with ID {client_id}")
    
    result = await get_cliente(ctx, client_id)
    
    # Basic validation of response format - get_cliente returns a Cliente Pydantic model
    from src.tools.blackpearl.schema import Cliente
    assert isinstance(result, Cliente)
    assert result.id == client_id
    
    logger.info(f"Got client: {result.razao_social}")
    return result

@skip_real_api_tests
@pytest.mark.asyncio
async def test_get_contatos():
    """Test get_contatos against real API."""
    logger.info("Testing get_contatos against real API")
    result = await get_contatos(ctx, limit=5)
    
    # Basic validation of response format
    assert isinstance(result, dict)
    assert "results" in result
    assert isinstance(result["results"], list)
    
    logger.info(f"Got {len(result['results'])} contacts")
    return result

@skip_real_api_tests
@pytest.mark.asyncio
async def test_get_contato():
    """Test get_contato against real API."""
    # First get a list of contacts to find an ID
    contacts_result = await get_contatos(ctx, limit=1)
    
    if not contacts_result["results"]:
        pytest.skip("No contacts available to test get_contato")
        
    contact_id = contacts_result["results"][0]["id"]
    logger.info(f"Testing get_contato with ID {contact_id}")
    
    result = await get_contato(ctx, contact_id)
    
    # Basic validation of response format - get_contato returns a Contato Pydantic model
    from src.tools.blackpearl.schema import Contato
    assert isinstance(result, Contato)
    assert result.id == contact_id
    
    logger.info(f"Got contact: {result.nome}")
    return result

@skip_real_api_tests
@pytest.mark.asyncio
async def test_get_vendedores():
    """Test get_vendedores against real API."""
    logger.info("Testing get_vendedores against real API")
    result = await get_vendedores(ctx, limit=5)
    
    # Basic validation of response format
    assert isinstance(result, dict)
    assert "results" in result
    assert isinstance(result["results"], list)
    
    logger.info(f"Got {len(result['results'])} salespeople")
    return result

@skip_real_api_tests
@pytest.mark.asyncio
async def test_get_vendedor():
    """Test get_vendedor against real API."""
    # First get a list of salespeople to find an ID
    salespeople_result = await get_vendedores(ctx, limit=1)
    
    if not salespeople_result["results"]:
        pytest.skip("No salespeople available to test get_vendedor")
        
    salesperson_id = salespeople_result["results"][0]["id"]
    logger.info(f"Testing get_vendedor with ID {salesperson_id}")
    
    result = await get_vendedor(ctx, salesperson_id)
    
    # Basic validation of response format
    assert isinstance(result, dict)
    assert "id" in result
    assert result["id"] == salesperson_id
    
    logger.info(f"Got salesperson: {result.get('nome', '')}")
    return result

@skip_real_api_tests
@pytest.mark.asyncio
async def test_get_produtos():
    """Test get_produtos against real API."""
    logger.info("Testing get_produtos against real API")
    result = await get_produtos(ctx, limit=5)
    
    # Basic validation of response format
    assert isinstance(result, dict)
    assert "results" in result
    assert isinstance(result["results"], list)
    
    logger.info(f"Got {len(result['results'])} products")
    return result

@skip_real_api_tests
@pytest.mark.asyncio
async def test_get_produto():
    """Test get_produto against real API."""
    # First get a list of products to find an ID
    products_result = await get_produtos(ctx, limit=1)
    
    if not products_result["results"]:
        pytest.skip("No products available to test get_produto")
        
    product_id = products_result["results"][0]["id"]
    logger.info(f"Testing get_produto with ID {product_id}")
    
    result = await get_produto(ctx, product_id)
    
    # Basic validation of response format
    assert isinstance(result, dict)
    assert "id" in result
    assert result["id"] == product_id
    
    logger.info(f"Got product: {result.get('nome', '')}")
    return result

@skip_real_api_tests
@pytest.mark.asyncio
async def test_get_pedidos():
    """Test get_pedidos against real API."""
    logger.info("Testing get_pedidos against real API")
    result = await get_pedidos(ctx, limit=5)
    
    # Basic validation of response format
    assert isinstance(result, dict)
    assert "results" in result
    assert isinstance(result["results"], list)
    
    logger.info(f"Got {len(result['results'])} orders")
    return result

@skip_real_api_tests
@pytest.mark.asyncio
async def test_get_pedido():
    """Test get_pedido against real API."""
    # First get a list of orders to find an ID
    orders_result = await get_pedidos(ctx, limit=1)
    
    if not orders_result["results"]:
        pytest.skip("No orders available to test get_pedido")
        
    order_id = orders_result["results"][0]["id"]
    logger.info(f"Testing get_pedido with ID {order_id}")
    
    result = await get_pedido(ctx, order_id)
    
    # Basic validation of response format
    assert isinstance(result, dict)
    assert "id" in result
    assert result["id"] == order_id
    
    logger.info(f"Got order: {result.get('numero', '')}")
    return result

@skip_real_api_tests
@pytest.mark.asyncio
async def test_get_regras_frete():
    """Test get_regras_frete against real API."""
    logger.info("Testing get_regras_frete against real API")
    result = await get_regras_frete(ctx, limit=5)
    
    # Basic validation of response format
    assert isinstance(result, dict)
    assert "results" in result
    assert isinstance(result["results"], list)
    
    logger.info(f"Got {len(result['results'])} shipping rules")
    return result

@skip_real_api_tests
@pytest.mark.asyncio
async def test_get_regra_frete():
    """Test get_regra_frete against real API."""
    # First get a list of shipping rules to find an ID
    rules_result = await get_regras_frete(ctx, limit=1)
    
    if not rules_result["results"]:
        pytest.skip("No shipping rules available to test get_regra_frete")
        
    rule_id = rules_result["results"][0]["id"]
    logger.info(f"Testing get_regra_frete with ID {rule_id}")
    
    result = await get_regra_frete(ctx, rule_id)
    
    # Basic validation of response format
    assert isinstance(result, dict)
    assert "id" in result
    assert result["id"] == rule_id
    
    logger.info(f"Got shipping rule: {result.get('nome', '')}")
    return result

@skip_real_api_tests
@pytest.mark.asyncio
async def test_get_regras_negocio():
    """Test get_regras_negocio against real API."""
    logger.info("Testing get_regras_negocio against real API")
    result = await get_regras_negocio(ctx, limit=5)
    
    # Basic validation of response format
    assert isinstance(result, dict)
    assert "results" in result
    assert isinstance(result["results"], list)
    
    logger.info(f"Got {len(result['results'])} business rules")
    return result

@skip_real_api_tests
@pytest.mark.asyncio
async def test_get_regra_negocio():
    """Test get_regra_negocio against real API."""
    # First get a list of business rules to find an ID
    rules_result = await get_regras_negocio(ctx, limit=1)
    
    if not rules_result["results"]:
        pytest.skip("No business rules available to test get_regra_negocio")
        
    rule_id = rules_result["results"][0]["id"]
    logger.info(f"Testing get_regra_negocio with ID {rule_id}")
    
    result = await get_regra_negocio(ctx, rule_id)
    
    # Basic validation of response format
    assert isinstance(result, dict)
    assert "id" in result
    assert result["id"] == rule_id
    
    logger.info(f"Got business rule: {result.get('nome', '')}")
    return result

@skip_real_api_tests
@pytest.mark.asyncio
async def test_search_functionality():
    """Test search functionality in get_clientes."""
    logger.info("Testing search functionality in get_clientes")
    
    # First get a list of clients to find a name to search for
    clients_result = await get_clientes(ctx, limit=1)
    
    if not clients_result["results"]:
        pytest.skip("No clients available to test search functionality")
        
    client_name = clients_result["results"][0]["razao_social"]  # Use razao_social instead of nome
    # Take just the first word to increase search results
    search_term = client_name.split()[0] if ' ' in client_name else client_name[:3]
    
    logger.info(f"Searching for clients with term: '{search_term}'")
    
    search_result = await get_clientes(ctx, search=search_term)
    
    # Basic validation of response format
    assert isinstance(search_result, dict)
    assert "results" in search_result
    assert isinstance(search_result["results"], list)
    
    logger.info(f"Found {len(search_result['results'])} clients matching search term")
    
    # Verify at least one result contains the search term
    if search_result["results"]:
        found = False
        for client in search_result["results"]:
            # Check both razao_social and nome_fantasia for the search term
            if (search_term.lower() in client.get("razao_social", "").lower() or 
                search_term.lower() in client.get("nome_fantasia", "").lower()):
                found = True
                break
        
        assert found, f"No clients found with search term '{search_term}' in their name"

@skip_real_api_tests
@pytest.mark.asyncio
async def test_ordering_functionality():
    """Test ordering functionality in get_clientes."""
    logger.info("Testing ordering functionality in get_clientes")
    
    # Get clients ordered by name ascending
    asc_result = await get_clientes(ctx, ordering="nome", limit=10)
    
    # Get clients ordered by name descending
    desc_result = await get_clientes(ctx, ordering="-nome", limit=10)
    
    # Basic validation of response format
    assert isinstance(asc_result, dict)
    assert isinstance(desc_result, dict)
    assert "results" in asc_result
    assert "results" in desc_result
    
    # Skip further checks if not enough results
    if len(asc_result["results"]) < 2 or len(desc_result["results"]) < 2:
        pytest.skip("Not enough clients to test ordering")
    
    # Check that the ordering is different
    asc_names = [client["nome"] for client in asc_result["results"]]
    desc_names = [client["nome"] for client in desc_result["results"]]
    
    logger.info(f"Ascending order: {asc_names[:3]} ...")
    logger.info(f"Descending order: {desc_names[:3]} ...")
    
    # Verify that the first items are in different order
    assert asc_names[0] != desc_names[0], "Ordering functionality doesn't appear to work"
    
    # Check if ascending is actually ascending
    for i in range(len(asc_names) - 1):
        if asc_names[i] > asc_names[i + 1]:
            logger.warning(f"Ascending order may not be working correctly: {asc_names[i]} > {asc_names[i + 1]}")
            break
            
    # Check if descending is actually descending
    for i in range(len(desc_names) - 1):
        if desc_names[i] < desc_names[i + 1]:
            logger.warning(f"Descending order may not be working correctly: {desc_names[i]} < {desc_names[i + 1]}")
            break

@skip_real_api_tests
@pytest.mark.asyncio
async def test_pagination():
    """Test pagination functionality."""
    logger.info("Testing pagination functionality")
    
    # Get first page with limit 3
    page1 = await get_clientes(ctx, limit=3, offset=0)
    
    # Get second page with limit 3
    page2 = await get_clientes(ctx, limit=3, offset=3)
    
    # Basic validation of response format
    assert isinstance(page1, dict)
    assert isinstance(page2, dict)
    assert "results" in page1
    assert "results" in page2
    
    # Skip further checks if not enough results
    if len(page1["results"]) < 3:
        pytest.skip("Not enough clients to test pagination")
    
    # Check that the pages have different results
    page1_ids = [client["id"] for client in page1["results"]]
    page2_ids = [client["id"] for client in page2["results"]]
    
    logger.info(f"Page 1 IDs: {page1_ids}")
    logger.info(f"Page 2 IDs: {page2_ids}")
    
    # Check for overlap
    overlap = set(page1_ids).intersection(set(page2_ids))
    assert not overlap, f"Pagination doesn't work correctly, found overlapping IDs: {overlap}" 