"""Notion tools interface.

This module defines the interface for Notion tools.
"""
from typing import List

from pydantic_ai import Tool

from .tool import (
    # Tool descriptions
    get_search_databases_description,
    get_create_database_description,
    get_update_database_description,
    get_get_database_description,
    get_query_database_description,
    get_get_page_description,
    get_create_page_description,
    get_update_page_description,
    get_archive_page_description,
    get_get_page_property_description,
    get_get_page_property_item_description,
    get_get_block_description,
    get_update_block_description,
    get_delete_block_description,
    get_get_block_children_description,
    get_append_block_children_description,
    
    # Tool implementations
    search_databases,
    create_database,
    update_database,
    get_database,
    query_database,
    create_page,
    update_page,
    get_page,
    archive_page,
    get_page_property,
    get_page_property_item,
    get_block,
    update_block,
    delete_block,
    get_block_children,
    append_block_children,
)

# Database tools
notion_search_databases = Tool(
    name="notion_search_databases",
    description=get_search_databases_description(),
    function=search_databases,
)

notion_create_database = Tool(
    name="notion_create_database",
    description=get_create_database_description(),
    function=create_database,
)

notion_update_database = Tool(
    name="notion_update_database",
    description=get_update_database_description(),
    function=update_database,
)

notion_get_database = Tool(
    name="notion_get_database",
    description=get_get_database_description(),
    function=get_database,
)

notion_query_database = Tool(
    name="notion_query_database",
    description=get_query_database_description(),
    function=query_database,
)

# Page tools
notion_create_page = Tool(
    name="notion_create_page",
    description=get_create_page_description(),
    function=create_page,
)

notion_update_page = Tool(
    name="notion_update_page",
    description=get_update_page_description(),
    function=update_page,
)

notion_get_page = Tool(
    name="notion_get_page",
    description=get_get_page_description(),
    function=get_page,
)

notion_archive_page = Tool(
    name="notion_archive_page",
    description=get_archive_page_description(),
    function=archive_page,
)

notion_get_page_property = Tool(
    name="notion_get_page_property",
    description=get_get_page_property_description(),
    function=get_page_property,
)

notion_get_page_property_item = Tool(
    name="notion_get_page_property_item",
    description=get_get_page_property_item_description(),
    function=get_page_property_item,
)

# Block tools
notion_get_block = Tool(
    name="notion_get_block",
    description=get_get_block_description(),
    function=get_block,
)

notion_update_block = Tool(
    name="notion_update_block",
    description=get_update_block_description(),
    function=update_block,
)

notion_delete_block = Tool(
    name="notion_delete_block",
    description=get_delete_block_description(),
    function=delete_block,
)

notion_get_block_children = Tool(
    name="notion_get_block_children",
    description=get_get_block_children_description(),
    function=get_block_children,
)

notion_append_block_children = Tool(
    name="notion_append_block_children",
    description=get_append_block_children_description(),
    function=append_block_children,
)

# Group tools by category
notion_database_tools = [
    notion_search_databases,
    notion_create_database,
    notion_update_database,
    notion_get_database,
    notion_query_database,
]

notion_page_tools = [
    notion_create_page,
    notion_update_page,
    notion_get_page,
    notion_archive_page,
    notion_get_page_property,
    notion_get_page_property_item,
]

notion_block_tools = [
    notion_get_block,
    notion_update_block,
    notion_delete_block,
    notion_get_block_children,
    notion_append_block_children,
]

# All Notion tools
notion_tools: List[Tool] = [
    *notion_database_tools,
    *notion_page_tools,
    *notion_block_tools,
] 