"""Database connections and queries for product folder matcher."""

import os
import sqlite3
import psycopg2
import urllib.parse
import json
import time
from typing import Dict, List, Set, Tuple, Optional, Any
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console

from scripts.solid_stan.product_folder_matcher.models import DriveFolder, BlackpearlProduct
from scripts.solid_stan.product_folder_matcher.observability import log_database_connection, log_error

# Initialize console for rich output
console = Console()

# Load environment variables
load_dotenv()

def connect_sqlite_db(db_path: str = "drive_product_catalog.db") -> sqlite3.Connection:
    """Connect to SQLite database.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        SQLite connection object
    """
    try:
        # Create database directory if it doesn't exist
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        # Connect to database (will create if doesn't exist)
        conn = sqlite3.connect(db_path)
        
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Configure for better performance
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        
        # Use basename to show just the filename in the log
        db_filename = os.path.basename(db_path)
        console.print(f"[green]Connected to SQLite database: [cyan]{db_filename}[/cyan] at path [dim]{db_path}[/dim][/green]")
        log_database_connection("sqlite", db_path, db_filename, True)
        
        return conn
    except Exception as e:
        error_msg = f"Failed to connect to SQLite database: {str(e)}"
        console.print(f"[red]{error_msg}[/red]")
        log_error(error_msg, "sqlite_connection_error", {"db_path": db_path})
        raise

def connect_postgres_db() -> psycopg2.extensions.connection:
    """Connect to PostgreSQL database using environment variables.
    
    Returns:
        PostgreSQL connection object
    """
    try:
        # Get database URI from environment
        db_uri = os.getenv('BLACKPEARL_DB_URI')
        
        if not db_uri:
            raise ValueError("BLACKPEARL_DB_URI not found in environment variables")

        # Parse the connection string
        result = urllib.parse.urlparse(db_uri)
        username = result.username
        password = result.password
        database = result.path[1:]
        hostname = result.hostname
        port = result.port
        
        console.print(f"[blue]Connecting to Blackpearl database {database} at {hostname}...[/blue]")
        
        # Connect with a timeout
        conn = psycopg2.connect(
            host=hostname,
            port=port,
            database=database,
            user=username,
            password=password,
            connect_timeout=10  # 10 seconds connection timeout
        )
        
        console.print(f"[green]Connected to Blackpearl database successfully![/green]")
        log_database_connection("postgres", hostname, database, True)
        
        return conn
    except Exception as e:
        error_msg = f"Failed to connect to PostgreSQL database: {str(e)}"
        console.print(f"[red]{error_msg}[/red]")
        
        # Add more specific error messages
        if "password authentication failed" in str(e).lower():
            console.print("[yellow]Hint: Check if the database credentials in BLACKPEARL_DB_URI are correct[/yellow]")
        elif "could not connect to server" in str(e).lower():
            console.print("[yellow]Hint: Check if the database server is running and accessible[/yellow]")
        elif "operation timed out" in str(e).lower():
            console.print("[yellow]Hint: Database connection timed out. Server might be unreachable.[/yellow]")
        
        log_error(error_msg, "postgres_connection_error", {})
        raise

def create_results_tables(conn: sqlite3.Connection) -> None:
    """Create tables for storing match results.
    
    Args:
        conn: SQLite connection object
    """
    cursor = conn.cursor()
    
    # Create match results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_folder_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            drive_folder_id TEXT NOT NULL,
            product_descricao TEXT NOT NULL,
            folder_name TEXT NOT NULL, 
            folder_path TEXT NOT NULL,
            confidence_score REAL NOT NULL,
            reasoning TEXT NOT NULL,
            warning_flags TEXT,
            match_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create duplicate matches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS duplicate_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drive_folder_id TEXT NOT NULL,
            product_ids TEXT NOT NULL,
            product_names TEXT NOT NULL,
            confidence_scores TEXT NOT NULL,
            detection_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_product_id ON product_folder_matches(product_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_drive_folder_id ON product_folder_matches(drive_folder_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_duplicates_drive_folder_id ON duplicate_matches(drive_folder_id)")
    
    conn.commit()

def create_progress_table(conn: sqlite3.Connection) -> None:
    """Create table to track matching progress for resumability.
    
    Args:
        conn: SQLite connection object
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matching_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            processed BOOLEAN DEFAULT FALSE,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(brand, product_id)
        )
    """)
    
    # Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_matching_progress_product_id ON matching_progress(product_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_matching_progress_last_updated ON matching_progress(last_updated)")
    
    conn.commit()

def save_progress(conn: sqlite3.Connection, brand: str, product_id: int, processed: bool = True) -> None:
    """Save progress for resumability.
    
    Args:
        conn: SQLite connection object
        brand: Brand name
        product_id: Product ID
        processed: Whether processing was successful
    """
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO matching_progress 
            (brand, product_id, processed, last_updated) 
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (brand, product_id, processed))
        
        conn.commit()
    except Exception as e:
        error_msg = f"Failed to save progress: {str(e)}"
        console.print(f"[red]{error_msg}[/red]")
        log_error(error_msg, "save_progress_error", {
            "brand": brand,
            "product_id": product_id,
            "processed": processed
        })
        conn.rollback()

def get_processed_products(conn: sqlite3.Connection) -> Set[int]:
    """Get set of product IDs that have already been processed.
    
    Args:
        conn: SQLite connection object
        
    Returns:
        Set of processed product IDs
    """
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT product_id FROM matching_progress WHERE processed = TRUE")
        return {row[0] for row in cursor.fetchall()}
    except Exception as e:
        error_msg = f"Failed to get processed products: {str(e)}"
        console.print(f"[red]{error_msg}[/red]")
        log_error(error_msg, "get_processed_products_error", {})
        return set()

def get_last_brand_product(conn: sqlite3.Connection) -> Tuple[Optional[str], Optional[int]]:
    """Get the last brand and product ID processed for resuming.
    
    Args:
        conn: SQLite connection object
        
    Returns:
        Tuple of (brand, product_id) or (None, None) if no progress exists
    """
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT brand, product_id FROM matching_progress 
            ORDER BY last_updated DESC LIMIT 1
        """)
        
        result = cursor.fetchone()
        return result if result else (None, None)
    except Exception as e:
        error_msg = f"Failed to get last brand and product: {str(e)}"
        console.print(f"[red]{error_msg}[/red]")
        log_error(error_msg, "get_last_brand_product_error", {})
        return (None, None)

def get_products_by_brand(conn: psycopg2.extensions.connection, brand_filter: Optional[str] = None) -> Dict[str, List[BlackpearlProduct]]:
    """Get all products from Blackpearl grouped by brand.
    
    Args:
        conn: PostgreSQL connection object
        brand_filter: Optional brand name to filter by
        
    Returns:
        Dictionary mapping brand names to lists of BlackpearlProduct objects
    """
    cursor = conn.cursor()
    
    query = """
        SELECT 
            p.id, 
            p.descricao, 
            p.descr_detalhada, 
            p.codigo, 
            p.especificacoes,
            p.valor_unitario,
            m.nome as marca_nome,
            f."nomeFamilia" as familia_nome,
            p.inativo
        FROM 
            catalogo_produto p
        LEFT JOIN 
            catalogo_marca m ON p.marca_id = m.id
        LEFT JOIN 
            catalogo_familiadeproduto f ON p.familia_id = f.id
        WHERE 
            p.inativo = FALSE
    """
    
    # Add brand filter if specified
    params = []
    if brand_filter:
        query += " AND m.nome ILIKE %s"
        params.append(f"%{brand_filter}%")
    
    query += " ORDER BY m.nome, p.descricao"
    
    try:
        start_time = time.time()
        cursor.execute(query, params)
        
        # Group by brand
        products_by_brand = {}
        
        for row in cursor.fetchall():
            product = BlackpearlProduct(
                id=row[0],
                descricao=row[1] or '',
                descr_detalhada=row[2] or '',
                codigo=row[3] or '',
                especificacoes=row[4] or '',
                valor_unitario=row[5],
                marca=row[6] or 'Unknown',
                familia=row[7] or '',
                inativo=row[8] or False
            )
            
            brand = product.marca.upper()
            
            if brand not in products_by_brand:
                products_by_brand[brand] = []
                
            products_by_brand[brand].append(product)
        
        elapsed = time.time() - start_time
        brand_count = len(products_by_brand)
        total_count = sum(len(products) for products in products_by_brand.values())
        
        console.print(f"[green]Retrieved {total_count} products across {brand_count} brands in {elapsed:.2f} seconds[/green]")
        
        return products_by_brand
    except Exception as e:
        error_msg = f"Failed to get products by brand: {str(e)}"
        console.print(f"[red]{error_msg}[/red]")
        log_error(error_msg, "get_products_by_brand_error", {"brand_filter": brand_filter})
        return {}

def get_folders_by_brand(conn: sqlite3.Connection, brand_filter: Optional[str] = None) -> Dict[str, List[DriveFolder]]:
    """Get all folders from Drive grouped by brand.
    
    Args:
        conn: SQLite connection object
        brand_filter: Optional brand name to filter by
        
    Returns:
        Dictionary mapping brand names to lists of DriveFolder objects
    """
    cursor = conn.cursor()
    
    try:
        start_time = time.time()
        
        # First get top-level brand folders
        brand_query = """
            SELECT 
                di.id,
                di.drive_id,
                di.name,
                di.full_path,
                di.item_type,
                di.is_folder,
                dh.level_name,
                di.parent_id,
                di.parent_drive_id
            FROM 
                drive_items di
            JOIN 
                drive_hierarchy dh ON di.id = dh.item_id
            WHERE 
                dh.level_name = 'brand'
                AND di.is_folder = 1
        """
        
        # Add brand filter if specified
        if brand_filter:
            brand_query += f" AND di.name LIKE '%{brand_filter}%' COLLATE NOCASE"
        
        cursor.execute(brand_query)
        
        # Store brand folders and initialize the result dictionary
        brand_folders = {}
        folders_by_brand = {}
        
        for row in cursor.fetchall():
            folder = DriveFolder(
                id=row[0],
                drive_id=row[1],
                name=row[2],
                full_path=row[3],
                item_type=row[4],
                is_folder=row[5],
                level_name=row[6],
                parent_id=row[7],
                parent_drive_id=row[8]
            )
            
            brand_name = folder.name.upper()
            brand_folders[folder.id] = folder
            
            if brand_name not in folders_by_brand:
                folders_by_brand[brand_name] = []
                
            folders_by_brand[brand_name].append(folder)
        
        # Now get all direct child folders for each brand
        for brand_folder_id in brand_folders:
            child_query = """
                SELECT 
                    di.id,
                    di.drive_id,
                    di.name,
                    di.full_path,
                    di.item_type,
                    di.is_folder,
                    dh.level_name,
                    di.parent_id,
                    di.parent_drive_id
                FROM 
                    drive_items di
                JOIN 
                    drive_hierarchy dh ON di.id = dh.item_id
                WHERE 
                    di.parent_id = ?
                    AND di.is_folder = 1
            """
            
            cursor.execute(child_query, (brand_folder_id,))
            
            for row in cursor.fetchall():
                folder = DriveFolder(
                    id=row[0],
                    drive_id=row[1],
                    name=row[2],
                    full_path=row[3],
                    item_type=row[4],
                    is_folder=row[5],
                    level_name=row[6],
                    parent_id=row[7],
                    parent_drive_id=row[8]
                )
                
                # Get the parent folder to determine the brand
                parent_folder = brand_folders.get(folder.parent_id)
                
                if parent_folder:
                    brand_name = parent_folder.name.upper()
                    
                    if brand_name not in folders_by_brand:
                        folders_by_brand[brand_name] = []
                        
                    folders_by_brand[brand_name].append(folder)
        
        elapsed = time.time() - start_time
        brand_count = len(folders_by_brand)
        total_count = sum(len(folders) for folders in folders_by_brand.values())
        
        console.print(f"[green]Retrieved {total_count} folders across {brand_count} brands in {elapsed:.2f} seconds[/green]")
        
        return folders_by_brand
    except Exception as e:
        error_msg = f"Failed to get folders by brand: {str(e)}"
        console.print(f"[red]{error_msg}[/red]")
        log_error(error_msg, "get_folders_by_brand_error", {"brand_filter": brand_filter})
        return {}

def get_folder_contents(conn: sqlite3.Connection, folder_id: str) -> Dict[str, Any]:
    """Get contents of a specific Drive folder.
    
    Args:
        conn: SQLite connection object
        folder_id: Drive folder ID
        
    Returns:
        Dictionary with folder details and children
    """
    cursor = conn.cursor()
    
    try:
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
            return {"error": f"Folder with ID {folder_id} not found"}
        
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
        
        return {
            "folder_id": folder_id,
            "folder_name": folder_row[1],
            "folder_path": folder_row[2],
            "children": children
        }
    except Exception as e:
        error_msg = f"Failed to get folder contents: {str(e)}"
        console.print(f"[red]{error_msg}[/red]")
        log_error(error_msg, "get_folder_contents_error", {"folder_id": folder_id})
        return {"error": str(e)}

def save_match_result(conn: sqlite3.Connection, match_result: Dict[str, Any]) -> bool:
    """Save a match result to the database.
    
    Args:
        conn: SQLite connection object
        match_result: Match result dictionary
        
    Returns:
        True if successful, False otherwise
    """
    cursor = conn.cursor()
    
    try:
        warning_flags = None
        if match_result.get("warning_flags"):
            warning_flags = json.dumps(match_result["warning_flags"])
        
        cursor.execute("""
            INSERT INTO product_folder_matches
            (product_id, drive_folder_id, product_descricao, folder_name, folder_path, 
             confidence_score, reasoning, warning_flags, match_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            match_result["product_id"],
            match_result["drive_folder_id"],
            match_result["product_descricao"],
            match_result["folder_name"],
            match_result["folder_path"],
            match_result["confidence_score"],
            match_result["reasoning"],
            warning_flags
        ))
        
        conn.commit()
        return True
    except Exception as e:
        error_msg = f"Failed to save match result: {str(e)}"
        console.print(f"[red]{error_msg}[/red]")
        log_error(error_msg, "save_match_result_error", {"match_result": str(match_result)})
        conn.rollback()
        return False

def check_and_record_duplicates(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Check for duplicates (multiple products matching the same folder) and record them.
    
    Args:
        conn: SQLite connection object
        
    Returns:
        List of duplicate records
    """
    cursor = conn.cursor()
    
    try:
        # Find folders that have been matched to multiple products
        cursor.execute("""
            SELECT 
                drive_folder_id, 
                COUNT(*) as product_count,
                GROUP_CONCAT(product_id, ',') as product_ids,
                GROUP_CONCAT(product_descricao, '|') as product_names,
                GROUP_CONCAT(confidence_score, ',') as confidence_scores
            FROM 
                product_folder_matches
            GROUP BY 
                drive_folder_id
            HAVING 
                COUNT(*) > 1
        """)
        
        duplicates = []
        for row in cursor.fetchall():
            duplicate = {
                "drive_folder_id": row[0],
                "product_count": row[1],
                "product_ids": row[2],
                "product_names": row[3],
                "confidence_scores": row[4]
            }
            
            duplicates.append(duplicate)
            
            # Record in the duplicates table
            cursor.execute("""
                INSERT INTO duplicate_matches
                (drive_folder_id, product_ids, product_names, confidence_scores, detection_date)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                duplicate["drive_folder_id"],
                duplicate["product_ids"],
                duplicate["product_names"],
                duplicate["confidence_scores"]
            ))
        
        conn.commit()
        
        if duplicates:
            console.print(f"[yellow]Found {len(duplicates)} folders with multiple product matches[/yellow]")
        
        return duplicates
    except Exception as e:
        error_msg = f"Failed to check for duplicates: {str(e)}"
        console.print(f"[red]{error_msg}[/red]")
        log_error(error_msg, "check_duplicates_error", {})
        conn.rollback()
        return []

def generate_summary_report(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Generate a summary report of the matching process.
    
    Args:
        conn: SQLite connection object
        
    Returns:
        Dictionary with summary statistics
    """
    cursor = conn.cursor()
    
    try:
        # Get total matches
        cursor.execute("SELECT COUNT(*) FROM product_folder_matches")
        total_matches = cursor.fetchone()[0]
        
        # Get matches by confidence level
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN confidence_score >= 0.9 THEN 1 END) as high_confidence,
                COUNT(CASE WHEN confidence_score >= 0.8 AND confidence_score < 0.9 THEN 1 END) as medium_confidence,
                COUNT(CASE WHEN confidence_score < 0.8 THEN 1 END) as low_confidence
            FROM 
                product_folder_matches
        """)
        
        confidence_counts = cursor.fetchone()
        
        # Get matches by brand
        cursor.execute("""
            SELECT 
                SUBSTR(folder_path, 1, INSTR(folder_path, '/') - 1) as brand,
                COUNT(*) as match_count
            FROM 
                product_folder_matches
            GROUP BY 
                brand
            ORDER BY 
                match_count DESC
        """)
        
        brand_counts = [(row[0], row[1]) for row in cursor.fetchall()]
        
        # Get duplicate counts
        cursor.execute("SELECT COUNT(*) FROM duplicate_matches")
        duplicate_count = cursor.fetchone()[0]
        
        return {
            "total_matches": total_matches,
            "high_confidence": confidence_counts[0],
            "medium_confidence": confidence_counts[1],
            "low_confidence": confidence_counts[2],
            "brand_counts": brand_counts,
            "duplicate_count": duplicate_count
        }
    except Exception as e:
        error_msg = f"Failed to generate summary report: {str(e)}"
        console.print(f"[red]{error_msg}[/red]")
        log_error(error_msg, "summary_report_error", {})
        return {
            "error": str(e),
            "total_matches": 0,
            "brand_counts": []
        } 