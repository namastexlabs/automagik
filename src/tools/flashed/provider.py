"""Flashed API provider.

This module provides the API client implementation for interacting with the Flashed API.
"""
import logging
import os
from typing import Optional, Dict, Any, List, Union
import aiohttp
# from src.tools.blackpearl.interface import validate_api_response, handle_api_error, format_api_request, filter_none_params
from src.tools.flashed.interface import format_api_request, filter_none_params
from src.config import settings
from .config import FLASHED_API_KEY

logger = logging.getLogger(__name__)

# Hardcoded for now
FLASHED_URL = "https://api.flashed.tech/admin/"

class FlashedProvider():
    """Client for interacting with the Flashed API."""

    def __init__(self):
        """Initialize the API client.
        
        Args:
        """
        self.base_url = (FLASHED_URL).rstrip('/')
        if not self.base_url:
            raise ValueError("API URL is not set. Provide a base URL or set FLASHED_URL environment variable.")
            
        self.session: Optional[aiohttp.ClientSession] = None

        self.auth_token = FLASHED_API_KEY
        if not self.auth_token:
            raise ValueError("Auth token not set. Provide a token or set the FLASHED_API_KEY environment variable.")

        
    async def __aenter__(self):
        """Create aiohttp session when entering context."""
        print("Inicializando sessão")
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
        params: Optional[Dict[str, Any]] = None,
        header: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an API request.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            header: HTTP headers, typically containing the Auth data
            
        Returns:
            API response data
        """
        if not self.session:
            raise RuntimeError("Client session not initialized")
            
        url = f"{self.base_url}{endpoint}"
        data = format_api_request(data) if data else None
        params = filter_none_params(params)
        header = header or {}        
        
        # Check if we're in development mode and debug log level
        is_dev_debug = (
            settings.AM_ENV.value == "development" and
            settings.AM_LOG_LEVEL.value == "DEBUG"
        )
        
        logger.info(f"BP - API Request: {method} {url}")
        if is_dev_debug:
            logger.debug(f"BP - Request Payload (detailed): {data}")
            logger.debug(f"BP - Request Params (detailed): {params}")
            logger.debug(f"BP - Request Headers (detailed): {header}")
        else:
            logger.info(f"BP - Request Payload: {data}")
            logger.info(f"BP - Request Params: {params}")
            logger.info(f"BP - Request Headers: {header}")
        
        try:
            async with self.session.request(method, url, json=data, params=params, headers=header) as response:
                response.raise_for_status()
                result = await response.json()
                
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
            
            raise

    async def get_user_data(self, user_uuid: str) -> Dict[str, Any]:
        """Get user data.
        
        Args:
            user_uuid: User UUID
            
        Returns:
            User data (cadastro & metadata)
        """

        print(f"Endpoint: /user/{user_uuid}")
        mock_user_data = {
            "cadastro": '9999-aaaa-!!!!',
            "metadata": {
                "uuid": user_uuid,
                "usuario_desde": "01/01/2025",
                "plano": "premium"
            }
        }
        return mock_user_data
        # print(f"Request to: /user/{user_uuid}/")
        # headers = {"Bearer Token": auth}
        # print(headers)
        # return await self._request("GET", f"/user/{user_uuid}", header=headers)

    async def get_user_score(self, user_uuid: str) -> Dict[str, Any]:
        """Get general user stats.
        
        Args:
            user_uuid: User UUID
            
        Returns:
            User stats (daily_progress, energy, streak)
        """
        print(f"Endpoint: /user-score/{user_uuid}")
        mock_user_data = {
            "daily_progress": 0.73,
            "energy": 33,
            "streak": 7,
        }
        return mock_user_data
    
    async def get_user_roadmap(self, user_uuid: str) -> Dict[str, Any]:
        """Get the study roadmap for a given user.
        
        Args:
            user_uuid: User UUID
            
        Returns:
            User roadmap data
        """
        print(f"Endpoint: /user-roadmap/{user_uuid}")
        mock_user_data = {
            "subjects": ["Quimica I","Biologia II","Trigonometria","Quimica II"],
            "due_date": "29/03/2025",
        }
        return mock_user_data

    async def get_user_objectives(self, user_uuid: str) -> Dict[str, Any]:
        """Get user objectives ordered by completion date (ascending).
        
        Args:
            user_uuid: User UUID
            
        Returns:
            List of objectives containing:
            - id: Objective identifier
            - title: Objective title
            - description: Detailed description
            - completion_date: Target completion date
            - status: Current status (pending, in_progress, completed)
            - priority: Priority level (low, medium, high)
        """
        print(f"Endpoint: /user-objectives/{user_uuid}")
        mock_objectives = {
            "objectives": [
                {
                    "id": "obj_001",
                    "title": "Completar exercícios de Química I",
                    "description": "Resolver todos os exercícios do capítulo de Estequiometria",
                    "completion_date": "15/03/2024",
                    "status": "in_progress",
                    "priority": "high"
                },
                {
                    "id": "obj_002",
                    "title": "Revisar Biologia II",
                    "description": "Revisar conteúdo sobre Genética e Evolução",
                    "completion_date": "20/03/2024",
                    "status": "pending",
                    "priority": "medium"
                },
                {
                    "id": "obj_003",
                    "title": "Praticar Trigonometria",
                    "description": "Resolver problemas de trigonometria aplicada",
                    "completion_date": "25/03/2024",
                    "status": "pending",
                    "priority": "high"
                },
                {
                    "id": "obj_004",
                    "title": "Estudar Química II",
                    "description": "Aprender conceitos de Termoquímica",
                    "completion_date": "30/03/2024",
                    "status": "pending",
                    "priority": "medium"
                }
            ]
        }
        return mock_objectives
    
    async def get_last_card_round(self, user_uuid: str) -> Dict[str, Any]:
        """Get the data for the last study cards round.
        
        Args:
            user_uuid: User UUID
            
        Returns:
            The Last Card Game Round data
        """
        print(f"Endpoint: /user-plays/{user_uuid}")
        mock_user_data = {
            "cards": [
                {
                    "id": "chemestry_hard_05",
                    "content": "demo card 1"
                },
                {
                    "id": "literature_hard_01",
                    "content": "demo card 2"
                },
                {
                    "id": "biology_medium_03",
                    "content": "demo card 3"
                },
                {
                    "id": "history_hard_05",
                    "content": "demo card 4"
                },
                {
                    "id": "chemestry_easy_07",
                    "content": "demo card 5"
                }
            ],
            "round_length": 5,
        }
        return mock_user_data
    
    async def get_user_energy(self, user_uuid: str) -> Dict[str, Any]:
        """Get the energy value for a given user.
        
        Args:
            user_uuid: User UUID
            
        Returns:
            User's energy value
        """
        print(f"Endpoint: /check-energy/{user_uuid}")
        mock_user_data = {
            "energy": 46,
        }
        return mock_user_data