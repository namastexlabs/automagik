from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Union, Any


class AgentResponse(BaseModel):
    """Standard response format for SimpleAgent.
    
    This class provides a standardized response format for the SimpleAgent
    that includes the text response, success status, and any tool calls or
    outputs that were made during processing.
    """
    text: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    tool_calls: List[Dict] = Field(default_factory=list)
    tool_outputs: List[Dict] = Field(default_factory=list)
    raw_message: Optional[Union[Dict, List]] = None 
    system_prompt: Optional[str] = None
    usage: Optional[Dict[str, Any]] = Field(None, description="Token usage information")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentResponse':
        """Create AgentResponse from dictionary, handling various response formats."""
        # Handle different response field names
        text = data.get("text") or data.get("response") or data.get("message")
        
        # Extract usage information if present
        usage = data.get("usage")
        if not usage and any(key in data for key in ["request_tokens", "response_tokens", "total_tokens"]):
            # Build usage from token fields if present
            usage = {
                key: data.get(key, 0) for key in 
                ["request_tokens", "response_tokens", "total_tokens", "cache_creation_tokens", "cache_read_tokens"]
                if key in data
            }
        
        return cls(
            text=text,
            success=data.get("success", True),
            error_message=data.get("error_message"),
            tool_calls=data.get("tool_calls", []),
            tool_outputs=data.get("tool_outputs", []),
            raw_message=data.get("raw_message"),
            system_prompt=data.get("system_prompt"),
            usage=usage
        )