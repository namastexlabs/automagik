"""Omie API provider implementation.

This module provides the API client implementation for interacting with the Omie API.
"""
import json
import logging
import os
from typing import Dict, Any, Optional
import requests

from .schema import ClientSearchInput, ClientSearchResult, ClientSimplifiedResult

logger = logging.getLogger(__name__)

class OmieProvider:
    """Client for interacting with the Omie API."""

    def __init__(self, app_key: Optional[str] = None, app_secret: Optional[str] = None):
        """Initialize the Omie API client.
        
        Args:
            app_key: Omie App Key
            app_secret: Omie App Secret
        """
        self.app_key = app_key or os.environ.get('OMIE_APP_KEY')
        self.app_secret = app_secret or os.environ.get('OMIE_APP_SECRET')
        
        if not self.app_key or not self.app_secret:
            logger.warning("Omie credentials not provided and not found in environment variables")
        else:
            logger.info("Initialized OmieProvider with credentials")
    
    def _validate_credentials(self) -> None:
        """Validate that app_key and app_secret are available."""
        if not self.app_key or not self.app_secret:
            raise ValueError("Omie API requires both app_key and app_secret. Set OMIE_APP_KEY and OMIE_APP_SECRET environment variables or provide them directly.")
            
    def _format_full_address(self, client: Dict[str, Any]) -> str:
        """Format full address from client data"""
        components = []
        
        # Add street and number
        if client.get('endereco'):
            address = f"{client['endereco']}"
            if client.get('endereco_numero'):
                address += f", {client['endereco_numero']}"
            components.append(address)
        
        # Add complement if exists
        if client.get('complemento'):
            components.append(client['complemento'])
            
        # Add neighborhood
        if client.get('bairro'):
            components.append(client['bairro'])
        
        # Add city and state
        location = []
        if client.get('cidade'):
            location.append(client['cidade'])
        if client.get('estado'):
            location.append(client['estado'])
        if location:
            components.append(" - ".join(location))
        
        # Add CEP
        if client.get('cep'):
            components.append(f"CEP: {client['cep']}")
        
        return " - ".join(components)

    def _simplify_client_data(self, client: Dict[str, Any]) -> Dict[str, Any]:
        """Extract essential information from client data"""
        # Format phone if exists
        phone = ""
        if client.get('telefone1_ddd') or client.get('telefone1_numero'):
            phone = f"{client.get('telefone1_ddd', '')} {client.get('telefone1_numero', '')}".strip()
        
        return {
            "codigo_cliente_omie": client.get("codigo_cliente_omie"),
            "codigo_cliente_integracao": client.get("codigo_cliente_integracao"),
            "razao_social": client.get("razao_social"),
            "nome_fantasia": client.get("nome_fantasia"),
            "cnpj_cpf": client.get("cnpj_cpf"),
            "email": client.get("email"),
            "telefone": phone,
            "inscricao_estadual": client.get("inscricao_estadual"),
            "full_address": self._format_full_address(client),
            "status": {
                "inativo": client.get("inativo"),
                "bloqueado": client.get("bloqueado"),
                "importado_api": client.get("importado_api")
            },
            "info": client.get("info", {})
        }
    
    def _build_search_payload(self, input: ClientSearchInput) -> Dict[str, Any]:
        """Build the API payload with search parameters."""
        self._validate_credentials()
        
        # Create the param object first
        param = {
            "pagina": input.pagina,
            "registros_por_pagina": input.registros_por_pagina,
            "apenas_importado_api": "S" if input.apenas_importado_api else "N",
        }

        # Add clientesFiltro if any search criteria is provided
        clientesFiltro = {}
        
        # Add search parameters if provided
        search_params = [
            'codigo_cliente_omie', 'codigo_cliente_integracao', 'cnpj_cpf',
            'email', 'razao_social', 'nome_fantasia'
        ]
        
        for param_name in search_params:
            if value := getattr(input, param_name, None):
                clientesFiltro[param_name] = value

        # Only add clientesFiltro if it has values
        if clientesFiltro:
            param["clientesFiltro"] = clientesFiltro

        # Build the final payload exactly matching the API format
        return {
            "call": "ListarClientes",
            "app_key": int(self.app_key) if self.app_key and self.app_key.isdigit() else self.app_key,
            "app_secret": self.app_secret,
            "param": [param]  # Note: param is wrapped in a list as shown in the example
        }
        
    async def search_clients(self, input: ClientSearchInput) -> ClientSearchResult:
        """Search clients from Omie API with various search options.
        
        Args:
            input: Search parameters
            
        Returns:
            Search results
        """
        logger.info("Starting Omie client search process")
        
        try:
            # Validate at least one search parameter
            search_params = [
                'codigo_cliente_omie', 'codigo_cliente_integracao', 'cnpj_cpf',
                'email', 'razao_social', 'nome_fantasia'
            ]
            
            has_search_param = any(getattr(input, param, None) for param in search_params)
            if not has_search_param:
                logger.warning("No search parameters provided")
            
            # Build API payload
            payload = self._build_search_payload(input)
            
            # Log payload (with sensitive data redacted)
            safe_payload = {**payload}
            safe_payload["app_key"] = "[REDACTED]"
            safe_payload["app_secret"] = "[REDACTED]"
            logger.info(f"Request payload prepared: {json.dumps(safe_payload, indent=2)}")

            # Make API request
            url = "https://app.omie.com.br/api/v1/geral/clientes/"
            headers = {"Content-Type": "application/json"}
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            api_response = response.json()

            # Extract clients list and pagination info
            clients_list = api_response.get("clientes_cadastro", [])
            current_page = api_response.get("pagina", 1)
            total_pages = api_response.get("total_de_paginas", 0)
            total_records = api_response.get("total_de_registros", 0)
            records_per_page = api_response.get("registros", 0)

            # Process client data based on simplified_info flag
            processed_clients = [
                self._simplify_client_data(client) if input.simplified_info else client
                for client in clients_list
            ]

            # Create success response
            result = {
                "clients": processed_clients,
                "pagination": {
                    "page": current_page,
                    "total_pages": total_pages,
                    "total_records": total_records,
                    "records_per_page": records_per_page,
                    "current_page_count": len(processed_clients)
                },
                "raw_response": api_response if not input.simplified_info else None
            }

            logger.info(f"Search completed successfully. Found {len(processed_clients)} clients.")
            
            return ClientSearchResult(
                success=True,
                data=result
            )

        except requests.exceptions.HTTPError as e:
            error_message = f"HTTP error: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            
            return ClientSearchResult(
                success=False,
                error=error_message
            )

        except Exception as e:
            error_message = f"Error searching clients: {str(e)}"
            logger.error(error_message)
            
            return ClientSearchResult(
                success=False,
                error=error_message
            )
    
    async def search_client_by_cnpj(self, cnpj: str) -> ClientSimplifiedResult:
        """Search for a client by CNPJ.
        
        Args:
            cnpj: The CNPJ to search for
            
        Returns:
            Client information
        """
        logger.info(f"Searching for client with CNPJ: {cnpj}")
        
        # Create input model for search
        input = ClientSearchInput(
            cnpj_cpf=cnpj,
            simplified_info=True,
            pagina=1,
            registros_por_pagina=1
        )
        
        # Perform search
        result = await self.search_clients(input)
        
        # Extract client data if found
        if result.success and result.data:
            clients = result.data.get("clients", [])
            if clients:
                return ClientSimplifiedResult(
                    success=True,
                    client=clients[0]
                )
                
        # Return error or empty result
        return ClientSimplifiedResult(
            success=False,
            error=result.error or "Client not found"
        ) 