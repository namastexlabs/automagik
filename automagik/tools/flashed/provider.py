"""Flashed API provider.

This module provides the API client implementation for interacting with the Flashed API.
"""
import logging
from typing import Optional, Dict, Any, List
import aiohttp
# from automagik.tools.blackpearl.interface import validate_api_response, handle_api_error, format_api_request, filter_none_params
from automagik.tools.flashed.interface import format_api_request, filter_none_params
from automagik.config import settings
import uuid

logger = logging.getLogger(__name__)


class FlashedProvider():
    """Client for interacting with the Flashed API."""

    def __init__(self):
        """Initialize the API client.
        
        Args:
        """
        # Store credentials without immediate validation
        self.base_url = settings.FLASHED_API_URL.rstrip('/') if settings.FLASHED_API_URL else None
        self.auth_token = settings.FLASHED_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Warn about missing credentials but don't raise errors
        if not self.base_url or not self.auth_token:
            missing = []
            if not self.base_url:
                missing.append("FLASHED_API_URL")
            if not self.auth_token:
                missing.append("FLASHED_API_KEY")
            logger.warning(f"Flashed credentials not provided: missing {', '.join(missing)}. Set environment variables or agent will have limited functionality.")
        else:
            logger.info("Initialized FlashedProvider with credentials")
        
        # Initialize mock data for testing - in production this would be a real API client
        self._mock_pro_users = [
            "123e4567-e89b-12d3-a456-426614174000",  # Test Pro user
            "550e8400-e29b-41d4-a716-446655440000",  # Another test Pro user
            "c0743fb7-7765-4cf0-9ab6-90a196a1559a",  # Cezar - test user
        ]
        
        # Mock conversation codes for testing
        self._mock_conversation_codes = {
            "1bl1UKm0JC": "c0743fb7-7765-4cf0-9ab6-90a196a1559a",  # Pro user code
            "FreeMock99": "aaaaaaaa-bbbb-cccc-dddd-ffffffffffff",  # Free user mock code (valid UUID format, 10 chars)
        }

    def _validate_credentials(self) -> None:
        """Validate that API URL and key are available."""
        if not self.base_url or not self.auth_token:
            missing = []
            if not self.base_url:
                missing.append("FLASHED_API_URL")
            if not self.auth_token:
                missing.append("FLASHED_API_KEY")
            raise ValueError(f"Flashed API requires credentials. Missing: {', '.join(missing)}. Set environment variables: {', '.join(missing)}.")
        
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
            settings.AUTOMAGIK_ENV.value == "development" and
            settings.AUTOMAGIK_LOG_LEVEL == "DEBUG"
        )
        
        logger.info(f"Flashed - API Request: {method} {url}")
        if is_dev_debug:
            logger.debug(f"Flashed - Request Payload (detailed): {data}")
            logger.debug(f"Flashed - Request Params (detailed): {params}")
            logger.debug(f"Flashed - Request Headers (detailed): {header}")
        else:
            logger.info(f"Flashed - Request Payload: {data}")
            logger.info(f"Flashed - Request Params: {params}")
            logger.info(f"Flashed - Request Headers: {header}")
        
        try:
            async with self.session.request(method, url, json=data, params=params, headers=header) as response:
                response.raise_for_status()
                result = await response.json()
                
                # Enhanced logging for API responses in development/debug mode
                if is_dev_debug:
                    logger.debug(f"Flashed - API Response Status: {response.status}")
                    logger.debug(f"Flashed - API Response Headers: {dict(response.headers)}")
                    logger.debug(f"Flashed - API Response (detailed): {result}")
                    
                    # Check if there are any error messages in the response
                    if isinstance(result, dict) and result.get('error'):
                        logger.debug(f"Flashed - API Error Message: {result.get('error')}")
                        if result.get('message'):
                            logger.debug(f"Flashed - API Error Details: {result.get('message')}")
                else:
                    logger.info(f"Flashed - API Response Status: {response.status}")
                
                return result
        except aiohttp.ClientResponseError as e:
            # Enhanced error logging in development/debug mode
            if is_dev_debug:
                logger.debug(f"Flashed - API Error: {str(e)}")
                logger.debug(f"Flashed - API Error Status: {e.status}")
                logger.debug(f"Flashed - API Error Message: {e.message}")
                
                # Try to get the response body for more details
                try:
                    if hasattr(e, 'history') and e.history:
                        response_text = await e.history[0].text()
                        logger.debug(f"Flashed - API Error Response: {response_text}")
                except Exception as text_error:
                    logger.debug(f"Flashed - Could not read error response: {str(text_error)}")
            
            raise

    async def get_user_data(self, user_uuid: str) -> Dict[str, Any]:
        """Get user data.
        
        Args:
            user_uuid: User UUID
            
        Returns:
            User data (cadastro & metadata)
        """
        return await self._request("GET", f"/user/{user_uuid}", header={"Authorization": self.auth_token})

    async def get_user_score(self, user_uuid: str) -> Dict[str, Any]:
        """Get general user stats.
        
        Args:
            user_uuid: User UUID
            
        Returns:
            User stats (daily_progress, energy, sequence)
        """
        return await self._request("GET", f"/user-score/{user_uuid}", header={"Authorization": self.auth_token})
    
    async def get_user_roadmap(self, user_uuid: str) -> Dict[str, Any]:
        """Get the study roadmap for a given user.
        
        Args:
            user_uuid: User UUID
            
        Returns:
            User roadmap data containing:
            - roadmap: Object with roadmap information:
              - updatedAt: Timestamp of last update
              - isOutdated: Boolean indicating if roadmap is outdated
              - roadmap: Object containing:
                - roadmap: Array of subject objects with:
                  - status: Current status (todo, in_progress, completed)
                  - subject: Subject name
                  - objectiveId: Related objective identifier
                  - subcategories: Array of subcategories with:
                    - id: Subcategory identifier
                    - name: Subcategory name
                    - order: Order in the roadmap
                    - totalPills: Total number of study pills
                    - playedPills: Number of pills played
                    - percentageHit: Hit percentage
                    - playedPillsHit: Number of correctly answered pills
                    - percentagePlayed: Percentage of pills played
                    - playedPillsError: Number of incorrectly answered pills
                    - performanceStatus: Performance status indicator
                - nextSubjectToStudy: Next recommended subject with same structure as roadmap items
                - objectivesProgress: Object mapping objective IDs to progress percentage
                - currentRoadmapPosition: Current position in the roadmap
              - roadmapsByObjectives: Object mapping objective IDs to specific roadmaps
        """
        return await self._request("GET", f"/user-roadmap/{user_uuid}", header={"Authorization": self.auth_token})

    async def get_user_objectives(self, user_uuid: str) -> Dict[str, Any]:
        """Get user objectives ordered by completion date (ascending).
        
        Args:
            user_uuid: User UUID
            
        Returns:
            Object containing:
            - objectives: Array of objective objects with:
              - id: Objective identifier
              - createdAt: Creation timestamp
              - updatedAt: Last update timestamp
              - type: Objective type (e.g., "schoolExam")
              - dueDate: Target completion date
              - name: Short objective name
              - subject: Subject name
              - topics: Array of topic objects:
                - id: Topic identifier
                - name: Topic name
                - subcategories: Array of subcategory objects:
                  - id: Subcategory identifier
                  - name: Subcategory name
              - userId: Owner user ID
              - courseId: Related course ID (if any)
              - progress: Completion progress (0-100)
        """
        return await self._request("GET", f"/user-objectives/{user_uuid}", header={"Authorization": self.auth_token})
    
    async def get_last_card_round(self, user_uuid: str) -> Dict[str, Any]:
        """Get the data for the last study cards round.
        
        Args:
            user_uuid: User UUID
            
        Returns:
            Object containing:
            - content: Object with last round information:
              - lastRoundPlayed: Object with details about the last round:
                - id: Round identifier
                - createdAt: Creation timestamp
                - completed: Whether the round was completed
                - completedAt: Completion timestamp
                - subcategory: Object with subcategory information:
                  - id: Subcategory identifier
                  - createdAt/updatedAt: Timestamps
                  - level1/level2/level3: Hierarchical categories
                  - name: Subcategory name
                  - code/courseId: Additional identifiers
                - objective: Object with objective information (similar to get_user_objectives output)
                - cards: Array of card objects with:
                  - id: Card identifier
                  - createdAt/updatedAt: Timestamps
                  - deckId: Related deck identifier
                  - order: Card position in round
                  - level: Difficulty level (easy, medium, hard)
                  - category/topic: Subject categorization
                  - subcategoryId: Related subcategory
                  - type: Card type (e.g., quiz)
                  - question: Question text
                  - answers: Array of possible answers
                  - answerIndex: Index of correct answer
                  - comment: Detailed explanation
                  - summary: Condensed explanation
                  - additional metadata fields
                - cardPlays: Array of play result objects:
                  - id: Play identifier
                  - date: Timestamp of play
                  - userId: User who played
                  - cardId: Related card
                  - result: Outcome (right/wrong)
                  - durationSec: Time spent on card
                  - roundId: Related round
        """
        return await self._request("GET", f"/user-plays/{user_uuid}", header={"Authorization": self.auth_token})
    
    async def get_user_energy(self, user_uuid: str) -> Dict[str, Any]:
        """Get user energy information.
        
        Args:
            user_uuid: User UUID
            
        Returns:
            User energy data
        """
        return await self._request("GET", f"/check-energy/{user_uuid}", header={"Authorization": self.auth_token})
    
    async def check_user_pro_status(self, user_id: Optional[str] = None) -> bool:
        """Check if user has Pro status.
        
        Args:
            user_id: User ID to check
            
        Returns:
            bool: True if user has Pro status, False otherwise
        """
        if not user_id:
            return False
            
        try:
            # Convert string UUID to UUID object if needed
            if isinstance(user_id, str):
                try:
                    user_id_obj = str(uuid.UUID(user_id))
                except ValueError:
                    logger.error(f"Invalid UUID format for user_id: {user_id}")
                    return False
            else:
                user_id_obj = str(user_id)
                
            # For testing purposes, we'll mock some Pro users
            # In production, this would be a call to the subscription API
            is_pro = user_id_obj in self._mock_pro_users
            
            if is_pro:
                logger.info(f"User {user_id} has Pro subscription")
            else:
                logger.info(f"User {user_id} has Free subscription")
                
            return is_pro
                
        except Exception as e:
            logger.error(f"Error checking Pro status: {e}")
            # Default to non-Pro on error
            return False
    
    async def search_users(self, email: str = None, phone: str = None, name: str = None) -> Dict[str, Any]:
        """Search for users by email, phone, or name.
        
        Args:
            email: User email address (optional)
            phone: User phone number (optional)
            name: User name (optional)
            
        Returns:
            List of matching users or empty list if none found
        """
        params = {}
        if email:
            params["email"] = email
        if phone:
            params["phone"] = phone
        if name:
            params["name"] = name
            
        return await self._request(
            "GET", 
            "/users/search", 
            params=params,
            header={"Authorization": self.auth_token}
        )
        
    async def get_user_by_email(self, email: str) -> Dict[str, Any]:
        """Find a user by their email address.
        
        Args:
            email: User email address
            
        Returns:
            First matching user or None if not found
        """
        try:
            result = await self.search_users(email=email)
            users = result.get("users", [])
            return users[0] if users else None
        except Exception as e:
            logger.error(f"Error finding user by email: {str(e)}")
            return None

    async def get_user_by_pretty_id(self, pretty_id: str) -> Dict[str, Any]:
        """Get user data by their prettyId.
        
        Args:
            pretty_id: User prettyId (conversation code)
            
        Returns:
            User data containing:
            - user: Object with user information:
              - id: User UUID
              - createdAt: Account creation timestamp
              - name: Full name
              - phone: Contact phone number
              - email: Email address
              - birthDate: Date of birth
              - metadata: Additional user metadata
        """
        # Check for mock conversation codes first
        if pretty_id in self._mock_conversation_codes:
            user_id = self._mock_conversation_codes[pretty_id]
            logger.info(f"Using mock conversation code {pretty_id} -> user {user_id}")
            
            # Return mock user data based on the conversation code
            if pretty_id == "FreeMock99":
                return {
                    "user": {
                        "id": user_id,  # aaaaaaaa-bbbb-cccc-dddd-ffffffffffff
                        "createdAt": "2024-01-15T10:00:00Z",
                        "name": "Free User Mock",
                        "phone": "+5511888888888",
                        "email": "freeuser@mock.test",
                        "birthDate": "1995-01-01",
                        "metadata": {
                            "account_type": "free",
                            "mock_user": True
                        }
                    }
                }
            elif pretty_id == "1bl1UKm0JC":
                return {
                    "user": {
                        "id": user_id,
                        "createdAt": "2024-01-01T10:00:00Z",
                        "name": "Cezar Test User",
                        "phone": "+5511999999999",
                        "email": "cezar@test.com",
                        "birthDate": "1990-01-01",
                        "metadata": {
                            "account_type": "pro",
                            "mock_user": True
                        }
                    }
                }
        
        # Fallback to real API call for non-mock codes
        return await self._request("GET", f"/user/{pretty_id}", header={"Authorization": self.auth_token})

    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict[str, Any]: User preferences
        """
        # Mock implementation - in production this would fetch from an API
        return {
            "language": "en",
            "theme": "light",
            "notifications": True
        }
    
    async def get_user_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user interaction history.
        
        Args:
            user_id: User ID
            limit: Maximum number of history items to return
            
        Returns:
            List[Dict[str, Any]]: User history
        """
        # Mock implementation - in production this would fetch from an API
        return [
            {"timestamp": "2023-01-01T12:00:00Z", "action": "login"},
            {"timestamp": "2023-01-01T12:05:00Z", "action": "search", "query": "math help"},
            {"timestamp": "2023-01-01T12:10:00Z", "action": "view_lesson", "lesson_id": "algebra-101"}
        ]

    async def check_user_pro_status_by_phone(self, phone: str) -> Dict[str, Any]:
        """Check if user has Pro status available via phone number.
        
        Args:
            phone: User phone number
            
        Returns:
            Dict containing:
            - userId: User UUID
            - isWhatsappProAvailable: Boolean indicating Pro availability
            - llmModel: Recommended model ("light" or "pro")
            - userFeedbackMessage: Message for user (optional)
        """
        return await self._request("GET", f"/is-whatsapp-pro-available/{phone}", header={"Authorization": self.auth_token})