"""Blackpearl API interface helpers.

This module provides utility functions and decorators for the Blackpearl API.
"""
import logging
from typing import Dict, Any, Optional
from functools import wraps
from datetime import datetime
import pytz
from enum import Enum
from automagik.config import settings

logger = logging.getLogger(__name__)

def validate_api_response(func):
    """Decorator to validate API response.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        if result is None:
            logger.error(f"API call {func.__name__} returned None")
            raise ValueError(f"API call {func.__name__} returned None")
        return result
    return wrapper

def handle_api_error(func):
    """Decorator to handle API errors.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Check if we're in development mode and debug log level
        is_dev_debug = (
            settings.ENVIRONMENT.value == "development" and
            settings.AUTOMAGIK_LOG_LEVEL == "DEBUG"
        )
        
        try:
            result = await func(*args, **kwargs)
            # If result is a tuple with status code 204, it's a successful deletion
            if isinstance(result, tuple) and len(result) == 2 and result[0] == 204:
                return None
            return result
        except Exception as e:
            # If the error is about 204 response, it's actually a success
            if "204" in str(e) and "Attempt to decode JSON with unexpected mimetype" in str(e):
                return None
            
            # If the error contains response data (typically with 4xx status codes), return it
            if hasattr(e, 'response') and hasattr(e.response, 'json'):
                try:
                    error_data = e.response.json()
                    logger.warning(f"API returned error status but with content: {error_data}")
                    return error_data
                except Exception:
                    pass
                
            # Enhanced error logging in development/debug mode
            if is_dev_debug:
                # Extract function call details for better debugging
                func_name = func.__name__
                cls_name = args[0].__class__.__name__ if args and hasattr(args[0], '__class__') else None
                endpoint = None
                
                # Try to extract the endpoint from the function code or docstring
                if func.__doc__ and "endpoint" in func.__doc__.lower():
                    doc_lines = func.__doc__.splitlines()
                    for line in doc_lines:
                        if "endpoint" in line.lower():
                            endpoint = line.strip()
                            break
                
                # Log detailed error information
                logger.debug("BP - API Error Details:")
                logger.debug(f"BP - Function: {cls_name}.{func_name}" if cls_name else f"BP - Function: {func_name}")
                if endpoint:
                    logger.debug(f"BP - Endpoint: {endpoint}")
                logger.debug(f"BP - Error Type: {type(e).__name__}")
                logger.debug(f"BP - Error Message: {str(e)}")
                
                # Log function arguments (with sensitive info redacted)
                safe_args = [f"<{type(arg).__name__}>" if i > 0 else arg for i, arg in enumerate(args)]
                safe_kwargs = {k: "<REDACTED>" if k.lower() in ("password", "token", "key", "secret") else v 
                              for k, v in kwargs.items()}
                logger.debug(f"BP - Function Args: {safe_args}")
                logger.debug(f"BP - Function Kwargs: {safe_kwargs}")
            else:
                logger.error(f"API error in {func.__name__}: {str(e)}")
            raise
    return wrapper

def format_api_request(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Format request data by removing None values and converting datetime to ISO format.
    
    Args:
        data: Request data
        
    Returns:
        Formatted request data
    """
    if data is None:
        return {}
        
    formatted_data = {}
    for k, v in data.items():
        if v is not None:
            if isinstance(v, Enum):
                # Convert enum to its string value
                formatted_data[k] = v.value
            elif isinstance(v, datetime):
                # Ensure datetime is timezone-aware
                if v.tzinfo is None:
                    v = pytz.timezone('America/Sao_Paulo').localize(v)
                # Format with microseconds and timezone offset
                formatted_data[k] = v.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
            else:
                formatted_data[k] = v
                
    return formatted_data

def filter_none_params(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Filter out None values from request parameters.
    
    Args:
        params: Request parameters
        
    Returns:
        Filtered parameters
    """
    if params is None:
        return {}
        
    return {k: v for k, v in params.items() if v is not None} 