"""Evolution tools for Automagik Agents.

Provides tools for interacting with Evolution messaging API.
"""

# Import from local tool modules
from .tool import (
    send_message,
    get_chat_history,
    get_send_message_description,
    get_chat_history_description
)

# Import from contact tool module
from .contact_tool import (
    send_contact,
    send_business_contact,
    send_personal_contact,
    get_send_contact_description
)

# Import schema models
from .schema import (
    Message,
    SendMessageResponse,
    GetChatHistoryResponse,
    Contact,
    SendContactRequest,
    SendContactResponse
)

# Import interface
from .interface import (
    EvolutionTools,
    evolution_tools
)

# Import api module for send_text_message
from .api import send_text_message

# Export public API
__all__ = [
    # Tool functions
    'send_message',
    'get_chat_history',
    'send_contact',
    'send_business_contact',
    'send_personal_contact',
    'send_text_message',
    
    # Description functions
    'get_send_message_description',
    'get_chat_history_description',
    'get_send_contact_description',
    
    # Schema models
    'Message',
    'SendMessageResponse',
    'GetChatHistoryResponse',
    'Contact',
    'SendContactRequest',
    'SendContactResponse',
    
    # Interface
    'EvolutionTools',
    'evolution_tools'
] 