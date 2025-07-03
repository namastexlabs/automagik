"""User identification and context enrichment for Flashinho Pro.

This module handles matching WhatsApp/Evolution users with Flashed API users
and populating the prompt variables with user-specific data.
"""

import logging
from typing import Dict, Optional, Any, List
import re
from datetime import datetime

from automagik.tools.flashed.tool import (
    get_user_data, get_user_score, get_user_roadmap, 
    get_user_objectives, get_last_card_round, get_user_energy,
    get_user_by_pretty_id
)

logger = logging.getLogger(__name__)


class FlashinhoProUserMatcher:
    """Handles user identification and context enrichment for Flashinho Pro."""
    
    def __init__(self, context: Dict[str, Any]):
        """Initialize with agent context containing channel information."""
        self.context = context
        self.flashed_user_id: Optional[str] = None
        self.user_variables: Dict[str, Any] = {}
        
    def normalize_phone_number(self, phone: str) -> str:
        """Normalize phone number for matching.
        
        Args:
            phone: Raw phone number from Evolution/WhatsApp
            
        Returns:
            Normalized phone number for comparison
        """
        if not phone:
            return ""
            
        # Remove all non-digit characters
        phone_digits = re.sub(r'\D', '', phone)
        
        # Brazilian phone number normalization
        if phone_digits.startswith('55') and len(phone_digits) > 2:
            # Remove Brazil country code if present
            phone_digits = phone_digits[2:]
            
        # Remove leading zeros
        phone_digits = phone_digits.lstrip('0')
        
        return phone_digits
    
    def extract_pretty_id_from_message(self, message: str) -> Optional[str]:
        """Extract prettyId from the standard WhatsApp identification message.
        
        Expected message format:
        "Olá, quero conversar com o Flashinho!\nMeu código de conversa: {prettyId}"
        
        Args:
            message: The user's message text
            
        Returns:
            The extracted prettyId if found, None otherwise
        """
        if not message:
            return None
            
        # Pattern to match the specific message format
        # Looking for "Meu código de conversa:" followed by the prettyId
        pattern = r"(?i)meu\s+código\s+de\s+conversa:\s*([A-Za-z0-9]+)"
        
        match = re.search(pattern, message)
        if match:
            pretty_id = match.group(1).strip()
            logger.info(f"Extracted prettyId from message: {pretty_id}")
            return pretty_id
            
        # Alternative pattern - sometimes the message might have variations
        # Looking for "código:" followed by alphanumeric characters
        alt_pattern = r"(?i)código:\s*([A-Za-z0-9]+)"
        alt_match = re.search(alt_pattern, message)
        if alt_match:
            pretty_id = alt_match.group(1).strip()
            logger.info(f"Extracted prettyId using alternative pattern: {pretty_id}")
            return pretty_id
            
        return None
    
    async def identify_user(self, message_text: Optional[str] = None) -> Optional[str]:
        """Identify Flashed user from Evolution/WhatsApp context.
        
        Args:
            message_text: Optional message text to extract prettyId from
        
        Returns:
            Flashed user ID if found, None otherwise
        """
        try:
            # Strategy 0: Check for prettyId in message first (highest priority)
            if message_text:
                pretty_id = self.extract_pretty_id_from_message(message_text)
                if pretty_id:
                    user_data = await self._find_user_by_pretty_id(pretty_id)
                    if user_data and user_data.get("user", {}).get("id"):
                        user_id = user_data["user"]["id"]
                        self.flashed_user_id = user_id
                        logger.info(f"Found user via prettyId {pretty_id}: {user_id}")
                        # Update context with user data for future use
                        self.context["flashed_user_id"] = user_id
                        self.context["user_identification_method"] = "prettyId"
                        return user_id
            
            # Extract phone and email from Evolution context
            whatsapp_phone = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
            user_email = self.context.get("user_email")
            
            if not whatsapp_phone and not user_email:
                logger.warning("No phone number, email, or prettyId available for user identification")
                return None
                
            # Normalize phone number if available
            normalized_phone = self.normalize_phone_number(whatsapp_phone) if whatsapp_phone else None
            
            logger.info(f"Attempting to identify user with phone: {normalized_phone}, email: {user_email}")
            
            # Strategy 1: Try exact user_id if provided in context
            if self.context.get("flashed_user_id"):
                user_id = self.context["flashed_user_id"]
                if await self._validate_user_exists(user_id):
                    self.flashed_user_id = user_id
                    logger.info(f"Found user via direct ID: {user_id}")
                    return user_id
                    
            # Strategy 2: Phone number matching (primary method)
            if normalized_phone:
                user_id = await self._find_user_by_phone(normalized_phone)
                if user_id:
                    self.flashed_user_id = user_id
                    logger.info(f"Found user via phone matching: {user_id}")
                    return user_id
                    
            # Strategy 3: Email matching (fallback)
            if user_email:
                user_id = await self._find_user_by_email(user_email)
                if user_id:
                    self.flashed_user_id = user_id
                    logger.info(f"Found user via email matching: {user_id}")
                    return user_id
                    
            logger.warning(f"No Flashed user found for phone: {normalized_phone}, email: {user_email}")
            return None
            
        except Exception as e:
            logger.error(f"Error identifying user: {str(e)}")
            return None
    
    async def _validate_user_exists(self, user_id: str) -> bool:
        """Validate that a user exists in Flashed API.
        
        Args:
            user_id: Flashed user ID to validate
            
        Returns:
            True if user exists, False otherwise
        """
        try:
            # Create temporary context with the user_id
            temp_context = {"user_id": user_id}
            user_data = await get_user_data(temp_context)
            return user_data is not None and "user" in user_data
        except Exception as e:
            logger.error(f"Error validating user {user_id}: {str(e)}")
            return False
    
    async def _find_user_by_phone(self, normalized_phone: str) -> Optional[str]:
        """Find user by phone number.
        
        Args:
            normalized_phone: Normalized phone number
            
        Returns:
            User ID if found, None otherwise
        """
        try:
            from .user_lookup import find_user_by_phone
            return await find_user_by_phone(normalized_phone)
        except Exception as e:
            logger.error(f"Error in phone lookup for {normalized_phone}: {str(e)}")
            return None
    
    async def _find_user_by_email(self, email: str) -> Optional[str]:
        """Find user by email address.
        
        Args:
            email: User email address
            
        Returns:
            User ID if found, None otherwise
        """
        try:
            from .user_lookup import find_user_by_email
            return await find_user_by_email(email)
        except Exception as e:
            logger.error(f"Error in email lookup for {email}: {str(e)}")
            return None

    async def _find_user_by_pretty_id(self, pretty_id: str) -> Optional[Dict[str, Any]]:
        """Find user by prettyId using the Flashed API.
        
        Args:
            pretty_id: User prettyId (conversation code)
            
        Returns:
            User data if found, None otherwise
        """
        try:
            # Create a simple context for the API call
            # The get_user_by_pretty_id function requires a context parameter for PydanticAI compatibility
            temp_context = {"pretty_id": pretty_id}
            return await get_user_by_pretty_id(temp_context, pretty_id)
        except Exception as e:
            logger.error(f"Error in prettyId lookup for {pretty_id}: {str(e)}")
            return None
    
    async def load_user_variables(self) -> Dict[str, Any]:
        """Load all user variables for prompt substitution.
        
        Returns:
            Dictionary mapping variable names to values
        """
        if not self.flashed_user_id:
            logger.warning("No Flashed user ID available, returning empty variables")
            return {}
            
        try:
            # Create context with user_id for API calls
            api_context = {"user_id": self.flashed_user_id}
            
            # Parallel API calls for efficiency
            user_data_response = await get_user_data(api_context)
            score_response = await get_user_score(api_context)
            roadmap_response = await get_user_roadmap(api_context)
            objectives_response = await get_user_objectives(api_context)
            last_card_response = await get_last_card_round(api_context)
            energy_response = await get_user_energy(api_context)
            
            # Extract and normalize data
            variables = {}
            
            # User profile data
            if user_data_response and "user" in user_data_response:
                user = user_data_response["user"]
                variables.update({
                    "name": user.get("name", "Estudante"),
                    "createdAt": self._format_date(user.get("createdAt")),
                    # These would come from user metadata if available
                    "levelOfEducation": user.get("metadata", {}).get("levelOfEducation", "Ensino Médio"),
                    "preferredSubject": user.get("metadata", {}).get("preferredSubject", ""),
                })
            
            # Score and progress data
            if score_response and "score" in score_response:
                score = score_response["score"]
                variables.update({
                    "flashinhoEnergy": score.get("flashinhoEnergy", 100),
                    "sequence": score.get("sequence", 0),
                    "dailyProgress": score.get("dailyProgress", 0),
                    "starsBalance": score.get("starsBalance", 0),  # Assuming this field exists
                })
            
            # Energy data (might be redundant with score)
            if energy_response and "energyLeft" in energy_response:
                variables["flashinhoEnergy"] = energy_response["energyLeft"]
            
            # Roadmap data
            if roadmap_response and "roadmap" in roadmap_response:
                roadmap = roadmap_response["roadmap"]["roadmap"]
                next_subject = roadmap.get("nextSubjectToStudy", {})
                variables["roadmap"] = next_subject.get("name", "Próxima matéria")
            
            # Last card play data
            if last_card_response and "lastRoundPlayed" in last_card_response:
                last_round = last_card_response["lastRoundPlayed"]
                
                # Determine result from card plays
                card_plays = last_round.get("cardPlays", [])
                if card_plays:
                    last_play = card_plays[-1]  # Get most recent play
                    # Determine correctness handling boolean or string values like "right"/"wrong"
                    result_val = last_play.get("result")
                    if isinstance(result_val, bool):
                        is_correct = result_val
                    else:
                        # Normalise string result values; treat "right"/"correct" as correct
                        is_correct = str(result_val).lower() in {"right", "correct", "certo", "true", "verdadeiro"}

                    variables.update({
                        "last_cardPlay_result": "certo" if is_correct else "errado",
                        "last_cardPlay_category": last_round.get("subcategory", {}).get("name", ""),
                        "last_cardPlay_topic": last_play.get("card", {}).get("topic", ""),
                        "last_cardPlay_date": self._format_date(last_round.get("completedAt")),
                    })
                
                variables["lastActivity"] = self._format_date(last_round.get("completedAt"))
            
            # Objectives data
            if objectives_response and "objectives" in objectives_response:
                objectives = objectives_response["objectives"]
                if objectives:
                    last_objective = objectives[-1]  # Get most recent objective
                    topics = [topic.get("name", "") for topic in last_objective.get("topics", [])]
                    variables.update({
                        "last_objectiveCreated_type": last_objective.get("type", ""),
                        "last_objectiveCreated_topics": ", ".join(topics),
                        "last_objectiveCreated_duedate": self._format_date(last_objective.get("dueDate")),
                    })
            
            # Default values for missing variables
            default_variables = {
                "has_opted_in": "true",  # Assume opted in if using the system
                "onboardingCompleted": "true",  # Assume completed if they have data
                "interesses_detectados": "",  # Will be populated dynamically during conversation
            }
            
            # Merge with defaults, keeping existing values
            for key, default_value in default_variables.items():
                if key not in variables:
                    variables[key] = default_value
            
            self.user_variables = variables
            logger.info(f"Loaded {len(variables)} user variables for user {self.flashed_user_id}")
            return variables
            
        except Exception as e:
            logger.error(f"Error loading user variables: {str(e)}")
            return {}
    
    def _format_date(self, date_str: Optional[str]) -> str:
        """Format date string for display.
        
        Args:
            date_str: ISO date string
            
        Returns:
            Formatted date string
        """
        if not date_str:
            return ""
            
        try:
            # Parse ISO date and format for Brazilian Portuguese
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%d/%m/%Y")
        except Exception:
            return date_str  # Return original if parsing fails
    
    async def get_enriched_context(self, message_text: Optional[str] = None) -> Dict[str, Any]:
        """Get complete enriched context for Flashinho Pro.
        
        Args:
            message_text: Optional message text to extract prettyId from
        
        Returns:
            Context dictionary with user variables and identification info
        """
        # Identify user first (with message text for prettyId detection)
        user_id = await self.identify_user(message_text)
        
        # Load variables if user found
        if user_id:
            variables = await self.load_user_variables()
        else:
            variables = self._get_default_variables()
        
        # Return enriched context
        enriched_context = self.context.copy()
        enriched_context.update({
            "flashed_user_id": user_id,
            "user_variables": variables,
            "flashinho_pro_ready": True,
        })
        
        return enriched_context
    
    def _get_default_variables(self) -> Dict[str, Any]:
        """Get default variables when user is not identified.
        
        Returns:
            Dictionary with default variable values
        """
        user_name = (
            self.context.get("whatsapp_user_name") or 
            self.context.get("user_name") or 
            "Estudante"
        )
        
        return {
            "name": user_name,
            "levelOfEducation": "Ensino Médio",
            "preferredSubject": "",
            "has_opted_in": "false",
            "onboardingCompleted": "false",
            "dailyProgress": 0,
            "sequence": 0,
            "flashinhoEnergy": 100,
            "starsBalance": 0,
            "createdAt": "",
            "roadmap": "Comece criando sua primeira revisão!",
            "last_cardPlay_result": "",
            "last_cardPlay_category": "",
            "last_cardPlay_topic": "",
            "last_objectiveCreated_type": "",
            "last_objectiveCreated_topics": "",
            "last_objectiveCreated_duedate": "",
            "last_cardPlay_date": "",
            "lastActivity": "",
            "interesses_detectados": "",
        }


# Convenience function for agent integration
async def enrich_flashinho_pro_context(context: Dict[str, Any], message_text: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to enrich context for Flashinho Pro agent.
    
    Args:
        context: Original agent context
        message_text: Optional message text to extract prettyId from
        
    Returns:
        Enriched context with user variables
    """
    matcher = FlashinhoProUserMatcher(context)
    return await matcher.get_enriched_context(message_text)