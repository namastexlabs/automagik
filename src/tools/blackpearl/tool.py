"""Blackpearl API tools.

This module provides tools for interacting with the Blackpearl API.
"""
import logging
import os
from typing import Optional, Dict, Any, List, Union
from src.config import Environment, settings
from src.tools.blackpearl.provider import BlackpearlProvider
from src.tools.blackpearl.schema import (
    Cliente, Contato, Vendedor, Produto, PedidoDeVenda, ItemDePedido,
    RegraDeFrete, RegraDeNegocio, ItemDePedidoCreate
)

logger = logging.getLogger(__name__)

async def get_clientes(
    ctx: Dict[str, Any],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    search: Optional[str] = None,
    ordering: Optional[str] = None,
    **filters
) -> Dict[str, Any]:
    """Get list of clients from the Blackpearl API.
    
    Args:
        ctx: Agent context
        limit: Number of results to return
        offset: Starting position
        search: Search term
        ordering: Order by field
        **filters: Additional filters
        
    Returns:
        List of clients
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_clientes(limit, offset, search, ordering, **filters)

async def get_cliente(ctx: Dict[str, Any], cliente_id: int) -> Cliente:
    """Get a specific client from the Blackpearl API.
    
    Args:
        ctx: Agent context
        cliente_id: Client ID
        
    Returns:
        Client data
    """
    provider = BlackpearlProvider()
    async with provider:
        cliente = await provider.get_cliente(cliente_id)
        return Cliente(**cliente)

async def create_cliente(ctx: Dict[str, Any], cliente: Cliente) -> Dict[str, Any]:
    """Create a new client in the Blackpearl API.
    
    Args:
        ctx: Agent context
        cliente: Client data
        
    Returns:
        Created client data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.create_cliente(cliente)

async def update_cliente(ctx: Dict[str, Any], cliente_id: int, cliente: Cliente) -> Dict[str, Any]:
    """Update a client in the Blackpearl API.
    
    Args:
        ctx: Agent context
        cliente_id: Client ID
        cliente: Updated client data
        
    Returns:
        Updated client data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.update_cliente(cliente_id, cliente)

async def delete_cliente(ctx: Dict[str, Any], cliente_id: int) -> None:
    """Delete a client from the Blackpearl API.
    
    Args:
        ctx: Agent context
        cliente_id: Client ID
    """
    provider = BlackpearlProvider()
    async with provider:
        await provider.delete_cliente(cliente_id)

async def get_contatos(
    ctx: Dict[str, Any],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    search: Optional[str] = None,
    ordering: Optional[str] = None
) -> Dict[str, Any]:
    """Get list of contacts from the Blackpearl API.
    
    Args:
        ctx: Agent context
        limit: Number of results to return
        offset: Starting position
        search: Search term
        ordering: Order by field
        
    Returns:
        List of contacts
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_contatos(limit, offset, search, ordering)

async def get_contato(ctx: Dict[str, Any], contato_id: int) -> Contato:
    """Get a specific contact from the Blackpearl API.
    
    Args:
        ctx: Agent context
        contato_id: Contact ID
        
    Returns:
        Contact data
    """
    provider = BlackpearlProvider()
    async with provider:
        contato = await provider.get_contato(contato_id)
        return Contato(**contato)

async def create_contato(ctx: Dict[str, Any], contato: Union[Contato, Dict[str, Any]]) -> Dict[str, Any]:
    """Create a new contact in the Blackpearl API.
    
    Args:
        ctx: Agent context
        contato: Contact data (either a Contato object or a dictionary)
        
    Returns:
        Created contact data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.create_contato(contato)

async def update_contato(ctx: Dict[str, Any], contato_id: int, contato: Contato) -> Dict[str, Any]:
    """Update a contact in the Blackpearl API.
    
    Args:
        ctx: Agent context
        contato_id: Contact ID
        contato: Updated contact data
        
    Returns:
        Updated contact data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.update_contato(contato_id, contato)

async def delete_contato(ctx: Dict[str, Any], contato_id: int) -> None:
    """Delete a contact from the Blackpearl API.
    
    Args:
        ctx: Agent context
        contato_id: Contact ID
    """
    provider = BlackpearlProvider()
    async with provider:
        await provider.delete_contato(contato_id)

async def get_vendedores(
    ctx: Dict[str, Any],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    search: Optional[str] = None,
    ordering: Optional[str] = None
) -> Dict[str, Any]:
    """Get list of salespeople from the Blackpearl API.
    
    Args:
        ctx: Agent context
        limit: Number of results to return
        offset: Starting position
        search: Search term
        ordering: Order by field
        
    Returns:
        List of salespeople
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_vendedores(limit, offset, search, ordering)

async def get_vendedor(ctx: Dict[str, Any], vendedor_id: int) -> Dict[str, Any]:
    """Get a specific salesperson from the Blackpearl API.
    
    Args:
        ctx: Agent context
        vendedor_id: Salesperson ID
        
    Returns:
        Salesperson data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_vendedor(vendedor_id)

async def create_vendedor(ctx: Dict[str, Any], vendedor: Vendedor) -> Dict[str, Any]:
    """Create a new salesperson in the Blackpearl API.
    
    Args:
        ctx: Agent context
        vendedor: Salesperson data
        
    Returns:
        Created salesperson data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.create_vendedor(vendedor)

async def update_vendedor(ctx: Dict[str, Any], vendedor_id: int, vendedor: Vendedor) -> Dict[str, Any]:
    """Update a salesperson in the Blackpearl API.
    
    Args:
        ctx: Agent context
        vendedor_id: Salesperson ID
        vendedor: Updated salesperson data
        
    Returns:
        Updated salesperson data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.update_vendedor(vendedor_id, vendedor)

async def get_produtos(
    ctx: Dict[str, Any],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    search: Optional[str] = None,
    ordering: Optional[str] = None,
    **filters
) -> Dict[str, Any]:
    """Get list of products from the Blackpearl API.
    
    Args:
        ctx: Agent context
        limit: Number of results to return
        offset: Starting position
        search: Search term
        ordering: Order by field
        **filters: Additional filters
        
    Returns:
        List of products
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_produtos(limit, offset, search, ordering, **filters)

async def get_produto(ctx: Dict[str, Any], produto_id: int) -> Dict[str, Any]:
    """Get a specific product from the Blackpearl API.
    
    Args:
        ctx: Agent context
        produto_id: Product ID
        
    Returns:
        Product data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_produto(produto_id)

async def get_familias_de_produtos(
    ctx: Dict[str, Any],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    search: Optional[str] = None,
    ordering: Optional[str] = None,
    **filters
) -> Dict[str, Any]:
    """Get list of product families from the Blackpearl API.
    
    Args:
        ctx: Agent context
        limit: Number of results to return
        offset: Starting position
        search: Search term
        ordering: Order by field
        **filters: Additional filters
        
    Returns:
        List of product families
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_familias_de_produtos(limit, offset, search, ordering, **filters)

async def get_familia_de_produto(ctx: Dict[str, Any], familia_id: int) -> Dict[str, Any]:
    """Get a specific product family from the Blackpearl API.
    
    Args:
        ctx: Agent context
        familia_id: Product family ID
        
    Returns:
        Product family data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_familia_de_produto(familia_id)

async def get_marcas(
    ctx: Dict[str, Any],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    search: Optional[str] = None,
    ordering: Optional[str] = None,
    **filters
) -> Dict[str, Any]:
    """Get list of brands from the Blackpearl API.
    
    Args:
        ctx: Agent context
        limit: Number of results to return
        offset: Starting position
        search: Search term
        ordering: Order by field
        **filters: Additional filters
        
    Returns:
        List of brands
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_marcas(limit, offset, search, ordering, **filters)

async def get_marca(ctx: Dict[str, Any], marca_id: int) -> Dict[str, Any]:
    """Get a specific brand from the Blackpearl API.
    
    Args:
        ctx: Agent context
        marca_id: Brand ID
        
    Returns:
        Brand data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_marca(marca_id)

async def get_imagens_de_produto(
    ctx: Dict[str, Any],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    search: Optional[str] = None,
    ordering: Optional[str] = None,
    **filters
) -> Dict[str, Any]:
    """Get list of product images from the Blackpearl API.
    
    Args:
        ctx: Agent context
        limit: Number of results to return
        offset: Starting position
        search: Search term
        ordering: Order by field
        **filters: Additional filters
        
    Returns:
        List of product images
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_imagens_de_produto(limit, offset, search, ordering, **filters)

async def get_pedidos(
    ctx: Dict[str, Any],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    search: Optional[str] = None,
    ordering: Optional[str] = None
) -> Dict[str, Any]:
    """Get list of orders from the Blackpearl API.
    
    Args:
        ctx: Agent context
        limit: Number of results to return
        offset: Starting position
        search: Search term
        ordering: Order by field
        
    Returns:
        List of orders
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_pedidos(limit, offset, search, ordering)

async def get_pedido(ctx: Dict[str, Any], pedido_id: int) -> Dict[str, Any]:
    """Get a specific order from the Blackpearl API.
    
    Args:
        ctx: Agent context
        pedido_id: Order ID
        
    Returns:
        Order data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_pedido(pedido_id)

async def create_pedido(ctx: Dict[str, Any], pedido: PedidoDeVenda) -> Dict[str, Any]:
    """Create a new order in the Blackpearl API.
    
    Args:
        ctx: Agent context
        pedido: Order data
        
    Returns:
        Created order data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.create_pedido(pedido)

async def update_pedido(ctx: Dict[str, Any], pedido_id: int, pedido: PedidoDeVenda) -> Dict[str, Any]:
    """Update an order in the Blackpearl API.
    
    Args:
        ctx: Agent context
        pedido_id: Order ID
        pedido: Updated order data
        
    Returns:
        Updated order data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.update_pedido(pedido_id, pedido)

async def get_regras_frete(
    ctx: Dict[str, Any],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    search: Optional[str] = None,
    ordering: Optional[str] = None
) -> Dict[str, Any]:
    """Get list of shipping rules from the Blackpearl API.
    
    Args:
        ctx: Agent context
        limit: Number of results to return
        offset: Starting position
        search: Search term
        ordering: Order by field
        
    Returns:
        List of shipping rules
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_regras_frete(limit, offset, search, ordering)

async def get_regra_frete(ctx: Dict[str, Any], regra_id: int) -> Dict[str, Any]:
    """Get a specific shipping rule from the Blackpearl API.
    
    Args:
        ctx: Agent context
        regra_id: Shipping rule ID
        
    Returns:
        Shipping rule data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_regra_frete(regra_id)

async def create_regra_frete(ctx: Dict[str, Any], regra: RegraDeFrete) -> Dict[str, Any]:
    """Create a new shipping rule in the Blackpearl API.
    
    Args:
        ctx: Agent context
        regra: Shipping rule data
        
    Returns:
        Created shipping rule data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.create_regra_frete(regra)

async def update_regra_frete(ctx: Dict[str, Any], regra_id: int, regra: RegraDeFrete) -> Dict[str, Any]:
    """Update a shipping rule in the Blackpearl API.
    
    Args:
        ctx: Agent context
        regra_id: Shipping rule ID
        regra: Updated shipping rule data
        
    Returns:
        Updated shipping rule data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.update_regra_frete(regra_id, regra)

async def get_regras_negocio(
    ctx: Dict[str, Any],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    search: Optional[str] = None,
    ordering: Optional[str] = None
) -> Dict[str, Any]:
    """Get list of business rules from the Blackpearl API.
    
    Args:
        ctx: Agent context
        limit: Number of results to return
        offset: Starting position
        search: Search term
        ordering: Order by field
        
    Returns:
        List of business rules
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_regras_negocio(limit, offset, search, ordering)

async def get_regra_negocio(ctx: Dict[str, Any], regra_id: int) -> Dict[str, Any]:
    """Get a specific business rule from the Blackpearl API.
    
    Args:
        ctx: Agent context
        regra_id: Business rule ID
        
    Returns:
        Business rule data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_regra_negocio(regra_id)

async def create_regra_negocio(ctx: Dict[str, Any], regra: RegraDeNegocio) -> Dict[str, Any]:
    """Create a new business rule in the Blackpearl API.
    
    Args:
        ctx: Agent context
        regra: Business rule data
        
    Returns:
        Created business rule data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.create_regra_negocio(regra)

async def update_regra_negocio(ctx: Dict[str, Any], regra_id: int, regra: RegraDeNegocio) -> Dict[str, Any]:
    """Update a business rule in the Blackpearl API.
    
    Args:
        ctx: Agent context
        regra_id: Business rule ID
        regra: Updated business rule data
        
    Returns:
        Updated business rule data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.update_regra_negocio(regra_id, regra)

async def verificar_cnpj(ctx: Dict[str, Any], cnpj: str) -> Dict[str, Any]:
    """Verify a CNPJ in the Blackpearl API.
    
    Args:
        ctx: Agent context
        cnpj: The CNPJ number to verify (format: xx.xxx.xxx/xxxx-xx or clean numbers)
        
    Returns:
        CNPJ verification result containing validation status and company information if valid
    """
    provider = BlackpearlProvider()
    async with provider:
        print(f"Verifying CNPJ: {cnpj}")
        verification_result = await provider.verificar_cnpj(cnpj)
        
        # Create a modified result without status and reason fields if they exist
        # Only remove these fields in development environment
        
        if isinstance(verification_result, dict) and settings.AM_ENV == Environment.DEVELOPMENT:
            if 'status' in verification_result:
                verification_result.pop('status', None)
            if 'reason' in verification_result:
                verification_result.pop('reason', None)
                
        return verification_result

async def finalizar_cadastro(ctx: Dict[str, Any], cliente_id: int) -> Dict[str, Any]:
    """Finalize client registration in Omie API.
    
    Args:
        ctx: Agent context
        cliente_id: Client ID
        
    Returns:
        Registration result with codigo_cliente_omie
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.finalizar_cadastro(cliente_id)

# --- PedidoDeVenda Tools ---

async def create_order_tool(ctx: Dict[str, Any], pedido: PedidoDeVenda) -> Dict[str, Any]:
    """Creates a new sales order draft in Blackpearl.
    
    Args:
        ctx: The context dictionary (unused currently).
        pedido: The sales order data conforming to the PedidoDeVenda schema.
            Make sure to include required fields like 'cliente', 'vendedor',
            and set 'status_negociacao' to 'rascunho'.
            
    Returns:
        A dictionary containing the created sales order data, including its ID.
    """
    async with BlackpearlProvider() as provider:
        result = await provider.create_pedido_venda(pedido=pedido)
        return result

async def get_order_tool(ctx: Dict[str, Any], pedido_id: int) -> Dict[str, Any]:
    """Retrieves details of a specific sales order from Blackpearl.
    
    Args:
        ctx: The context dictionary (unused currently).
        pedido_id: The unique ID of the sales order to retrieve.
        
    Returns:
        A dictionary containing the details of the specified sales order.
    """
    async with BlackpearlProvider() as provider:
        result = await provider.get_pedido_venda(pedido_id=pedido_id)
        return result

async def list_orders_tool(
    ctx: Dict[str, Any],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    search: Optional[str] = None,
    ordering: Optional[str] = None,
    cliente_id: Optional[int] = None,
    status_negociacao: Optional[str] = None,
) -> Dict[str, Any]:
    """Lists sales orders from Blackpearl, with optional filtering and pagination.
    
    Args:
        ctx: The context dictionary (unused currently).
        limit: Maximum number of orders to return.
        offset: Starting index for pagination.
        search: A search term to filter orders.
        ordering: Field to sort the orders by (e.g., 'id', '-data_emissao').
        cliente_id: Filter orders by a specific client ID.
        status_negociacao: Filter orders by negotiation status (e.g., 'rascunho', 'aprovado').
        
    Returns:
        A dictionary containing a list of sales orders and pagination details.
    """
    filters = {}
    if cliente_id:
        filters['cliente_id'] = cliente_id
    if status_negociacao:
        filters['status_negociacao'] = status_negociacao
        
    async with BlackpearlProvider() as provider:
        result = await provider.list_pedidos_venda(
            limit=limit, offset=offset, search=search, ordering=ordering, **filters
        )
        return result

async def update_order_tool(ctx: Dict[str, Any], pedido_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """Updates specific fields of an existing sales order in Blackpearl.
    
    Args:
        ctx: The context dictionary (unused currently).
        pedido_id: The ID of the sales order to update.
        update_data: A dictionary containing the fields and new values to update
                     (e.g., {'pagamento': 1, 'observacao': 'Updated note'}).
                     Only include fields that need to be changed.
                     
    Returns:
        A dictionary containing the updated sales order data.
    """
    async with BlackpearlProvider() as provider:
        result = await provider.update_pedido_venda(pedido_id=pedido_id, pedido_data=update_data)
        return result

async def approve_order_tool(ctx: Dict[str, Any], pedido_id: int) -> Dict[str, Any]:
    """Approves a sales order in Blackpearl, potentially triggering integration (e.g., Omie).
    
    Args:
        ctx: The context dictionary (unused currently).
        pedido_id: The ID of the sales order to approve.
        
    Returns:
        A dictionary containing the result of the approval process.
    """
    async with BlackpearlProvider() as provider:
        result = await provider.aprovar_pedido(pedido_id=pedido_id)
        return result

# --- ItemDePedido Tools ---

async def add_item_to_order_tool(ctx: Dict[str, Any], item_data: ItemDePedidoCreate) -> Dict[str, Any]:
    """Adds a new item to a specific sales order in Blackpearl.
    
    Args:
        ctx: The context dictionary (unused currently).
        item_data: The order item data conforming to the ItemDePedidoCreate schema.
                   Must include 'pedido' (the order ID), 'produto' (the product ID),
                   'quantidade', and 'valor_unitario' (as string, e.g., "100.00").
                   'desconto' (string) and 'porcentagem_desconto' (float) are optional.
              
    Returns:
        A dictionary containing the created order item data, including its ID.
    """
    async with BlackpearlProvider() as provider:
        result = await provider.create_pedido_item(item=item_data)
        return result

async def get_order_item_tool(ctx: Dict[str, Any], item_id: int) -> Dict[str, Any]:
    """Retrieves details of a specific item within a sales order from Blackpearl.
    
    Args:
        ctx: The context dictionary (unused currently).
        item_id: The unique ID of the order item to retrieve.
        
    Returns:
        A dictionary containing the details of the specified order item.
    """
    async with BlackpearlProvider() as provider:
        result = await provider.get_pedido_item(item_id=item_id)
        return result

async def list_order_items_tool(
    ctx: Dict[str, Any],
    pedido_id: Optional[int] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    search: Optional[str] = None,
    ordering: Optional[str] = None,
) -> Dict[str, Any]:
    """Lists items associated with sales orders from Blackpearl.
    Can optionally filter by a specific order ID.
    
    Args:
        ctx: The context dictionary (unused currently).
        pedido_id: (Optional) The ID of the sales order to list items for.
        limit: Maximum number of items to return.
        offset: Starting index for pagination.
        search: A search term to filter items (e.g., by product name/code).
        ordering: Field to sort the items by.
        
    Returns:
        A dictionary containing a list of order items and pagination details.
    """
    async with BlackpearlProvider() as provider:
        result = await provider.list_pedido_items(
            pedido_id=pedido_id, limit=limit, offset=offset, search=search, ordering=ordering
        )
        return result

async def update_order_item_tool(ctx: Dict[str, Any], item_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """Updates specific fields of an existing item within a sales order in Blackpearl.
    
    Args:
        ctx: The context dictionary (unused currently).
        item_id: The ID of the order item to update.
        update_data: A dictionary containing the fields and new values to update
                     (e.g., {'quantidade': 10, 'valor_unitario': 9.99}).
                     Only include fields that need to be changed.
                     
    Returns:
        A dictionary containing the updated order item data.
    """
    async with BlackpearlProvider() as provider:
        result = await provider.update_pedido_item(item_id=item_id, item_data=update_data)
        return result

async def delete_order_item_tool(ctx: Dict[str, Any], item_id: int) -> Dict[str, Any]:
    """Deletes an item from a sales order in Blackpearl.
    
    Args:
        ctx: The context dictionary (unused currently).
        item_id: The ID of the order item to delete.
        
    Returns:
        A confirmation dictionary, often empty on success (depends on API response).
    """
    # Provider method returns None on success (204), tool should probably return confirmation.
    async with BlackpearlProvider() as provider:
        await provider.delete_pedido_item(item_id=item_id)
        return {"status": "success", "message": f"Item {item_id} deleted successfully."}

# --- CondicaoDePagamento Tools ---

async def list_payment_conditions_tool(
    ctx: Dict[str, Any],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    search: Optional[str] = None,
    ordering: Optional[str] = None,
) -> Dict[str, Any]:
    """Lists available payment conditions from Blackpearl.
    
    Args:
        ctx: The context dictionary (unused currently).
        limit: Maximum number of conditions to return.
        offset: Starting index for pagination.
        search: A search term to filter payment conditions.
        ordering: Field to sort the conditions by.
        
    Returns:
        A dictionary containing a list of payment conditions and pagination details.
    """
    async with BlackpearlProvider() as provider:
        result = await provider.list_condicoes_pagamento(
            limit=limit, offset=offset, search=search, ordering=ordering
        )
        return result