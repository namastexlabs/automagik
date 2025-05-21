"""Airtable tools interface.

This module defines the interface for Airtable tools by creating
`pydantic_ai.Tool` objects that wrap the underlying async functions in
`tool.py`. The pattern follows the Notion tools implementation.
"""

from typing import List

from pydantic_ai import Tool

from .tool import (
    # Descriptions
    get_list_records_description,
    get_get_record_description,
    get_create_records_description,
    get_update_records_description,
    get_delete_records_description,
    get_list_bases_description,
    get_list_tables_description,
    # Implementations
    list_records,
    get_record,
    create_records,
    update_records,
    delete_records,
    list_bases,
    list_tables,
)

# Record tools --------------------------------------------------------------

airtable_list_records = Tool(
    name="airtable_list_records",
    description=get_list_records_description(),
    function=list_records,
)

airtable_get_record = Tool(
    name="airtable_get_record",
    description=get_get_record_description(),
    function=get_record,
)

airtable_create_records = Tool(
    name="airtable_create_records",
    description=get_create_records_description(),
    function=create_records,
)

airtable_update_records = Tool(
    name="airtable_update_records",
    description=get_update_records_description(),
    function=update_records,
)

airtable_delete_records = Tool(
    name="airtable_delete_records",
    description=get_delete_records_description(),
    function=delete_records,
)

# Groupings -----------------------------------------------------------------

airtable_record_tools = [
    airtable_list_records,
    airtable_get_record,
    airtable_create_records,
    airtable_update_records,
    airtable_delete_records,
]

# Meta tools --------------------------------------------------------------

airtable_list_bases = Tool(
    name="airtable_list_bases",
    description=get_list_bases_description(),
    function=list_bases,
)

airtable_list_tables = Tool(
    name="airtable_list_tables",
    description=get_list_tables_description(),
    function=list_tables,
)

# Extend grouping
airtable_meta_tools = [
    airtable_list_bases,
    airtable_list_tables,
]

# All Airtable tools ---------------------------------------------------------

airtable_tools: List[Tool] = [
    *airtable_meta_tools,
    *airtable_record_tools,
] 