"""Blackpearl API tools.

This module provides tools for interacting with the Blackpearl API.
"""
import logging
from typing import Optional, Dict, Any, Union
from pydantic_ai import RunContext
from automagik.config import Environment, settings
from automagik.tools.blackpearl.provider import BlackpearlProvider
from automagik.tools.blackpearl.schema import (
    Cliente, Contato, Vendedor, PedidoDeVenda, RegraDeFrete, RegraDeNegocio, ItemDePedidoCreate
)

logger = logging.getLogger(__name__)

async def get_clientes(
    ctx: RunContext[Dict],
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

async def get_cliente(ctx: RunContext[Dict], cliente_id: int) -> Cliente:
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

async def create_cliente(ctx: RunContext[Dict], cliente: Cliente) -> Dict[str, Any]:
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

async def update_cliente(ctx: RunContext[Dict], cliente_id: int, cliente: Cliente) -> Dict[str, Any]:
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

async def delete_cliente(ctx: RunContext[Dict], cliente_id: int) -> None:
    """Delete a client from the Blackpearl API.
    
    Args:
        ctx: Agent context
        cliente_id: Client ID
    """
    provider = BlackpearlProvider()
    async with provider:
        await provider.delete_cliente(cliente_id)

async def get_contatos(
    ctx: RunContext[Dict],
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

async def get_contato(ctx: RunContext[Dict], contato_id: int) -> Contato:
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

async def create_contato(ctx: RunContext[Dict], contato: Union[Contato, Dict[str, Any]]) -> Dict[str, Any]:
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

async def update_contato(ctx: RunContext[Dict], contato_id: int, contato: Contato) -> Dict[str, Any]:
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

async def delete_contato(ctx: RunContext[Dict], contato_id: int) -> None:
    """Delete a contact from the Blackpearl API.
    
    Args:
        ctx: Agent context
        contato_id: Contact ID
    """
    provider = BlackpearlProvider()
    async with provider:
        await provider.delete_contato(contato_id)

async def get_vendedores(
    ctx: RunContext[Dict],
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

async def get_vendedor(ctx: RunContext[Dict], vendedor_id: int) -> Dict[str, Any]:
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

async def create_vendedor(ctx: RunContext[Dict], vendedor: Vendedor) -> Dict[str, Any]:
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

async def update_vendedor(ctx: RunContext[Dict], vendedor_id: int, vendedor: Vendedor) -> Dict[str, Any]:
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
    ctx: RunContext[Dict],
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

async def get_produto(ctx: RunContext[Dict], produto_id: int, tabela_preco: Optional[int] = None) -> Dict[str, Any]:
    """Get a specific product from the Blackpearl API.
    
    Args:
        ctx: Agent context
        produto_id: Product ID
        
    Returns:
        Product data
    """
    provider = BlackpearlProvider()
    async with provider:
        return await provider.get_produto(produto_id, tabela_preco)

async def get_familias_de_produtos(
    ctx: RunContext[Dict],
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

async def get_familia_de_produto(ctx: RunContext[Dict], familia_id: int) -> Dict[str, Any]:
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
    ctx: RunContext[Dict],
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

async def get_marca(ctx: RunContext[Dict], marca_id: int) -> Dict[str, Any]:
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
    ctx: RunContext[Dict],
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
    ctx: RunContext[Dict],
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

async def get_pedido(ctx: RunContext[Dict], pedido_id: int) -> Dict[str, Any]:
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

async def create_pedido(ctx: RunContext[Dict], pedido: PedidoDeVenda) -> Dict[str, Any]:
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

async def update_pedido(ctx: RunContext[Dict], pedido_id: int, pedido: PedidoDeVenda) -> Dict[str, Any]:
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
    ctx: RunContext[Dict],
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

async def get_regra_frete(ctx: RunContext[Dict], regra_id: int) -> Dict[str, Any]:
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

async def create_regra_frete(ctx: RunContext[Dict], regra: RegraDeFrete) -> Dict[str, Any]:
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

async def update_regra_frete(ctx: RunContext[Dict], regra_id: int, regra: RegraDeFrete) -> Dict[str, Any]:
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
    ctx: RunContext[Dict],
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

async def get_regra_negocio(ctx: RunContext[Dict], regra_id: int) -> Dict[str, Any]:
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

async def create_regra_negocio(ctx: RunContext[Dict], regra: RegraDeNegocio) -> Dict[str, Any]:
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

async def update_regra_negocio(ctx: RunContext[Dict], regra_id: int, regra: RegraDeNegocio) -> Dict[str, Any]:
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

def _format_cnpj_for_api(cnpj: str) -> str:
    """Format CNPJ to the standard format expected by BlackPearl API: XX.XXX.XXX/XXXX-XX"""
    import re
    
    # Remove all non-numeric characters
    clean_cnpj = re.sub(r'[^0-9]', '', cnpj)
    
    # If not 14 digits, return original
    if len(clean_cnpj) != 14:
        return cnpj
    
    # Format to XX.XXX.XXX/XXXX-XX
    formatted = f"{clean_cnpj[:2]}.{clean_cnpj[2:5]}.{clean_cnpj[5:8]}/{clean_cnpj[8:12]}-{clean_cnpj[12:14]}"
    return formatted

async def verificar_cnpj(ctx: RunContext[Dict], cnpj: str) -> Dict[str, Any]:
    """Verify a CNPJ in the Blackpearl API.
    
    Args:
        ctx: Agent context
        cnpj: The CNPJ number to verify (accepts any format, automatically formats for API)
        
    Returns:
        CNPJ verification result containing validation status and company information if valid
    """
    # Format CNPJ to the standard format expected by the API
    formatted_cnpj = _format_cnpj_for_api(cnpj)
    
    provider = BlackpearlProvider()
    async with provider:
        print(f"Verifying CNPJ: {cnpj} -> formatted: {formatted_cnpj}")
        verification_result = await provider.verificar_cnpj(formatted_cnpj)
        
        # Create a modified result without status and reason fields if they exist
        # Only remove these fields in development environment
        
        if isinstance(verification_result, dict) and settings.ENVIRONMENT == Environment.DEVELOPMENT:
            if 'status' in verification_result:
                verification_result.pop('status', None)
            if 'reason' in verification_result:
                verification_result.pop('reason', None)
                
        return verification_result

async def finalizar_cadastro(ctx: RunContext[Dict], cliente_id: int) -> Dict[str, Any]:
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

async def create_order_tool(ctx: RunContext[Dict], pedido: PedidoDeVenda) -> Dict[str, Any]:
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

async def get_order_tool(ctx: RunContext[Dict], pedido_id: int) -> Dict[str, Any]:
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
    ctx: RunContext[Dict],
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

async def update_order_tool(ctx: RunContext[Dict], pedido_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
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

async def approve_order_tool(ctx: RunContext[Dict], pedido_id: int) -> Dict[str, Any]:
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

async def add_item_to_order_tool(ctx: RunContext[Dict], item_data: ItemDePedidoCreate) -> Dict[str, Any]:
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

async def get_order_item_tool(ctx: RunContext[Dict], item_id: int) -> Dict[str, Any]:
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
    ctx: RunContext[Dict],
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

async def update_order_item_tool(ctx: RunContext[Dict], item_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
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

async def delete_order_item_tool(ctx: RunContext[Dict], item_id: int) -> Dict[str, Any]:
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

# --- Contact Management Tools ---

async def get_or_create_contact(context: Dict[str, Any], 
                               user_number: str, 
                               user_name: str,
                               user_id: str = "unknown",
                               agent_id: str = "unknown") -> Dict[str, Any]:
    """Get an existing contact or create a new one.
    
    This method implements the following logic:
    1. First search by phone number
    2. If not found, create a new contact
    
    Args:
        context: The context dictionary to use for API calls
        user_number: The user's phone number
        user_name: The user's name
        user_id: Optional user ID for session
        agent_id: Optional agent ID for session
        
    Returns:
        The contact data dictionary or None if not found/created
    """
    from datetime import datetime
    from automagik.tools.blackpearl.schema import StatusAprovacaoEnum
    
    if not user_number:
        return None
        
    # Try to find contact by phone number
    contacts_response = await get_contatos(context, search=user_number)
    
    # Check if we found any matching contacts
    if contacts_response and "results" in contacts_response and contacts_response["results"]:
        # Return the first matching contact
        contato = contacts_response["results"][0]
        return contato
            
    
    # No contact found, create a new one
    logger.info(f"Creating new contact for {user_name} with number {user_number}")
    
    # Generate wpp_session_id using user_id and agent_id
    wpp_session_id = f"{user_id}_{agent_id}"
    
    try:
        # Create current time as ISO format string
        current_time = datetime.now().isoformat()
        
        # Create contact data as a dictionary
        contact_data = {
            "id": 0,
            "nome": user_name or "Unknown",
            "telefone": user_number,
            "wpp_session_id": wpp_session_id,
            "ativo": True,
            "data_registro": current_time,
            "status_aprovacao": StatusAprovacaoEnum.NOT_REGISTERED,
            "data_aprovacao": None,
            "detalhes_aprovacao": "Usuário novo, esperando cadastro...",
            "ultima_atualizacao": None
        }
        
        # Create the contact in BlackPearl API
        created_contact = await create_contato(context, contact_data)
        logger.info(f"Successfully created contact with ID: {created_contact.get('id')}")
        return created_contact
    except Exception as e:
        logger.error(f"Failed to create contact: {str(e)}")
        return None

# --- CondicaoDePagamento Tools ---

async def list_payment_conditions_tool(
    ctx: RunContext[Dict],
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