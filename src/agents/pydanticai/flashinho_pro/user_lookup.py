"""User lookup implementation for Flashinho Pro.

This module provides a simple implementation for mapping phone numbers and emails
to Flashed user IDs. In production, this would be replaced with a proper database
or API-based lookup system.
"""

import logging
from typing import Dict, Optional, Set
import re

logger = logging.getLogger(__name__)


class FlashedUserLookup:
    """Simple user lookup service for demonstration purposes."""
    
    def __init__(self):
        """Initialize with sample user mappings."""
        # In production, this would be a database or external service
        self._phone_to_user: Dict[str, str] = {
            # Normalized phone -> user_id mappings
            "11987654321": "6ba9568d-54a2-4f49-a960-7c3fae9b194c",
            "11999887766": "test-user-2",
            "21987654321": "test-user-3",
        }
        
        self._email_to_user: Dict[str, str] = {
            # Email -> user_id mappings
            "carvalhocleusia0@gmail.com": "6ba9568d-54a2-4f49-a960-7c3fae9b194c",
            "student@example.com": "test-user-2",
            "test@flashed.tech": "test-user-3",
        }
        
        # Cache for performance
        self._lookup_cache: Dict[str, Optional[str]] = {}
    
    def normalize_phone(self, phone: str) -> str:
        """Normalize phone number for lookup.
        
        Args:
            phone: Raw phone number
            
        Returns:
            Normalized phone number
        """
        if not phone:
            return ""
            
        # Remove all non-digit characters
        phone_digits = re.sub(r'\D', '', phone)
        
        # Brazilian phone number normalization
        if phone_digits.startswith('55') and len(phone_digits) > 2:
            phone_digits = phone_digits[2:]
            
        # Remove leading zeros
        phone_digits = phone_digits.lstrip('0')
        
        return phone_digits
    
    async def find_user_by_phone(self, phone: str) -> Optional[str]:
        """Find user by phone number.
        
        Args:
            phone: Phone number (will be normalized)
            
        Returns:
            User ID if found, None otherwise
        """
        try:
            # Check cache first
            cache_key = f"phone:{phone}"
            if cache_key in self._lookup_cache:
                return self._lookup_cache[cache_key]
            
            # Normalize phone
            normalized = self.normalize_phone(phone)
            if not normalized:
                return None
            
            # Try exact match first
            user_id = self._phone_to_user.get(normalized)
            
            # Try variations if no exact match
            if not user_id:
                # Try with 9 prefix for mobile numbers (São Paulo)
                if len(normalized) == 10 and normalized.startswith('11'):
                    alt_phone = f"11{normalized[2:]}"
                    user_id = self._phone_to_user.get(alt_phone)
                
                # Try without area code
                if not user_id and len(normalized) > 8:
                    short_phone = normalized[-8:]  # Last 8 digits
                    for stored_phone, stored_user in self._phone_to_user.items():
                        if stored_phone.endswith(short_phone):
                            user_id = stored_user
                            break
            
            # Cache result
            self._lookup_cache[cache_key] = user_id
            
            if user_id:
                logger.info(f"Found user {user_id} for phone {normalized}")
            else:
                logger.info(f"No user found for phone {normalized}")
                
            return user_id
            
        except Exception as e:
            logger.error(f"Error finding user by phone {phone}: {str(e)}")
            return None
    
    async def find_user_by_email(self, email: str) -> Optional[str]:
        """Find user by email address.
        
        Args:
            email: Email address
            
        Returns:
            User ID if found, None otherwise
        """
        try:
            # Check cache first
            cache_key = f"email:{email}"
            if cache_key in self._lookup_cache:
                return self._lookup_cache[cache_key]
            
            # Normalize email
            email_lower = email.lower().strip()
            
            # Direct lookup
            user_id = self._email_to_user.get(email_lower)
            
            # Cache result
            self._lookup_cache[cache_key] = user_id
            
            if user_id:
                logger.info(f"Found user {user_id} for email {email_lower}")
            else:
                logger.info(f"No user found for email {email_lower}")
                
            return user_id
            
        except Exception as e:
            logger.error(f"Error finding user by email {email}: {str(e)}")
            return None
    
    def add_phone_mapping(self, phone: str, user_id: str) -> None:
        """Add a phone-to-user mapping.
        
        Args:
            phone: Phone number
            user_id: Flashed user ID
        """
        normalized = self.normalize_phone(phone)
        if normalized:
            self._phone_to_user[normalized] = user_id
            # Clear cache for this phone
            cache_key = f"phone:{phone}"
            self._lookup_cache.pop(cache_key, None)
            logger.info(f"Added phone mapping: {normalized} -> {user_id}")
    
    def add_email_mapping(self, email: str, user_id: str) -> None:
        """Add an email-to-user mapping.
        
        Args:
            email: Email address
            user_id: Flashed user ID
        """
        email_lower = email.lower().strip()
        self._email_to_user[email_lower] = user_id
        # Clear cache for this email
        cache_key = f"email:{email}"
        self._lookup_cache.pop(cache_key, None)
        logger.info(f"Added email mapping: {email_lower} -> {user_id}")
    
    def get_all_users(self) -> Set[str]:
        """Get all known user IDs.
        
        Returns:
            Set of all user IDs
        """
        all_users = set()
        all_users.update(self._phone_to_user.values())
        all_users.update(self._email_to_user.values())
        return all_users
    
    def get_user_contacts(self, user_id: str) -> Dict[str, list]:
        """Get all contact methods for a user.
        
        Args:
            user_id: Flashed user ID
            
        Returns:
            Dictionary with 'phones' and 'emails' lists
        """
        phones = [phone for phone, uid in self._phone_to_user.items() if uid == user_id]
        emails = [email for email, uid in self._email_to_user.items() if uid == user_id]
        
        return {
            "phones": phones,
            "emails": emails
        }


# Global instance for the application
_user_lookup_instance: Optional[FlashedUserLookup] = None


def get_user_lookup() -> FlashedUserLookup:
    """Get the global user lookup instance.
    
    Returns:
        FlashedUserLookup instance
    """
    global _user_lookup_instance
    if _user_lookup_instance is None:
        _user_lookup_instance = FlashedUserLookup()
    return _user_lookup_instance


# Convenience functions for easy usage
async def find_user_by_phone(phone: str) -> Optional[str]:
    """Convenience function to find user by phone."""
    return await get_user_lookup().find_user_by_phone(phone)


async def find_user_by_email(email: str) -> Optional[str]:
    """Convenience function to find user by email."""
    return await get_user_lookup().find_user_by_email(email)