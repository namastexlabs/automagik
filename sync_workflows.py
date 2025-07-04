#!/usr/bin/env python3
"""Sync workflows from filesystem to database."""

from automagik.agents.claude_code.workflow_discovery import WorkflowDiscovery
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to sync workflows."""
    print("🔄 Starting workflow sync...")
    
    # Run workflow discovery and registration
    stats = WorkflowDiscovery.sync_workflows_with_database()
    
    print(f"\n✅ Workflow sync completed!")
    print(f"   Discovered: {stats.get('discovered', 0)} workflows")
    print(f"   Registered: {stats.get('registered', 0)} new workflows")
    print(f"   Updated: {stats.get('updated', 0)} existing workflows")
    print(f"   Errors: {stats.get('errors', 0)}")
    
    # List all discovered workflows
    workflows = WorkflowDiscovery.discover_workflows()
    print(f"\n📋 Available workflows:")
    for workflow in workflows:
        data = WorkflowDiscovery.get_workflow_data(workflow)
        if data:
            config = data.get('config', {})
            print(f"   - {workflow}: {config.get('display_name', workflow)}")

if __name__ == "__main__":
    main()