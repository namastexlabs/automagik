"""
Airtable Linked Records Helper

This module provides utilities to handle linked records in Airtable,
particularly for converting between record IDs and display names.
"""

import logging
from typing import Dict, List, Optional
from automagik.tools.airtable.tool import list_records, get_record

logger = logging.getLogger(__name__)


async def resolve_linked_record_ids(
    ctx: Dict,
    record_ids: List[str],
    table_id: str,
    base_id: str,
    display_field: str = "Name"
) -> Dict[str, str]:
    """
    Resolve linked record IDs to their display names.
    
    Args:
        ctx: Runtime context
        record_ids: List of record IDs to resolve
        table_id: ID of the table containing the linked records
        base_id: Airtable base ID
        display_field: Field to use as display name (default: "Name")
    
    Returns:
        Dictionary mapping record_id -> display_name
    """
    id_to_name = {}
    
    for record_id in record_ids:
        try:
            result = await get_record(ctx, table=table_id, record_id=record_id, base_id=base_id)
            
            if result["success"]:
                record = result["record"]
                fields = record.get("fields", {})
                display_name = fields.get(display_field, record_id)  # Fallback to ID
                id_to_name[record_id] = display_name
            else:
                logger.warning(f"Failed to resolve record {record_id}: {result.get('error')}")
                id_to_name[record_id] = record_id  # Fallback to ID
                
        except Exception as e:
            logger.error(f"Error resolving record {record_id}: {e}")
            id_to_name[record_id] = record_id  # Fallback to ID
    
    return id_to_name


async def find_record_id_by_name(
    ctx: Dict,
    name: str,
    table_id: str,
    base_id: str,
    name_field: str = "Name"
) -> Optional[str]:
    """
    Find a record ID by searching for a display name.
    
    Args:
        ctx: Runtime context
        name: Display name to search for
        table_id: ID of the table to search
        base_id: Airtable base ID
        name_field: Field containing the display name (default: "Name")
    
    Returns:
        Record ID if found, None otherwise
    """
    try:
        # Search for records with the given name
        filter_formula = f"{{{name_field}}} = '{name}'"
        result = await list_records(
            ctx,
            table=table_id,
            filter_formula=filter_formula,
            base_id=base_id,
            page_size=1
        )
        
        if result["success"] and result["records"]:
            return result["records"][0]["id"]
        
    except Exception as e:
        logger.error(f"Error finding record ID for '{name}': {e}")
    
    return None


async def resolve_team_member_id(ctx: Dict, name: str, base_id: str) -> Optional[str]:
    """
    Resolve a team member name to their record ID.
    
    Args:
        ctx: Runtime context
        name: Team member name (e.g., "Cezar Vasconcelos")
        base_id: Airtable base ID
    
    Returns:
        Record ID if found, None otherwise
    """
    # Try common field names for team member names
    name_fields = ["Name", "Full Name", "Nome", "Team Member"]
    
    # Get tables to find Team Members table
    from automagik.tools.airtable.tool import list_tables
    tables_result = await list_tables(ctx, base_id=base_id)
    
    if not tables_result["success"]:
        logger.error(f"Failed to get tables: {tables_result.get('error')}")
        return None
    
    # Find Team Members table
    team_table_id = None
    for table in tables_result["tables"]:
        table_name = table["name"].lower()
        if "team" in table_name or "member" in table_name:
            team_table_id = table["id"]
            break
    
    if not team_table_id:
        logger.warning("Could not find Team Members table")
        return None
    
    # Try different name fields
    for name_field in name_fields:
        record_id = await find_record_id_by_name(ctx, name, team_table_id, base_id, name_field)
        if record_id:
            return record_id
    
    return None


async def create_smart_filter_for_person(
    ctx: Dict,
    person_name: str,
    field_name: str,
    base_id: str,
    additional_conditions: Optional[List[str]] = None
) -> str:
    """
    Create a smart filter that works whether linked records show as names or IDs.
    
    Args:
        ctx: Runtime context
        person_name: Name of the person to filter for
        field_name: Name of the linked field (e.g., "Assigned Team Members")
        base_id: Airtable base ID
        additional_conditions: Other filter conditions to combine with AND
    
    Returns:
        Filter formula string
    """
    # Try to get the record ID for the person
    person_id = await resolve_team_member_id(ctx, person_name, base_id)
    
    if person_id:
        # Create filter that searches for both name and ID
        base_filter = f"OR(SEARCH('{person_name}', {{{field_name}}}), SEARCH('{person_id}', {{{field_name}}}))"
    else:
        # Fallback to just name search
        base_filter = f"SEARCH('{person_name}', {{{field_name}}})"
        logger.warning(f"Could not resolve ID for '{person_name}', using name-only filter")
    
    # Combine with additional conditions if provided
    if additional_conditions:
        all_conditions = [base_filter] + additional_conditions
        return f"AND({', '.join(all_conditions)})"
    
    return base_filter


async def resolve_milestone_id(ctx: Dict, milestone_name: str, base_id: str) -> Optional[str]:
    """
    Resolve a milestone name to its record ID.
    
    Args:
        ctx: Runtime context
        milestone_name: Milestone name (e.g., "Automagik - Plataforma")
        base_id: Airtable base ID
    
    Returns:
        Record ID if found, None otherwise
    """
    # Get tables to find Milestones table
    from automagik.tools.airtable.tool import list_tables
    tables_result = await list_tables(ctx, base_id=base_id)
    
    if not tables_result["success"]:
        return None
    
    # Find Milestones table
    milestone_table_id = None
    for table in tables_result["tables"]:
        table_name = table["name"].lower()
        if "milestone" in table_name:
            milestone_table_id = table["id"]
            break
    
    if not milestone_table_id:
        return None
    
    # Try to find the milestone by name
    name_fields = ["Name", "Title", "Milestone Name", "Nome"]
    for name_field in name_fields:
        record_id = await find_record_id_by_name(ctx, milestone_name, milestone_table_id, base_id, name_field)
        if record_id:
            return record_id
    
    return None 