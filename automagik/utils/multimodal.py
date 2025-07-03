"""Utility functions for multimodal content processing.

This module provides helper functions for handling multimodal content 
such as images, audio, and documents.
"""

import base64
import logging
import re
import mimetypes
from typing import Dict, Any, Tuple, List, Union
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

def detect_content_type(url_or_data: str) -> str:
    """Detect content type based on URL extension or base64 data.
    
    Args:
        url_or_data: URL or base64 data
        
    Returns:
        MIME type string
    """
    # Check if it's a URL
    if url_or_data.startswith(('http://', 'https://')):
        # Try to determine from URL extension
        ext = Path(url_or_data.split('?')[0]).suffix.lower()
        guessed_type = mimetypes.guess_type(url_or_data)[0]
        
        if guessed_type:
            return guessed_type
            
        # If mimetypes module couldn't detect, use common types
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
            return f"image/{ext[1:]}"
        elif ext in ['.mp3', '.wav', '.ogg', '.m4a']:
            return f"audio/{ext[1:]}"
        elif ext in ['.mp4', '.webm', '.mov']:
            return "video/mp4"
        elif ext == '.pdf':
            return "application/pdf"
        elif ext in ['.doc', '.docx']:
            return "application/msword"
        
        # If we can't determine from extension, try HEAD request
        try:
            response = requests.head(url_or_data, timeout=5)
            if 'Content-Type' in response.headers:
                return response.headers['Content-Type'].split(';')[0]
        except Exception as e:
            logger.warning(f"Error determining content type from URL {url_or_data}: {str(e)}")
            
        # Default to octet-stream
        return "application/octet-stream"
        
    # Check if it's base64 data
    if url_or_data.startswith('data:'):
        # Extract MIME type from data URL
        match = re.match(r'data:([^;]+);base64,', url_or_data)
        if match:
            return match.group(1)
    
    # Detect by examining first few bytes
    try:
        # Get first few bytes from base64 content
        if ',' in url_or_data:
            data = url_or_data.split(',')[1]
        else:
            data = url_or_data
            
        # Remove any non-base64 characters
        data = re.sub(r'[^A-Za-z0-9+/=]', '', data)
        
        # Decode first few bytes
        header = base64.b64decode(data[:20] + "=" * ((4 - len(data[:20]) % 4) % 4))
        
        # Detect image types
        if header.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        elif header.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png'
        elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
            return 'image/gif'
        elif header.startswith(b'RIFF') and header[8:12] == b'WEBP':
            return 'image/webp'
            
        # Detect audio types
        if header.startswith(b'ID3') or header.startswith(b'\xff\xfb') or header.startswith(b'\xff\xf3'):
            return 'audio/mpeg'
        elif header.startswith(b'RIFF') and header[8:12] == b'WAVE':
            return 'audio/wav'
            
        # Detect PDF
        if header.startswith(b'%PDF'):
            return 'application/pdf'
    except Exception as e:
        logger.warning(f"Error detecting MIME type from binary data: {str(e)}")
    
    # Default to binary
    return 'application/octet-stream'

def is_image_type(mime_type: str) -> bool:
    """Check if MIME type is an image type.
    
    Args:
        mime_type: MIME type string
        
    Returns:
        True if image type, False otherwise
    """
    return mime_type.startswith('image/')

def is_audio_type(mime_type: str) -> bool:
    """Check if MIME type is an audio type.
    
    Args:
        mime_type: MIME type string
        
    Returns:
        True if audio type, False otherwise
    """
    return mime_type.startswith('audio/')

def is_document_type(mime_type: str) -> bool:
    """Check if MIME type is a document type.
    
    Args:
        mime_type: MIME type string
        
    Returns:
        True if document type, False otherwise
    """
    return (mime_type.startswith('application/') or 
            mime_type.startswith('text/') or
            mime_type == 'application/pdf')

def encode_binary_to_base64(binary_data: bytes, mime_type: str = None) -> str:
    """Encode binary data as base64 string.
    
    Args:
        binary_data: Binary data to encode
        mime_type: Optional MIME type to include in data URL
        
    Returns:
        Base64 encoded string
    """
    encoded = base64.b64encode(binary_data).decode('utf-8')
    if mime_type:
        return f"data:{mime_type};base64,{encoded}"
    return encoded

def decode_base64_to_binary(base64_data: str) -> bytes:
    """Decode base64 string to binary data.
    
    Args:
        base64_data: Base64 encoded string
        
    Returns:
        Binary data
    """
    # If it's a data URL, extract the base64 part
    if base64_data.startswith('data:'):
        base64_data = base64_data.split(',')[1]
    
    # Remove any non-base64 characters
    base64_data = re.sub(r'[^A-Za-z0-9+/=]', '', base64_data)
    
    # Decode
    return base64.b64decode(base64_data)

def get_binary_from_url(url: str) -> Tuple[bytes, str]:
    """Download binary content from URL.
    
    Args:
        url: URL to download
        
    Returns:
        Tuple of (binary_data, mime_type)
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content_type = response.headers.get('Content-Type', 'application/octet-stream').split(';')[0]
        return response.content, content_type
    except Exception as e:
        logger.error(f"Error downloading content from {url}: {str(e)}")
        raise

def prepare_for_db_storage(content_type: str, content: Union[str, bytes]) -> Dict[str, Any]:
    """Prepare multimodal content for database storage.
    
    Args:
        content_type: Type of content ('image', 'audio', 'document')
        content: Content as URL or binary data
        
    Returns:
        Dictionary for database storage
    """
    result = {
        "type": content_type,
        "timestamp": None,  # Will be set by DB
    }
    
    # Handle URL vs binary content
    if isinstance(content, str) and content.startswith(('http://', 'https://')):
        result["url"] = content
        result["mime_type"] = detect_content_type(content)
    elif isinstance(content, str) and content.startswith('data:'):
        # It's a base64 data URL
        mime_match = re.match(r'data:([^;]+);base64,', content)
        if mime_match:
            result["mime_type"] = mime_match.group(1)
        else:
            result["mime_type"] = "application/octet-stream"
        result["base64_data"] = content
    elif isinstance(content, bytes):
        # It's binary data
        result["mime_type"] = detect_content_type(content[:100])
        result["base64_data"] = encode_binary_to_base64(content, result["mime_type"])
    
    return result

def extract_from_context(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract multimodal content from context dictionary.
    
    Args:
        context: Context dictionary
        
    Returns:
        List of multimodal content dictionaries
    """
    result = []
    
    # Extract from multimodal_content if it exists
    if "multimodal_content" in context:
        mc = context["multimodal_content"]
        
        # Handle image content
        if "image_url" in mc:
            result.append(prepare_for_db_storage("image", mc["image_url"]))
        if "image_data" in mc and mc["image_data"]:
            result.append(prepare_for_db_storage("image", mc["image_data"]))
            
        # Handle audio content
        if "audio_url" in mc:
            result.append(prepare_for_db_storage("audio", mc["audio_url"]))
        if "audio_data" in mc and mc["audio_data"]:
            result.append(prepare_for_db_storage("audio", mc["audio_data"]))
            
        # Handle document content
        if "document_url" in mc:
            result.append(prepare_for_db_storage("document", mc["document_url"]))
        if "document_data" in mc and mc["document_data"]:
            result.append(prepare_for_db_storage("document", mc["document_data"]))
    

    
    return result 