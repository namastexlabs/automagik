"""Evolution tools for Automagik Agents.

Provides tools for interacting with Evolution messaging API.
"""

# Import from tool module
from src.tools.evolution.tool import (
    send_message,
    get_chat_history,
    get_send_message_description,
    get_chat_history_description
)


# Import from contact tool module
from src.tools.evolution.contact_tool import (
    send_contact,
    send_business_contact,
    send_personal_contact,
    get_send_contact_description
)

# Import schema models
from src.tools.evolution.schema import (
    Message,
    SendMessageResponse,
    GetChatHistoryResponse
)

# Import interface
from src.tools.evolution.interface import (
    EvolutionTools,
    evolution_tools
)

# Export public API
__all__ = [
    # Tool functions
    'send_message',
    'get_chat_history',
    
    # Description functions
    'get_send_message_description',
    'get_chat_history_description',
    
    # Schema models
    'Message',
    'SendMessageResponse',
    'GetChatHistoryResponse',
    
    # Interface
    'EvolutionTools',
    'evolution_tools'
] 