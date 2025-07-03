"""
Loose Filtering Helper for Airtable

This module provides flexible, forgiving filtering strategies that work
even when users don't provide exact field names, character matches, etc.
"""

import logging
from typing import Dict, List, Optional
from automagik.tools.airtable.tool import list_records

logger = logging.getLogger(__name__)


async def loose_milestone_search(
    ctx: Dict,
    search_term: str,
    milestone_table_id: str,
    base_id: str
) -> Optional[str]:
    """
    Find a milestone using loose, flexible search strategies.
    
    Args:
        ctx: Runtime context
        search_term: User's search term (e.g., "Automagik - Plataforma")
        milestone_table_id: ID of the milestones table
        base_id: Airtable base ID
    
    Returns:
        Milestone record ID if found, None otherwise
    """
    
    # Extract key words from search term
    key_words = []
    for word in search_term.replace('-', ' ').replace('–', ' ').split():
        if len(word) > 2:  # Only use meaningful words
            key_words.append(word)
    
    logger.info(f"Searching for milestone with key words: {key_words}")
    
    # Strategy 1: Try partial search with each key word
    for word in key_words:
        field_names = ["Name", "Milestone Name", "Title"]
        
        for field_name in field_names:
            try:
                filter_formula = f"SEARCH('{word}', {{{field_name}}})"
                result = await list_records(
                    ctx,
                    table=milestone_table_id,
                    filter_formula=filter_formula,
                    base_id=base_id,
                    page_size=10
                )
                
                if result["success"] and result["records"]:
                    # Check if any result contains most of our key words
                    for record in result["records"]:
                        milestone_fields = record.get("fields", {})
                        milestone_name = (
                            milestone_fields.get("Name", "") + " " + 
                            milestone_fields.get("Milestone Name", "")
                        ).lower()
                        
                        # Count how many key words match
                        matches = sum(1 for kw in key_words if kw.lower() in milestone_name)
                        
                        if matches >= len(key_words) * 0.6:  # 60% match threshold
                            logger.info(f"Found milestone match: {record['id']} - {milestone_name}")
                            return record["id"]
                            
            except Exception as e:
                logger.debug(f"Search attempt failed for {word} in {field_name}: {e}")
                continue
    
    # Strategy 2: Get all milestones and do fuzzy matching
    try:
        all_milestones = await list_records(
            ctx,
            table=milestone_table_id,
            base_id=base_id,
            page_size=50
        )
        
        if all_milestones["success"]:
            search_term.lower()
            
            for record in all_milestones["records"]:
                milestone_fields = record.get("fields", {})
                milestone_name = (
                    milestone_fields.get("Name", "") + " " + 
                    milestone_fields.get("Milestone Name", "")
                ).lower()
                
                # Check for fuzzy matches
                if any(kw.lower() in milestone_name for kw in key_words):
                    logger.info(f"Fuzzy match found: {record['id']} - {milestone_name}")
                    return record["id"]
                    
    except Exception as e:
        logger.debug(f"Fuzzy search failed: {e}")
    
    logger.warning(f"No milestone found for search term: {search_term}")
    return None


async def loose_person_search(
    ctx: Dict,
    person_name: str,
    team_table_id: str,
    base_id: str
) -> Optional[str]:
    """
    Find a person using loose, flexible search strategies.
    
    Args:
        ctx: Runtime context
        person_name: Person's name (e.g., "Cezar Vasconcelos")
        team_table_id: ID of the team members table
        base_id: Airtable base ID
    
    Returns:
        Person record ID if found, None otherwise
    """
    
    # Extract name parts
    name_parts = person_name.split()
    
    # Strategy 1: Try searching with full name
    field_names = ["Name", "Full Name", "Team Member", "Display Name"]
    
    for field_name in field_names:
        try:
            filter_formula = f"SEARCH('{person_name}', {{{field_name}}})"
            result = await list_records(
                ctx,
                table=team_table_id,
                filter_formula=filter_formula,
                base_id=base_id,
                page_size=5
            )
            
            if result["success"] and result["records"]:
                return result["records"][0]["id"]
                
        except Exception as e:
            logger.debug(f"Full name search failed for {field_name}: {e}")
            continue
    
    # Strategy 2: Try searching with individual name parts
    for part in name_parts:
        if len(part) > 2:  # Skip short parts like initials
            for field_name in field_names:
                try:
                    filter_formula = f"SEARCH('{part}', {{{field_name}}})"
                    result = await list_records(
                        ctx,
                        table=team_table_id,
                        filter_formula=filter_formula,
                        base_id=base_id,
                        page_size=10
                    )
                    
                    if result["success"] and result["records"]:
                        # Check if any result is a good match
                        for record in result["records"]:
                            record_fields = record.get("fields", {})
                            record_name = (
                                record_fields.get("Name", "") + " " +
                                record_fields.get("Full Name", "")
                            ).lower()
                            
                            # If multiple name parts match, it's probably the right person
                            matches = sum(1 for np in name_parts if np.lower() in record_name)
                            if matches >= len(name_parts) * 0.7:  # 70% match
                                logger.info(f"Found person match: {record['id']} - {record_name}")
                                return record["id"]
                                
                except Exception as e:
                    logger.debug(f"Name part search failed for {part} in {field_name}: {e}")
                    continue
    
    logger.warning(f"No person found for: {person_name}")
    return None


async def create_loose_filter_for_milestone_and_person(
    ctx: Dict,
    person_name: str,
    milestone_name: str,
    base_id: str,
    additional_conditions: Optional[List[str]] = None
) -> Optional[str]:
    """
    Create a loose filter combining person and milestone searches.
    
    Args:
        ctx: Runtime context
        person_name: Person to search for
        milestone_name: Milestone to search for
        base_id: Airtable base ID
        additional_conditions: Other conditions to add
    
    Returns:
        Filter formula string or None if components can't be found
    """
    
    # Find table IDs
    from automagik.tools.airtable.tool import list_tables
    tables_result = await list_tables(ctx, base_id=base_id)
    
    if not tables_result["success"]:
        return None
    
    milestone_table_id = None
    team_table_id = None
    
    for table in tables_result["tables"]:
        table_name = table["name"].lower()
        if "milestone" in table_name:
            milestone_table_id = table["id"]
        elif "team" in table_name or "member" in table_name:
            team_table_id = table["id"]
    
    conditions = []
    
    # Try to find person
    if person_name and team_table_id:
        person_id = await loose_person_search(ctx, person_name, team_table_id, base_id)
        if person_id:
            # Use both ID and name search for maximum flexibility
            person_condition = f"OR(SEARCH('{person_name}', {{Assigned Team Members}}), SEARCH('{person_id}', {{Assigned Team Members}}))"
            conditions.append(person_condition)
        else:
            # Fallback to just name search
            conditions.append(f"SEARCH('{person_name}', {{Assigned Team Members}})")
    
    # Try to find milestone
    if milestone_name and milestone_table_id:
        milestone_id = await loose_milestone_search(ctx, milestone_name, milestone_table_id, base_id)
        if milestone_id:
            # Use both ID and name search for maximum flexibility
            milestone_condition = f"OR(SEARCH('{milestone_name}', {{Related Milestones}}), SEARCH('{milestone_id}', {{Related Milestones}}))"
            conditions.append(milestone_condition)
        else:
            # Fallback to just name search
            conditions.append(f"SEARCH('{milestone_name}', {{Related Milestones}})")
    
    # Add any additional conditions
    if additional_conditions:
        conditions.extend(additional_conditions)
    
    if conditions:
        if len(conditions) == 1:
            return conditions[0]
        else:
            return f"AND({', '.join(conditions)})"
    
    return None


async def loose_status_filter(status_term: str) -> str:
    """
    Create a loose status filter that handles variations.
    
    Args:
        status_term: Status to search for (e.g., "to do", "A fazer", "working")
    
    Returns:
        Filter formula string
    """
    
    # Map common variations to actual status values
    status_mapping = {
        "to do": "A fazer",
        "todo": "A fazer", 
        "pending": "A fazer",
        "working": "Estou trabalhando",
        "in progress": "Estou trabalhando",
        "blocked": "Estou bloqueado",
        "completed": "Terminei",
        "done": "Terminei",
        "finished": "Terminei"
    }
    
    status_lower = status_term.lower()
    
    # Check for exact mapping
    if status_lower in status_mapping:
        return f"{{Status}} = '{status_mapping[status_lower]}'"
    
    # Check for partial matches
    for key, value in status_mapping.items():
        if key in status_lower or status_lower in key:
            return f"{{Status}} = '{value}'"
    
    # Fallback: search within status field
    return f"SEARCH('{status_term}', {{Status}})" 