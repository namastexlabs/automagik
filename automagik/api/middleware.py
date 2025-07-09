import logging
import json
import re
import time
import uuid
from typing import Callable, Any, Dict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all incoming HTTP requests and responses.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.request_counter = 0
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate simple request ID (counter-based for simplicity)
        self.request_counter += 1
        request_id = f"R{self.request_counter:04d}"
        
        # Store request ID in request state for access in other parts of the app
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Get request details
        method = request.method
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"
        
        # Log request
        logger.info(f"[{request_id}] 📨 {method} {path} - Client: {client_host}")
        
        # Get request headers (excluding sensitive ones)
        safe_headers = {}
        for key, value in request.headers.items():
            if key.lower() not in ['authorization', 'x-api-key', 'cookie']:
                safe_headers[key] = value
            else:
                safe_headers[key] = "***REDACTED***"
        
        logger.debug(f"[{request_id}] Request headers: {safe_headers}")
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate response time
            process_time = time.time() - start_time
            
            # Log response
            status_emoji = "✅" if 200 <= response.status_code < 300 else "❌" if response.status_code >= 400 else "⚠️"
            logger.info(f"[{request_id}] {status_emoji} {method} {path} - Status: {response.status_code} - Time: {process_time:.3f}s")
            
            # Add custom headers
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.error(f"[{request_id}] ❌ {method} {path} - Error: {str(e)} - Time: {process_time:.3f}s")
            raise


class JSONParsingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle problematic JSON requests.
    This middleware attempts to fix common JSON parsing issues before FastAPI's validation.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only apply to POST/PUT/PATCH requests to /api/v1/agent endpoints
        if (request.method in ["POST", "PUT", "PATCH"] and 
            "/api/v1/agent" in request.url.path and
            request.headers.get("content-type", "").startswith("application/json")):
            
            try:
                # Store original body to restore it later
                original_body = await request.body()
                
                # If empty body, continue with normal processing
                if not original_body:
                    return await call_next(request)
            except Exception as e:
                # If client disconnected or any other error reading body, skip middleware processing
                logger.debug(f"Client disconnected or error reading request body: {e}")
                return await call_next(request)
                
            try:
                # Try to decode the body
                body_str = original_body.decode('utf-8')
                
                # First, try standard parsing
                try:
                    json.loads(body_str)
                    # If it parses correctly, no need to modify
                    request._body = original_body
                except json.JSONDecodeError as e:
                    logger.info(f"JSON parsing error: {str(e)}")
                    fixed_body = None
                    
                    # Fix 1: Clean control characters from the entire body
                    sanitized_body = self._sanitize_json(body_str)
                    try:
                        json.loads(sanitized_body)
                        fixed_body = sanitized_body
                        logger.info("Fixed JSON by sanitizing control characters")
                    except json.JSONDecodeError:
                        # If that fails, try more specific approaches
                        pass
                        
                    # Fix 2: Fix message_content with problematic characters
                    if not fixed_body:
                        try:
                            message_match = re.search(r'"message_content"\s*:\s*"((?:[^"\\]|\\.)*?)(?<!\\)"', body_str, re.DOTALL)
                            if message_match:
                                content = message_match.group(1)
                                
                                # Process content more aggressively
                                processed_content = self._clean_content(content)
                                
                                # Replace in the original body with the fixed content
                                fixed_body = body_str.replace(message_match.group(0), f'"message_content":"{processed_content}"')
                                
                                try:
                                    # Try to validate the JSON
                                    json.loads(fixed_body)
                                    logger.info("Fixed malformed JSON in message_content")
                                except json.JSONDecodeError:
                                    # If still broken, do more cleanup
                                    fixed_body = None
                        except Exception as e:
                            logger.warning(f"Failed to fix message_content: {str(e)}")
                    
                    # Fix 3: More aggressive approach - extract all fields and rebuild JSON
                    if not fixed_body:
                        try:
                            data = self._extract_fields_manually(body_str)
                            if data:
                                fixed_body = json.dumps(data)
                                logger.info("Fixed JSON by manual field extraction")
                        except Exception as e:
                            logger.warning(f"Manual field extraction failed: {str(e)}")
                    
                    # If we have a fixed body, use it
                    if fixed_body:
                        request._body = fixed_body.encode('utf-8')
                    else:
                        # Last resort - use the sanitized version even if it's still invalid
                        # FastAPI will provide a proper error message
                        request._body = sanitized_body.encode('utf-8')
                        logger.warning("Could not fully fix malformed JSON")
                        
            except UnicodeDecodeError:
                # If body can't be decoded as UTF-8, use original
                request._body = original_body
                logger.warning("Non-UTF8 request body received")
                
        # Continue with the request
        return await call_next(request)
    
    def _sanitize_json(self, json_str: str) -> str:
        """
        Sanitize JSON string by removing control characters.
        """
        # Replace all control characters with spaces
        sanitized = ''
        for c in json_str:
            # Keep newlines and tabs to preserve structure
            if c in ('\n', '\t'):
                sanitized += c
            # Replace other control characters
            elif ord(c) < 32:
                sanitized += ' '
            else:
                sanitized += c
                
        # Add proper escaping for newlines in strings
        sanitized = re.sub(r'(?<!\\)(\n)', r'\\n', sanitized)
        sanitized = re.sub(r'(?<!\\)(\r)', r'\\r', sanitized)
        sanitized = re.sub(r'(?<!\\)(\t)', r'\\t', sanitized)
        
        return sanitized
    
    def _clean_content(self, content: str) -> str:
        """
        Clean content string for use in JSON.
        """
        # Remove or escape all special characters
        result = content
        # Escape newlines
        result = result.replace('\n', '\\n')
        result = result.replace('\r', '\\r')
        # Escape tabs 
        result = result.replace('\t', '\\t')
        # Escape quotes
        result = result.replace('"', '\\"')
        # Fix any double escapes that might have been created
        result = result.replace('\\\\n', '\\n')
        result = result.replace('\\\\r', '\\r')
        result = result.replace('\\\\t', '\\t')
        result = result.replace('\\\\"', '\\"')
        # Remove other control characters
        result = ''.join(c if ord(c) >= 32 or c in ['\\n', '\\r', '\\t'] else ' ' for c in result)
        
        return result
    
    def _extract_fields_manually(self, body_str: str) -> Dict[str, Any]:
        """
        Manually extract fields from potentially broken JSON.
        """
        data = {}
        
        # Extract message_content
        message_match = re.search(r'"message_content"\s*:\s*"(.*?)(?<!\\)"', body_str, re.DOTALL)
        if message_match:
            data['message_content'] = self._clean_content(message_match.group(1))
            
        # Extract other simple string fields
        simple_fields = ['message_type', 'session_name', 'user_id', 'session_origin']
        for field in simple_fields:
            match = re.search(rf'"{field}"\s*:\s*"([^"]*)"', body_str)
            if match:
                data[field] = match.group(1)
        
        # Extract numeric fields
        numeric_fields = ['message_limit']
        for field in numeric_fields:
            match = re.search(rf'"{field}"\s*:\s*(\d+)', body_str)
            if match:
                data[field] = int(match.group(1))
                
        # Extract user object if present
        user_match = re.search(r'"user"\s*:\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', body_str, re.DOTALL)
        if user_match:
            user_data = {}
            # Extract user fields
            email_match = re.search(r'"email"\s*:\s*"([^"]*)"', user_match.group(1))
            if email_match:
                user_data['email'] = email_match.group(1)
                
            phone_match = re.search(r'"phone_number"\s*:\s*"([^"]*)"', user_match.group(1))
            if phone_match:
                user_data['phone_number'] = phone_match.group(1)
                
            # Try to extract user_data object
            ud_match = re.search(r'"user_data"\s*:\s*\{([^{}]*)\}', user_match.group(1))
            if ud_match:
                try:
                    name_match = re.search(r'"name"\s*:\s*"([^"]*)"', ud_match.group(1))
                    if name_match:
                        user_data['user_data'] = {'name': name_match.group(1)}
                except Exception:
                    pass
                    
            if user_data:
                data['user'] = user_data
                
        return data 