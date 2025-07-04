"""User matching utilities for Flashinho Pro."""
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class FlashinhoProUserMatcher:
    """User matcher for extracting prettyId from messages."""
    
    def __init__(self, context: Dict[str, Any]):
        self.context = context
    
    def extract_pretty_id_from_message(self, message: str) -> Optional[str]:
        """Extract prettyId/conversation code from message.
        
        Args:
            message: User message
            
        Returns:
            Extracted prettyId or None
        """
        if not message:
            return None
        
        # Look for patterns like "código: ABC123XYZ" or just a 10-character alphanumeric string
        patterns = [
            r'(?:código|codigo|code)[:\s]+([A-Za-z0-9]{10})',
            r'\b([A-Za-z0-9]{10})\b'  # Any 10-character alphanumeric
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    async def _find_user_by_pretty_id(self, pretty_id: str) -> Optional[Dict[str, Any]]:
        """Find user data by prettyId using Flashed API.
        
        Args:
            pretty_id: User's prettyId/conversation code
            
        Returns:
            User data dict or None
        """
        try:
            # Import here to avoid circular dependencies
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
            from tools import FlashedProvider
            
            provider = FlashedProvider()
            async with provider:
                user_data = await provider.get_user_by_pretty_id(pretty_id)
                return user_data
        except Exception as e:
            logger.error(f"Error finding user by prettyId {pretty_id}: {e}")
            return None