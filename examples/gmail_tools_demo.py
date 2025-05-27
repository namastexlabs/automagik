#!/usr/bin/env python
"""Gmail API tools demo.

This script demonstrates how to use the Gmail API tools.
The script will use the GOOGLE_CREDENTIAL_FILE environment variable for authentication.

Example:
    python examples/gmail_tools_demo.py send --to recipient@example.com
"""
import argparse
import asyncio
import logging
import os
import sys

from src.tools.gmail import GmailTools

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def send_test_email(to_email, subject, message, cc=None):
    """Send a test email using the Gmail API tools.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        message: Email message content
        cc: Optional list of CC recipients
    """
    # Get credentials path from environment variable
    credentials_path = os.environ.get("GOOGLE_CREDENTIAL_FILE")
    if not credentials_path:
        logger.error("GOOGLE_CREDENTIAL_FILE environment variable not set")
        sys.exit(1)
        
    logger.info(f"Using credentials from: {credentials_path}")
    
    # Initialize Gmail tools
    gmail_tools = GmailTools(credentials_path=credentials_path)
    
    # Send email
    logger.info(f"Sending email to: {to_email}")
    result = await gmail_tools.send_email(
        to=to_email,
        subject=subject,
        message=message,
        cc=cc,
        extra_content="This email was sent using the Gmail API tools demo."
    )
    
    # Check result
    if result.get("success"):
        logger.info(f"Email sent successfully! Message ID: {result.get('message_id')}")
    else:
        logger.error(f"Failed to send email: {result.get('error')}")

def setup_arg_parser():
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(description="Gmail API Tools Demo")
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Send email command
    send_parser = subparsers.add_parser("send", help="Send a test email")
    send_parser.add_argument("--to", required=True, help="Recipient email address")
    send_parser.add_argument("--subject", default="Test Email from Gmail API Tools", help="Email subject")
    send_parser.add_argument("--message", default="This is a test email sent using the Gmail API tools.", help="Email message content")
    send_parser.add_argument("--cc", nargs="+", help="CC recipients (multiple emails can be provided)")
    
    return parser

async def main():
    """Main entry point for the demo script."""
    parser = setup_arg_parser()
    args = parser.parse_args()
    
    if args.command == "send":
        await send_test_email(args.to, args.subject, args.message, args.cc)
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main()) 