from typing import Dict, Any
from src.tools.flashed.provider import FlashedProvider

async def get_user_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
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
        return await provider.get_user_data(ctx["user_id"])

async def get_user_score(ctx: Dict[str, Any]) -> Dict[str, Any]:
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
        return await provider.get_user_score(ctx["user_id"])

async def get_user_roadmap(ctx: Dict[str, Any]) -> Dict[str, Any]:
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
        return await provider.get_user_roadmap(ctx["user_id"])

async def get_user_objectives(ctx: Dict[str, Any]) -> Dict[str, Any]:
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
        return await provider.get_user_objectives(ctx["user_id"])

async def get_last_card_round(ctx: Dict[str, Any]) -> Dict[str, Any]:
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
        return await provider.get_last_card_round(ctx["user_id"])

async def get_user_energy(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Get the current energy value for a specific user from the Flashed API.
    
    Args:
        ctx: Agent context
        
    Returns:
        User energy data containing:
        - energy: Current energy value
    """
    provider = FlashedProvider()
    async with provider:
        return await provider.get_user_energy(ctx["user_id"])