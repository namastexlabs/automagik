"""Google Drive tool schemas.

This module defines the Pydantic models for Google Drive tool input and output.
"""
from pydantic import BaseModel, Field
from typing import Optional, List

class GoogleDriveFile(BaseModel):
    """Model for Google Drive file metadata."""
    id: str = Field(..., description="Google Drive file ID")
    name: str = Field(..., description="File name")
    mimeType: str = Field(..., description="MIME type of the file")
    webViewLink: str = Field(..., description="Web view link for the file")
    createdTime: str = Field(..., description="Creation time of the file")

class SearchFilesResponse(BaseModel):
    """Response model for search_files."""
    success: bool = Field(..., description="Whether the operation was successful")
    error: Optional[str] = Field(None, description="Error message if the operation failed")
    files: List[GoogleDriveFile] = Field(default_factory=list, description="List of files matching the search query")

class GetFileContentResponse(BaseModel):
    """Response model for get_file_content."""
    success: bool = Field(..., description="Whether the operation was successful")
    error: Optional[str] = Field(None, description="Error message if the operation failed")
    content: Optional[str] = Field(None, description="File content as a string")
    file_id: str = Field(..., description="ID of the requested file") 