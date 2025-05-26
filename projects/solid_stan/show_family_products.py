#!/usr/bin/env python3
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import os
from rich.console import Console
from rich.table import Table
import urllib.parse
import signal
import sys

console = Console()

# Handle keyboard interrupt (CTRL+C)
def signal_handler(sig, frame):
    console.print("\n[yellow]User interrupted the process. Exiting...[/yellow]")
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

def display_family_products(cursor, family_code):
    """Display all products from a specific product family."""
    try:
        # First get the family name and ID
        cursor.execute("""
            SELECT id, "nomeFamilia"
            FROM catalogo_familiadeproduto
            WHERE codigo = %s
        """, (family_code,))
        
        family_result = cursor.fetchone()
        if not family_result:
            console.print(f"[red]Product family with code {family_code} not found.[/red]")
            return
            
        family_id = family_result[0]
        family_name = family_result[1]
        console.print(f"\n[bold]Products in family: {family_name} (Code: {family_code}, ID: {family_id})[/bold]")
        
        # Get all products from this family
        cursor.execute("""
            SELECT 
                p.id,
                p.codigo,
                p.descricao,
                p.descr_detalhada,
                p.valor_unitario,
                p.inativo,
                m.nome as marca_nome
            FROM 
                catalogo_produto p
            LEFT JOIN 
                catalogo_marca m ON p.marca_id = m.id
            WHERE 
                p.familia_id = %s
            ORDER BY 
                p.descricao
        """, (family_id,))
        
        products = cursor.fetchall()
        
        if not products:
            console.print("[yellow]No products found in this family.[/yellow]")
            return
            
        # Create a table for display
        table = Table(title=f"Products in Family: {family_name}")
        table.add_column("ID", style="cyan")
        table.add_column("Code", style="green")
        table.add_column("Description", style="yellow")
        table.add_column("Price", style="magenta")
        table.add_column("Brand", style="blue")
        table.add_column("Status", style="red")
        
        # Add rows to the table
        for product in products:
            status = "Inactive" if product[5] else "Active"
            status_style = "red" if product[5] else "green"
            
            table.add_row(
                str(product[0]),  # id
                str(product[1] or ''),  # codigo
                product[2] or '',  # descricao
                f"R$ {product[4]:.2f}" if product[4] else "N/A",  # valor_unitario
                product[6] or "N/A",  # marca_nome
                f"[{status_style}]{status}[/{status_style}]"  # status
            )
        
        console.print(table)
        console.print(f"\n[green]Total products in family: {len(products)}[/green]")
        
        # Show detailed information for each product
        console.print("\n[bold]Detailed Product Information:[/bold]")
        for product in products:
            console.print(f"\n[cyan]Product ID: {product[0]}[/cyan]")
            console.print(f"Description: {product[2] or 'N/A'}")
            console.print(f"Detailed Description: {product[3] or 'N/A'}")
            console.print(f"Price: R$ {product[4]:.2f}" if product[4] else "Price: N/A")
            console.print(f"Brand: {product[6] or 'N/A'}")
            console.print(f"Status: {'Inactive' if product[5] else 'Active'}")
            console.print("-" * 50)
        
    except Exception as e:
        console.print(f"[red]Error displaying products:[/red] {str(e)}")

def main():
    try:
        # Load environment variables
        load_dotenv()
        
        console.print("[bold]Starting product family check...[/bold]")
        
        # Get database URI from environment
        db_uri = os.getenv('BLACKPEARL_DB_URI')
        
        if not db_uri:
            console.print("[red]Error: BLACKPEARL_DB_URI not found in environment variables[/red]")
            return

        # Parse the connection string
        result = urllib.parse.urlparse(db_uri)
        username = result.username
        password = result.password
        database = result.path[1:]
        hostname = result.hostname
        port = result.port
        
        console.print(f"[blue]Attempting to connect to database {database} at {hostname}...[/blue]")
        
        # Connect to database with timeout
        conn = None
        cursor = None
        
        try:
            # Connect with a connect_timeout
            conn = psycopg2.connect(
                host=hostname,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=10  # 10 seconds connection timeout
            )
            
            # Create a cursor
            cursor = conn.cursor()
            
            # Get database version
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            console.print(f"\n[green]Connected to Blackpearl Database successfully![/green]")
            console.print(f"[blue]Database Version:[/blue] {version}")
            console.print(f"[blue]Database Host:[/blue] {hostname}")
            console.print(f"[blue]Database Name:[/blue] {database}")
            
            # Display products from the specified family
            family_code = 1129682249  # This is the code for the MOUSE family
            display_family_products(cursor, family_code)
            
        except Exception as e:
            console.print(f"[red]Error connecting to database:[/red] {str(e)}")
            if "password authentication failed" in str(e).lower():
                console.print("[yellow]Hint: Check if the database credentials in BLACKPEARL_DB_URI are correct[/yellow]")
            elif "could not connect to server" in str(e).lower():
                console.print("[yellow]Hint: Check if the database server is running and accessible[/yellow]")
            elif "operation timed out" in str(e).lower():
                console.print("[yellow]Hint: Database connection timed out. Server might be unreachable.[/yellow]")
            
        finally:
            # Always properly close connections
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            
            console.print("[blue]Database inspection complete.[/blue]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]User interrupted the process. Exiting...[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]An unexpected error occurred:[/red] {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
    # Ensure a clean exit
    sys.exit(0) 