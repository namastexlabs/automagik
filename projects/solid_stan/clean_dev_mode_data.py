#!/usr/bin/env python
"""
Script to clean development mode test data.

This script:
1. Fetches all contacts from BlackPearl API
2. Identifies contacts with "_devmode" in their wpp_session_id
3. Deletes related cliente, contato, messages, sessions, and user records
"""

import os
import sys
import asyncio
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
import argparse
from colorama import init, Fore, Back, Style
from datetime import datetime

# Initialize colorama
init(autoreset=True)

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.blackpearl import (
    get_contatos, get_cliente, delete_cliente, delete_contato, get_clientes
)
from src.db.repository.message import delete_session_messages
from src.db.repository.session import list_sessions, delete_session
from src.db.repository.user import get_user, delete_user

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors."""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE,
    }
    
    def format(self, record):
        # Add color to the level name
        level_color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{level_color}{record.levelname}{Style.RESET_ALL}"
        
        # Add color to the message
        if record.levelno >= logging.ERROR:
            record.msg = f"{Fore.RED}{record.msg}{Style.RESET_ALL}"
        elif record.levelno >= logging.WARNING:
            record.msg = f"{Fore.YELLOW}{record.msg}{Style.RESET_ALL}"
        elif record.levelno >= logging.INFO:
            record.msg = f"{Fore.GREEN}{record.msg}{Style.RESET_ALL}"
        
        # Add timestamp with color (only day, month, and time)
        record.created_fmt = f"{Fore.BLUE}{datetime.fromtimestamp(record.created).strftime('%d-%m %H:%M:%S')}{Style.RESET_ALL}"
        
        return super().format(record)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with custom formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter(
    '%(created_fmt)s - %(message)s'
))

# Create file handler with full format for debugging
file_handler = logging.FileHandler("dev_mode_cleanup.log")
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Load environment variables
load_dotenv()

async def get_all_contatos() -> List[Dict[str, Any]]:
    """Get all contacts from BlackPearl API."""
    logger.info("Fetching all contacts from BlackPearl API...")
    
    all_contatos = []
    offset = 0
    limit = 100
    
    while True:
        try:
            # Context dictionary for API calls
            ctx = {"user_id": None, "_agent_id_numeric": None}
            
            # Get contacts with pagination
            result = await get_contatos(ctx, limit=limit, offset=offset)
            contatos = result.get("results", [])
            
            if not contatos:
                break
            
            all_contatos.extend(contatos)
            logger.info(f"Retrieved {len(contatos)} contacts (offset: {offset})")
            
            # Break if we've reached the end
            if len(contatos) < limit:
                break
            
            offset += limit
        except Exception as e:
            logger.error(f"Error fetching contacts: {str(e)}")
            break
    
    logger.info(f"Total contacts retrieved: {len(all_contatos)}")
    return all_contatos

async def find_dev_mode_contatos(contatos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find contacts with '_devmode' in wpp_session_id."""
    logger.info("Identifying contacts with '_devmode' in wpp_session_id...")
    
    dev_mode_contatos = []
    
    for contato in contatos:
        wpp_session_id = contato.get("wpp_session_id", "")
        if wpp_session_id and "_devmode" in wpp_session_id:
            dev_mode_contatos.append(contato)
    
    logger.info(f"Found {len(dev_mode_contatos)} contacts with '_devmode' in wpp_session_id")
    return dev_mode_contatos

async def get_all_clients_for_contact(ctx: Dict[str, Any], contato_id: int) -> List[Dict[str, Any]]:
    """Get all clients that have a specific contact."""
    logger.info(f"Looking for clients containing contato ID: {contato_id}")
    
    all_clientes = []
    offset = 0
    limit = 100
    
    while True:
        try:
            # Get all clients with pagination
            result = await get_clientes(ctx, limit=limit, offset=offset)
            clientes = result.get("results", [])
            
            if not clientes:
                break
            
            # Check each client to see if it has the contact we're looking for
            for cliente in clientes:
                contatos = cliente.get("contatos", [])
                if contato_id in contatos:
                    logger.info(f"Found client {cliente.get('id')} with contato {contato_id}")
                    all_clientes.append(cliente)
            
            # Break if we've reached the end
            if len(clientes) < limit:
                break
            
            offset += limit
        except Exception as e:
            logger.error(f"Error fetching clients: {str(e)}")
            break
    
    logger.info(f"Found {len(all_clientes)} clients containing contato ID: {contato_id}")
    return all_clientes

async def clean_dev_mode_data(dry_run: bool = False, test_mode: bool = False):
    """Find and clean development mode test data."""
    # Get all contacts
    contatos = await get_all_contatos()
    
    # Find dev mode contacts
    dev_mode_contatos = await find_dev_mode_contatos(contatos)
    
    if not dev_mode_contatos:
        logger.info("No development mode contacts found.")
        return
    
    # In test mode, just list what would be deleted without deleting anything
    if test_mode:
        logger.info("TEST MODE: Showing contacts with '_devmode' in wpp_session_id")
        for i, contato in enumerate(dev_mode_contatos, 1):
            contato_id = contato.get("id")
            nome = contato.get("nome", "Unknown")
            telefone = contato.get("telefone", "Unknown")
            wpp_session_id = contato.get("wpp_session_id", "")
            
            try:
                parts = wpp_session_id.split("_")
                # Don't attempt to convert UUID parts to integers
                user_id = parts[0] if len(parts) > 0 else "Unknown"
                agent_id = parts[1] if len(parts) > 1 else "Unknown"
            except (ValueError, IndexError):
                user_id = "Invalid"
                agent_id = "Invalid"
            
            logger.info(f"{i}. Contato ID: {contato_id}, Nome: {nome}, Telefone: {telefone}")
            logger.info(f"   wpp_session_id: {wpp_session_id}")
            logger.info(f"   Parsed: user_id={user_id}, agent_id={agent_id}")
        return
    
    # Process each dev mode contact
    for contato in dev_mode_contatos:
        contato_id = contato.get("id")
        wpp_session_id = contato.get("wpp_session_id", "")
        
        logger.info(f"Processing contato ID {contato_id} with wpp_session_id '{wpp_session_id}'")
        
        try:
            # Parse user_id and agent_id from wpp_session_id
            parts = wpp_session_id.split("_")
            # Don't try to convert UUID-like strings to integers
            if len(parts) >= 2:
                user_id = parts[0]  # Keep as string, don't convert to int
                agent_id = parts[1]  # Keep as string, don't convert to int
                
                logger.info(f"Extracted user_id: {user_id}, agent_id: {agent_id}")
                
                # Attempt to find the user locally - only convert to int if needed by the DB function
                user_exists_locally = False
                try:
                    # If get_user requires an integer, try to check if it's numeric first
                    numeric_user_id = None
                    try:
                        if user_id.isdigit():
                            numeric_user_id = int(user_id)
                        else:
                            logger.info(f"User ID '{user_id}' is not numeric, will use as string")
                    except (ValueError, AttributeError):
                        logger.info(f"Could not convert user_id '{user_id}' to integer, will use as string")
                    
                    # Try with numeric ID if converted, otherwise use the string
                    user = get_user(numeric_user_id if numeric_user_id is not None else user_id)
                    if user:
                        logger.info(f"Found user record for user_id {user_id}")
                        user_exists_locally = True
                    else:
                        logger.warning(f"No user record found for user_id {user_id}. Proceeding with BP cleanup.")
                except Exception as e:
                    logger.error(f"Error checking local user {user_id}: {str(e)}. Skipping this contact.")
                    continue
                
                # Always proceed with BlackPearl cleanup steps unless local DB check failed
                
                # Find associated BlackPearl client(s)
                cliente_ids_to_delete = []
                try:
                    # Context dictionary for API calls
                    ctx = {"user_id": None, "_agent_id_numeric": None}
                    
                    # Search for clients that have this contact
                    for cliente in await get_all_clients_for_contact(ctx, contato_id):
                        cliente_id = cliente.get("id")
                        if cliente_id:
                            logger.info(f"Found client record with ID {cliente_id} for contato {contato_id}")
                            cliente_ids_to_delete.append(cliente_id)
                except Exception as e:
                    logger.error(f"Error searching clients for contato {contato_id}: {str(e)}")
                
                if not dry_run:
                    # Delete local data ONLY if the user existed locally
                    if user_exists_locally:
                        # Delete all session messages
                        # Try to convert agent_id to int if it's numeric for compatibility with list_sessions
                        numeric_agent_id = None
                        try:
                            if agent_id.isdigit():
                                numeric_agent_id = int(agent_id)
                            else:
                                logger.info(f"Agent ID '{agent_id}' is not numeric, will use as string")
                        except (ValueError, AttributeError):
                            logger.info(f"Could not convert agent_id '{agent_id}' to integer, will use as string")
                        
                        # Use either numeric ID or string based on conversion success
                        sessions = list_sessions(
                            user_id=numeric_user_id if numeric_user_id is not None else user_id, 
                            agent_id=numeric_agent_id if numeric_agent_id is not None else agent_id
                        )
                        if sessions:
                            logger.info(f"Found {len(sessions)} sessions for user {user_id}, agent {agent_id}")
                            deleted_session_count = 0
                            for i, session in enumerate(sessions):
                                # DEBUG: Log session type and attributes
                                logger.debug(f"Processing session {i+1}/{len(sessions)}: type={type(session)}, dir={dir(session)}")
                                
                                # Access session ID using the correct attribute 'id'
                                try:
                                    session_uuid = session.id
                                except AttributeError as e:
                                    logger.error(f"AttributeError accessing session.id for session {i+1}: {e}")
                                    logger.error(f"Session object details: {session}")
                                    continue # Skip this session if ID cannot be accessed
                                    
                                if session_uuid:
                                    # Delete messages for this specific session
                                    logger.info(f"Deleting messages for session {session_uuid}...")
                                    deleted_message_count = delete_session_messages(session_id=session_uuid)
                                    logger.info(f"Deleted {deleted_message_count} messages for session {session_uuid}")

                                    # Delete this specific session
                                    logger.info(f"Deleting session {session_uuid}...")
                                    if delete_session(session_id=session_uuid):
                                        logger.info(f"Deleted session {session_uuid}")
                                        deleted_session_count += 1
                                    else:
                                        logger.warning(f"Failed to delete session {session_uuid}")
                                else:
                                    logger.warning(f"Session {i+1} found but has no ID (session.id is None or evaluates to False).")
                                    
                            # Log total sessions deleted for this user/agent pair
                            logger.info(f"Deleted {deleted_session_count} sessions in total for user {user_id}, agent {agent_id}")
                        else:
                           logger.info(f"No sessions found locally for user {user_id}, agent {agent_id}")
                           
                        # Delete user record (if user existed locally)
                        logger.info(f"Deleting user record for user_id {user_id}...")
                        if delete_user(user_id):
                            logger.info(f"Deleted user record for user_id {user_id}")
                        else:
                            logger.warning(f"Could not delete user record for user_id {user_id} (already deleted?)")
                    else:
                        logger.info(f"Skipping local data deletion as user {user_id} was not found locally.")

                    # Always delete BlackPearl data (client and contact)
                    
                    # Delete associated BlackPearl client(s)
                    if cliente_ids_to_delete:
                        for cliente_id_to_delete in cliente_ids_to_delete:
                            try:
                                logger.info(f"Deleting client record with ID {cliente_id_to_delete} from BlackPearl...")
                                await delete_cliente(ctx, cliente_id_to_delete)
                                logger.info(f"Deleted client record with ID {cliente_id_to_delete} from BlackPearl")
                            except Exception as e:
                                logger.error(f"Error deleting client {cliente_id_to_delete}: {str(e)}")
                    else:
                        logger.info(f"No associated client found in BlackPearl for contato {contato_id}")

                    # Delete BlackPearl contact
                    try:
                        logger.info(f"Deleting contato record {contato_id} from BlackPearl...")
                        await delete_contato(ctx, contato_id)
                        logger.info(f"Deleted contato record {contato_id} from BlackPearl")
                    except Exception as e:
                        logger.error(f"Error deleting contato {contato_id}: {str(e)}")
            else:
                logger.warning(f"Invalid wpp_session_id format: {wpp_session_id}")
        except Exception as e:
            logger.error(f"Error processing contato {contato_id}: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean development mode test data")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually delete data, just show what would be deleted")
    parser.add_argument("--test", action="store_true", help="Test mode: Just list contacts with '_devmode' in wpp_session_id")
    
    args = parser.parse_args()
    
    logger.info("Starting cleanup script")
    if args.dry_run:
        logger.info("DRY RUN MODE: No data will be deleted")
    if args.test:
        logger.info("TEST MODE: Only listing contacts, no deletion")
    
    asyncio.run(clean_dev_mode_data(dry_run=args.dry_run, test_mode=args.test))
    
    logger.info("Cleanup complete") 