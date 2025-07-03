import logging
from typing import Dict, Any, Optional
from pydantic_ai import Agent, RunContext
import traceback

# Import Black Pearl order/item tools and schemas
from automagik.tools.blackpearl.tool import (
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
    get_produto,
)
from automagik.tools.blackpearl.schema import (
    PedidoDeVendaCreate, PedidoDeVendaUpdate, ItemDePedidoCreate, ItemDePedidoUpdate
)

# Import product agent
from .product import product_agent

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
    
    # Store these values in a context dict that will be available to all tools
    # This is critical for order creation
    order_context = {
        "blackpearl_cliente_id": blackpearl_client_id,
        "blackpearl_contact_id": blackpearl_contact_id,
        "client_name": client_name,
        "user_id": user_id
    }
    
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
                status_negociacao="0"  # Get draft/open orders using numeric string code
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
    - Create new sales orders - just call bp_create_pedido_venda() without parameters.
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
    
    IMPORTANT - USING EXISTING ORDERS:
    ALWAYS check for existing open orders for the client before creating a new one. Use the following priority:
    1. If there is an EMPTY order (an order with no items), automatically use it without asking the user
    2. If there are orders with items already, ask the user if they want to use an existing order or create a new one
    3. If user wants to use an existing order, use the most recent one
    4. Only create a new order when explicitly requested or when no open orders exist
    
    To check if an order is empty, use bp_list_items_pedido with the order ID to see if it has any items.
    
    IMPORTANT - CREATING ORDERS:
    When a user wants to create a new order, simply call bp_create_pedido_venda() without any parameters.
    All necessary default values (including client ID) are automatically set.
    Example: "User: Create a new order" → You call bp_create_pedido_venda() with no parameters.
    
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
    
    TOOL USAGE NOTES:
    - When calling `bp_list_pedidos_venda` and filtering by `status_negociacao`, you MUST use the numeric string code (e.g., '0', '1', '2', '3', '4'). DO NOT use descriptive terms like 'rascunho', 'aberto', 'aprovado'. For example, to list draft/negotiation orders, use status_negociacao='0'.
    - Always ensure you have the necessary information before attempting an action (e.g., client ID for creating an order, order ID for adding items or updating).
    Use the client ID and contact ID available in the context when creating or managing orders.
    Communicate clearly with the main Stan agent about the results of your actions (success, failure, IDs created, etc.).
    
    When working with this client, use their specific information and refer to existing orders when relevant.
    """

    order_agent = Agent(
        'openai:gpt-4o', 
        deps_type=Dict[str, Any],
        system_prompt=SYSTEM_PROMPT
    )
    
    # Store the client_id and other context in the order_agent's context
    # This is a crucial step to ensure context is available to tool calls
    setattr(order_agent, '_context', order_context)
    
    # Patch the deps.context to include our necessary data
    if hasattr(ctx.deps, 'context'):
        if isinstance(ctx.deps.context, dict):
            # Update the existing context
            ctx.deps.context.update(order_context)
        else:
            # Set a new context
            ctx.deps.context = order_context
    else:
        # Create context attribute
        setattr(ctx.deps, 'context', order_context)
    
    logger.info(f"Order agent context set: {order_context}")
    
    # --- Define Order Tools --- 

    @order_agent.tool
    async def bp_create_pedido_venda(ctx: RunContext[Dict[str, Any]], pedido_data: Optional[PedidoDeVendaCreate] = None) -> Dict[str, Any]:
        """Create a new sales order (pedido de venda) in BlackPearl.
        
        This function creates a new sales order with default configurations.
        You don't need to provide any parameters - the client ID will be pulled from the context.
        
        Returns:
            Dictionary with created order data
        """
        try:
            # Log initial call information 
            logger.info("=== BP CREATE PEDIDO VENDA CALLED ===")
            logger.info(f"Context type: {type(ctx)}")
            logger.info(f"Has 'context' attribute: {hasattr(ctx, 'context')}")
            logger.info(f"Has 'deps' attribute: {hasattr(ctx, 'deps')}")
            
            if hasattr(ctx, 'deps'):
                logger.info(f"deps type: {type(ctx.deps)}")
                logger.info(f"deps has 'context' attribute: {hasattr(ctx.deps, 'context')}")
                
                if hasattr(ctx.deps, 'context') and ctx.deps.context:
                    logger.info(f"Keys in deps.context: {list(ctx.deps.context.keys()) if isinstance(ctx.deps.context, dict) else 'Not a dict'}")
                    if isinstance(ctx.deps.context, dict) and 'blackpearl_cliente_id' in ctx.deps.context:
                        logger.info(f"blackpearl_cliente_id in deps.context: {ctx.deps.context['blackpearl_cliente_id']}")
            
            if hasattr(ctx, 'context') and ctx.context:
                logger.info(f"Keys in ctx.context: {list(ctx.context.keys()) if isinstance(ctx.context, dict) else 'Not a dict'}")
                if isinstance(ctx.context, dict) and 'blackpearl_cliente_id' in ctx.context:
                    logger.info(f"blackpearl_cliente_id in ctx.context: {ctx.context['blackpearl_cliente_id']}")
            
            logger.info(f"pedido_data provided: {pedido_data is not None}")
            if pedido_data:
                logger.info(f"Input pedido_data: {pedido_data.model_dump()}")
            
            # Get client ID from context - PATCHED TO LOOK IN OUTER CONTEXT
            cliente_id = None
            
            # Check if this is being called directly from order_agent
            order_agent_context = getattr(order_agent, '_context', {})
            if isinstance(order_agent_context, dict) and 'blackpearl_cliente_id' in order_agent_context:
                cliente_id = order_agent_context.get('blackpearl_cliente_id')
                logger.info(f"Got cliente_id from order_agent._context: {cliente_id}")
                
            # Try standard locations if not found above
            if not cliente_id:
                if hasattr(ctx, 'context') and isinstance(ctx.context, dict):
                    cliente_id = ctx.context.get('blackpearl_cliente_id')
                    logger.info(f"Getting cliente_id from ctx.context: {cliente_id}")
                elif hasattr(ctx.deps, 'context') and isinstance(ctx.deps.context, dict):
                    cliente_id = ctx.deps.context.get('blackpearl_cliente_id')
                    logger.info(f"Getting cliente_id from ctx.deps.context: {cliente_id}")
            
            # Try other possible locations for cliente_id if not found yet
            if not cliente_id:
                logger.info("Cliente ID not found in standard locations, trying other locations")
                
                # Try ctx.deps.blackpearl_cliente_id
                if hasattr(ctx.deps, 'blackpearl_cliente_id'):
                    cliente_id = ctx.deps.blackpearl_cliente_id
                    logger.info(f"Found cliente_id in ctx.deps.blackpearl_cliente_id: {cliente_id}")
                
                # Try ctx.deps.evolution_payload
                elif hasattr(ctx.deps, 'evolution_payload'):
                    evolution_payload = ctx.deps.evolution_payload
                    logger.info(f"Found evolution_payload in deps: {type(evolution_payload)}")
                    
                    # Try to extract context from evolution_payload
                    try:
                        user_number = evolution_payload.get_user_number()
                        logger.info(f"Got user_number from evolution_payload: {user_number}")
                    except Exception as e:
                        logger.error(f"Error extracting from evolution_payload: {e}")
            
            # Check if cliente ID was provided directly in the order data
            if not cliente_id and pedido_data and hasattr(pedido_data, 'cliente') and pedido_data.cliente:
                cliente_id = pedido_data.cliente
                logger.info(f"Using cliente_id from pedido_data: {cliente_id}")
            
            if not cliente_id:
                logger.error("Cliente ID not found in any context location")
                return {"success": False, "error": "Cliente ID not found in context. Cannot create order. Please ensure client information is available before creating an order."}
            
            logger.info(f"Final cliente_id to use: {cliente_id}")
            
            # Set up default payload
            default_payload = {
                "status_negociacao": "0",  # Draft/rascunho
                "status_pedido": "0",
                "cliente": cliente_id,
                "vendedor": [33],  # Default seller ID
                "pagamento": 1,    # Default payment condition
                "observacoes": "Pedido criado via Stan",
                "transportadora": 1,
                "frete_modalidade": "0",  # CIF
                "cancelado": False
            }
            
            logger.info(f"Default payload created: {default_payload}")
            
            # Create validated data, either from defaults or from provided model
            if pedido_data:
                # If a model is provided, use its values but ensure cliente_id is set
                model_dict = pedido_data.model_dump()
                logger.info(f"Using custom model_dict: {model_dict}")
                
                if "cliente" not in model_dict or not model_dict["cliente"]:
                    model_dict["cliente"] = cliente_id
                    logger.info(f"Set missing cliente in model_dict to: {cliente_id}")
                    
                validated_data = PedidoDeVendaCreate(**model_dict)
                logger.info("Created validated_data from custom model")
            else:
                # Otherwise use the defaults
                validated_data = PedidoDeVendaCreate(**default_payload)
                logger.info("Created validated_data from defaults")
            
            logger.info(f"Final validated_data: {validated_data}")
            
            # Use the create_order_tool with validated data
            logger.info("Calling create_order_tool...")
            result = await create_order_tool(ctx, validated_data)
            logger.info(f"create_order_tool returned: {result}")
            
            return result
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"success": False, "error": f"API error in create_pedido_venda: {e}"}
            
  
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
    async def bp_add_item_pedido(ctx: RunContext[Dict[str, Any]], 
                                pedido_id: int, 
                                produto_id: int, 
                                quantidade: int = 1,
                                valor_unitario: Optional[str] = None,
                                desconto: Optional[str] = None,
                                porcentagem_desconto: Optional[float] = 0.0) -> Dict[str, Any]:
        """Add an item to a sales order (pedido de venda).
        
        Args:
            pedido_id: The ID of the order to add the item to
            produto_id: The ID of the product to add
            quantidade: Quantity of the product (default: 1)
            valor_unitario: Unit price as string (optional, will fetch from product if not provided)
            desconto: Discount amount as string (optional)
            porcentagem_desconto: Discount percentage (optional, default: 0.0)
        
        Returns:
            Dictionary with the created item data
        """
        try:
            logger.info(f"Adding item to order: Order ID={pedido_id}, Product ID={produto_id}, Quantity={quantidade}")
            
            # If valor_unitario is not provided, fetch it from the product
            if not valor_unitario:
                try:
                    # Fetch product details to get the price
                    produto = await get_produto(ctx, produto_id)
                    if produto and "valor_unitario" in produto:
                        # Format the price to exactly 2 decimal places
                        price_value = float(produto["valor_unitario"])
                        valor_unitario = f"{price_value:.2f}"
                        logger.info(f"Fetched product price: {produto['valor_unitario']}, formatted to: {valor_unitario}")
                    else:
                        logger.error(f"Failed to get price for product {produto_id}")
                        return {"success": False, "error": f"Could not determine price for product {produto_id}"}
                except Exception as e:
                    logger.error(f"Error fetching product details: {e}")
                    return {"success": False, "error": f"Error fetching product details: {e}"}
            else:
                # If valor_unitario was provided, ensure it has 2 decimal places
                try:
                    price_value = float(valor_unitario)
                    valor_unitario = f"{price_value:.2f}"
                    logger.info(f"Formatted provided price to: {valor_unitario}")
                except ValueError:
                    logger.error(f"Invalid price format: {valor_unitario}")
                    return {"success": False, "error": f"Invalid price format: {valor_unitario}. Must be a valid number."}
            
            # Format discount if provided
            if desconto:
                try:
                    discount_value = float(desconto)
                    desconto = f"{discount_value:.2f}"
                    logger.info(f"Formatted discount to: {desconto}")
                except ValueError:
                    logger.error(f"Invalid discount format: {desconto}")
                    return {"success": False, "error": f"Invalid discount format: {desconto}. Must be a valid number."}
            
            # Construct the ItemDePedidoCreate object
            item_data = {
                "pedido": pedido_id,
                "produto": produto_id,
                "quantidade": quantidade,
                "valor_unitario": valor_unitario
            }
            
            # Add optional fields if provided
            if desconto:
                item_data["desconto"] = desconto
            if porcentagem_desconto:
                item_data["porcentagem_desconto"] = porcentagem_desconto
                
            logger.info(f"Creating item with data: {item_data}")
            
            # Create a properly validated ItemDePedidoCreate instance
            validated_data = ItemDePedidoCreate(**item_data)
            
            # Use the add_item_to_order_tool with validated data
            return await add_item_to_order_tool(ctx, item=validated_data)
        except Exception as e:
            logger.error(f"Error adding item to order {pedido_id}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"success": False, "error": f"API error in add_item_pedido: {e}"}

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
            logger.info("Product agent response received")
            
            return result.output
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
        return result.output
    except Exception as e:
        error_msg = f"Error in order agent: {e}"
        logger.error(error_msg)
        logger.exception(e) # Log full traceback
        return f"I apologize, but I encountered an error processing your order request: {str(e)}"
