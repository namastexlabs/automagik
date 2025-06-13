#!/usr/bin/env python3
import os
import json
import time
import sqlite3
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import re
import threading
import signal

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

# Define constants
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]
ROOT_FOLDER_ID = '1nKUT0uSr8U_ZkrCO408_VS41LN4PG8RZ'
DB_NAME = "scripts/solid_stan/product_folder_matcher/product_folder_matches.db"
MAX_WORKERS = 5
REQUEST_DELAY = 0.1

# Create console for rich output
console = Console()
# Thread-local storage
thread_local = threading.local()
# Global credential cache
global_creds = None

class DriveCatalogBuilder:
    def __init__(self, credential_dir: str = 'credentials'):
        self.credential_dir = credential_dir
        self.root_folder_id = ROOT_FOLDER_ID
        self.db_path = DB_NAME
        self.conn = None
        self.cursor = None
        self.processed_items = set()
        self.checkpoint_frequency = 50  # Save checkpoint after processing this many items
        self.items_since_checkpoint = 0
        self.resume_mode = False
        # Thread lock for database operations
        self.db_lock = threading.Lock()
        # Stats tracking
        self.start_time = None
        self.last_count = 0
        self.items_per_minute = 0
        self.estimated_total = 500  # Initial estimate, will adjust based on findings
        self.mime_type_map = {
            'application/vnd.google-apps.folder': 'folder',
            'application/vnd.google-apps.document': 'google_doc',
            'application/vnd.google-apps.spreadsheet': 'google_sheet',
            'application/vnd.google-apps.presentation': 'google_presentation',
            'application/pdf': 'pdf',
            'image/jpeg': 'image',
            'image/png': 'image',
            'image/gif': 'image',
            'image/webp': 'image',
            'image/tiff': 'image',
            'image/bmp': 'image',
            'text/plain': 'text',
            'text/csv': 'csv',
            'application/zip': 'archive',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'word',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'excel',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'powerpoint',
        }
        # Initialize service
        self._init_service()

    def _get_credentials(self, verbose=False):
        """Get valid user credentials from storage or create new ones."""
        global global_creds
        
        # If we already have valid credentials, return them
        if global_creds and global_creds.valid:
            return global_creds
        
        creds = None
        token_path = os.path.join(self.credential_dir, 'drive_token.json')
        
        # Ensure credentials directory exists
        if not os.path.exists(self.credential_dir):
            os.makedirs(self.credential_dir)
        
        # Check if token file exists and load credentials
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_info(
                    json.loads(open(token_path).read()), SCOPES
                )
                if verbose:
                    console.print("[green]Loaded existing credentials[/green]")
            except Exception as e:
                if verbose:
                    console.print(f"[red]Error loading credentials: {e}[/red]")
        
        # If credentials are invalid or don't exist, refresh or create new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    if verbose:
                        console.print("[green]Successfully refreshed credentials[/green]")
                except Exception as e:
                    if verbose:
                        console.print(f"[red]Error refreshing credentials: {e}[/red]")
                    creds = None
            
            if not creds:
                credential_path = os.path.join(self.credential_dir, 'theros-google-credentials.json')
                if not os.path.exists(credential_path):
                    raise FileNotFoundError(f"Credentials file not found: {credential_path}")
                
                flow = InstalledAppFlow.from_client_secrets_file(credential_path, SCOPES)
                creds = flow.run_local_server(port=0)
                if verbose:
                    console.print("[green]New OAuth flow completed successfully[/green]")
            
            # Save the credentials for future use
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
                if verbose:
                    console.print(f"[green]Token saved to {token_path}[/green]")
        
        # Cache the credentials
        global_creds = creds
        return creds

    def _get_drive_service(self):
        """Get a thread-local Drive service instance to avoid concurrency issues."""
        if not hasattr(thread_local, 'drive_service'):
            # Only log credentials the first time we initialize the service in a thread
            verbose = not hasattr(threading.current_thread(), '_drive_service_initialized')
            threading.current_thread()._drive_service_initialized = True
            thread_local.drive_service = build('drive', 'v3', credentials=self._get_credentials(verbose=verbose))
        return thread_local.drive_service

    def _init_service(self):
        """Initialize the main Drive service."""
        # Initialize the main thread's service once
        self.service = build('drive', 'v3', credentials=self._get_credentials(verbose=True))
        threading.current_thread()._drive_service_initialized = True
        console.print("[green]Successfully authenticated with Google Drive API[/green]")

    def setup_database(self):
        """Create database schema with checkpoint support."""
        # Check if database exists
        db_exists = os.path.exists(self.db_path)
        
        # Connect to database
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        if db_exists:
            # Check if checkpoint table exists
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='drive_checkpoint'")
            if self.cursor.fetchone():
                # If checkpoint table exists, we can resume
                console.print(f"[yellow]Existing database found at {self.db_path}[/yellow]")
                user_input = input("Do you want to resume from where you left off? (y/n): ")
                if user_input.lower() == 'y':
                    self.resume_mode = True
                    console.print("[green]Resuming from checkpoint...[/green]")
                    # Load processed items from database
                    self._load_checkpoint()
                    return
                else:
                    console.print("[yellow]Recreating database from scratch...[/yellow]")
                    self.conn.close()
                    os.remove(self.db_path)
                    self.conn = sqlite3.connect(self.db_path)
                    self.cursor = self.conn.cursor()
            else:
                # Existing database without checkpoint support - recreate
                console.print("[yellow]Existing database without checkpoint support found.[/yellow]")
                console.print("[yellow]Recreating database with checkpoint support...[/yellow]")
                self.conn.close()
                os.remove(self.db_path)
                self.conn = sqlite3.connect(self.db_path)
                self.cursor = self.conn.cursor()
        
        # Create tables
        
        # Drive items table for all items (folders and files)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS drive_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drive_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                original_mime_type TEXT NOT NULL,
                item_type TEXT NOT NULL,
                parent_id TEXT,
                parent_drive_id TEXT,
                full_path TEXT NOT NULL,
                web_view_link TEXT,
                export_links TEXT,
                created_time TEXT,
                modified_time TEXT,
                is_folder BOOLEAN NOT NULL,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(parent_id) REFERENCES drive_items(id)
            )
        """)

        # Create hierarchy tables for brand, category, product relationships
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS drive_hierarchy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                level INTEGER NOT NULL,
                level_name TEXT NOT NULL,
                FOREIGN KEY(item_id) REFERENCES drive_items(id)
            )
        """)

        # Create item metadata table for extracted metadata
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS drive_item_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                FOREIGN KEY(item_id) REFERENCES drive_items(id)
            )
        """)
        
        # Create checkpoint table to enable resuming
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS drive_checkpoint (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drive_id TEXT NOT NULL UNIQUE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create checkpoint metadata table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS drive_checkpoint_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for better query performance
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_drive_items_drive_id ON drive_items(drive_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_drive_items_parent_id ON drive_items(parent_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_drive_items_parent_drive_id ON drive_items(parent_drive_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_drive_items_type ON drive_items(item_type)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_drive_items_full_path ON drive_items(full_path)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_hierarchy_level ON drive_hierarchy(level)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_metadata_key ON drive_item_metadata(key)")
        
        # Add index for checkpoint table
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_checkpoint_drive_id ON drive_checkpoint(drive_id)")

        self.conn.commit()
        console.print("[green]Database created successfully with checkpoint support[/green]")

    def _load_checkpoint(self):
        """Load previously processed items from checkpoint."""
        try:
            # Load processed drive IDs from checkpoint table
            self.cursor.execute("SELECT drive_id FROM drive_checkpoint")
            checkpoints = self.cursor.fetchall()
            
            for row in checkpoints:
                self.processed_items.add(row[0])
            
            # Get checkpoint metadata
            self.cursor.execute("SELECT key, value FROM drive_checkpoint_meta")
            meta = {row[0]: row[1] for row in self.cursor.fetchall()}
            
            console.print(f"[green]Loaded {len(self.processed_items)} processed items from checkpoint[/green]")
            
            # Check last timestamp
            last_checkpoint = meta.get('last_checkpoint')
            if last_checkpoint:
                console.print(f"[blue]Last checkpoint: {last_checkpoint}[/blue]")
                
            return True
        except Exception as e:
            console.print(f"[red]Error loading checkpoint: {str(e)}[/red]")
            return False
            
    def _save_checkpoint(self, drive_id: str):
        """Save a checkpoint for a processed item."""
        try:
            # Use main thread's connection for checkpoints
            if not self.conn:
                return False
                
            # Insert into checkpoint table
            with self.db_lock:
                self.cursor.execute(
                    "INSERT OR REPLACE INTO drive_checkpoint (drive_id) VALUES (?)",
                    (drive_id,)
                )
                
                # Update checkpoint metadata
                now = datetime.now().isoformat()
                self.cursor.execute(
                    "INSERT OR REPLACE INTO drive_checkpoint_meta (key, value, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)",
                    ('last_checkpoint', now)
                )
                
                self.conn.commit()
                self.items_since_checkpoint = 0
                return True
        except Exception as e:
            console.print(f"[red]Error saving checkpoint: {str(e)}[/red]")
            return False

    def _list_folder_items(self, folder_id: str) -> Dict[str, Any]:
        """List items in a folder with pagination support."""
        service = self._get_drive_service()
        
        # Small delay to avoid rate limiting
        time.sleep(REQUEST_DELAY)
        
        query = f"'{folder_id}' in parents and trashed = false"
        try:
            # Requesting additional fields for more data
            fields = "nextPageToken, files(id, name, mimeType, parents, webViewLink, exportLinks, createdTime, modifiedTime)"
            
            results = service.files().list(
                q=query,
                fields=fields,
                pageSize=100,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            return results
        except Exception as e:
            console.print(f"[red]Error listing folder {folder_id}: {str(e)}[/red]")
            return {"files": []}

    def _get_item_details(self, item_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific Drive item."""
        service = self._get_drive_service()
        
        # Small delay to avoid rate limiting
        time.sleep(REQUEST_DELAY)
        
        try:
            fields = "id, name, mimeType, parents, webViewLink, exportLinks, createdTime, modifiedTime"
            
            return service.files().get(
                fileId=item_id,
                fields=fields,
                supportsAllDrives=True
            ).execute()
        except Exception as e:
            console.print(f"[red]Error getting details for item {item_id}: {str(e)}[/red]")
            return None

    def _extract_metadata(self, name: str) -> Dict[str, str]:
        """Extract possible metadata from item name."""
        metadata = {}
        
        # Pattern for SKU and EAN
        sku_ean_pattern = r"([A-Z0-9]+)\s*-\s*(.+?)\s*-\s*(\d{13}|\d{12})"
        match = re.match(sku_ean_pattern, name)
        
        if match:
            metadata["sku"] = match.group(1)
            metadata["product_name"] = match.group(2).strip()
            metadata["ean"] = match.group(3)
        
        return metadata

    def _get_item_type(self, mime_type: str) -> str:
        """Map Google MIME type to our simplified item type."""
        return self.mime_type_map.get(mime_type, 'other')

    def _get_export_links_json(self, export_links: Dict) -> str:
        """Convert export links dictionary to JSON string."""
        if export_links:
            return json.dumps(export_links)
        return None

    def _get_db_connection(self):
        """Get a thread-local database connection."""
        if not hasattr(thread_local, 'db_conn'):
            thread_local.db_conn = sqlite3.connect(self.db_path)
            thread_local.db_cursor = thread_local.db_conn.cursor()
        return thread_local.db_conn, thread_local.db_cursor

    def _close_db_connections(self):
        """Close all thread-local database connections."""
        if hasattr(thread_local, 'db_conn'):
            thread_local.db_cursor.close()
            thread_local.db_conn.close()
            del thread_local.db_cursor
            del thread_local.db_conn

    def process_drive_item(self, item: Dict[str, Any], parent_id: Optional[int], parent_drive_id: Optional[str], 
                           parent_path: str, level: int, level_name: str):
        """Process a Drive item and insert it into the database."""
        # Use the thread local connection or main connection
        with self.db_lock:  # Lock to prevent race conditions on the processed_items set
            if item['id'] in self.processed_items:
                return None
            self.processed_items.add(item['id'])
        
        is_folder = item['mimeType'] == 'application/vnd.google-apps.folder'
        item_type = self._get_item_type(item['mimeType'])
        full_path = f"{parent_path}/{item['name']}" if parent_path else item['name']
        
        # Get additional fields if available
        web_view_link = item.get('webViewLink')
        export_links = self._get_export_links_json(item.get('exportLinks', {}))
        created_time = item.get('createdTime')
        modified_time = item.get('modifiedTime')
        
        # Get a thread-safe DB connection
        conn, cursor = self._get_db_connection()
        
        try:
            # Insert into drive_items table
            cursor.execute("""
                INSERT INTO drive_items (
                    drive_id, name, original_mime_type, item_type, parent_id, parent_drive_id,
                    full_path, web_view_link, export_links, created_time, modified_time, is_folder
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item['id'], item['name'], item['mimeType'], item_type, parent_id, parent_drive_id,
                full_path, web_view_link, export_links, created_time, modified_time, is_folder
            ))
            
            item_id = cursor.lastrowid
            
            # Insert into hierarchy table
            cursor.execute("""
                INSERT INTO drive_hierarchy (item_id, level, level_name)
                VALUES (?, ?, ?)
            """, (item_id, level, level_name))
            
            # Extract and store metadata
            metadata = self._extract_metadata(item['name'])
            for key, value in metadata.items():
                cursor.execute("""
                    INSERT INTO drive_item_metadata (item_id, key, value)
                    VALUES (?, ?, ?)
                """, (item_id, key, value))
            
            # Commit changes in this thread's connection
            conn.commit()
            
            # Save checkpoint periodically (only in main thread)
            if threading.current_thread() is threading.main_thread():
                self.items_since_checkpoint += 1
                
                # Check total items milestone for estimate adjustment
                total_items = len(self.processed_items)
                if total_items in [100, 500, 1000, 2000, 5000]:
                    # Update estimate based on what we've seen
                    # This helps provide a more accurate ETA as we learn more
                    if total_items >= 1000:
                        self.estimated_total = max(self.estimated_total, int(total_items * 1.2))
                    else:
                        self.estimated_total = max(self.estimated_total, int(total_items * 1.5))
                
                if self.items_since_checkpoint >= self.checkpoint_frequency:
                    self._save_checkpoint(item['id'])
                    if hasattr(thread_local, 'progress') and hasattr(thread_local, 'task_id'):
                        self.update_progress_display(
                            thread_local.task_id, 
                            "Saved checkpoint"
                        )
                elif self.items_since_checkpoint % 10 == 0:
                    # Regular commit in main thread
                    if self.conn:
                        self.conn.commit()
            
            return item_id if is_folder else None
            
        except Exception as e:
            console.print(f"[red]Error processing item {item['id']}: {str(e)}[/red]")
            return None

    def process_folders_recursive(self, folder_id: str, parent_id: Optional[int] = None, 
                                 parent_drive_id: Optional[str] = None, parent_path: str = "", 
                                 level: int = 0, level_name: str = "root"):
        """Recursively process a folder and its contents with checkpoint awareness."""
        # Skip if already processed (only for non-root folders)
        with self.db_lock:
            if level > 0 and folder_id in self.processed_items:
                return

        # Get folder info first if not root
        folder_name = None
        if level > 0:
            folder_details = self._get_item_details(folder_id)
            if not folder_details:
                return
            folder_name = folder_details['name']
        else:
            # For root, get the name
            try:
                folder_details = self.service.files().get(fileId=folder_id, fields="name").execute()
                folder_name = folder_details.get('name', "Root")
            except Exception:
                folder_name = "Root"
        
        # Process this folder first
        new_parent_id = parent_id
        if level > 0:  # Skip inserting the root folder
            folder_item = {
                'id': folder_id,
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            new_parent_id = self.process_drive_item(
                folder_item, parent_id, parent_drive_id, parent_path, level, level_name
            )
        
        current_path = parent_path
        if level > 0:
            current_path = f"{parent_path}/{folder_name}" if parent_path else folder_name
        
        # Determine the level name for children
        next_level_name = "brand"
        if level_name == "brand":
            next_level_name = "category"
        elif level_name == "category":
            next_level_name = "product"
        elif level_name == "product":
            next_level_name = "asset"
        
        # List all items in the folder
        items_response = self._list_folder_items(folder_id)
        items = items_response.get('files', [])
        
        # Update progress info with new stats display
        current_folder = f"{current_path}" if current_path else "Root"
        if hasattr(thread_local, 'progress') and hasattr(thread_local, 'task_id'):
            self.update_progress_display(
                thread_local.task_id,
                f"Processing: {current_folder} \n"
            )
            
        # Process regular files first (files are less likely to be important for structure)
        file_items = [item for item in items if item['mimeType'] != 'application/vnd.google-apps.folder']
        for item in file_items:
            # Skip if already processed
            with self.db_lock:
                if item['id'] in self.processed_items:
                    continue
                
            self.process_drive_item(
                item, new_parent_id, folder_id, current_path, level + 1, 
                next_level_name if level_name != "asset" else "asset_child"
            )
            
            # Update progress periodically (every 10 items)
            if len(self.processed_items) % 10 == 0:
                if hasattr(thread_local, 'progress') and hasattr(thread_local, 'task_id'):
                    self.update_progress_display(
                        thread_local.task_id,
                        f"Processing: {current_folder} \n"
                    )
        
        # Then process subfolders recursively (depth-first)
        folder_items = [item for item in items if item['mimeType'] == 'application/vnd.google-apps.folder']
        
        # For top levels, use parallel processing - but not if we're resuming (to avoid race conditions)
        if level < 2 and len(folder_items) > 1 and not self.resume_mode:
            # Process sequentially to avoid SQLite thread issues
            for item in folder_items:
                # Skip already processed folders
                with self.db_lock:
                    if item['id'] in self.processed_items:
                        continue
                    
                self.process_folders_recursive(
                    item['id'], new_parent_id, folder_id, current_path, level + 1, next_level_name
                )
        else:
            # Process sequentially
            for item in folder_items:
                # Skip already processed folders
                with self.db_lock:
                    if item['id'] in self.processed_items:
                        continue
                    
                self.process_folders_recursive(
                    item['id'], new_parent_id, folder_id, current_path, level + 1, next_level_name
                )
                
        # Save checkpoint after processing a significant folder (brand or category level)
        if level in [1, 2] and threading.current_thread() is threading.main_thread():
            with self.db_lock:
                if folder_id not in self.processed_items:
                    self._save_checkpoint(folder_id)
                    # Update progress with completed folder info
                    if hasattr(thread_local, 'progress') and hasattr(thread_local, 'task_id'):
                        self.update_progress_display(
                            thread_local.task_id, 
                            f"Completed folder: {folder_name}"
                        )
    
    def _update_progress_stats(self):
        """Update progress statistics for ETA calculation."""
        if not self.start_time:
            self.start_time = time.time()
            return
            
        current_count = len(self.processed_items)
        elapsed_seconds = time.time() - self.start_time
        elapsed_minutes = elapsed_seconds / 60
        
        if elapsed_minutes > 0:
            # Calculate items processed per minute
            self.items_per_minute = current_count / elapsed_minutes
            
            # Adjust the estimated total based on observed rate
            if current_count > 50:
                # Estimate total based on observed folder-to-item ratio
                if hasattr(self, 'folder_count') and self.folder_count > 0:
                    current_count / self.folder_count
                    # Adjust the estimated total gradually
                    self.estimated_total = max(self.estimated_total, int(current_count * 1.5))
                
        # Update count for next calculation
        self.last_count = current_count
                
    def _get_progress_info(self):
        """Get formatted progress information for display."""
        current_count = len(self.processed_items)
        
        # Update stats
        self._update_progress_stats()
        
        # Calculate elapsed time
        elapsed_seconds = 0
        if self.start_time:
            elapsed_seconds = time.time() - self.start_time
        elapsed_str = str(timedelta(seconds=int(elapsed_seconds)))
        
        # Calculate ETA
        eta_str = "Calculating..."
        if self.items_per_minute > 0:
            remaining_items = max(0, self.estimated_total - current_count)
            eta_minutes = remaining_items / self.items_per_minute
            eta_str = str(timedelta(minutes=int(eta_minutes)))
            
        # Calculate processing rate
        rate_str = f"{self.items_per_minute:.1f} items/min \n" if self.items_per_minute > 0 else "Calculating..."
        
        # Estimate completion percentage
        percent = min(100, (current_count / max(1, self.estimated_total)) * 100)
        percent_str = f"{percent:.1f}% \n"
        
        return {
            "count": current_count,
            "elapsed": elapsed_str,
            "eta": eta_str,
            "rate": rate_str,
            "percent": percent_str
        }
    
    def update_progress_display(self, task_id, description):
        """Update the progress display with timing information."""
        if hasattr(thread_local, 'progress') and hasattr(thread_local, 'task_id'):
            progress_info = self._get_progress_info()
            
            # Format the description with stats
            full_desc = (
                f"\n{description} | "
                f"[cyan]{progress_info['count']} items[/cyan] | "
                f"[yellow]~{progress_info['percent']}[/yellow] | "
                f"[green]{progress_info['rate']}[/green] | "
                f"Elapsed: [blue]{progress_info['elapsed']}[/blue] | "
                f"ETA: [magenta]{progress_info['eta']}[/magenta] \n"
            )
            
            thread_local.progress.update(task_id, description=full_desc)

    def build_catalog(self):
        """Build the Drive catalog with checkpoint support."""
        console.print("[bold blue]Setting up catalog database...[/bold blue]")
        self.setup_database()
        
        if not self.resume_mode:
            console.print("\n[bold green]Starting new catalog build from Drive folder structure...[/bold green]")
        else:
            console.print("\n[bold green]Resuming catalog build from checkpoint...[/bold green]")
            
        console.print("[yellow]This will catalog the entire Drive structure into a database for easier querying.[/yellow]")
        console.print("[blue]Press Ctrl+C at any time to stop. You can resume later.[/blue]")
        console.print("[yellow]Using sequential processing for thread safety.[/yellow]")
        
        # Initialize timing tracking
        self.start_time = time.time()
        
        try:
            # Start progress tracking with enhanced columns
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
            ) as progress:
                # Store progress in thread_local for access from other threads
                thread_local.progress = progress
                processed_count = len(self.processed_items)
                thread_local.task_id = progress.add_task(
                    f"Cataloging Drive structure ({processed_count} items)", 
                    total=None
                )
                
                # Process the root folder recursively
                self.process_folders_recursive(self.root_folder_id)
                
                # Final progress update
                self.update_progress_display(
                    thread_local.task_id,
                    "Completed cataloging"
                )
                
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            console.print("\n[yellow]Operation interrupted by user. Progress has been saved.[/yellow]")
            console.print("[green]You can resume later by running the script again.[/green]")
            # Save final checkpoint
            now = datetime.now().isoformat()
            self.cursor.execute(
                "INSERT OR REPLACE INTO drive_checkpoint_meta (key, value, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)",
                ('last_checkpoint', now)
            )
            self.cursor.execute(
                "INSERT OR REPLACE INTO drive_checkpoint_meta (key, value, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)",
                ('terminated', 'keyboard_interrupt')
            )
            self.conn.commit()
        finally:
            # Close all thread-local database connections
            self._close_db_connections()
            
        # Print summary
        self.cursor.execute("SELECT COUNT(*) FROM drive_items WHERE is_folder = 1")
        folder_count = self.cursor.fetchone()[0]
        self.folder_count = folder_count  # Store for stats calculations
        
        self.cursor.execute("SELECT COUNT(*) FROM drive_items WHERE is_folder = 0")
        file_count = self.cursor.fetchone()[0]
        
        self.cursor.execute("""
            SELECT level_name, COUNT(*) 
            FROM drive_hierarchy 
            GROUP BY level_name
            ORDER BY level
        """)
        level_stats = self.cursor.fetchall()
        
        # Calculate total elapsed time
        elapsed_seconds = time.time() - self.start_time
        elapsed_str = str(timedelta(seconds=int(elapsed_seconds)))
        
        # Create results table
        results_table = Table(title=f"Catalog Build Complete! (Total time: {elapsed_str})")
        results_table.add_column("Category", style="cyan")
        results_table.add_column("Count", style="green")
        
        results_table.add_row("Folders", str(folder_count))
        results_table.add_row("Files", str(file_count))
        results_table.add_row("Total Items", str(folder_count + file_count))
        results_table.add_row("Processing Rate", f"{self.items_per_minute:.1f} items/minute")
        
        console.print("\n")
        console.print(results_table)
        
        # Level stats table
        level_table = Table(title="Items by Level")
        level_table.add_column("Level", style="cyan")
        level_table.add_column("Count", style="green")
        
        for level_name, count in level_stats:
            level_table.add_row(level_name.capitalize(), str(count))
            
        console.print(level_table)
        
        # Final checkpoint
        now = datetime.now().isoformat()
        self.cursor.execute(
            "INSERT OR REPLACE INTO drive_checkpoint_meta (key, value, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)",
            ('completed', now)
        )
        self.conn.commit()
        
        console.print(f"\n[bold]Database saved to:[/bold] {self.db_path}")
        console.print("\n[green]You can now query the database to work with the catalog.[/green]")

    def save_checkpoint_manually(self):
        """Force a checkpoint save, for example when interrupted or periodically."""
        try:
            # Use main thread's connection
            if not self.conn:
                return False
                
            now = datetime.now().isoformat()
            with self.db_lock:
                self.cursor.execute(
                    "INSERT OR REPLACE INTO drive_checkpoint_meta (key, value, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)",
                    ('manual_checkpoint', now)
                )
                self.conn.commit()
            return True
        except Exception as e:
            console.print(f"[red]Error saving manual checkpoint: {str(e)}[/red]")
            return False

def main():
    # Create catalog builder
    catalog_builder = None
    
    # Set up signal handlers for graceful shutdown
    def handle_exit_signal(sig, frame):
        console.print("\n[yellow]Received exit signal. Saving checkpoint before exiting...[/yellow]")
        if catalog_builder and catalog_builder.conn:
            try:
                with catalog_builder.db_lock:
                    datetime.now().isoformat()
                    catalog_builder.cursor.execute(
                        "INSERT OR REPLACE INTO drive_checkpoint_meta (key, value, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)",
                        ('interrupted', f"signal_{sig}")
                    )
                    catalog_builder.conn.commit()
                console.print("[green]Checkpoint saved. You can resume later.[/green]")
            except Exception as e:
                console.print(f"[red]Error saving checkpoint: {str(e)}[/red]")
        # Exit without using sys.exit to avoid thread issues
        os._exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_exit_signal)   # Ctrl+C
    signal.signal(signal.SIGTERM, handle_exit_signal)  # termination request
    
    try:
        # Initialize catalog builder
        catalog_builder = DriveCatalogBuilder()
        
        # Display information about the script
        console.print("[bold cyan]===== Drive Catalog Builder =====")
        console.print("[blue]This script will catalog your Google Drive structure into a SQLite database.")
        console.print("[blue]The catalog includes file and folder IDs, paths, metadata, and direct links.")
        console.print("[green]✓ Checkpoint support: You can stop and resume the process at any time.")
        console.print("[green]✓ Press Ctrl+C to gracefully stop the process with automatic checkpoint saving.")
        console.print("[yellow]Database will be saved to: [bold]{0}[/bold][/yellow]\n".format(DB_NAME))
        
        # Build the catalog
        catalog_builder.build_catalog()
        
        # Sample query suggestion
        console.print("\n[bold]Sample queries you can run on this database:[/bold]")
        console.print("""
        -- Get all products with their brand and category
        SELECT
            product.name AS product_name, 
            brand.name AS brand_name,
            category.name AS category_name,
            product.drive_id,
            product.web_view_link
        FROM drive_items product
        JOIN drive_hierarchy product_h ON product.id = product_h.item_id AND product_h.level_name = 'product'
        JOIN drive_items category ON product.parent_drive_id = category.drive_id
        JOIN drive_items brand ON category.parent_drive_id = brand.drive_id;
        
        -- Get all images for a specific product
        SELECT 
            product.name AS product_name,
            image.name AS image_name,
            image.web_view_link,
            image.original_mime_type
        FROM drive_items product
        JOIN drive_items image ON image.parent_drive_id = product.drive_id
        WHERE product.is_folder = 1
        AND image.item_type = 'image';
        
        -- Find products by SKU or EAN
        SELECT 
            di.name AS product_name,
            di.full_path,
            di.web_view_link,
            dim.value AS sku_or_ean
        FROM drive_items di
        JOIN drive_item_metadata dim ON di.id = dim.item_id
        WHERE dim.key IN ('sku', 'ean')
        AND dim.value LIKE '%SEARCH_TERM%';
        """)
        
        # Show how to use SQLite to query
        console.print("\n[bold]To query the database:[/bold]")
        console.print("sqlite3 drive_product_catalog.db")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        if catalog_builder and catalog_builder.conn:
            catalog_builder.save_checkpoint_manually()
            console.print("[green]Manual checkpoint saved.[/green]")
    except Exception as e:
        console.print(f"\n[red]An error occurred: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        if catalog_builder and catalog_builder.conn:
            try:
                # Save error info in checkpoint
                catalog_builder.cursor.execute(
                    "INSERT OR REPLACE INTO drive_checkpoint_meta (key, value, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)",
                    ('error', str(e))
                )
                catalog_builder.conn.commit()
                console.print("[yellow]Error info saved to checkpoint metadata.[/yellow]")
            except Exception:
                pass

if __name__ == "__main__":
    main() 