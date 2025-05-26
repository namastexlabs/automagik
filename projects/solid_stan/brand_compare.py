#!/usr/bin/env python3
import sqlite3
import psycopg2
import os
import sys
import signal
import urllib.parse
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.layout import Layout
from rich.columns import Columns
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Initialize rich console
console = Console()

# Handle keyboard interrupt (CTRL+C)
def signal_handler(sig, frame):
    console.print("\n[yellow]User interrupted the process. Exiting...[/yellow]")
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

class BrandComparison:
    def __init__(self, sqlite_db_path: str = "drive_product_catalog.db"):
        # Drive catalog SQLite connection
        self.sqlite_db_path = sqlite_db_path
        self.sqlite_conn = None
        self.sqlite_cursor = None
        
        # Blackpearl PostgreSQL connection
        self.pg_conn = None
        self.pg_cursor = None
        
        # Connect to both databases
        self._connect_sqlite()
        self._connect_postgres()
        
    def _connect_sqlite(self):
        """Connect to the SQLite database."""
        if not os.path.exists(self.sqlite_db_path):
            raise FileNotFoundError(f"Drive Catalog database not found: {self.sqlite_db_path}")
        
        self.sqlite_conn = sqlite3.connect(self.sqlite_db_path)
        self.sqlite_cursor = self.sqlite_conn.cursor()
        console.print(f"[green]Connected to Drive Catalog database: {self.sqlite_db_path}[/green]")
    
    def _connect_postgres(self):
        """Connect to the PostgreSQL database."""
        # Load environment variables
        load_dotenv()
        
        # Get database URI from environment
        db_uri = os.getenv('BLACKPEARL_DB_URI')
        
        if not db_uri:
            console.print("[red]Error: BLACKPEARL_DB_URI not found in environment variables[/red]")
            return False
            
        # Parse the connection string
        result = urllib.parse.urlparse(db_uri)
        username = result.username
        password = result.password
        database = result.path[1:]
        hostname = result.hostname
        port = result.port
        
        console.print(f"[blue]Connecting to Blackpearl database {database} at {hostname}...[/blue]")
        
        try:
            # Connect with a connect_timeout
            self.pg_conn = psycopg2.connect(
                host=hostname,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=10  # 10 seconds connection timeout
            )
            
            # Create a cursor
            self.pg_cursor = self.pg_conn.cursor()
            
            # Get database version
            self.pg_cursor.execute("SELECT version()")
            version = self.pg_cursor.fetchone()[0]
            console.print(f"[green]Connected to Blackpearl Database successfully![/green]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]Error connecting to Blackpearl database:[/red] {str(e)}")
            if "password authentication failed" in str(e).lower():
                console.print("[yellow]Hint: Check if the database credentials in BLACKPEARL_DB_URI are correct[/yellow]")
            elif "could not connect to server" in str(e).lower():
                console.print("[yellow]Hint: Check if the database server is running and accessible[/yellow]")
            elif "operation timed out" in str(e).lower():
                console.print("[yellow]Hint: Database connection timed out. Server might be unreachable.[/yellow]")
            
            return False
    
    def close(self):
        """Close all database connections."""
        if self.sqlite_cursor:
            self.sqlite_cursor.close()
        if self.sqlite_conn:
            self.sqlite_conn.close()
            
        if self.pg_cursor:
            self.pg_cursor.close()
        if self.pg_conn:
            self.pg_conn.close()
            
        console.print("[yellow]All database connections closed[/yellow]")
    
    def get_available_brands_from_drive(self) -> List[Tuple[str, int]]:
        """Get all available high-level brand folders from the Drive catalog."""
        try:
            # Get top-level folders (excluding special folders)
            self.sqlite_cursor.execute("""
                SELECT 
                    di.id,
                    di.name,
                    COUNT(children.id) as child_count
                FROM 
                    drive_items di
                LEFT JOIN 
                    drive_items children ON children.parent_id = di.id
                WHERE 
                    di.is_folder = 1
                    AND di.parent_id IS NULL
                    AND di.name NOT LIKE '%*%'
                    AND di.name NOT LIKE '%-%'
                    AND di.name NOT LIKE 'PNG%'
                    AND di.name NOT LIKE '%png%'
                    AND di.name NOT LIKE '%JPG%'
                    AND di.name NOT LIKE '%jpg%'
                    AND di.name NOT LIKE '%Imagens%'
                    AND di.name NOT LIKE 'Tamanho%'
                    AND LENGTH(di.name) > 2
                GROUP BY 
                    di.id, di.name
                ORDER BY 
                    di.name
            """)
            
            brand_folders = self.sqlite_cursor.fetchall()
            
            # Also get first-level brand folders (level_name = 'brand')
            self.sqlite_cursor.execute("""
                SELECT 
                    di.id,
                    di.name,
                    COUNT(children.id) as child_count
                FROM 
                    drive_items di
                JOIN 
                    drive_hierarchy dh ON di.id = dh.item_id
                LEFT JOIN 
                    drive_items children ON children.parent_id = di.id
                WHERE 
                    dh.level_name = 'brand'
                    AND di.is_folder = 1
                    AND di.name NOT LIKE '%*%'
                    AND di.name NOT LIKE '%-%'
                    AND di.name NOT LIKE 'PNG%'
                    AND di.name NOT LIKE '%png%'
                    AND di.name NOT LIKE '%JPG%'
                    AND di.name NOT LIKE '%jpg%'
                    AND di.name NOT LIKE '%Imagens%'
                    AND di.name NOT LIKE 'Tamanho%'
                    AND LENGTH(di.name) > 2
                GROUP BY 
                    di.id, di.name
                ORDER BY 
                    di.name
            """)
            
            level1_brands = self.sqlite_cursor.fetchall()
            
            # Combine and deduplicate
            all_brands = {}
            for brand_id, brand_name, child_count in brand_folders + level1_brands:
                # Uppercase brand name for consistency
                brand_name = brand_name.upper()
                if brand_name in all_brands:
                    all_brands[brand_name] = (brand_id, all_brands[brand_name][1] + child_count)
                else:
                    all_brands[brand_name] = (brand_id, child_count)
            
            # Convert to list of (name, count) tuples
            return [(name, count) for name, (brand_id, count) in all_brands.items()]
            
        except Exception as e:
            console.print(f"[red]Error getting brands from Drive catalog:[/red] {str(e)}")
            return []
    
    def get_available_brands_from_blackpearl(self) -> List[Tuple[str, int]]:
        """Get all available brands from the Blackpearl database."""
        if not self.pg_cursor:
            return []
            
        try:
            self.pg_cursor.execute("""
                SELECT 
                    UPPER(m.nome) as brand_name, 
                    COUNT(p.id) as product_count
                FROM 
                    catalogo_marca m
                LEFT JOIN 
                    catalogo_produto p ON m.id = p.marca_id
                GROUP BY 
                    m.id, m.nome
                ORDER BY 
                    brand_name
            """)
            
            return self.pg_cursor.fetchall()
        except Exception as e:
            console.print(f"[red]Error getting brands from Blackpearl:[/red] {str(e)}")
            return []
    
    def get_drive_items_by_brand(self, brand_name: str) -> List[Dict]:
        """Get all items from Drive catalog for a specific brand."""
        try:
            # Use flexible search with wildcards
            search_term = f"%{brand_name}%"
            
            # First try to find brand folders at any level
            self.sqlite_cursor.execute("""
                SELECT 
                    di.id
                FROM 
                    drive_items di
                WHERE 
                    di.is_folder = 1 
                    AND di.name LIKE ? COLLATE NOCASE
                ORDER BY 
                    di.id
                LIMIT 1
            """, (search_term,))
            
            brand_id_result = self.sqlite_cursor.fetchone()
            
            if not brand_id_result:
                return []
                
            brand_id = brand_id_result[0]
            
            # Get direct child folders (categories/product types)
            self.sqlite_cursor.execute("""
                SELECT 
                    child.id,
                    child.name,
                    child.is_folder,
                    (SELECT COUNT(*) FROM drive_items subchild WHERE subchild.parent_id = child.id) as item_count
                FROM 
                    drive_items child
                WHERE 
                    child.parent_id = ?
                ORDER BY 
                    child.name
            """, (brand_id,))
            
            columns = [col[0] for col in self.sqlite_cursor.description]
            items = []
            
            for row in self.sqlite_cursor.fetchall():
                items.append(dict(zip(columns, row)))
                
            return items
            
        except Exception as e:
            console.print(f"[red]Error getting items from Drive catalog for brand {brand_name}:[/red] {str(e)}")
            return []
    
    def get_blackpearl_products_by_brand(self, brand_name: str) -> List[Dict]:
        """Get all products from Blackpearl for a specific brand."""
        if not self.pg_cursor:
            return []
            
        try:
            # Use flexible search with wildcards
            search_term = f"%{brand_name}%"
            
            self.pg_cursor.execute("""
                SELECT 
                    p.id,
                    p.codigo,
                    p.descricao,
                    f."nomeFamilia" as familia,
                    p.valor_unitario,
                    p.inativo
                FROM 
                    catalogo_produto p
                JOIN 
                    catalogo_marca m ON p.marca_id = m.id
                LEFT JOIN 
                    catalogo_familiadeproduto f ON p.familia_id = f.id
                WHERE 
                    m.nome ILIKE %s
                ORDER BY 
                    f."nomeFamilia", p.descricao
            """, (search_term,))
            
            columns = [col[0] for col in self.pg_cursor.description]
            products = []
            
            for row in self.pg_cursor.fetchall():
                products.append(dict(zip(columns, row)))
                
            return products
            
        except Exception as e:
            console.print(f"[red]Error getting products from Blackpearl for brand {brand_name}:[/red] {str(e)}")
            return []
    
    def display_brand_comparison(self, brand_name: str):
        """Display a comparison between Drive catalog items and Blackpearl products for a given brand."""
        drive_items = self.get_drive_items_by_brand(brand_name)
        blackpearl_products = self.get_blackpearl_products_by_brand(brand_name)
        
        console.print(f"\n[bold cyan]Brand Comparison: {brand_name}[/bold cyan]")
        
        # Create tables for both sources
        drive_table = Table(title=f"Drive Catalog Categories for {brand_name}")
        drive_table.add_column("Category Name", style="cyan")
        drive_table.add_column("Type", style="green")
        drive_table.add_column("Items", style="yellow")
        
        # Group Blackpearl products by family for easier comparison
        families = {}
        for product in blackpearl_products:
            family = product.get('familia', 'Unknown')
            if family not in families:
                families[family] = []
            families[family].append(product)
        
        blackpearl_table = Table(title=f"Blackpearl Product Families for {brand_name}")
        blackpearl_table.add_column("Family", style="cyan")
        blackpearl_table.add_column("Product Count", style="yellow")
        blackpearl_table.add_column("Status", style="green")
        
        # Fill Drive table
        for item in drive_items:
            item_type = "Folder" if item.get('is_folder') else "File"
            drive_table.add_row(
                item.get('name', ''),
                item_type,
                str(item.get('item_count', 0))
            )
        
        # Fill Blackpearl table (grouped by family)
        for family_name, products in families.items():
            active_count = sum(1 for p in products if not p.get('inativo'))
            inactive_count = len(products) - active_count
            status = f"Active: {active_count}, Inactive: {inactive_count}"
            
            blackpearl_table.add_row(
                family_name,
                str(len(products)),
                status
            )
        
        # Display stats
        console.print(f"\n[green]Found {len(drive_items)} categories in Drive Catalog[/green]")
        console.print(f"[green]Found {len(blackpearl_products)} products across {len(families)} families in Blackpearl Database[/green]")
        
        # Display tables side by side if there's enough space
        try:
            console_width = console.width
            if console_width >= 150:  # Enough space for side-by-side
                console.print(Columns([drive_table, blackpearl_table]))
            else:
                console.print(drive_table)
                console.print("\n")
                console.print(blackpearl_table)
        except:
            # Fallback if we can't determine console width
            console.print(drive_table)
            console.print("\n")
            console.print(blackpearl_table)
            
        # Optionally show product details for a specific family
        if blackpearl_products and Confirm.ask("\nShow detailed product list?"):
            family_names = list(families.keys())
            
            if len(family_names) > 1:
                console.print("\n[bold]Available product families:[/bold]")
                for i, name in enumerate(family_names, 1):
                    console.print(f"{i}. {name} ({len(families[name])} products)")
                
                choice = Prompt.ask(
                    "Select a family number (or 'all' for all families)",
                    choices=[str(i) for i in range(1, len(family_names) + 1)] + ["all"],
                    default="all"
                )
                
                if choice == "all":
                    selected_families = family_names
                else:
                    selected_families = [family_names[int(choice) - 1]]
            else:
                selected_families = family_names
            
            # Display products for selected families
            for family_name in selected_families:
                products = families.get(family_name, [])
                
                product_table = Table(title=f"Products in Family: {family_name}")
                product_table.add_column("Code", style="green")
                product_table.add_column("Description", style="cyan") 
                product_table.add_column("Price", style="magenta")
                product_table.add_column("Status", style="red")
                
                for product in products:
                    status = "Inactive" if product.get('inativo') else "Active"
                    status_style = "red" if product.get('inativo') else "green"
                    
                    product_table.add_row(
                        str(product.get('codigo', '')),
                        product.get('descricao', ''),
                        f"R$ {product.get('valor_unitario', 0):.2f}" if product.get('valor_unitario') else "N/A",
                        f"[{status_style}]{status}[/{status_style}]"
                    )
                
                console.print(product_table)

def main():
    try:
        brand_comp = BrandComparison()
        
        # Get available brands from both sources
        drive_brands = brand_comp.get_available_brands_from_drive()
        blackpearl_brands = brand_comp.get_available_brands_from_blackpearl()
        
        # Display brands for selection
        console.print("\n[bold cyan]Available Brands in Drive Catalog:[/bold cyan]")
        drive_brand_table = Table()
        drive_brand_table.add_column("Name", style="cyan")
        drive_brand_table.add_column("Item Count", style="green")
        
        for brand_name, count in drive_brands:
            drive_brand_table.add_row(brand_name, str(count))
            
        console.print(drive_brand_table)
        
        if blackpearl_brands:
            console.print("\n[bold cyan]Available Brands in Blackpearl:[/bold cyan]")
            blackpearl_brand_table = Table()
            blackpearl_brand_table.add_column("Name", style="cyan")
            blackpearl_brand_table.add_column("Product Count", style="green")
            
            for brand_name, count in blackpearl_brands:
                blackpearl_brand_table.add_row(brand_name, str(count))
                
            console.print(blackpearl_brand_table)
        
        # Get brand selection
        while True:
            brand_name = Prompt.ask("\nEnter a brand name to compare (or 'exit' to quit)")
            
            if brand_name.lower() == 'exit':
                break
                
            brand_comp.display_brand_comparison(brand_name)
            
            if not Confirm.ask("Continue with another brand?"):
                break
        
    except KeyboardInterrupt:
        console.print("\n[yellow]User interrupted the process. Exiting...[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]An unexpected error occurred:[/red] {str(e)}")
    finally:
        if 'brand_comp' in locals():
            brand_comp.close()

if __name__ == "__main__":
    main()
    # Ensure a clean exit
    sys.exit(0) 