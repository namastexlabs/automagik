from pydantic import BaseModel
from typing import Optional, List, Dict
import logging

from automagik.memory.message_history import MessageHistory
from pydantic_ai.messages import SystemPromptPart, UserPromptPart, ModelResponse, ModelRequest

class MessageModel(BaseModel):
    role: str
    content: str

class HistoryModel(BaseModel):
    messages: List[MessageModel]

    @classmethod
    def from_message_history(cls, history: MessageHistory):
        messages = []
        for msg in history._messages:
            if isinstance(msg, SystemPromptPart):
                messages.append(MessageModel(role="system", content=msg.system_prompt))
            elif isinstance(msg, UserPromptPart):
                messages.append(MessageModel(role="user", content=msg.prompt))
            elif isinstance(msg, ModelResponse):
                # Extract just the text content from ModelResponse
                content = ""
                for part in msg.parts:
                    if hasattr(part, "content"):
                        content += part.content
                messages.append(MessageModel(role="assistant", content=content))
            elif isinstance(msg, ModelRequest):
                # Process each part of the ModelRequest separately
                for part in msg.parts:
                    if isinstance(part, SystemPromptPart):
                        messages.append(MessageModel(role="system", content=part.content))
                    elif isinstance(part, UserPromptPart):
                        messages.append(MessageModel(role="user", content=part.content))
            else:
                # For any other type, try to get content or convert to string
                content = getattr(msg, "content", str(msg))
                role = getattr(msg, "role", "unknown")
                messages.append(MessageModel(role=role, content=content))
        
        return cls(messages=messages)

class AgentBaseResponse_v2(BaseModel):
    message: str
    history: Dict
    error: Optional[str] = None
    session_id: str

    @classmethod
    def from_agent_response(
        cls,
        message: str,
        history: MessageHistory,
        error: Optional[str] = None,
        tool_calls: List[Dict] = [],
        tool_outputs: List[Dict] = [],
        session_id: str = None
    ) -> "AgentBaseResponse_v2":
        """Create an AgentBaseResponse from the agent's response components.
        
        Args:
            message: The response message from the agent.
            history: The message history object.
            error: Optional error message.
            tool_calls: List of tool calls made during processing (ignored as it's in history).
            tool_outputs: List of outputs from tool calls (ignored as it's in history).
            session_id: The session identifier used for this conversation.
            
        Returns:
            An AgentBaseResponse instance.
        """
        # Create a safe history dict
        try:
            # First try a direct conversion to dictionary
            history_dict = history.to_dict()
            
            # Assert that we have a valid structure
            if not isinstance(history_dict, dict) or "messages" not in history_dict:
                raise ValueError("Invalid history dictionary structure")
                
            # Validate each message has the proper structure
            for i, msg in enumerate(history_dict["messages"]):
                if not isinstance(msg, dict):
                    logging.warning(f"Message at index {i} is not a dict, removing it")
                    history_dict["messages"][i] = None
            
            # Filter out None messages
            history_dict["messages"] = [msg for msg in history_dict["messages"] if msg is not None]
            
        except Exception as e:
            # If history serialization fails, provide a minimal valid dict
            logging.error(f"Error serializing history: {str(e)}")
            history_dict = {"messages": []}
            
        return cls(
            message=message,
            history=history_dict,
            error=error,
            session_id=session_id or history.session_id
        )