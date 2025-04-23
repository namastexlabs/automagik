"""Pydantic models for product folder matcher."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class DriveFolder(BaseModel):
    """Represents a folder in Google Drive."""
    id: int = Field(description="Internal SQLite ID")
    drive_id: str = Field(description="Google Drive ID")
    name: str = Field(description="Folder name")
    full_path: str = Field(description="Full path to folder")
    item_type: str = Field(description="Type of item (folder)")
    is_folder: bool = Field(description="Whether this is a folder")
    level_name: Optional[str] = Field(None, description="Hierarchy level name")
    parent_id: Optional[int] = Field(None, description="Parent folder ID in SQLite")
    parent_drive_id: Optional[str] = Field(None, description="Parent folder ID in Drive")
    
    class Config:
        from_attributes = True

class BlackpearlProduct(BaseModel):
    """Represents a product from the Blackpearl database."""
    id: int = Field(description="Product ID in Blackpearl")
    codigo: Optional[str] = Field(None, description="Product code")
    descricao: str = Field(description="Product description/name")
    descr_detalhada: Optional[str] = Field(None, description="Detailed product description")
    valor_unitario: Optional[float] = Field(None, description="Product price")
    familia: Optional[str] = Field(None, description="Product family")
    inativo: bool = Field(False, description="Whether product is inactive")
    marca: str = Field(description="Product brand")
    especificacoes: Optional[str] = Field(None, description="Product specifications")
    
    class Config:
        from_attributes = True

class MatchResult(BaseModel):
    """Result of a product-folder matching operation."""
    product_id: int = Field(description="Product ID in Blackpearl")
    drive_folder_id: str = Field(description="Matched folder ID in Drive")
    product_descricao: str = Field(description="Product name for readability")
    folder_name: str = Field(description="Folder name for readability")
    folder_path: str = Field(description="Folder path for context")
    confidence_score: float = Field(description="Confidence score (0.0-1.0)")
    reasoning: str = Field(description="Agent's reasoning for the match")
    warning_flags: Optional[List[str]] = Field(None, description="Any warning flags")
    match_date: datetime = Field(default_factory=datetime.now, description="When match was made")

class FolderContent(BaseModel):
    """Content of a Drive folder for agent tools."""
    folder_id: str = Field(description="Drive folder ID")
    folder_name: str = Field(description="Folder name")
    folder_path: str = Field(description="Full folder path")
    children: List[Dict[str, Any]] = Field(description="Child items in folder") 