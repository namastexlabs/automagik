"""Notion tools schema.

This module defines the schemas for Notion tools.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class NotionResponse(BaseModel):
    """Base response model for Notion tools."""
    success: bool = Field(description="Whether the operation was successful")
    error: Optional[str] = Field(None, description="Error message if the operation failed")


class DatabaseSearchResponse(NotionResponse):
    """Response model for notion_search_databases tool."""
    results: List[Dict[str, Any]] = Field(default_factory=list, description="List of database objects")
    has_more: bool = Field(default=False, description="Whether there are more results available")
    next_cursor: Optional[str] = Field(None, description="Cursor for pagination")


class DatabaseQueryResponse(NotionResponse):
    """Response model for notion_query_database tool."""
    results: List[Dict[str, Any]] = Field(default_factory=list, description="List of page objects")
    has_more: bool = Field(default=False, description="Whether there are more results available")
    next_cursor: Optional[str] = Field(None, description="Cursor for pagination")


class PagePropertyResponse(NotionResponse):
    """Response model for notion_get_page_property tool."""
    property: Optional[Dict[str, Any]] = Field(None, description="The page property data")


class PagePropertyItemResponse(NotionResponse):
    """Response model for notion_get_page_property_item tool."""
    results: List[Dict[str, Any]] = Field(default_factory=list, description="List of property items")
    has_more: bool = Field(default=False, description="Whether there are more results available")
    next_cursor: Optional[str] = Field(None, description="Cursor for pagination")


class BlockChildrenResponse(NotionResponse):
    """Response model for notion_get_block_children and notion_append_block_children tools."""
    results: List[Dict[str, Any]] = Field(default_factory=list, description="List of block objects")
    has_more: bool = Field(default=False, description="Whether there are more results available")
    next_cursor: Optional[str] = Field(None, description="Cursor for pagination") 