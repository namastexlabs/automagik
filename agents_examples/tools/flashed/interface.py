"""Flashed API interface helpers.

This module provides utility functions and decorators for the Flashed API.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import pytz



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
            if isinstance(v, datetime):
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