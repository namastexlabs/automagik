import logging
from typing import Dict, Any, Optional, List
from pydantic_ai import Agent, RunContext

# Import Black Pearl order/item tools and schemas
from src.tools.blackpearl.tool import (
    create_order_tool,
    get_order_tool,         
    list_orders_tool,           
    update_order_tool,      
    add_item_to_order_tool, 
    get_order_item_tool,    
    list_order_items_tool,  
    update_order_item_tool,
    delete_order_item_tool,
    list_payment_conditions_tool,
)
from src.tools.blackpearl.schema import (
    PedidoDeVendaCreate, PedidoDeVendaUpdate, ItemDePedidoCreate, ItemDePedidoUpdate
)

# Import product agent
from src.agents.simple.stan_agent.specialized.product import product_agent

logger = logging.getLogger(__name__)

async def order_agent(ctx: RunContext[Dict[str, Any]], input_text: str) -> str:
    """Specialized agent for managing Black Pearl sales orders and items."""
    
    # Extract user info from context
    user_id = ctx.deps.get("user_id") if isinstance(ctx.deps, dict) else None
    if hasattr(ctx.deps, 'user_id'):
        user_id = ctx.deps.user_id
    
    # Get client info from context
    blackpearl_client_id = None
    blackpearl_contact_id = None
    client_name = "cliente"
    
    if isinstance(ctx.deps, dict):
        blackpearl_client_id = ctx.deps.get("blackpearl_cliente_id")
        blackpearl_contact_id = ctx.deps.get("blackpearl_contact_id")
        client_name = ctx.deps.get("blackpearl_cliente_nome", "cliente")
    
    if hasattr(ctx.deps, 'context'):
        ctx_dict = ctx.deps.context
        if isinstance(ctx_dict, dict):
            blackpearl_client_id = ctx_dict.get("blackpearl_cliente_id", blackpearl_client_id)
            blackpearl_contact_id = ctx_dict.get("blackpearl_contact_id", blackpearl_contact_id)
            client_name = ctx_dict.get("blackpearl_cliente_nome", client_name)
    
    logger.info(f"Order Agent - User ID: {user_id}")
    logger.info(f"Order Agent - BlackPearl Client ID: {blackpearl_client_id}")
    logger.info(f"Order Agent - BlackPearl Contact ID: {blackpearl_contact_id}")
    
    # Check for active orders
    active_orders = None
    active_orders_info = ""
    
    if blackpearl_client_id:
        try:
            # Attempt to fetch active orders for this client
            orders_response = await list_orders_tool(
                ctx.deps, 
                cliente_id=blackpearl_client_id, 
                limit=5,
                status_negociacao="open"  # Get open orders
            )
            
            if orders_response and "results" in orders_response and orders_response["results"]:
                active_orders = orders_response["results"]
                
                # Format active orders for the prompt
                active_orders_info = f"\n\nINFORMAÇÕES DE PEDIDOS ATIVOS PARA {client_name.upper()}:\n"
                for idx, order in enumerate(active_orders, 1):
                    order_id = order.get("id", "ID desconhecido")
                    order_date = order.get("data_criacao", "Data desconhecida")
                    order_status = order.get("status_negociacao", "Status desconhecido")
                    order_value = order.get("valor_total", 0)
                    
                    active_orders_info += f"Pedido #{idx}: ID: {order_id}, Data: {order_date}, Status: {order_status}, Valor: R$ {order_value:.2f}\n"
                    
                    # Add items if available
                    try:
                        items_response = await list_order_items_tool(ctx.deps, pedido_id=order_id)
                        if items_response and "results" in items_response and items_response["results"]:
                            active_orders_info += "  Itens:\n"
                            for item in items_response["results"]:
                                item_name = item.get("descricao", "Item desconhecido")
                                item_qty = item.get("quantidade", 0)
                                item_price = item.get("valor_unitario", 0)
                                active_orders_info += f"  - {item_qty}x {item_name} (R$ {item_price:.2f}/un)\n"
                    except Exception as e:
                        logger.error(f"Error fetching items for order {order_id}: {e}")
                        
                logger.info(f"Found {len(active_orders)} active orders for client {blackpearl_client_id}")
            else:
                active_orders_info = f"\n\nNenhum pedido ativo encontrado para {client_name}."
                logger.info(f"No active orders found for client {blackpearl_client_id}")
        except Exception as e:
            logger.error(f"Error fetching active orders: {e}")
            active_orders_info = "\n\nErro ao buscar pedidos ativos."
    
    SYSTEM_PROMPT = f"""
    You are a specialized Order Agent within the Stan/Solid ecosystem.
    Your primary function is to manage sales orders ('pedidos de venda') and their items for registered and approved clients.
    
    CURRENT USER INFORMATION:
    - Cliente ID: {blackpearl_client_id or "Não disponível"}
    - Contato ID: {blackpearl_contact_id or "Não disponível"}
    - Nome do Cliente: {client_name or "Não disponível"}
    {active_orders_info}
    
    You can perform the following actions:
    - Create new sales orders.
    - Add items to existing sales orders.
    - List existing sales orders (optionally filtering).
    - Retrieve details of a specific sales order.
    - Update existing sales orders.
    - Approve sales orders (change their status).
    - List items within a specific sales order.
    - Retrieve details of a specific item in an order.
    - Update items within an order.
    - Delete items from an order.
    - List available payment conditions ('condições de pagamento').
    - Query product information directly with the product_agent tool.
    
    IMPORTANT - PRODUCT INFORMATION ACCESS:
    You have direct access to the product agent through the "product_agent_tool" function.
    Use this tool when you need to:
    1. Search for products by name, description, or SKU
    2. Get specific product information (price, availability, etc.)
    3. Access product IDs for adding items to orders
    4. Find previously searched products in the current session
    
    For example, when the user mentions products they want to order, use the product_agent_tool 
    to find the correct product IDs before creating an order or adding items.
    
    Example query to product_agent_tool: "Find products with 'tablet' in the name"
    Example query to product_agent_tool: "What was the last product search result?"
    
    Always ensure you have the necessary information before attempting an action (e.g., client ID for creating an order, order ID for adding items or updating).
    Use the client ID and contact ID available in the context when creating or managing orders.
    Communicate clearly with the main Stan agent about the results of your actions (success, failure, IDs created, etc.).
    
    When working with this client, use their specific information and refer to existing orders when relevant.
    """

    order_agent = Agent(
        'openai:o4-mini', 
        deps_type=Dict[str, Any],
        model_settings={"parallel_tool_calls": True},
        system_prompt=SYSTEM_PROMPT
    )

    # --- Define Order Tools --- 

    @order_agent.tool
    async def bp_create_pedido_venda(ctx: RunContext[Dict[str, Any]], pedido_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new sales order (pedido de venda) in BlackPearl.
        Requires client ID (cliente) and contact ID (contato_id) from context.
        Args:
            pedido_data: Dictionary conforming to PedidoDeVendaCreate schema.
        """
        # Ensure client and contact IDs are in context
        if 'blackpearl_cliente_id' not in ctx.context and 'cliente' not in pedido_data:
            return {"success": False, "error": "Client ID missing in context and request. Cannot create order."}
        
        if 'blackpearl_contact_id' not in ctx.context and 'contato_id' not in pedido_data:
            return {"success": False, "error": "Contact ID missing in context and request. Cannot create order."}
        
        # Add context IDs to pedido_data if not present
        if 'cliente' not in pedido_data:
            pedido_data['cliente'] = ctx.context.get('blackpearl_cliente_id')
        if 'contato_id' not in pedido_data:
             pedido_data['contato_id'] = ctx.context.get('blackpearl_contact_id')

        try:
            validated_data = PedidoDeVendaCreate(**pedido_data)
            return await create_order_tool(ctx, validated_data.model_dump(by_alias=True))
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return {"success": False, "error": f"Validation or API error creating order: {e}"} 

    @order_agent.tool
    async def bp_get_pedido_venda(ctx: RunContext[Dict[str, Any]], pedido_id: int) -> Dict[str, Any]:
        """Get details of a specific sales order (pedido de venda)."""
        return await get_order_tool(ctx, pedido_id=pedido_id)

    @order_agent.tool
    async def bp_list_pedidos_venda(ctx: RunContext[Dict[str, Any]], 
                                  limit: Optional[int] = None, 
                                  offset: Optional[int] = None,
                                  search: Optional[str] = None, 
                                  ordering: Optional[str] = None,
                                  cliente_id: Optional[int] = None,
                                  status_negociacao: Optional[str] = None) -> Dict[str, Any]:
        """List sales orders (pedidos de venda) from BlackPearl."""
        # Use client ID from context if not provided
        effective_cliente_id = cliente_id
        if effective_cliente_id is None:
            if hasattr(ctx, 'context') and isinstance(ctx.context, dict):
                effective_cliente_id = ctx.context.get('blackpearl_cliente_id')
            elif hasattr(ctx.deps, 'context') and isinstance(ctx.deps.context, dict):
                effective_cliente_id = ctx.deps.context.get('blackpearl_cliente_id')
                
        return await list_orders_tool(ctx, limit=limit, offset=offset, search=search, ordering=ordering, cliente_id=effective_cliente_id, status_negociacao=status_negociacao)

    @order_agent.tool
    async def bp_update_pedido_venda(ctx: RunContext[Dict[str, Any]], pedido_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing sales order (pedido de venda)."""
        try:
            validated_data = PedidoDeVendaUpdate(**update_data)
            return await update_order_tool(ctx, pedido_id=pedido_id, update_data=validated_data.model_dump(by_alias=True))
        except Exception as e:
            logger.error(f"Error updating order {pedido_id}: {e}")
            return {"success": False, "error": f"Validation or API error updating order: {e}"} 

    # @order_agent.tool
    # async def bp_approve_pedido_venda(ctx: RunContext[Dict[str, Any]], pedido_id: int) -> Dict[str, Any]:
    #     """Approve a sales order (pedido de venda)."""
    #     # No direct approve_order_tool found, might be part of update_order_tool logic?
    #     # Placeholder: Approval might be handled by updating status via update_order_tool
    #     status_update = {"status": "approved"} # Example status field
    #     return await update_order_tool(ctx, pedido_id=pedido_id, update_data=status_update)

    # --- Define Order Item Tools --- 

    @order_agent.tool
    async def bp_add_item_pedido(ctx: RunContext[Dict[str, Any]], item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add an item to a sales order (pedido de venda). Requires 'pedido' (order ID) in item_data."""
        if 'pedido' not in item_data:
             return {"success": False, "error": "Order ID ('pedido') missing in item data."}
        try:
            validated_data = ItemDePedidoCreate(**item_data)
            return await add_item_to_order_tool(ctx, item=validated_data.model_dump(by_alias=True)) # Pass as 'item' argument
        except Exception as e:
            pedido_id = item_data.get('pedido', 'unknown')
            logger.error(f"Error adding item to order {pedido_id}: {e}")
            return {"success": False, "error": f"Validation or API error adding item: {e}"} 

    @order_agent.tool
    async def bp_list_items_pedido(ctx: RunContext[Dict[str, Any]], 
                                 pedido_id: int,
                                 limit: Optional[int] = None, 
                                 offset: Optional[int] = None,
                                 search: Optional[str] = None, 
                                 ordering: Optional[str] = None) -> Dict[str, Any]:
        """List items within a specific sales order (pedido de venda)."""
        return await list_order_items_tool(ctx, pedido_id=pedido_id, limit=limit, offset=offset, search=search, ordering=ordering)

    @order_agent.tool
    async def bp_get_item_pedido(ctx: RunContext[Dict[str, Any]], item_id: int) -> Dict[str, Any]:
        """Get details of a specific item within a sales order."""
        return await get_order_item_tool(ctx, item_id=item_id)

    @order_agent.tool
    async def bp_update_item_pedido(ctx: RunContext[Dict[str, Any]], item_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing item within a sales order."""
        try:
            validated_data = ItemDePedidoUpdate(**update_data)
            return await update_order_item_tool(ctx, item_id=item_id, update_data=validated_data.model_dump(by_alias=True))
        except Exception as e:
            logger.error(f"Error updating item {item_id}: {e}")
            return {"success": False, "error": f"Validation or API error updating item: {e}"} 

    @order_agent.tool
    async def bp_delete_item_pedido(ctx: RunContext[Dict[str, Any]], item_id: int) -> Dict[str, Any]:
        """Delete an item from a sales order."""
        return await delete_order_item_tool(ctx, item_id=item_id)

    # --- Define Other Related Tools --- 

    # async def bp_get_payment_condition(ctx: RunContext[Dict[str, Any]], name_or_code: str) -> Dict[str, Any]:
    #     """Gets a payment condition by name or code."""
    #     logger.info(f"Attempting to get payment condition: {name_or_code}")
    #     try:
    #         # Use the corresponding tool function - REMOVED as it does not exist
    #         # return await get_payment_condition_by_name_or_code(ctx, name_or_code=name_or_code)
    #         return {"success": False, "error": "Functionality to get a single payment condition is not implemented."}
    #     except Exception as e:
    #         logger.error(f"Error getting payment condition {name_or_code}: {e}")
    #         return {"success": False, "error": f"API error getting payment condition: {e}"}

    @order_agent.tool
    async def bp_list_condicoes_pagamento(ctx: RunContext[Dict[str, Any]], 
                                          limit: Optional[int] = None, 
                                          offset: Optional[int] = None,
                                          search: Optional[str] = None) -> Dict[str, Any]:
        """List available payment conditions (condições de pagamento)."""
        return await list_payment_conditions_tool(ctx, limit=limit, offset=offset, search=search)
    
    # @order_agent.tool
    # async def bp_list_transportadoras(ctx: RunContext[Dict[str, Any]],
    #                                   limit: Optional[int] = None,
    #                                   offset: Optional[int] = None,
    #                                   search: Optional[str] = None) -> Dict[str, Any]:
    #     """List available carriers (transportadoras, mapped to regras_frete)."""
    #     # Assuming list_transportadoras maps to list_regras_frete_tool - REMOVED as it does not exist
    #     # return await list_regras_frete_tool(ctx, limit=limit, offset=offset, search=search)
    #     return {"success": False, "error": "Functionality to list carriers/shipping rules is not implemented."}

    # --- Product Agent Integration ---
    
    @order_agent.tool
    async def product_agent_tool(ctx: RunContext[Dict[str, Any]], query: str) -> str:
        """Communicate with the Product Agent to get product information.
        Use this to search products, get product details, or ask about previous searches.
        
        Args:
            query: A text query about products, like "find products with 'notebook' in the name" 
                  or "what are the recent product search results"
        
        Returns:
            Response from the Product Agent with the requested product information
        """
        try:
            logger.info(f"Order agent querying Product agent with: '{query}'")
            
            # Pass the context to the product agent
            product_agent_ctx = ctx.deps
            
            # Ensure the same context is available to the product agent
            if hasattr(ctx.deps, 'context') and isinstance(ctx.deps.context, dict):
                # Create a clean copy of the context
                product_context_copy = dict(ctx.deps.context)
                
                # Make sure the user_id is consistent
                if user_id and 'user_id' not in product_context_copy:
                    product_context_copy['user_id'] = user_id
                
                # Ensure evolution_payload is copied if available
                if 'evolution_payload' in product_context_copy:
                    logger.info("Evolution payload found in context, will be available to product agent")
                
                # Update the context
                if hasattr(product_agent_ctx, 'set_context'):
                    product_agent_ctx.set_context(product_context_copy)
            
            # Call the product agent with the query
            result = await product_agent(product_agent_ctx, query)
            logger.info(f"Product agent response received")
            
            return result
        except Exception as e:
            error_msg = f"Error communicating with Product agent: {e}"
            logger.error(error_msg)
            logger.exception(e)
            return f"I couldn't retrieve product information: {str(e)}"

    # --- Execute Agent --- 
    try:
        logger.info(f"Executing Order Agent with input: {input_text}")
        result = await order_agent.run(input_text, deps=ctx)
        logger.info(f"Order agent response: {result}")
        return result.data
    except Exception as e:
        error_msg = f"Error in order agent: {e}"
        logger.error(error_msg)
        logger.exception(e) # Log full traceback
        return f"I apologize, but I encountered an error processing your order request: {str(e)}"
