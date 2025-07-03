from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class AirtableRecord(BaseModel):
    """Airtable record wrapper returned by the API."""

    id: str = Field(..., description="Record ID (e.g., recXXXXXXXXXXXXXX)")
    createdTime: Optional[str] = Field(None, description="ISO timestamp when the record was created")
    fields: Dict[str, Any] = Field(default_factory=dict, description="Record field data")


class BaseAirtableResponse(BaseModel):
    """Common base for responses returned by Airtable tool functions."""

    success: bool = Field(..., description="Whether the operation succeeded")
    error: Optional[str] = Field(None, description="Error message when success is False")


class ListRecordsResponse(BaseAirtableResponse):
    """Response model for list_records tool."""

    records: List[AirtableRecord] = Field(default_factory=list, description="Fetched records")
    offset: Optional[str] = Field(None, description="Offset cursor to fetch next page, if present")


class GetRecordResponse(BaseAirtableResponse):
    """Response model for get_record tool."""

    record: Optional[AirtableRecord] = Field(None, description="The requested record, if found")


class CreateRecordsResponse(BaseAirtableResponse):
    """Response model for create_records tool."""

    records: List[AirtableRecord] = Field(default_factory=list, description="Created records")


class UpdateRecordsResponse(BaseAirtableResponse):
    """Response model for update_records tool."""

    records: List[AirtableRecord] = Field(default_factory=list, description="Updated records")


class DeleteRecordsResponse(BaseAirtableResponse):
    """Response model for delete_records tool."""

    deleted_record_ids: List[str] = Field(default_factory=list, description="IDs of deleted records")


class AirtableBase(BaseModel):
    """Airtable base metadata."""
    id: str = Field(..., description="Base ID (e.g., appXXXXXXXXXXXXXX)")
    name: str = Field(..., description="Human-readable name of the base")


class AirtableTable(BaseModel):
    """Simplified Airtable table metadata."""
    id: str = Field(..., description="Table ID (e.g., tblXXXXXXXXXXXXXX)")
    name: str = Field(..., description="Table name")


class ListBasesResponse(BaseAirtableResponse):
    bases: List[AirtableBase] = Field(default_factory=list, description="List of bases user can access")


class ListTablesResponse(BaseAirtableResponse):
    tables: List[AirtableTable] = Field(default_factory=list, description="List of tables in the base") 