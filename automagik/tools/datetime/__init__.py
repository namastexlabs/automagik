"""Datetime tools for Automagik Agents.

Provides tools for retrieving date and time information.
"""

# Import from tool module
from automagik.tools.datetime.tool import (
    get_current_date,
    get_current_time,
    get_current_date_description,
    get_current_time_description,
    format_date,
    format_date_description
)

# Import schema models
from automagik.tools.datetime.schema import DatetimeInput, DatetimeOutput

# Create a collection of all datetime tools for easy import
from pydantic_ai import Tool

# Create Tool instances
get_current_date_tool = Tool(
    name="get_current_date",
    description=get_current_date_description(),
    function=get_current_date
)

get_current_time_tool = Tool(
    name="get_current_time",
    description=get_current_time_description(),
    function=get_current_time
)

format_date_tool = Tool(
    name="format_date",
    description=format_date_description(),
    function=format_date
)

# Group all datetime tools
datetime_tools = [
    get_current_date_tool,
    get_current_time_tool,
    format_date_tool
]

# Export public API
__all__ = [
    'get_current_date',
    'get_current_time',
    'get_current_date_description',
    'get_current_time_description',
    'format_date',
    'format_date_description',
    'DatetimeInput',
    'DatetimeOutput',
    'datetime_tools',
    'get_current_date_tool',
    'get_current_time_tool',
    'format_date_tool'
] 