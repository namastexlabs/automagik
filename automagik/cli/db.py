"""
Database management commands for Automagik Agents.
"""
import os
import typer
import logging
from dotenv import load_dotenv
from pathlib import Path
from automagik.config import settings
from automagik.db.providers.factory import get_database_provider

# Create the database command group
db_app = typer.Typer()

def apply_migrations(logger=None):
    """Apply database migrations using the provider-based system"""
    if logger is None:
        logger = logging.getLogger("apply_migrations")
    
    # Get the database provider
    provider = get_database_provider()
    logger.info(f"Using {provider.get_database_type()} database provider")
    
    # Find migrations directory from installed package
    try:
        import importlib.resources as pkg_resources
        try:
            # Try to get migrations from package resources
            migrations_base = pkg_resources.files('automagik.db') / 'migrations'
            
            # Apply file-based migrations - check for database-specific directory first
            db_type = provider.get_database_type()
            if db_type == "sqlite":
                sqlite_migrations_dir = migrations_base / 'sqlite'
                if sqlite_migrations_dir.is_dir():
                    migrations_dir = Path(str(sqlite_migrations_dir))
                    logger.info(f"Using SQLite-specific migrations directory: {migrations_dir}")
                else:
                    migrations_dir = Path(str(migrations_base))
                    logger.info(f"Using base migrations directory: {migrations_dir}")
            else:
                # For other databases, use base directory
                migrations_dir = Path(str(migrations_base))
                logger.info(f"Using base migrations directory: {migrations_dir}")
                
        except (ImportError, AttributeError):
            # Fallback for older Python versions
            import pkg_resources as legacy_pkg_resources
            try:
                # Get package path and construct migrations path
                package_path = legacy_pkg_resources.resource_filename('automagik', 'db/migrations')
                migrations_base = Path(package_path)
                
                db_type = provider.get_database_type()
                if db_type == "sqlite":
                    sqlite_migrations_dir = migrations_base / 'sqlite'
                    if sqlite_migrations_dir.exists():
                        migrations_dir = sqlite_migrations_dir
                        logger.info(f"Using SQLite-specific migrations directory: {migrations_dir}")
                    else:
                        migrations_dir = migrations_base
                        logger.info(f"Using base migrations directory: {migrations_dir}")
                else:
                    migrations_dir = migrations_base
                    logger.info(f"Using base migrations directory: {migrations_dir}")
            except:
                # Final fallback to relative paths (development mode)
                logger.warning("Could not find migrations via package resources, trying relative paths")
                db_type = provider.get_database_type()
                if db_type == "sqlite":
                    sqlite_migrations_dir = Path("automagik/db/migrations/sqlite")
                    if sqlite_migrations_dir.exists():
                        migrations_dir = sqlite_migrations_dir
                        logger.info(f"Using SQLite-specific migrations directory: {migrations_dir}")
                    else:
                        migrations_dir = Path("automagik/db/migrations")
                        logger.info(f"Using base migrations directory: {migrations_dir}")
                else:
                    migrations_dir = Path("automagik/db/migrations")
                    logger.info(f"Using base migrations directory: {migrations_dir}")
                    
    except Exception as e:
        logger.error(f"Error finding migrations directory: {e}")
        return False
    
    if not migrations_dir.exists():
        logger.warning(f"No migrations directory found at: {migrations_dir}")
        return False
    
    logger.info(f"Applying migrations from {migrations_dir}")
    success = provider.apply_migrations(str(migrations_dir))
    
    if success:
        logger.info("✅ All migrations applied successfully")
        return True
    else:
        logger.error("❌ Some migrations failed to apply")
        return False

@db_app.callback()
def db_callback(
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode", is_flag=True, hidden=True)
):
    """
    Database management commands.
    
    Use these commands to initialize, backup, and manage the database.
    """
    # If debug flag is set, ensure AUTOMAGIK_LOG_LEVEL is set to DEBUG
    if debug:
        os.environ["AUTOMAGIK_LOG_LEVEL"] = "DEBUG"

@db_app.command("init")
def db_init(
    force: bool = typer.Option(False, "--force", "-f", help="Force initialization even if database already exists")
):
    """
    Initialize the database if it doesn't exist yet.
    
    This command creates the database and required tables if they don't exist already.
    Use --force to recreate tables even if they already exist.
    """
    typer.echo("Initializing database...")
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("db_init")
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Get database provider
        provider = get_database_provider()
        db_type = provider.get_database_type()
        
        logger.info(f"Using {db_type} database")
        
        # Initialize database (provider-specific)
        if db_type == "sqlite":
            # For SQLite, just check if file exists (it will be created automatically)
            logger.info(f"SQLite database will be created automatically if needed")
        elif db_type == "postgresql":
            # For PostgreSQL, try to create database if it doesn't exist
            config = provider._get_db_config()
            database_name = config.get('database', 'automagik_agents')
            
            logger.info("Checking PostgreSQL database...")
            
            # Try to create database if it doesn't exist
            if hasattr(provider, 'create_database_if_not_exists'):
                created = provider.create_database_if_not_exists(database_name)
                if not created:
                    logger.warning(f"⚠️ Could not create database '{database_name}' - will try to connect anyway")
            
            # Verify connection and that database exists (skip health check - migrations haven't been applied yet)
            logger.info("Verifying PostgreSQL database connection...")
            try:
                pool = provider.get_connection_pool(skip_health_check=True)
                with pool.getconn() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT version()")
                        version = cursor.fetchone()[0]
                        logger.info(f"Connected to: {version}")
                    pool.putconn(conn)
            except Exception as conn_error:
                logger.error(f"❌ Failed to connect to database '{database_name}': {conn_error}")
                logger.error("This could mean:")
                logger.error("1. Database doesn't exist and user lacks CREATEDB permissions")
                logger.error("2. Connection parameters are incorrect")
                logger.error("3. PostgreSQL server is not running")
                raise conn_error
        
        # Apply migrations using the provider - this is critical for new databases
        logger.info("Applying database migrations...")
        success = apply_migrations(logger)
        
        if not success:
            logger.error("❌ Database migration failed")
            raise typer.Exit(1)
        
        # Verify essential tables exist after migration
        essential_tables = ['users', 'agents', 'sessions', 'messages', 'memories']
        missing_tables = []
        
        for table in essential_tables:
            if not provider.table_exists(table):
                missing_tables.append(table)
        
        if missing_tables:
            logger.error(f"❌ Essential tables missing after migration: {missing_tables}")
            logger.error("This indicates a migration failure or incomplete initial schema")
            raise typer.Exit(1)
        
        logger.info(f"✅ Verified essential tables exist: {essential_tables}")
        
        # Verify database health
        if provider.verify_health():
            logger.info("✅ Database initialization completed successfully!")
        else:
            logger.error("❌ Database health check failed")
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise typer.Exit(1)

@db_app.command("clear")
def db_clear(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
):
    """
    Clear all data from the database (keeping schema).
    
    This removes all records but keeps tables and structure intact.
    """
    if not yes:
        confirmed = typer.confirm("This will delete ALL data in the database. Are you sure?")
        if not confirmed:
            typer.echo("Operation cancelled.")
            return
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("db_clear")
    
    try:
        provider = get_database_provider()
        logger.info(f"Clearing data from {provider.get_database_type()} database")
        
        # For now, just provide guidance - implementation would be provider-specific
        logger.warning("Clear operation not yet implemented for provider-based system")
        logger.info("To clear data manually:")
        if provider.get_database_type() == "sqlite":
            logger.info("- Delete the SQLite database file and run 'db init' again")
        else:
            logger.info("- Run SQL DELETE statements on all tables")
            
    except Exception as e:
        logger.error(f"❌ Failed to clear database: {e}")
        raise typer.Exit(1)