from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Union, Any


class AgentResponse(BaseModel):
    """Standard response format for SimpleAgent.
    
    This class provides a standardized response format for the SimpleAgent
    that includes the text response, success status, and any tool calls or
    outputs that were made during processing.
    """
    text: str
    success: bool = True
    error_message: Optional[str] = None
    tool_calls: List[Dict] = Field(default_factory=list)
    tool_outputs: List[Dict] = Field(default_factory=list)
    raw_message: Optional[Union[Dict, List]] = None 
    system_prompt: Optional[str] = None
    usage: Optional[Dict[str, Any]] = Field(None, description="Token usage information")