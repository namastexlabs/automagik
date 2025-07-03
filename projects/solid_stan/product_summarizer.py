import logfire
import psycopg2
from dotenv import load_dotenv
import os
import sys
import csv
import signal
import urllib.parse
import argparse
import random
from rich.console import Console
from rich.progress import Progress
from pydantic_ai import Agent
from typing import Dict, Any

from automagik.config import settings

console = Console()

# Handle keyboard interrupt (CTRL+C)
def signal_handler(sig, frame):
    console.print("\n[yellow]User interrupted the process. Exiting...[/yellow]")
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

os.environ["LOGFIRE_TOKEN"] = settings.LOGFIRE_TOKEN
logfire.configure(scrubbing=False, console=False)  # Logfire reads token from environment
logfire.instrument_pydantic_ai()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate product summaries using AI.')
    
    parser.add_argument(
        '--sample', 
        type=int, 
        default=0,
        help='Number of products to sample randomly (0 for all products)'
    )
    
    parser.add_argument(
        '--output', 
        type=str, 
        default='product_summaries.csv',
        help='Output CSV file path'
    )
    
    parser.add_argument(
        '--model', 
        type=str, 
        default='openai:gpt-4o',
        help='AI model to use (openai:gpt-4o, google-gla:gemini-2.0-flash-exp, etc.)'
    )
    
    parser.add_argument(
        '--limit', 
        type=int, 
        default=0,
        help='Limit the number of products to process (0 for no limit)'
    )
    
    parser.add_argument(
        '--offset', 
        type=int, 
        default=0,
        help='Offset to start from in the product list'
    )
    
    return parser.parse_args()

async def generate_product_summary(
    product_data: Dict[str, Any],
    model_name: str = 'openai:gpt-4o'
) -> str:
    """Generate a summary of a product using an AI agent.
    
    Args:
        product_data: Dictionary containing product details
        model_name: Name of the AI model to use
        
    Returns:
        A concise summary of the product
    """
    # Set up the agent with appropriate system prompt
    summary_agent = Agent(
        model_name,  # Use the provided model name
        deps_type=Dict[str, Any],
        result_type=str,
        system_prompt=(
            'You are a specialized product summarization agent.'
            'Given product information, create a concise, descriptive summary in Brazilian Portuguese.'
            'Focus on key selling points, technical details, and use cases.'
            'The summary should be 2-3 sentences maximum.'
            'Do not add any prefix like "This product is" - go straight to describing it.'
        ),
    )
    
    # Create a formatted prompt with product data
    prompt = (
        f"Produto: {product_data.get('descricao', 'N/A')}\n"
        f"Descrição detalhada: {product_data.get('descr_detalhada', 'N/A')}\n"
        f"Código: {product_data.get('codigo', 'N/A')}\n"
        f"Marca: {product_data.get('marca_nome', 'N/A')}\n"
        f"Família: {product_data.get('familia_nome', 'N/A')}\n"
        f"Especificações: {product_data.get('especificacoes', 'N/A')}\n"
        f"Informações de marketing: {product_data.get('marketing_info', 'N/A')}\n"
    )
    
    # Run the agent and get the result
    result = await summary_agent.run(user_prompt=prompt)
    return result.data

async def main():
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Load environment variables
        load_dotenv()
        
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
        
        console.print(f"[blue]Connecting to database {database} at {hostname}...[/blue]")
        
        # Connect to database
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
            
            # Count total products
            cursor.execute("SELECT COUNT(*) FROM catalogo_produto WHERE inativo = FALSE")
            total_products = cursor.fetchone()[0]
            
            console.print(f"[green]Found {total_products} active products in the database.[/green]")
            
            # Build SQL query with limit and offset if provided
            query = """
                SELECT 
                    p.id, 
                    p.descricao, 
                    p.descr_detalhada, 
                    p.codigo, 
                    p.especificacoes, 
                    p.marketing_info,
                    m.nome as marca_nome,
                    f."nomeFamilia" as familia_nome
                FROM 
                    catalogo_produto p
                LEFT JOIN 
                    catalogo_marca m ON p.marca_id = m.id
                LEFT JOIN 
                    catalogo_familiadeproduto f ON p.familia_id = f.id
                WHERE 
                    p.inativo = FALSE
                ORDER BY 
                    p.id
            """
            
            # Add limit and offset if specified
            params = []
            if args.limit > 0:
                query += " LIMIT %s"
                params.append(args.limit)
            
            if args.offset > 0:
                query += " OFFSET %s"
                params.append(args.offset)
            
            try:
                # Execute the query
                cursor.execute(query, params)
                products = cursor.fetchall()
            except Exception as e:
                console.print(f"[red]SQL Error: {str(e)}[/red]")
                
                # Print table structure when an error occurs
                console.print("[yellow]Checking table structure to help diagnose the issue...[/yellow]")
                
                # Check catalogo_familiadeproduto table structure
                try:
                    # Create a new connection to avoid transaction issues
                    conn.rollback()
                    
                    cursor.execute("""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = 'catalogo_familiadeproduto'
                        ORDER BY ordinal_position
                    """)
                    
                    columns = cursor.fetchall()
                    console.print("[blue]Table: catalogo_familiadeproduto[/blue]")
                    for col in columns:
                        console.print(f"  - {col[0]} ({col[1]})")
                    
                    # Also check catalogo_produto and catalogo_marca for completeness
                    cursor.execute("""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = 'catalogo_produto'
                        ORDER BY ordinal_position
                        LIMIT 10
                    """)
                    
                    columns = cursor.fetchall()
                    console.print("[blue]Table: catalogo_produto (first 10 columns)[/blue]")
                    for col in columns:
                        console.print(f"  - {col[0]} ({col[1]})")
                    
                    cursor.execute("""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = 'catalogo_marca'
                        ORDER BY ordinal_position
                    """)
                    
                    columns = cursor.fetchall()
                    console.print("[blue]Table: catalogo_marca[/blue]")
                    for col in columns:
                        console.print(f"  - {col[0]} ({col[1]})")
                        
                except Exception as schema_error:
                    console.print(f"[red]Error checking schema: {str(schema_error)}[/red]")
                
                return
            
            if not products:
                console.print("[yellow]No active products found.[/yellow]")
                return
                
            # Sample products randomly if requested
            if args.sample > 0 and args.sample < len(products):
                console.print(f"[blue]Sampling {args.sample} products from {len(products)} total products[/blue]")
                products = random.sample(products, args.sample)
            
            # Prepare CSV file
            csv_file_path = args.output
            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(['Product ID', 'Code', 'Description', 'Summary'])
                
                # Display selected model
                console.print(f"[blue]Using AI model: {args.model}[/blue]")
                
                # Process products with progress bar
                with Progress() as progress:
                    task = progress.add_task("[cyan]Generating summaries...", total=len(products))
                    
                    for product in products:
                        product_data = {
                            'id': product[0],
                            'descricao': product[1] or '',
                            'descr_detalhada': product[2] or '',
                            'codigo': product[3] or '',
                            'especificacoes': product[4] or '',
                            'marketing_info': product[5] or '',
                            'marca_nome': product[6] or '',
                            'familia_nome': product[7] or '',
                        }
                        
                        # Generate summary using AI with specified model
                        summary = await generate_product_summary(product_data, args.model)
                        
                        # Write to CSV
                        csv_writer.writerow([
                            product_data['id'],
                            product_data['codigo'],
                            product_data['descricao'],
                            summary
                        ])
                        
                        # Update progress
                        progress.update(task, advance=1)
            
            console.print(f"[green]Successfully generated summaries for {len(products)} products![/green]")
            console.print(f"[blue]Results saved to: {csv_file_path}[/blue]")
            
        except Exception as e:
            console.print(f"[red]Error processing products:[/red] {str(e)}")
            
        finally:
            # Always properly close connections
            if cursor:
                cursor.close()
            if conn:
                conn.close()
                
    except KeyboardInterrupt:
        console.print("\n[yellow]User interrupted the process. Exiting...[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]An unexpected error occurred:[/red] {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
    # Ensure a clean exit
    sys.exit(0) 



# automagik-agents) root@stan:~/automagik-agents# python scripts/solid_stan/product_summarizer.py --limit 2
# 📝 .env file loaded from: /root/automagik-agents/.env
# Connecting to database solidpower_db at db-postgresql-theros-do-user-19117798-0.g.db.ondigitalocean.com...
# Printing table structures for reference:
# Table: catalogo_produto
# - id (bigint)
# - descricao (character varying)
# - descr_detalhada (text)
# - codigo (character varying)
# - ean (character varying)
# - unidade (character varying)
# - peso_liq (double precision)
# - peso_bruto (double precision)
# - largura (double precision)
# - altura (double precision)
# - profundidade (double precision)
# - familia_id (bigint)
# - marca_id (bigint)
# - especificacoes (text)
# - marketing_info (text)
# - codigo_produto (bigint)
# - inativo (boolean)
# - valor_unitario (double precision)
# - cfop (character varying)
# - ncm (character varying)
# Table: catalogo_marca
# - id (bigint)
# - nome (character varying)
# - site (character varying)
# - logo (character varying)
# Table: catalogo_familiadeproduto
# - id (bigint)
# - nomeFamilia (character varying)
# - codigo (bigint)
# Table structure printing complete
