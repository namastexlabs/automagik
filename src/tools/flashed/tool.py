from typing import Optional, Dict, Any, List, Union
from src.tools.flashed.provider import FlashedProvider

async def get_user_data(ctx: Dict[str, Any], user_uuid: str) -> Dict[str, Any]:
    """Get user data from a specific user registered in the Flashed API.
    
    Args:
        ctx: Agent context
        user_uuid: User UUID
        
    Returns:
        User Data
    """
    provider = FlashedProvider()
    async with provider:
        return await provider.get_user_data(user_uuid)

async def get_user_score(ctx: Dict[str, Any], user_uuid: str) -> Dict[str, Any]:
    """Get user score data including daily progress, energy and streak.
    
    Args:
        ctx: Agent context
        user_uuid: User UUID
        
    Returns:
        User score data containing:
        - daily_progress: float (0-1)
        - energy: int
        - streak: int
    """
    provider = FlashedProvider()
    async with provider:
        return await provider.get_user_score(user_uuid)

async def get_user_roadmap(ctx: Dict[str, Any], user_uuid: str) -> Dict[str, Any]:
    """Get the study roadmap for a specific user from the Flashed API.
    
    Args:
        ctx: Agent context
        user_uuid: User UUID
        
    Returns:
        User roadmap data containing:
        - subjects: List of subjects to study
        - due_date: Target completion date
    """
    provider = FlashedProvider()
    async with provider:
        return await provider.get_user_roadmap(user_uuid)

async def get_user_objectives(ctx: Dict[str, Any], user_uuid: str) -> Dict[str, Any]:
    """Get user objectives ordered by completion date from the Flashed API.
    
    Args:
        ctx: Agent context
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
    provider = FlashedProvider()
    async with provider:
        return await provider.get_user_objectives(user_uuid)

async def get_last_card_round(ctx: Dict[str, Any], user_uuid: str) -> Dict[str, Any]:
    """Get the data for the last study cards round from the Flashed API.
    
    Args:
        ctx: Agent context
        user_uuid: User UUID
        
    Returns:
        Last card round data containing:
        - cards: List of study cards with:
          - id: Card identifier
          - content: Card content
        - round_length: Number of cards in the round
    """
    provider = FlashedProvider()
    async with provider:
        return await provider.get_last_card_round(user_uuid)

async def get_user_energy(ctx: Dict[str, Any], user_uuid: str) -> Dict[str, Any]:
    """Get the current energy value for a specific user from the Flashed API.
    
    Args:
        ctx: Agent context
        user_uuid: User UUID
        
    Returns:
        User energy data containing:
        - energy: Current energy value
    """
    provider = FlashedProvider()
    async with provider:
        return await provider.get_user_energy(user_uuid)