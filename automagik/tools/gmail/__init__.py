"""Gmail tools for Automagik Agents.

Provides tools for sending emails via Gmail API.
"""

# Import from tool module
from automagik.tools.gmail.tool import (
    send_email,
    get_send_email_description,
    fetch_emails,
    get_fetch_emails_description,
    mark_emails_read,
    get_mark_emails_read_description
)

# Import schema models
from automagik.tools.gmail.schema import (
    SendEmailInput,
    SendEmailResult,
    FetchEmailsInput,
    FetchEmailsResult,
    EmailMessage
)

# Import interface
from automagik.tools.gmail.interface import (
    GmailTools,
    gmail_tools
)

# Export public API
__all__ = [
    # Tool functions
    'send_email',
    'fetch_emails',
    'mark_emails_read',
    
    # Description functions
    'get_send_email_description',
    'get_fetch_emails_description',
    'get_mark_emails_read_description',
    
    # Schema models
    'SendEmailInput',
    'SendEmailResult',
    'FetchEmailsInput',
    'FetchEmailsResult',
    'EmailMessage',
    
    # Interface
    'GmailTools',
    'gmail_tools'
] 