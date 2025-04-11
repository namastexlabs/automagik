"""Utility functions for the Stan Agent.

This module provides utility functions for the Stan Agent, such as managing
contact information and processing incoming messages.
"""
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from src.tools import blackpearl
from src.tools.blackpearl.schema import Contato, StatusAprovacaoEnum
from src.agents.simple.stan_agent.models import EvolutionMessagePayload

logger = logging.getLogger(__name__)

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
    if not user_number:
        return None
        
    # Try to find contact by phone number
    contacts_response = await blackpearl.get_contatos(context, search=user_number)
    
    # Check if we found any matching contacts
    if contacts_response and "results" in contacts_response and contacts_response["results"]:
        # Return the first matching contact
        contato = contacts_response["results"][0]
        return contato
            
    
    # No contact found, create a new one
    logger.info(f"Creating new contact for {user_name} with number {user_number}")
    
    # Generate wpp_session_id using user_id and agent_id
    wpp_session_id = f"{user_id}_{agent_id}_devmode"
    
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
        created_contact = await blackpearl.create_contato(context, contact_data)
        logger.info(f"Successfully created contact with ID: {created_contact.get('id')}")
        return created_contact
    except Exception as e:
        logger.error(f"Failed to create contact: {str(e)}")
        return None 