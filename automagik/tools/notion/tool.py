"""Notion tool implementation.

This module provides the core functionality for Notion tools.
"""
import logging
from typing import List, Optional, Dict, Any
from pydantic_ai import RunContext
from notion_client import Client

from automagik.config import settings
from .schema import (
    DatabaseSearchResponse, 
    DatabaseQueryResponse,
    PagePropertyResponse,
    PagePropertyItemResponse,
    BlockChildrenResponse
)

logger = logging.getLogger(__name__)

class NotionError(Exception):
    """Base exception for Notion API errors"""
    pass

# Helper functions
def get_notion_token() -> str:
    """Gets the Notion token from settings."""
    token = settings.NOTION_TOKEN
    if not token:
        raise ValueError("NOTION_TOKEN setting not configured")
    return token

def initialize_notion_client() -> Client:
    """Initialize a Notion client using the API token."""
    try:
        token = get_notion_token()
        return Client(auth=token)
    except Exception as e:
        logger.error(f"Failed to initialize Notion client: {str(e)}")
        raise NotionError(f"Failed to initialize Notion client: {str(e)}")

# Tool descriptions
def get_search_databases_description() -> str:
    """Get description for search_databases function."""
    return "Search for databases shared with the integration."

def get_create_database_description() -> str:
    """Get description for create_database function."""
    return "Creates a new database as a child of an existing page."

def get_update_database_description() -> str:
    """Get description for update_database function."""
    return "Updates an existing database."

def get_get_database_description() -> str:
    """Get description for get_database function."""
    return "Retrieves a database by ID."

def get_query_database_description() -> str:
    """Get description for query_database function."""
    return "Queries a database with optional filters and sorting."

def get_create_database_item_description() -> str:
    """Get description for create_database_item function."""
    return "Creates a new item in a database."

def get_update_database_item_description() -> str:
    """Get description for update_database_item function."""
    return "Updates an existing database item."

def get_get_page_description() -> str:
    """Get description for get_page function."""
    return "Retrieves a page by ID."

def get_create_page_description() -> str:
    """Get description for create_page function."""
    return "Creates a new page."

def get_update_page_description() -> str:
    """Get description for update_page function."""
    return "Updates an existing page."

def get_archive_page_description() -> str:
    """Get description for archive_page function."""
    return "Archives (deletes) a page."

def get_get_page_property_description() -> str:
    """Get description for get_page_property function."""
    return "Retrieves a page property by ID."

def get_get_page_property_item_description() -> str:
    """Get description for get_page_property_item function."""
    return "Retrieves a page property item."

def get_get_block_description() -> str:
    """Get description for get_block function."""
    return "Retrieves a block by ID."

def get_update_block_description() -> str:
    """Get description for update_block function."""
    return "Updates a block."

def get_delete_block_description() -> str:
    """Get description for delete_block function."""
    return "Deletes (archives) a block."

def get_get_block_children_description() -> str:
    """Get description for get_block_children function."""
    return "Retrieves the children of a block."

def get_append_block_children_description() -> str:
    """Get description for append_block_children function."""
    return "Appends children to a block."

# Database tools
async def search_databases(
    ctx: RunContext[Dict],
    query: str = "",
    start_cursor: Optional[str] = None,
    page_size: int = 100,
) -> Dict[str, Any]:
    """
    Search for databases shared with the integration.

    Args:
        ctx: The run context
        query: Search query (default: "", which returns all databases)
        start_cursor: Starting point for the results
        page_size: Maximum number of databases to return (default: 100)
    
    Returns:
        Dict with search results
    """
    try:
        logger.info(f"Searching Notion databases with query: '{query}'")
        notion = initialize_notion_client()
        
        response = notion.search(
            query=query,
            filter={"property": "object", "value": "database"},
            start_cursor=start_cursor,
            page_size=page_size,
        )

        result = DatabaseSearchResponse(
            success=True,
            results=response.get("results", []),
            has_more=response.get("has_more", False),
            next_cursor=response.get("next_cursor")
        )
        return result.dict()
    except Exception as e:
        logger.error(f"Error searching databases: {str(e)}")
        result = DatabaseSearchResponse(
            success=False,
            error=f"Failed to search databases: {str(e)}",
            results=[]
        )
        return result.dict()

async def create_database(
    ctx: RunContext[Dict],
    parent: Dict[str, Any],
    title: List[Dict[str, Any]],
    properties: Dict[str, Dict[str, Any]],
    icon: Optional[Dict[str, Any]] = None,
    cover: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Creates a new database as a child of an existing page.

    Args:
        ctx: The run context
        parent: Parent page info
        title: Database title
        properties: Database properties schema
        icon: Database icon
        cover: Database cover
    
    Returns:
        Dict with the created database
    """
    try:
        logger.info(f"Creating Notion database with title: {title}")
        notion = initialize_notion_client()
        
        database = notion.databases.create(
            parent=parent, 
            title=title, 
            properties=properties, 
            icon=icon, 
            cover=cover
        )
        
        return {"success": True, "database": database}
    except Exception as e:
        logger.error(f"Error creating database: {str(e)}")
        return {"success": False, "error": f"Failed to create database: {str(e)}"}

async def query_database(
    ctx: RunContext[Dict],
    database_id: str,
    filter_dict: Optional[Dict[str, Any]] = None,
    sorts: Optional[List[Dict[str, Any]]] = None,
    start_cursor: Optional[str] = None,
    page_size: int = 100,
) -> Dict[str, Any]:
    """
    Queries a database with optional filters and sorting.

    Args:
        ctx: The run context
        database_id: The ID of the database to query
        filter_dict: Filter conditions
        sorts: Sort conditions
        start_cursor: Starting point for pagination
        page_size: Maximum number of results to return (default: 100)
    
    Returns:
        Dict with query results
    """
    try:
        logger.info(f"Querying Notion database: {database_id}")
        notion = initialize_notion_client()
        
        # Default sort by created time if no sort specified
        default_sort = [{"timestamp": "created_time", "direction": "descending"}]
        query_args = {
            "database_id": database_id,
            "page_size": page_size,
            "sorts": sorts if sorts is not None else default_sort,
        }

        if filter_dict is not None:
            query_args["filter"] = filter_dict

        if start_cursor is not None:
            query_args["start_cursor"] = start_cursor

        response = notion.databases.query(**query_args)
        
        result = DatabaseQueryResponse(
            success=True,
            results=response.get("results", []),
            has_more=response.get("has_more", False),
            next_cursor=response.get("next_cursor")
        )
        return result.dict()
    except Exception as e:
        logger.error(f"Error querying database: {str(e)}")
        result = DatabaseQueryResponse(
            success=False,
            error=f"Failed to query database: {str(e)}",
            results=[]
        )
        return result.dict()

async def get_database(
    ctx: RunContext[Dict],
    database_id: str,
) -> Dict[str, Any]:
    """
    Retrieves a database by ID.

    Args:
        ctx: The run context
        database_id: The ID of the database to retrieve
    
    Returns:
        Dict with the database details
    """
    try:
        logger.info(f"Getting Notion database: {database_id}")
        notion = initialize_notion_client()
        
        database = notion.databases.retrieve(database_id=database_id)
        
        return {"success": True, "database": database}
    except Exception as e:
        logger.error(f"Error retrieving database: {str(e)}")
        return {"success": False, "error": f"Failed to retrieve database: {str(e)}"}

async def update_database(
    ctx: RunContext[Dict],
    database_id: str,
    title: Optional[List[Dict[str, Any]]] = None,
    properties: Optional[Dict[str, Dict[str, Any]]] = None,
    icon: Optional[Dict[str, Any]] = None,
    cover: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Updates an existing database.

    Args:
        ctx: The run context
        database_id: The ID of the database to update
        title: New database title
        properties: Updated properties schema
        icon: Updated icon
        cover: Updated cover
    
    Returns:
        Dict with the updated database
    """
    try:
        logger.info(f"Updating Notion database: {database_id}")
        notion = initialize_notion_client()
        
        # Build update payload with only provided fields
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if properties is not None:
            update_data["properties"] = properties
        if icon is not None:
            update_data["icon"] = icon
        if cover is not None:
            update_data["cover"] = cover
        
        database = notion.databases.update(database_id=database_id, **update_data)
        
        return {"success": True, "database": database}
    except Exception as e:
        logger.error(f"Error updating database: {str(e)}")
        return {"success": False, "error": f"Failed to update database: {str(e)}"}

# Page tools
async def get_page(
    ctx: RunContext[Dict],
    page_id: str,
) -> Dict[str, Any]:
    """
    Retrieves a page by ID.

    Args:
        ctx: The run context
        page_id: The ID of the page to retrieve
    
    Returns:
        Dict with the page details
    """
    try:
        logger.info(f"Getting Notion page: {page_id}")
        notion = initialize_notion_client()
        
        page = notion.pages.retrieve(page_id=page_id)
        
        return {"success": True, "page": page}
    except Exception as e:
        logger.error(f"Error retrieving page: {str(e)}")
        return {"success": False, "error": f"Failed to retrieve page: {str(e)}"}

async def create_page(
    ctx: RunContext[Dict],
    parent: Dict[str, Any],
    properties: Dict[str, Dict[str, Any]],
    icon: Optional[Dict[str, Any]] = None,
    cover: Optional[Dict[str, Any]] = None,
    children: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Creates a new page.

    Args:
        ctx: The run context
        parent: Parent database or page
        properties: Page properties
        icon: Page icon
        cover: Page cover
        children: Page content blocks
    
    Returns:
        Dict with the created page
    """
    try:
        logger.info(f"Creating Notion page with parent: {parent}")
        notion = initialize_notion_client()
        
        # Build page creation payload
        page_data = {
            "parent": parent,
            "properties": properties,
        }
        
        if icon is not None:
            page_data["icon"] = icon
        if cover is not None:
            page_data["cover"] = cover
        if children is not None:
            page_data["children"] = children
        
        page = notion.pages.create(**page_data)
        
        return {"success": True, "page": page}
    except Exception as e:
        logger.error(f"Error creating page: {str(e)}")
        return {"success": False, "error": f"Failed to create page: {str(e)}"}

async def update_page(
    ctx: RunContext[Dict],
    page_id: str,
    properties: Optional[Dict[str, Dict[str, Any]]] = None,
    icon: Optional[Dict[str, Any]] = None,
    cover: Optional[Dict[str, Any]] = None,
    archived: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Updates an existing page.

    Args:
        ctx: The run context
        page_id: The ID of the page to update
        properties: Updated page properties
        icon: Updated icon
        cover: Updated cover
        archived: Set to True to archive the page
    
    Returns:
        Dict with the updated page
    """
    try:
        logger.info(f"Updating Notion page: {page_id}")
        notion = initialize_notion_client()
        
        # Build update payload with only provided fields
        update_data = {}
        if properties is not None:
            update_data["properties"] = properties
        if icon is not None:
            update_data["icon"] = icon
        if cover is not None:
            update_data["cover"] = cover
        if archived is not None:
            update_data["archived"] = archived
        
        page = notion.pages.update(page_id=page_id, **update_data)
        
        return {"success": True, "page": page}
    except Exception as e:
        logger.error(f"Error updating page: {str(e)}")
        return {"success": False, "error": f"Failed to update page: {str(e)}"}

async def archive_page(
    ctx: RunContext[Dict],
    page_id: str,
) -> Dict[str, Any]:
    """
    Archives (deletes) a page.

    Args:
        ctx: The run context
        page_id: The ID of the page to archive
    
    Returns:
        Dict with the result of the operation
    """
    try:
        logger.info(f"Archiving Notion page: {page_id}")
        notion = initialize_notion_client()
        
        page = notion.pages.update(page_id=page_id, archived=True)
        
        return {"success": True, "page": page}
    except Exception as e:
        logger.error(f"Error archiving page: {str(e)}")
        return {"success": False, "error": f"Failed to archive page: {str(e)}"}

async def get_page_property(
    ctx: RunContext[Dict],
    page_id: str,
    property_id: str,
) -> Dict[str, Any]:
    """
    Retrieves a page property by ID.

    Args:
        ctx: The run context
        page_id: The ID of the page
        property_id: The ID of the property to retrieve
    
    Returns:
        Dict with the property details
    """
    try:
        logger.info(f"Getting Notion page property: {property_id} from page {page_id}")
        notion = initialize_notion_client()
        
        property_data = notion.pages.properties.retrieve(
            page_id=page_id, 
            property_id=property_id
        )
        
        result = PagePropertyResponse(
            success=True,
            property=property_data
        )
        return result.dict()
    except Exception as e:
        logger.error(f"Error retrieving page property: {str(e)}")
        result = PagePropertyResponse(
            success=False,
            error=f"Failed to retrieve page property: {str(e)}"
        )
        return result.dict()

async def get_page_property_item(
    ctx: RunContext[Dict],
    page_id: str,
    property_id: str,
    start_cursor: Optional[str] = None,
    page_size: int = 100,
) -> Dict[str, Any]:
    """
    Retrieves a page property item list.

    Args:
        ctx: The run context
        page_id: The ID of the page
        property_id: The ID of the property to retrieve
        start_cursor: Pagination cursor
        page_size: Maximum number of results to return (default: 100)
    
    Returns:
        Dict with the property items
    """
    try:
        logger.info(f"Getting Notion page property items: {property_id} from page {page_id}")
        notion = initialize_notion_client()
        
        params = {"page_size": page_size}
        if start_cursor:
            params["start_cursor"] = start_cursor
            
        property_items = notion.pages.properties.retrieve(
            page_id=page_id,
            property_id=property_id,
            **params
        )
        
        result = PagePropertyItemResponse(
            success=True,
            results=property_items.get("results", []),
            has_more=property_items.get("has_more", False),
            next_cursor=property_items.get("next_cursor")
        )
        return result.dict()
    except Exception as e:
        logger.error(f"Error retrieving page property items: {str(e)}")
        result = PagePropertyItemResponse(
            success=False,
            error=f"Failed to retrieve page property items: {str(e)}",
            results=[]
        )
        return result.dict()

# Block tools
async def get_block(
    ctx: RunContext[Dict],
    block_id: str,
) -> Dict[str, Any]:
    """
    Retrieves a block by ID.

    Args:
        ctx: The run context
        block_id: The ID of the block to retrieve
    
    Returns:
        Dict with the block details
    """
    try:
        logger.info(f"Getting Notion block: {block_id}")
        notion = initialize_notion_client()
        
        block = notion.blocks.retrieve(block_id=block_id)
        
        return {"success": True, "block": block}
    except Exception as e:
        logger.error(f"Error retrieving block: {str(e)}")
        return {"success": False, "error": f"Failed to retrieve block: {str(e)}"}

async def update_block(
    ctx: RunContext[Dict],
    block_id: str,
    block_data: Dict[str, Any],
    archived: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Updates a block.

    Args:
        ctx: The run context
        block_id: The ID of the block to update
        block_data: The updated block content
        archived: Set to True to archive the block
    
    Returns:
        Dict with the updated block
    """
    try:
        logger.info(f"Updating Notion block: {block_id}")
        notion = initialize_notion_client()
        
        # Build update payload
        update_data = block_data.copy()
        if archived is not None:
            update_data["archived"] = archived
        
        block = notion.blocks.update(block_id=block_id, **update_data)
        
        return {"success": True, "block": block}
    except Exception as e:
        logger.error(f"Error updating block: {str(e)}")
        return {"success": False, "error": f"Failed to update block: {str(e)}"}

async def delete_block(
    ctx: RunContext[Dict],
    block_id: str,
) -> Dict[str, Any]:
    """
    Deletes (archives) a block.

    Args:
        ctx: The run context
        block_id: The ID of the block to delete
    
    Returns:
        Dict with the result of the operation
    """
    try:
        logger.info(f"Deleting Notion block: {block_id}")
        notion = initialize_notion_client()
        
        block = notion.blocks.update(block_id=block_id, archived=True)
        
        return {"success": True, "block": block}
    except Exception as e:
        logger.error(f"Error deleting block: {str(e)}")
        return {"success": False, "error": f"Failed to delete block: {str(e)}"}

async def get_block_children(
    ctx: RunContext[Dict],
    block_id: str,
    start_cursor: Optional[str] = None,
    page_size: int = 100,
) -> Dict[str, Any]:
    """
    Retrieves the children of a block.

    Args:
        ctx: The run context
        block_id: The ID of the block
        start_cursor: Pagination cursor
        page_size: Maximum number of results to return (default: 100)
    
    Returns:
        Dict with the block's children
    """
    try:
        logger.info(f"Getting children of Notion block: {block_id}")
        notion = initialize_notion_client()
        
        params = {"block_id": block_id, "page_size": page_size}
        if start_cursor:
            params["start_cursor"] = start_cursor
            
        response = notion.blocks.children.list(**params)
        
        result = BlockChildrenResponse(
            success=True,
            results=response.get("results", []),
            has_more=response.get("has_more", False),
            next_cursor=response.get("next_cursor")
        )
        return result.dict()
    except Exception as e:
        logger.error(f"Error retrieving block children: {str(e)}")
        result = BlockChildrenResponse(
            success=False,
            error=f"Failed to retrieve block children: {str(e)}",
            results=[]
        )
        return result.dict()

async def append_block_children(
    ctx: RunContext[Dict],
    block_id: str,
    children: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Appends children to a block.

    Args:
        ctx: The run context
        block_id: The ID of the block
        children: The children blocks to append
    
    Returns:
        Dict with the result of the operation
    """
    try:
        logger.info(f"Appending children to Notion block: {block_id}")
        notion = initialize_notion_client()
        
        response = notion.blocks.children.append(
            block_id=block_id,
            children=children
        )
        
        result = BlockChildrenResponse(
            success=True,
            results=response.get("results", []),
            has_more=False,  # Always False for append operation
            next_cursor=None  # Always None for append operation
        )
        return result.dict()
    except Exception as e:
        logger.error(f"Error appending block children: {str(e)}")
        result = BlockChildrenResponse(
            success=False,
            error=f"Failed to append block children: {str(e)}",
            results=[]
        )
        return result.dict() 