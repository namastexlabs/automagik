"""Gmail API provider implementation.

This module provides the API client implementation for interacting with the Gmail API.
"""
import base64
import json
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional

import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow

from .schema import SendEmailInput, SendEmailResult, FetchEmailsResult, EmailMessage

logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']

class GmailProvider:
    """Client for interacting with the Gmail API."""

    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None):
        """Initialize the Gmail API client.
        
        Args:
            credentials_path: Path to OAuth credentials JSON file
            token_path: Path to OAuth token file
        """
        self.credentials_path = credentials_path or os.environ.get('GOOGLE_CREDENTIAL_FILE')
        self.token_path = token_path or os.path.join('credentials', 'gmail_token.json')
        self.credentials = None
        logger.info(f"Initialized GmailProvider with credentials path: {self.credentials_path}")
    
    def _get_credentials(self):
        """Get or refresh OAuth credentials.
        
        Returns:
            Google OAuth credentials
        """
        creds = None
        # The file token.json stores the user's access and refresh tokens
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_info(
                    json.load(open(self.token_path)), SCOPES
                )
            except Exception as e:
                logger.error(f"Error loading credentials from token file: {str(e)}")
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(google.auth.transport.requests.Request())
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {str(e)}")
                    creds = None
            
            if not creds:
                try:
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    
                    # Save the credentials for the next run
                    with open(self.token_path, 'w') as token:
                        token.write(creds.to_json())
                    logger.info(f"Saved new credentials to {self.token_path}")
                except Exception as e:
                    logger.error(f"Error obtaining new credentials: {str(e)}")
                    return None
        
        self.credentials = creds
        return creds
    
    def _check_auth(self) -> Dict[str, Any]:
        """Check if authentication is available and get credentials.
        
        Returns:
            Dictionary with auth status information
        """
        if not self.credentials_path or not os.path.exists(self.credentials_path):
            return {"authenticated": False, "error": f"Credentials file not found: {self.credentials_path}"}
        
        credentials = self._get_credentials()
        if not credentials:
            return {"authenticated": False, "error": "Failed to authenticate with Google"}
            
        return {"authenticated": True, "credentials": credentials}
    
    def _create_message(self, input: SendEmailInput) -> dict:
        """Create a message for an email.
        
        Args:
            input: Email input parameters
            
        Returns:
            Raw message dictionary ready for Gmail API
        """
        # Determine if we're sending HTML or plain text
        is_html = input.content_type and "html" in input.content_type.lower()
        
        # Combine message with extra content if provided
        full_message = input.message
        if input.extra_content:
            if is_html:
                full_message = f"{input.message}<br><br>{input.extra_content}"
            else:
                full_message = f"{input.message}\n\n{input.extra_content}"
        
        # For HTML emails with plain text alternative, create multipart message
        if is_html and input.plain_text_alternative:
            message = MIMEMultipart('alternative')
            
            # Add plain text part
            text_part = MIMEText(input.plain_text_alternative, 'plain')
            message.attach(text_part)
            
            # Add HTML part
            html_part = MIMEText(full_message, 'html')
            message.attach(html_part)
        else:
            # For simple emails (HTML-only or plain text)
            subtype = 'html' if is_html else 'plain'
            message = MIMEText(full_message, subtype)
        
        message['to'] = input.to
        message['subject'] = input.subject
        
        if input.cc and len(input.cc) > 0:
            message['cc'] = ', '.join(input.cc)
            
        return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
    
    async def send_email(self, input: SendEmailInput) -> SendEmailResult:
        """Send an email via Gmail API.
        
        Args:
            input: Email parameters
            
        Returns:
            Result of the email sending operation
        """
        logger.info(f"Sending email to: {input.to}")
        
        try:
            # Check authentication
            auth_status = self._check_auth()
            if not auth_status.get("authenticated", False):
                return SendEmailResult(
                    success=False,
                    error=auth_status.get("error", "Authentication failed")
                )
                
            # Create the email message
            message = self._create_message(input)
            
            try:
                # Create Gmail API service
                service = build('gmail', 'v1', credentials=self.credentials)
                
                # Send the email
                sent_message = service.users().messages().send(
                    userId='me', body=message
                ).execute()
                
                logger.info(f"Email sent successfully to {input.to} with ID: {sent_message['id']}")
                
                return SendEmailResult(
                    success=True,
                    message_id=sent_message['id']
                )
            except HttpError as error:
                error_msg = f"Gmail API error: {error}"
                logger.error(error_msg)
                return SendEmailResult(
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            error_msg = f"Error sending email: {str(e)}"
            logger.error(error_msg)
            
            return SendEmailResult(
                success=False,
                error=error_msg
            )
            
    def _parse_message(self, message: Dict[str, Any]) -> EmailMessage:
        """Parse a Gmail API message into an EmailMessage object.
        
        Args:
            message: Raw message from Gmail API
            
        Returns:
            EmailMessage object with parsed data
        """
        try:
            # Get message data
            message_id = message.get('id', '')
            payload = message.get('payload', {})
            headers = payload.get('headers', [])
            
            # Extract header information
            from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
            to_email = next((h['value'] for h in headers if h['name'].lower() == 'to'), '')
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
            
            # Extract body content
            body = ''
            if 'body' in payload and 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            elif 'parts' in payload:
                # For multipart messages, try to find text/plain or text/html part
                for part in payload['parts']:
                    if part.get('mimeType') in ['text/plain', 'text/html'] and 'data' in part.get('body', {}):
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
            
            # Create EmailMessage object
            return EmailMessage(
                id=message_id,
                from_email=from_email,
                to=to_email,
                subject=subject,
                date=date,
                body=body,
                raw_data=message
            )
        except Exception as e:
            logger.error(f"Error parsing message {message.get('id', 'unknown')}: {str(e)}")
            # Return minimal message with ID
            return EmailMessage(
                id=message.get('id', 'unknown'),
                from_email='',
                to='',
                subject='[Error parsing message]',
                date='',
                body=f"Error parsing message: {str(e)}",
                raw_data=message
            )
    
    async def fetch_unread_emails(self, subject_filter: Optional[str] = None, max_results: int = 10) -> FetchEmailsResult:
        """Fetch unread emails, optionally filtering by subject.
        
        Args:
            subject_filter: Optional subject filter string
            max_results: Maximum number of emails to retrieve
            
        Returns:
            FetchEmailsResult with list of emails
        """
        logger.info(f"Fetching unread emails with subject filter: {subject_filter}")
        
        try:
            # Check authentication
            auth_status = self._check_auth()
            if not auth_status.get("authenticated", False):
                return FetchEmailsResult(
                    success=False,
                    error=auth_status.get("error", "Authentication failed"),
                    emails=[]
                )
            
            # Build query
            query = "is:unread"
            if subject_filter:
                query += f" subject:{subject_filter}"
            
            # Create Gmail API service
            service = build('gmail', 'v1', credentials=self.credentials)
            
            # List messages matching query
            results = service.users().messages().list(
                userId='me', 
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            if not messages:
                logger.info(f"No unread emails found matching filter: {subject_filter}")
                return FetchEmailsResult(
                    success=True,
                    emails=[]
                )
            
            # Fetch full message details
            emails = []
            for msg in messages:
                message = service.users().messages().get(
                    userId='me', 
                    id=msg['id'],
                    format='full'
                ).execute()
                
                # Parse message
                email = self._parse_message(message)
                emails.append(email)
            
            logger.info(f"Found {len(emails)} unread emails matching filter: {subject_filter}")
            return FetchEmailsResult(
                success=True,
                emails=emails
            )
            
        except HttpError as error:
            error_msg = f"Gmail API error: {error}"
            logger.error(error_msg)
            return FetchEmailsResult(
                success=False,
                error=error_msg,
                emails=[]
            )
        except Exception as e:
            error_msg = f"Error fetching emails: {str(e)}"
            logger.error(error_msg)
            return FetchEmailsResult(
                success=False,
                error=error_msg,
                emails=[]
            )
    
    async def mark_emails_as_read(self, message_ids: List[str]) -> Dict[str, Any]:
        """Mark emails as read by removing the UNREAD label.
        
        Args:
            message_ids: List of message IDs to mark as read
            
        Returns:
            Dictionary with operation result
        """
        if not message_ids:
            return {
                'success': True,
                'message': 'No messages to mark as read',
                'marked_count': 0
            }
            
        logger.info(f"Marking {len(message_ids)} emails as read")
        
        try:
            # Check authentication
            auth_status = self._check_auth()
            if not auth_status.get("authenticated", False):
                return {
                    'success': False,
                    'error': auth_status.get("error", "Authentication failed"),
                    'marked_count': 0
                }
            
            # Create Gmail API service
            service = build('gmail', 'v1', credentials=self.credentials)
            
            # Process each message
            marked_count = 0
            for msg_id in message_ids:
                try:
                    # Remove UNREAD label
                    service.users().messages().modify(
                        userId='me',
                        id=msg_id,
                        body={'removeLabelIds': ['UNREAD']}
                    ).execute()
                    marked_count += 1
                except HttpError as error:
                    logger.error(f"Error marking message {msg_id} as read: {error}")
            
            logger.info(f"Successfully marked {marked_count} out of {len(message_ids)} messages as read")
            
            return {
                'success': True,
                'message': f'Marked {marked_count} emails as read',
                'marked_count': marked_count
            }
            
        except HttpError as error:
            error_msg = f"Gmail API error: {error}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'marked_count': 0
            }
        except Exception as e:
            error_msg = f"Error marking emails as read: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'marked_count': 0
            }
    
    async def fetch_thread_by_email_id(self, email_id: str) -> FetchEmailsResult:
        """Fetch all emails from a thread by email ID.
        
        Args:
            email_id: The email ID to get the thread from
            
        Returns:
            FetchEmailsResult with list of emails in the thread
        """
        logger.info(f"Fetching emails from thread with email ID: {email_id}")
        
        try:
            # Check authentication
            auth_status = self._check_auth()
            if not auth_status.get("authenticated", False):
                return FetchEmailsResult(
                    success=False,
                    error=auth_status.get("error", "Authentication failed"),
                    emails=[]
                )
            
            # Create Gmail API service
            service = build('gmail', 'v1', credentials=self.credentials)
            
            # Get the message to find its thread ID
            try:
                message = service.users().messages().get(
                    userId='me',
                    id=email_id,
                    format='minimal'
                ).execute()
            except HttpError as error:
                error_msg = f"Error fetching message {email_id}: {error}"
                logger.error(error_msg)
                return FetchEmailsResult(
                    success=False,
                    error=error_msg,
                    emails=[]
                )
            
            # Get the thread ID
            thread_id = message.get('threadId', None)
            if not thread_id:
                error_msg = f"Message {email_id} has no thread ID"
                logger.error(error_msg)
                return FetchEmailsResult(
                    success=False,
                    error=error_msg,
                    emails=[]
                )
            
            # Get all messages in the thread
            try:
                thread = service.users().threads().get(
                    userId='me',
                    id=thread_id,
                    format='full'
                ).execute()
            except HttpError as error:
                error_msg = f"Error fetching thread {thread_id}: {error}"
                logger.error(error_msg)
                return FetchEmailsResult(
                    success=False,
                    error=error_msg,
                    emails=[]
                )
            
            # Process all messages in the thread
            emails = []
            thread_messages = thread.get('messages', [])
            
            if not thread_messages:
                logger.info(f"No messages found in thread {thread_id}")
                return FetchEmailsResult(
                    success=True,
                    emails=[]
                )
            
            # Parse each message in the thread
            for message in thread_messages:
                email = self._parse_message(message)
                emails.append(email)
            
            logger.info(f"Found {len(emails)} emails in thread {thread_id}")
            return FetchEmailsResult(
                success=True,
                emails=emails
            )
            
        except HttpError as error:
            error_msg = f"Gmail API error: {error}"
            logger.error(error_msg)
            return FetchEmailsResult(
                success=False,
                error=error_msg,
                emails=[]
            )
        except Exception as e:
            error_msg = f"Error fetching thread: {str(e)}"
            logger.error(error_msg)
            return FetchEmailsResult(
                success=False,
                error=error_msg,
                emails=[]
            ) 