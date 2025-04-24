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

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a specialized Order Agent within the Stan/Solid ecosystem.
Your primary function is to manage sales orders ('pedidos de venda') and their items for registered and approved clients.

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

Always ensure you have the necessary information before attempting an action (e.g., client ID for creating an order, order ID for adding items or updating).
Use the client ID and contact ID available in the context when creating or managing orders.
Communicate clearly with the main Stan agent about the results of your actions (success, failure, IDs created, etc.).
"""

async def order_agent(ctx: RunContext[Dict[str, Any]], input_text: str) -> str:
    """Specialized agent for managing Black Pearl sales orders and items."""
    
    order_agent = Agent(
        'google-gla:gemini-2.5-flash-exp', # Or appropriate model
        deps_type=Dict[str, Any],
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
        if 'blackpearl_cliente_id' not in ctx.context or 'blackpearl_contact_id' not in ctx.context:
            return {"success": False, "error": "Client ID or Contact ID missing in context. Cannot create order."}
        
        # Add context IDs to pedido_data if not present
        if 'cliente' not in pedido_data:
            pedido_data['cliente'] = ctx.context['blackpearl_cliente_id']
        if 'contato_id' not in pedido_data:
             pedido_data['contato_id'] = ctx.context['blackpearl_contact_id']

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
        effective_cliente_id = cliente_id if cliente_id is not None else ctx.context.get('blackpearl_cliente_id')
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
