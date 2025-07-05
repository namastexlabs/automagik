"""Workflow discovery and registration system (like agent discovery)."""

import logging
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from automagik.db import (
    create_workflow,
    get_workflow_by_name,
    list_workflows,
    register_workflow,
    WorkflowCreate
)

logger = logging.getLogger(__name__)


class WorkflowDiscovery:
    """Discover and register workflows from filesystem (like AgentFactory)."""
    
    @classmethod
    def discover_workflows(cls) -> List[str]:
        """Discover all available workflows from filesystem.
        
        Returns:
            List of discovered workflow names
        """
        discovered_workflows = []
        
        # Look for workflow directories in the claude_code workflows directory
        workflows_base_dir = Path(__file__).parent / "workflows"
        
        if not workflows_base_dir.exists():
            logger.info(f"Workflows directory not found: {workflows_base_dir}")
            return discovered_workflows
        
        logger.info(f"Scanning for workflows in: {workflows_base_dir}")
        
        for workflow_dir in workflows_base_dir.iterdir():
            if workflow_dir.is_dir() and not workflow_dir.name.startswith('.'):
                workflow_name = workflow_dir.name
                try:
                    workflow_data = cls._load_workflow_from_directory(workflow_dir)
                    if workflow_data:
                        discovered_workflows.append(workflow_name)
                        logger.debug(f"Discovered workflow: {workflow_name}")
                except Exception as e:
                    logger.error(f"Error loading workflow {workflow_name}: {e}")
        
        return discovered_workflows
    
    @classmethod
    def register_discovered_workflows(cls) -> int:
        """Register discovered workflows in database (like agent registration).
        
        Returns:
            Number of workflows registered
        """
        discovered_workflows = cls.discover_workflows()
        registered_count = 0
        
        for workflow_name in discovered_workflows:
            try:
                workflow_data = cls.get_workflow_data(workflow_name)
                if workflow_data:
                    # Check if workflow already exists
                    existing = get_workflow_by_name(workflow_name)
                    if not existing:
                        # Register new workflow
                        workflow_id = register_workflow(workflow_data)
                        if workflow_id:
                            registered_count += 1
                            logger.info(f"Registered new workflow: {workflow_name}")
                    else:
                        logger.debug(f"Workflow already exists: {workflow_name}")
            except Exception as e:
                logger.error(f"Failed to register workflow {workflow_name}: {e}")
        
        return registered_count
    
    @classmethod
    def get_workflow_data(cls, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Get workflow data from filesystem for a specific workflow.
        
        Args:
            workflow_name: Name of the workflow
            
        Returns:
            Dictionary containing workflow data
        """
        workflows_base_dir = Path(__file__).parent / "workflows"
        workflow_dir = workflows_base_dir / workflow_name
        
        if not workflow_dir.exists():
            return None
        
        return cls._load_workflow_from_directory(workflow_dir)
    
    @classmethod
    def _load_workflow_from_directory(cls, workflow_dir: Path) -> Optional[Dict[str, Any]]:
        """Load workflow configuration from a directory.
        
        Args:
            workflow_dir: Path to workflow directory
            
        Returns:
            Dictionary containing workflow data or None if invalid
        """
        workflow_name = workflow_dir.name
        
        # Look for key files in the workflow directory
        prompt_file = workflow_dir / "prompt.md"
        config_file = workflow_dir / "config.json"
        tools_file = workflow_dir / "allowed_tools.json"
        mcp_file = workflow_dir / ".mcp.json"
        
        # Prompt is required
        if not prompt_file.exists():
            logger.warning(f"No prompt.md found for workflow: {workflow_name}")
            return None
        
        try:
            # Load prompt template
            prompt_template = prompt_file.read_text(encoding='utf-8').strip()
            
            # Load configuration
            config = {}
            if config_file.exists():
                config = json.loads(config_file.read_text(encoding='utf-8'))
            
            # Load allowed tools
            allowed_tools = []
            if tools_file.exists():
                allowed_tools = json.loads(tools_file.read_text(encoding='utf-8'))
            
            # Load MCP configuration (with root fallback)
            mcp_config = {}
            if mcp_file.exists():
                mcp_config = json.loads(mcp_file.read_text(encoding='utf-8'))
            else:
                # Try to use root project .mcp.json as fallback
                root_mcp_file = Path(__file__).parent.parent.parent.parent / ".mcp.json"
                if root_mcp_file.exists():
                    try:
                        mcp_config = json.loads(root_mcp_file.read_text(encoding='utf-8'))
                        logger.debug(f"Using root .mcp.json for workflow {workflow_name}")
                    except Exception as e:
                        logger.debug(f"Could not load root .mcp.json: {e}")
            
            # Build workflow data
            workflow_data = {
                "name": workflow_name,
                "display_name": config.get("display_name", workflow_name.title()),
                "description": config.get("description", f"{workflow_name} workflow"),
                "category": config.get("category", "custom"),
                "prompt_template": prompt_template,
                "allowed_tools": allowed_tools,
                "mcp_config": mcp_config,
                "active": config.get("active", True),
                "is_system_workflow": config.get("is_system_workflow", False),
                "config": config
            }
            
            return workflow_data
            
        except Exception as e:
            logger.error(f"Error loading workflow data for {workflow_name}: {e}")
            return None
    
    @classmethod
    def sync_workflows_with_database(cls) -> Dict[str, int]:
        """Sync workflows from filesystem to database (like agent sync).
        
        Returns:
            Dictionary with sync statistics
        """
        stats = {
            "discovered": 0,
            "registered": 0,
            "updated": 0,
            "errors": 0
        }
        
        try:
            # Discover workflows from filesystem
            discovered_workflows = cls.discover_workflows()
            stats["discovered"] = len(discovered_workflows)
            
            for workflow_name in discovered_workflows:
                try:
                    workflow_data = cls.get_workflow_data(workflow_name)
                    if not workflow_data:
                        stats["errors"] += 1
                        continue
                    
                    # Check if workflow exists in database
                    existing = get_workflow_by_name(workflow_name)
                    
                    if existing:
                        # For system workflows, check if we should update from filesystem
                        if existing.is_system_workflow:
                            # System workflows can be updated from filesystem
                            logger.debug(f"System workflow found in DB: {workflow_name}")
                            # Update system workflow with latest filesystem data
                            from automagik.db import update_workflow, WorkflowUpdate
                            
                            # Only update config field to preserve other database values
                            update_data = WorkflowUpdate(
                                config=workflow_data.get('config', {})
                            )
                            
                            if update_workflow(existing.id, update_data):
                                stats["updated"] += 1
                                logger.info(f"Updated system workflow from filesystem: {workflow_name}")
                            else:
                                logger.warning(f"Failed to update system workflow: {workflow_name}")
                        else:
                            # Custom workflows in database take priority
                            logger.debug(f"Custom workflow exists in DB: {workflow_name}")
                    else:
                        # Register new workflow
                        workflow_id = register_workflow(workflow_data)
                        if workflow_id:
                            stats["registered"] += 1
                            logger.info(f"Registered workflow from filesystem: {workflow_name}")
                        else:
                            stats["errors"] += 1
                            
                except Exception as e:
                    logger.error(f"Error syncing workflow {workflow_name}: {e}")
                    stats["errors"] += 1
            
            logger.info(f"Workflow sync completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error during workflow sync: {e}")
            stats["errors"] += 1
            return stats
    
    @classmethod
    def get_available_workflows(cls) -> Dict[str, Dict[str, Any]]:
        """Get all available workflows (from database and filesystem).
        
        Returns:
            Dictionary mapping workflow names to their information
        """
        workflows = {}
        
        try:
            # Get workflows from database
            db_workflows = list_workflows()
            
            for workflow in db_workflows:
                workflows[workflow.name] = {
                    "id": workflow.id,
                    "name": workflow.name,
                    "display_name": workflow.display_name,
                    "description": workflow.description,
                    "category": workflow.category,
                    "active": workflow.active,
                    "is_system_workflow": workflow.is_system_workflow,
                    "source": "database",
                    "allowed_tools": workflow.allowed_tools,
                    "mcp_config": workflow.mcp_config
                }
            
            # Also check filesystem for any not in database
            discovered_workflows = cls.discover_workflows()
            
            for workflow_name in discovered_workflows:
                if workflow_name not in workflows:
                    workflow_data = cls.get_workflow_data(workflow_name)
                    if workflow_data:
                        workflows[workflow_name] = {
                            "name": workflow_name,
                            "display_name": workflow_data.get("display_name"),
                            "description": workflow_data.get("description"),
                            "category": workflow_data.get("category"),
                            "active": workflow_data.get("active", True),
                            "is_system_workflow": workflow_data.get("is_system_workflow", False),
                            "source": "filesystem",
                            "allowed_tools": workflow_data.get("allowed_tools", []),
                            "mcp_config": workflow_data.get("mcp_config", {})
                        }
            
            return workflows
            
        except Exception as e:
            logger.error(f"Error getting available workflows: {e}")
            return {}
    
    @classmethod
    def initialize_workflows(cls) -> bool:
        """Initialize workflow system at startup (like agent initialization).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Initializing workflow discovery system...")
            
            # Sync workflows from filesystem to database
            stats = cls.sync_workflows_with_database()
            
            # Log summary
            logger.info(f"Workflow initialization complete: "
                       f"discovered={stats['discovered']}, "
                       f"registered={stats['registered']}, "
                       f"errors={stats['errors']}")
            
            return stats["errors"] == 0
            
        except Exception as e:
            logger.error(f"Failed to initialize workflows: {e}")
            return False