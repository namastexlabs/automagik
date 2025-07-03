"""Blackpearl API provider.

This module provides the API client implementation for interacting with the Blackpearl API.
"""
import logging
import os
from typing import Optional, Dict, Any, Union
import aiohttp
from automagik.tools.blackpearl.interface import validate_api_response, handle_api_error, format_api_request, filter_none_params
from automagik.tools.blackpearl.schema import (
    Cliente, Contato, Vendedor, PedidoDeVenda, RegraDeFrete, RegraDeNegocio, ItemDePedidoCreate
)
from automagik.config import settings

logger = logging.getLogger(__name__)

# Get API URL from environment variables
BLACKPEARL_API_URL = os.environ.get("BLACKPEARL_API_URL", "")

class BlackpearlProvider:
    """Client for interacting with the Blackpearl API."""
    
    def __init__(self, base_url: str = None):
        """Initialize the API client.
        
        Args:
            base_url: Base URL of the API (optional, defaults to BLACKPEARL_API_URL env var)
        """
        self.base_url = (base_url or BLACKPEARL_API_URL).rstrip('/')
        if not self.base_url:
            raise ValueError("API URL is not set. Provide base_url or set BLACKPEARL_API_URL environment variable.")
            
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Create aiohttp session when entering context."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close aiohttp session when exiting context."""
        if self.session:
            await self.session.close()
            
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an API request.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            
        Returns:
            API response data
        """
        if not self.session:
            raise RuntimeError("Client session not initialized")
            
        url = f"{self.base_url}{endpoint}"
        data = format_api_request(data) if data else None
        params = filter_none_params(params)
        
        # Check if we're in development mode and debug log level
        is_dev_debug = (
            settings.ENVIRONMENT.value == "development" and
            settings.AUTOMAGIK_LOG_LEVEL == "DEBUG"
        )
        
        logger.info(f"BP - API Request: {method} {url}")
        if is_dev_debug:
            logger.debug(f"BP - Request Payload (detailed): {data}")
            logger.debug(f"BP - Request Params (detailed): {params}")
        else:
            logger.info(f"BP - Request Payload: {data}")
            logger.info(f"BP - Request Params: {params}")
        
        try:
            async with self.session.request(method, url, json=data, params=params) as response:
                # Always read the response body first, regardless of status
                try:
                    result = await response.json()
                except Exception as json_error:
                    # If JSON parsing fails, try to get text
                    try:
                        result = await response.text()
                        logger.error(f"BP - Non-JSON response received: {result[:500]}...")
                    except Exception as text_error:
                        result = f"Could not read response: {str(text_error)}"
                        logger.error(f"BP - Failed to read response: {str(text_error)}")
                
                # Enhanced logging for API responses in development/debug mode
                if is_dev_debug:
                    logger.debug(f"BP - API Response Status: {response.status}")
                    logger.debug(f"BP - API Response Headers: {dict(response.headers)}")
                    logger.debug(f"BP - API Response (detailed): {result}")
                    
                    # Check if there are any error messages in the response
                    if isinstance(result, dict) and result.get('error'):
                        logger.debug(f"BP - API Error Message: {result.get('error')}")
                        if result.get('message'):
                            logger.debug(f"BP - API Error Details: {result.get('message')}")
                else:
                    logger.info(f"BP - API Response Status: {response.status}")
                
                # Log detailed error information for non-successful responses
                if response.status >= 400:
                    logger.error(f"BP - HTTP {response.status} Error Response: {result}")
                    if isinstance(result, dict):
                        for key in ['error', 'message', 'detail', 'errors', 'non_field_errors']:
                            if key in result:
                                logger.error(f"BP - {key.title()}: {result[key]}")
                
                # Raise for status after we've captured the response body
                response.raise_for_status()
                
                return result
        except aiohttp.ClientResponseError as e:
            # Enhanced error logging in development/debug mode
            if is_dev_debug:
                logger.debug(f"BP - API Error: {str(e)}")
                logger.debug(f"BP - API Error Status: {e.status}")
                logger.debug(f"BP - API Error Message: {e.message}")
                
                # Try to get the response body for more details
                try:
                    if hasattr(e, 'history') and e.history:
                        response_text = await e.history[0].text()
                        logger.debug(f"BP - API Error Response: {response_text}")
                except Exception as text_error:
                    logger.debug(f"BP - Could not read error response: {str(text_error)}")
            else:
                # Always log error details for 500 errors even in non-debug mode
                if e.status >= 500:
                    logger.error(f"BP - Server Error {e.status}: {e.message}")
                    logger.error(f"BP - Error URL: {e.request_info.url if hasattr(e, 'request_info') else 'Unknown'}")
            
            raise
        
    @handle_api_error
    @validate_api_response
    async def get_clientes(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        ordering: Optional[str] = None,
        **filters
    ) -> Dict[str, Any]:
        """Get list of clients.
        
        Args:
            limit: Number of results to return
            offset: Starting position
            search: Search term
            ordering: Order by field
            **filters: Additional filters
            
        Returns:
            List of clients
        """
        params = {
            "limit": limit,
            "offset": offset,
            "search": search,
            "ordering": ordering,
            **filters
        }
        return await self._request("GET", "/api/v1/cadastro/clientes/", params=params)
        
    @handle_api_error
    @validate_api_response
    async def get_cliente(self, cliente_id: int) -> Dict[str, Any]:
        """Get a specific client.
        
        Args:
            cliente_id: Client ID
            
        Returns:
            Client data
        """
        return await self._request("GET", f"/api/v1/cadastro/clientes/{cliente_id}/")
        
    @handle_api_error
    @validate_api_response
    async def create_cliente(self, cliente: Cliente) -> Dict[str, Any]:
        """Create a new client.
        
        Args:
            cliente: Client data
            
        Returns:
            Created client data
        """
        return await self._request("POST", "/api/v1/cadastro/clientes/", data=cliente.model_dump())
        
    @handle_api_error
    @validate_api_response
    async def update_cliente(self, cliente_id: int, cliente: Cliente) -> Dict[str, Any]:
        """Update a client.
        
        Args:
            cliente_id: Client ID
            cliente: Updated client data
            
        Returns:
            Updated client data
        """
        logger.info(f"Updating client {cliente_id} with data: {cliente.model_dump(exclude_unset=True)}")
        return await self._request(
            "PATCH",
            f"/api/v1/cadastro/clientes/{cliente_id}/",
            data=cliente.model_dump(exclude_unset=True)
        )
        
    @handle_api_error
    @validate_api_response
    async def delete_cliente(self, cliente_id: int) -> None:
        """Delete a client.
        
        Args:
            cliente_id: Client ID
        """
        await self._request("DELETE", f"/api/v1/cadastro/clientes/{cliente_id}/")
        
    @handle_api_error
    @validate_api_response
    async def get_contatos(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        ordering: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get list of contacts.
        
        Args:
            limit: Number of results to return
            offset: Starting position
            search: Search term
            ordering: Order by field
            
        Returns:
            List of contacts
        """
        params = {
            "limit": limit,
            "offset": offset,
            "search": search,
            "ordering": ordering
        }
        return await self._request("GET", "/api/v1/cadastro/contatos/", params=params)
        
    @handle_api_error
    @validate_api_response
    async def get_contato(self, contato_id: int) -> Dict[str, Any]:
        """Get a specific contact.
        
        Args:
            contato_id: Contact ID
            
        Returns:
            Contact data
        """
        return await self._request("GET", f"/api/v1/cadastro/contatos/{contato_id}/")
        
    @handle_api_error
    @validate_api_response
    async def create_contato(self, contato: Union[Contato, Dict[str, Any]]) -> Dict[str, Any]:
        """Create a new contact.
        
        Args:
            contato: Contact data (either Contato object or dictionary)
            
        Returns:
            Created contact data
        """
        # Handle both Contato objects and dictionaries
        if isinstance(contato, Contato):
            data = contato.model_dump()
        else:
            data = contato
            
        return await self._request("POST", "/api/v1/cadastro/contatos/", data=data)
        
    @handle_api_error
    @validate_api_response
    async def update_contato(self, contato_id: int, contato: Contato) -> Dict[str, Any]:
        """Update a contact.
        
        Args:
            contato_id: Contact ID
            contato: Updated contact data
            
        Returns:
            Updated contact data
        """
        return await self._request(
            "PATCH",
            f"/api/v1/cadastro/contatos/{contato_id}/",
            data=contato.model_dump(exclude_unset=True)
        )
        
    @handle_api_error
    @validate_api_response
    async def delete_contato(self, contato_id: int) -> None:
        """Delete a contact.
        
        Args:
            contato_id: Contact ID
        """
        await self._request("DELETE", f"/api/v1/cadastro/contatos/{contato_id}/")
        
    @handle_api_error
    @validate_api_response
    async def get_vendedores(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        ordering: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get list of salespeople.
        
        Args:
            limit: Number of results to return
            offset: Starting position
            search: Search term
            ordering: Order by field
            
        Returns:
            List of salespeople
        """
        params = {
            "limit": limit,
            "offset": offset,
            "search": search,
            "ordering": ordering
        }
        return await self._request("GET", "/api/v1/cadastro/vendedores/", params=params)
        
    @handle_api_error
    @validate_api_response
    async def get_vendedor(self, vendedor_id: int) -> Dict[str, Any]:
        """Get a specific salesperson.
        
        Args:
            vendedor_id: Salesperson ID
            
        Returns:
            Salesperson data
        """
        return await self._request("GET", f"/api/v1/cadastro/vendedores/{vendedor_id}/")
        
    @handle_api_error
    @validate_api_response
    async def create_vendedor(self, vendedor: Vendedor) -> Dict[str, Any]:
        """Create a new salesperson.
        
        Args:
            vendedor: Salesperson data
            
        Returns:
            Created salesperson data
        """
        return await self._request("POST", "/api/v1/cadastro/vendedores/", data=vendedor.model_dump())
        
    @handle_api_error
    @validate_api_response
    async def update_vendedor(self, vendedor_id: int, vendedor: Vendedor) -> Dict[str, Any]:
        """Update a salesperson.
        
        Args:
            vendedor_id: Salesperson ID
            vendedor: Updated salesperson data
            
        Returns:
            Updated salesperson data
        """
        return await self._request(
            "PATCH",
            f"/api/v1/cadastro/vendedores/{vendedor_id}/",
            data=vendedor.model_dump(exclude_unset=True)
        )
        
    @handle_api_error
    @validate_api_response
    async def get_produtos(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        ordering: Optional[str] = None,
        **filters
    ) -> Dict[str, Any]:
        """Get list of products.
        
        Args:
            limit: Number of results to return
            offset: Starting position
            search: Search term
            ordering: Order by field
            **filters: Additional filters
            
        Returns:
            List of products
        """
        params = {
            "limit": limit,
            "offset": offset,
            "search": search,
            "ordering": ordering,
            **filters
        }
        return await self._request("GET", "/api/v1/catalogo/produtos/", params=params)
        
    @handle_api_error
    @validate_api_response
    async def get_produto(self, produto_id: int, tabela_preco: Optional[int] = None) -> Dict[str, Any]:
        """Get a specific product.
        
        Args:
            produto_id: Product ID
            
        Returns:
            Product data
        """
        return await self._request("GET", f"/api/v1/catalogo/produtos/{produto_id}/?tabela_preco={tabela_preco}")
        
    @handle_api_error
    @validate_api_response
    async def get_familias_de_produtos(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        ordering: Optional[str] = None,
        **filters
    ) -> Dict[str, Any]:
        """Get list of product families.
        
        Args:
            limit: Number of results to return
            offset: Starting position
            search: Search term
            ordering: Order by field
            **filters: Additional filters
            
        Returns:
            List of product families
        """
        params = {
            "limit": limit,
            "offset": offset,
            "search": search,
            "ordering": ordering,
            **filters
        }
        return await self._request("GET", "/api/v1/catalogo/familiadeprodutos/", params=params)
        
    @handle_api_error
    @validate_api_response
    async def get_familia_de_produto(self, familia_id: int) -> Dict[str, Any]:
        """Get a specific product family.
        
        Args:
            familia_id: Product family ID
            
        Returns:
            Product family data
        """
        return await self._request("GET", f"/api/v1/catalogo/familiadeprodutos/{familia_id}/")
        
    @handle_api_error
    @validate_api_response
    async def get_marcas(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        ordering: Optional[str] = None,
        **filters
    ) -> Dict[str, Any]:
        """Get list of brands.
        
        Args:
            limit: Number of results to return
            offset: Starting position
            search: Search term
            ordering: Order by field
            **filters: Additional filters
            
        Returns:
            List of brands
        """
        params = {
            "limit": limit,
            "offset": offset,
            "search": search,
            "ordering": ordering,
            **filters
        }
        return await self._request("GET", "/api/v1/catalogo/marcas/", params=params)
        
    @handle_api_error
    @validate_api_response
    async def get_marca(self, marca_id: int) -> Dict[str, Any]:
        """Get a specific brand.
        
        Args:
            marca_id: Brand ID
            
        Returns:
            Brand data
        """
        return await self._request("GET", f"/api/v1/catalogo/marcas/{marca_id}/")
        
    @handle_api_error
    @validate_api_response
    async def get_imagens_de_produto(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        ordering: Optional[str] = None,
        **filters
    ) -> Dict[str, Any]:
        """Get list of product images.
        
        Args:
            limit: Number of results to return
            offset: Starting position
            search: Search term
            ordering: Order by field
            **filters: Additional filters
            
        Returns:
            List of product images
        """
        params = {
            "limit": limit,
            "offset": offset,
            "search": search,
            "ordering": ordering,
            **filters
        }
        return await self._request("GET", "/api/v1/catalogo/imagensdeproduto/", params=params)
        
    @handle_api_error
    @validate_api_response
    async def get_pedidos(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        ordering: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get list of orders.
        
        Args:
            limit: Number of results to return
            offset: Starting position
            search: Search term
            ordering: Order by field
            
        Returns:
            List of orders
        """
        params = {
            "limit": limit,
            "offset": offset,
            "search": search,
            "ordering": ordering
        }
        return await self._request("GET", "/api/v1/pedidos/vendas/", params=params)
        
    @handle_api_error
    @validate_api_response
    async def get_pedido(self, pedido_id: int) -> Dict[str, Any]:
        """Get a specific order.
        
        Args:
            pedido_id: Order ID
            
        Returns:
            Order data
        """
        return await self._request("GET", f"/api/v1/pedidos/vendas/{pedido_id}/")
        
    @handle_api_error
    @validate_api_response
    async def create_pedido(self, pedido: PedidoDeVenda) -> Dict[str, Any]:
        """Create a new order.
        
        Args:
            pedido: Order data
            
        Returns:
            Created order data
        """
        return await self._request("POST", "/api/v1/pedidos/vendas/", data=pedido.model_dump())
        
    @handle_api_error
    @validate_api_response
    async def update_pedido(self, pedido_id: int, pedido: PedidoDeVenda) -> Dict[str, Any]:
        """Update an order.
        
        Args:
            pedido_id: Order ID
            pedido: Updated order data
            
        Returns:
            Updated order data
        """
        return await self._request(
            "PATCH",
            f"/api/v1/pedidos/vendas/{pedido_id}/",
            data=pedido.model_dump(exclude_unset=True)
        )
        
    @handle_api_error
    @validate_api_response
    async def get_regras_frete(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        ordering: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get list of shipping rules.
        
        Args:
            limit: Number of results to return
            offset: Starting position
            search: Search term
            ordering: Order by field
            
        Returns:
            List of shipping rules
        """
        params = {
            "limit": limit,
            "offset": offset,
            "search": search,
            "ordering": ordering
        }
        return await self._request("GET", "/api/v1/regras/frete/", params=params)
        
    @handle_api_error
    @validate_api_response
    async def get_regra_frete(self, regra_id: int) -> Dict[str, Any]:
        """Get a specific shipping rule.
        
        Args:
            regra_id: Shipping rule ID
            
        Returns:
            Shipping rule data
        """
        return await self._request("GET", f"/api/v1/regras/frete/{regra_id}/")
        
    @handle_api_error
    @validate_api_response
    async def create_regra_frete(self, regra: RegraDeFrete) -> Dict[str, Any]:
        """Create a new shipping rule.
        
        Args:
            regra: Shipping rule data
            
        Returns:
            Created shipping rule data
        """
        return await self._request("POST", "/api/v1/regras/frete/", data=regra.model_dump())
        
    @handle_api_error
    @validate_api_response
    async def update_regra_frete(self, regra_id: int, regra: RegraDeFrete) -> Dict[str, Any]:
        """Update a shipping rule.
        
        Args:
            regra_id: Shipping rule ID
            regra: Updated shipping rule data
            
        Returns:
            Updated shipping rule data
        """
        return await self._request(
            "PATCH",
            f"/api/v1/regras/frete/{regra_id}/",
            data=regra.model_dump(exclude_unset=True)
        )
        
    @handle_api_error
    @validate_api_response
    async def get_regras_negocio(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        ordering: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get list of business rules.
        
        Args:
            limit: Number of results to return
            offset: Starting position
            search: Search term
            ordering: Order by field
            
        Returns:
            List of business rules
        """
        params = {
            "limit": limit,
            "offset": offset,
            "search": search,
            "ordering": ordering
        }
        return await self._request("GET", "/api/v1/regras/negocio/", params=params)
        
    @handle_api_error
    @validate_api_response
    async def get_regra_negocio(self, regra_id: int) -> Dict[str, Any]:
        """Get a specific business rule.
        
        Args:
            regra_id: Business rule ID
            
        Returns:
            Business rule data
        """
        return await self._request("GET", f"/api/v1/regras/negocio/{regra_id}/")
        
    @handle_api_error
    @validate_api_response
    async def create_regra_negocio(self, regra: RegraDeNegocio) -> Dict[str, Any]:
        """Create a new business rule.
        
        Args:
            regra: Business rule data
            
        Returns:
            Created business rule data
        """
        return await self._request("POST", "/api/v1/regras/negocio/", data=regra.model_dump())
        
    @handle_api_error
    @validate_api_response
    async def update_regra_negocio(self, regra_id: int, regra: RegraDeNegocio) -> Dict[str, Any]:
        """Update a business rule.
        
        Args:
            regra_id: Business rule ID
            regra: Updated business rule data
            
        Returns:
            Updated business rule data
        """
        return await self._request(
            "PATCH",
            f"/api/v1/regras/negocio/{regra_id}/",
            data=regra.model_dump(exclude_unset=True)
        )
        
    @handle_api_error
    @validate_api_response
    async def verificar_cnpj(self, cnpj: str) -> Dict[str, Any]:
        """Verify CNPJ.
        
        Args:
            cnpj: CNPJ to verify
            
        Returns:
            Verification result
        """
        return await self._request("POST", "/api/tools/cnpj/verificar/", data={"cnpj": cnpj})
        
    @handle_api_error
    @validate_api_response
    async def finalizar_cadastro(self, cliente_id: int) -> Dict[str, Any]:
        """Finalize client registration in Omie API.
        
        Args:
            cliente_id: Client ID
            
        Returns:
            Registration result with codigo_cliente_omie
        """
        import logging
        from automagik.config import settings
        
        logger = logging.getLogger(__name__)
        
        # Check if environment is development
        is_development = settings.ENVIRONMENT == "development"
        development_param = "?development=true" if is_development else ""
        
        if is_development:
            logger.warning("Development mode detected: Will not send data to OMIE")
            
        return await self._request("GET", f"/api/v1/cadastro/finalizar/{cliente_id}/{development_param}")

    # --- PedidoDeVenda Methods ---

    @handle_api_error
    @validate_api_response
    async def create_pedido_venda(self, pedido: PedidoDeVenda) -> Dict[str, Any]:
        """Create a new sales order.
        
        Args:
            pedido: Sales order data
            
        Returns:
            Created sales order data
        """
        return await self._request("POST", "/api/v1/pedidos/vendas/", data=pedido.model_dump())

    @handle_api_error
    @validate_api_response
    async def get_pedido_venda(self, pedido_id: int) -> Dict[str, Any]:
        """Get a specific sales order.
        
        Args:
            pedido_id: Sales order ID
            
        Returns:
            Sales order data
        """
        return await self._request("GET", f"/api/v1/pedidos/vendas/{pedido_id}/")

    @handle_api_error
    @validate_api_response
    async def list_pedidos_venda(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        ordering: Optional[str] = None,
        **filters
    ) -> Dict[str, Any]:
        """Get list of sales orders.
        
        Args:
            limit: Number of results to return
            offset: Starting position
            search: Search term
            ordering: Order by field
            **filters: Additional filters (e.g., cliente_id, status_negociacao)
            
        Returns:
            List of sales orders
        """
        params = {
            "limit": limit,
            "offset": offset,
            "search": search,
            "ordering": ordering,
            **filters
        }
        return await self._request("GET", "/api/v1/pedidos/vendas/", params=params)

    @handle_api_error
    @validate_api_response
    async def update_pedido_venda(self, pedido_id: int, pedido_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a sales order (partial update).
        
        Args:
            pedido_id: Sales order ID
            pedido_data: Dictionary with fields to update (e.g., {'pagamento': payment_id})
            
        Returns:
            Updated sales order data
        """
        # Note: Assumes API uses PATCH and accepts partial updates.
        # If a specific PatchedPedidoDeVenda schema is needed, adjust accordingly.
        return await self._request(
            "PATCH",
            f"/api/v1/pedidos/vendas/{pedido_id}/",
            data=pedido_data
        )
        
    @handle_api_error
    @validate_api_response
    async def aprovar_pedido(self, pedido_id: int) -> Dict[str, Any]:
        """Approve a sales order (triggers Omie registration).
        
        Args:
            pedido_id: Sales order ID
            
        Returns:
            Approval result (potentially including codigo_pedido_omie)
        """
        return await self._request("GET", f"/api/v1/pedidos/aprovar/{pedido_id}/")

    # --- ItemDePedido Methods ---

    @handle_api_error
    @validate_api_response
    async def create_pedido_item(self, item: ItemDePedidoCreate) -> Dict[str, Any]:
        """Create a new order item.
        
        Args:
            item: Order item data conforming to ItemDePedidoCreate
            
        Returns:
            Created order item data
        """
        # Ensure 'pedido' and 'produto' are integers if passed as part of ItemDePedido model
        item_data = item.model_dump()
        return await self._request("POST", "/api/v1/pedidos/items/", data=item_data)

    @handle_api_error
    @validate_api_response
    async def get_pedido_item(self, item_id: int) -> Dict[str, Any]:
        """Get a specific order item.
        
        Args:
            item_id: Order item ID
            
        Returns:
            Order item data
        """
        return await self._request("GET", f"/api/v1/pedidos/items/{item_id}/")

    @handle_api_error
    @validate_api_response
    async def list_pedido_items(
        self,
        pedido_id: Optional[int] = None, # Add pedido_id filter
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        ordering: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get list of order items.
        
        Args:
            pedido_id: Filter items by sales order ID (optional)
            limit: Number of results to return
            offset: Starting position
            search: Search term
            ordering: Order by field
            
        Returns:
            List of order items
        """
        params = {
            "pedido": pedido_id, # Map to API query parameter if needed
            "limit": limit,
            "offset": offset,
            "search": search,
            "ordering": ordering
        }
        return await self._request("GET", "/api/v1/pedidos/items/", params=params)

    @handle_api_error
    @validate_api_response
    async def update_pedido_item(self, item_id: int, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an order item (partial update).
        
        Args:
            item_id: Order item ID
            item_data: Dictionary with fields to update (e.g., {'quantidade': 5})
            
        Returns:
            Updated order item data
        """
        # Note: Assumes API uses PATCH and accepts partial updates.
        # If a specific PatchedItemDePedido schema is needed, adjust accordingly.
        return await self._request(
            "PATCH",
            f"/api/v1/pedidos/items/{item_id}/",
            data=item_data
        )

    @handle_api_error
    @validate_api_response
    async def delete_pedido_item(self, item_id: int) -> None:
        """Delete an order item.
        
        Args:
            item_id: Order item ID
            
        Returns:
            None on success (HTTP 204)
        """
        await self._request("DELETE", f"/api/v1/pedidos/items/{item_id}/")
        
    # --- CondicaoDePagamento Methods ---
    
    @handle_api_error
    @validate_api_response
    async def list_condicoes_pagamento(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        ordering: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get list of payment conditions.
        
        Args:
            limit: Number of results to return
            offset: Starting position
            search: Search term
            ordering: Order by field
            
        Returns:
            List of payment conditions
        """
        params = {
            "limit": limit,
            "offset": offset,
            "search": search,
            "ordering": ordering
        }
        return await self._request("GET", "/api/v1/pedidos/pagamento/", params=params)