"""Tools for product folder matcher agent."""

import sqlite3
import time
from typing import Dict, Any, List, Optional
from rich.console import Console

from scripts.solid_stan.product_folder_matcher.observability import log_error
from scripts.solid_stan.product_folder_matcher.models import FolderContent

# Initialize console for rich output
console = Console()

class ProductFolderMatcherTools:
    """Tools for the matching agent to use during decision making."""
    
    def __init__(self, sqlite_conn: sqlite3.Connection):
        """Initialize tools with SQLite connection.
        
        Args:
            sqlite_conn: Connection to SQLite database
        """
        self.sqlite_conn = sqlite_conn
    
    def read_folder_contents(self, folder_id: str) -> Dict[str, Any]:
        """Read contents of a Drive folder.
        
        Args:
            folder_id: Drive folder ID
            
        Returns:
            Dictionary with folder details and children
        """
        cursor = self.sqlite_conn.cursor()
        
        try:
            start_time = time.time()
            
            # Get folder details
            cursor.execute("""
                SELECT 
                    id, name, full_path
                FROM 
                    drive_items
                WHERE 
                    drive_id = ?
            """, (folder_id,))
            
            folder_row = cursor.fetchone()
            
            if not folder_row:
                error_msg = f"Folder with ID {folder_id} not found"
                log_error(error_msg, "folder_not_found", {"folder_id": folder_id})
                return {"error": error_msg}
            
            # Get folder contents
            cursor.execute("""
                SELECT 
                    id, drive_id, name, full_path, item_type, is_folder
                FROM 
                    drive_items
                WHERE 
                    parent_drive_id = ?
                ORDER BY
                    is_folder DESC, name
            """, (folder_id,))
            
            children = []
            for row in cursor.fetchall():
                children.append({
                    "id": row[0],
                    "drive_id": row[1],
                    "name": row[2],
                    "full_path": row[3],
                    "item_type": row[4],
                    "is_folder": bool(row[5])
                })
            
            # Format as a FolderContent object
            result = {
                "folder_id": folder_id,
                "folder_name": folder_row[1],
                "folder_path": folder_row[2],
                "children": children
            }
            
            console.print(f"[cyan]Read {len(children)} items from folder '{folder_row[1]}'[/cyan]")
            
            # Log timing
            elapsed = time.time() - start_time
            console.print(f"[cyan]Folder read completed in {elapsed:.2f} seconds[/cyan]")
            
            return result
        except Exception as e:
            error_msg = f"Failed to read folder contents: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            log_error(error_msg, "read_folder_contents_error", {"folder_id": folder_id})
            return {"error": str(e)}
    
    def examine_product_files(self, folder_id: str, pattern: Optional[str] = None) -> Dict[str, Any]:
        """Examine files within a product folder that might contain product details.
        
        Args:
            folder_id: Drive folder ID
            pattern: Optional file name pattern to filter by
            
        Returns:
            Dictionary with file details and content summary
        """
        cursor = self.sqlite_conn.cursor()
        
        try:
            start_time = time.time()
            
            # Get folder details first
            cursor.execute("""
                SELECT 
                    id, name, full_path
                FROM 
                    drive_items
                WHERE 
                    drive_id = ?
            """, (folder_id,))
            
            folder_row = cursor.fetchone()
            
            if not folder_row:
                error_msg = f"Folder with ID {folder_id} not found"
                log_error(error_msg, "folder_not_found", {"folder_id": folder_id})
                return {"error": error_msg}
            
            # Use pattern if provided, otherwise get all files
            if pattern:
                cursor.execute("""
                    SELECT 
                        id, drive_id, name, full_path, item_type
                    FROM 
                        drive_items
                    WHERE 
                        parent_drive_id = ?
                        AND name LIKE ?
                        AND is_folder = 0
                    ORDER BY
                        name
                """, (folder_id, f"%{pattern}%"))
            else:
                cursor.execute("""
                    SELECT 
                        id, drive_id, name, full_path, item_type
                    FROM 
                        drive_items
                    WHERE 
                        parent_drive_id = ?
                        AND is_folder = 0
                    ORDER BY
                        name
                """, (folder_id,))
            
            files = []
            for row in cursor.fetchall():
                files.append({
                    "id": row[0],
                    "drive_id": row[1],
                    "name": row[2],
                    "full_path": row[3],
                    "item_type": row[4]
                })
            
            # Extract file info and organize by type
            image_files = [f for f in files if f["item_type"] == "image"]
            document_files = [f for f in files if f["item_type"] in ["google_doc", "pdf", "word", "text"]]
            spreadsheet_files = [f for f in files if f["item_type"] in ["google_sheet", "excel", "csv"]]
            other_files = [f for f in files if f not in image_files + document_files + spreadsheet_files]
            
            result = {
                "folder_name": folder_row[1],
                "folder_path": folder_row[2],
                "image_count": len(image_files),
                "document_count": len(document_files),
                "spreadsheet_count": len(spreadsheet_files),
                "other_files_count": len(other_files),
                "total_files": len(files),
                "images": image_files[:5],  # Limit to first 5 of each type
                "documents": document_files[:5],
                "spreadsheets": spreadsheet_files[:5],
                "other_files": other_files[:5]
            }
            
            console.print(f"[cyan]Examined folder '{folder_row[1]}', found {len(files)} files[/cyan]")
            
            # Log timing
            elapsed = time.time() - start_time
            console.print(f"[cyan]File examination completed in {elapsed:.2f} seconds[/cyan]")
            
            return result
        except Exception as e:
            error_msg = f"Failed to examine product files: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            log_error(error_msg, "examine_product_files_error", {"folder_id": folder_id, "pattern": pattern})
            return {"error": str(e)}
    
    def extract_product_info_from_path(self, folder_path: str) -> Dict[str, str]:
        """Extract potential product information from a folder path.
        
        Args:
            folder_path: Full path to a folder
            
        Returns:
            Dictionary with extracted product information
        """
        try:
            # Common patterns in folder paths:
            # 1. EAN/code at the beginning - "1234567890123 - Product Name"
            # 2. SKU/code - "BRAND/Category/SKU123 - Product Name"
            
            # Get just the folder name (last part of path)
            parts = folder_path.split('/')
            folder_name = parts[-1] if parts else folder_path
            
            # Initialize extracted info
            extracted = {
                "possible_ean": None,
                "possible_sku": None,
                "possible_product_name": None,
                "folder_name": folder_name,
                "brand": parts[0] if parts else None,
                "category": parts[1] if len(parts) > 1 else None
            }
            
            # Try to extract EAN and product name
            # Pattern: "1234567890123 - Product Name"
            if "-" in folder_name:
                prefix, rest = folder_name.split("-", 1)
                prefix = prefix.strip()
                
                # Check if prefix is a potential EAN (12-13 digits)
                digits_only = ''.join(c for c in prefix if c.isdigit())
                if len(digits_only) in (12, 13) and digits_only.isdigit():
                    extracted["possible_ean"] = digits_only
                    extracted["possible_product_name"] = rest.strip()
                else:
                    # Might be a SKU
                    extracted["possible_sku"] = prefix
                    extracted["possible_product_name"] = rest.strip()
            
            return extracted
        except Exception as e:
            error_msg = f"Failed to extract product info from path: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            log_error(error_msg, "extract_product_info_error", {"folder_path": folder_path})
            return {
                "error": str(e),
                "folder_path": folder_path
            } 