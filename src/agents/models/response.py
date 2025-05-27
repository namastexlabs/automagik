from pydantic import BaseModel
from typing import Optional, List, Dict, Union


class AgentResponse(BaseModel):
    """Standard response format for SimpleAgent.
    
    This class provides a standardized response format for the SimpleAgent
    that includes the text response, success status, and any tool calls or
    outputs that were made during processing.
    """
    text: str
    success: bool = True
    error_message: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_outputs: Optional[List[Dict]] = None
    raw_message: Optional[Union[Dict, List]] = None 
    system_prompt: Optional[str] = None