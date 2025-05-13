#!/usr/bin/env python
"""Script to migrate existing agent system prompts to the new prompts table.

This script:
1. Reads all agents from the agents table
2. For each agent with a non-empty system_prompt, creates a new entry in the prompts table
3. Sets this new prompt as active and marks it as default
4. Updates the agent's active_default_prompt_id to point to this new prompt
5. Optionally (with --drop flag) removes the system_prompt column after migration
"""

import argparse
import asyncio
import logging
import sys
import os

# Add parent directory to path so we can import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db.connection import execute_query, init_db
from src.db.repository import list_agents, get_agent
from src.db.models import PromptCreate
from src.db.repository.prompt import create_prompt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def migrate_agent_prompts(dry_run: bool = False) -> None:
    """Migrate all agent system prompts to the new prompts table.
    
    Args:
        dry_run: If True, don't make any actual changes to the database
    """
    # Get all agents from the database (including inactive ones)
    agents = list_agents(active_only=False)
    
    if not agents:
        logger.info("No agents found in the database.")
        return
        
    logger.info(f"Found {len(agents)} agents to process.")
    
    migrated_count = 0
    skipped_count = 0
    
    for agent in agents:
        logger.info(f"Processing agent: {agent.name} (ID: {agent.id})")
        
        # Skip agents with empty system_prompt
        if not agent.system_prompt:
            logger.info(f"  Skipping agent {agent.name} - no system_prompt")
            skipped_count += 1
            continue
            
        # Create a new prompt entry
        prompt_data = PromptCreate(
            agent_id=agent.id,
            prompt_text=agent.system_prompt,
            version=1,
            is_active=True,
            is_default_from_code=False,  # Not from code, migrated from DB
            status_key="default",
            name=f"Migrated {agent.name} Prompt"
        )
        
        if dry_run:
            logger.info(f"  [DRY RUN] Would create prompt for agent {agent.name}")
            migrated_count += 1
            continue
            
        # Create the prompt
        prompt_id = create_prompt(prompt_data)
        
        if not prompt_id:
            logger.error(f"  Failed to create prompt for agent {agent.name}")
            continue
            
        logger.info(f"  Created prompt (ID: {prompt_id}) for agent {agent.name}")
        
        # The agent.active_default_prompt_id will be set by create_prompt when is_active=True
        # But we'll verify it just to be sure
        updated_agent = get_agent(agent.id)
        if updated_agent and updated_agent.active_default_prompt_id == prompt_id:
            logger.info(f"  Updated agent {agent.name} with active_default_prompt_id={prompt_id}")
        else:
            logger.warning(f"  Agent {agent.name} active_default_prompt_id not updated correctly")
            
            # Try to update it manually
            execute_query(
                """
                UPDATE agents SET 
                    active_default_prompt_id = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (prompt_id, agent.id),
                fetch=False
            )
            logger.info(f"  Manually updated agent {agent.name} with active_default_prompt_id={prompt_id}")
            
        migrated_count += 1
    
    logger.info(f"Migration complete. Migrated: {migrated_count}, Skipped: {skipped_count}")

async def drop_system_prompt_column(dry_run: bool = False) -> None:
    """Drop the system_prompt column from the agents table.
    
    Args:
        dry_run: If True, don't make any actual changes to the database
    """
    if dry_run:
        logger.info("[DRY RUN] Would drop system_prompt column from agents table")
        return
        
    try:
        # First check if system_prompt column exists
        check_result = execute_query(
            """
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'agents' AND column_name = 'system_prompt'
            """
        )
        
        if not check_result:
            logger.info("system_prompt column does not exist in agents table")
            return
            
        # Drop the column
        execute_query(
            "ALTER TABLE agents DROP COLUMN system_prompt",
            fetch=False
        )
        
        logger.info("Dropped system_prompt column from agents table")
    except Exception as e:
        logger.error(f"Error dropping system_prompt column: {str(e)}")

async def main():
    """Run the migration script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Migrate agent system prompts to the new prompts table')
    parser.add_argument('--dry-run', action='store_true', help='Run without making any changes')
    parser.add_argument('--drop', action='store_true', help='Drop system_prompt column after migration')
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("Running in DRY RUN mode - no changes will be made to the database")
    
    # Initialize database connection
    await init_db()
    
    # Migrate agent prompts
    await migrate_agent_prompts(dry_run=args.dry_run)
    
    # Drop system_prompt column if requested
    if args.drop:
        await drop_system_prompt_column(dry_run=args.dry_run)
    
    logger.info("Migration script completed successfully")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 