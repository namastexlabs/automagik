from typing import Dict, Any
from pydantic_ai import RunContext
from automagik.tools.flashed.provider import FlashedProvider

def _extract_user_id(ctx_or_dict) -> str:
    """Extract user_id from either a RunContext object or plain context dictionary.
    
    Args:
        ctx_or_dict: Either a PydanticAI RunContext or a plain context dictionary
        
    Returns:
        user_id string
        
    Raises:
        ValueError: If user_id is not found
    """
    user_id = None
    
    # Case 1: Plain dictionary (from ToolWrapperFactory)
    if isinstance(ctx_or_dict, dict):
        user_id = ctx_or_dict.get("user_id")
    # Case 2: RunContext object (direct PydanticAI usage)
    elif hasattr(ctx_or_dict, 'deps') and ctx_or_dict.deps and hasattr(ctx_or_dict.deps, 'context'):
        user_id = ctx_or_dict.deps.context.get("user_id")
    # Case 3: RunContext with deps as dict-like
    elif hasattr(ctx_or_dict, 'deps') and hasattr(ctx_or_dict.deps, 'get'):
        user_id = ctx_or_dict.deps.get("user_id")
    
    if not user_id:
        raise ValueError("user_id not found in context")
    
    return user_id

async def get_user_data(ctx: RunContext[Dict]) -> Dict[str, Any]:
    """Get user data from a specific user registered in the Flashed API.
    
    Args:
        ctx: Agent context
        
    Returns:
        User Data containing:
        - user: Object with user information:
          - id: User UUID
          - createdAt: Account creation timestamp
          - name: Full name
          - phone: Contact phone number
          - email: Email address
          - birthDate: Date of birth
          - metadata: Additional user metadata:
            - levelOfEducation: Current education level
            - preferredSubject: Preferred study subject
    """
    provider = FlashedProvider()
    async with provider:
        user_id = _extract_user_id(ctx)
        return await provider.get_user_data(user_id)

async def get_user_score(ctx: RunContext[Dict]) -> Dict[str, Any]:
    """Get user score data including daily progress, energy and streak.
    
    Args:
        ctx: Agent context
        
    Returns:
        - score: User score data
            - flashinhoEnergy: User's current energy
            - sequence: Study streak
            - dailyProgress: Daily progress percentage
    """
    provider = FlashedProvider()
    async with provider:
        user_id = _extract_user_id(ctx)
        return await provider.get_user_score(user_id)

async def get_user_roadmap(ctx: RunContext[Dict]) -> Dict[str, Any]:
    """Get the study roadmap for a specific user from the Flashed API.
    
    Args:
        ctx: Agent context
        
    Returns:
        User roadmap data containing:
        - subjects: List of subjects to study
        - due_date: Target completion date
    """
    provider = FlashedProvider()
    async with provider:
        user_id = _extract_user_id(ctx)
        return await provider.get_user_roadmap(user_id)

async def get_user_objectives(ctx: RunContext[Dict]) -> Dict[str, Any]:
    """Get user objectives ordered by completion date from the Flashed API.
    
    Args:
        ctx: Agent context
        
    Returns:
        List of objectives containing:
        - id: Objective identifier
        - title: Objective title
        - description: Detailed description
        - completion_date: Target completion date
        - status: Current status (pending, in_progress, completed)
        - priority: Priority level (low, medium, high)
    """
    provider = FlashedProvider()
    async with provider:
        user_id = _extract_user_id(ctx)
        return await provider.get_user_objectives(user_id)

async def get_last_card_round(ctx: RunContext[Dict]) -> Dict[str, Any]:
    """Get the data for the last study cards round from the Flashed API.
    
    Args:
        ctx: Agent context
        
    Returns:
        Last card round data containing:
        - cards: List of study cards with:
          - id: Card identifier
          - content: Card content
        - round_length: Number of cards in the round
    """
    provider = FlashedProvider()
    async with provider:
        user_id = _extract_user_id(ctx)
        return await provider.get_last_card_round(user_id)

async def get_user_energy(ctx: RunContext[Dict]) -> Dict[str, Any]:
    """Get the current energy value for a specific user from the Flashed API.
    
    Args:
        ctx: Agent context
        
    Returns:
        User energy data containing:
        - energy: Current energy value
    """
    provider = FlashedProvider()
    async with provider:
        user_id = _extract_user_id(ctx)
        return await provider.get_user_energy(user_id)

async def get_user_by_pretty_id(ctx: RunContext[Dict], pretty_id: str) -> Dict[str, Any]:
    """Get user data by their prettyId (conversation code).
    
    Args:
        ctx: Agent context (required for PydanticAI compatibility)
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
    provider = FlashedProvider()
    async with provider:
        return await provider.get_user_by_pretty_id(pretty_id)