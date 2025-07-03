"""Omie API tool schemas.

This module defines the Pydantic models for Omie API tool input and output.
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ClientSearchInput(BaseModel):
    """Input model for client search in Omie."""
    simplified_info: bool = Field(True, description="Return simplified client information")
    pagina: int = Field(1, description="Page number for pagination")
    registros_por_pagina: int = Field(50, description="Number of records per page (max 50)")
    codigo_cliente_omie: Optional[str] = Field(None, description="Search by Omie Client Code")
    codigo_cliente_integracao: Optional[str] = Field(None, description="Search by Integration Client Code")
    cnpj_cpf: Optional[str] = Field(None, description="Search by CPF or CNPJ")
    email: Optional[str] = Field(None, description="Search by client email")
    razao_social: Optional[str] = Field(None, description="Search by client company name")
    nome_fantasia: Optional[str] = Field(None, description="Search by client trade name")
    apenas_importado_api: bool = Field(False, description="Filter only clients imported through API")

class ClientSearchResult(BaseModel):
    """Response model for client search in Omie."""
    success: bool = Field(..., description="Whether the search was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Search results data")
    error: Optional[str] = Field(None, description="Error message if search failed")

class ClientSimplifiedResult(BaseModel):
    """Simplified result for a single client search."""
    success: bool = Field(..., description="Whether the search was successful")
    client: Optional[Dict[str, Any]] = Field(None, description="Client information if found")
    error: Optional[str] = Field(None, description="Error message if search failed") 