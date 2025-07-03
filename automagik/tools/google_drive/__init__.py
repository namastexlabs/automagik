"""Google Drive tools for Automagik Agents.

Provides tools for interacting with Google Drive via API.
"""

# Import from tool module
from automagik.tools.google_drive.tool import (
    search_files,
    get_file_content,
    get_search_files_description,
    get_file_content_description
)

# Import schema models
from automagik.tools.google_drive.schema import (
    GoogleDriveFile,
    SearchFilesResponse,
    GetFileContentResponse
)

# Import interface
from automagik.tools.google_drive.interface import (
    GoogleDriveTools,
    google_drive_tools
)

# Export public API
__all__ = [
    # Tool functions
    'search_files',
    'get_file_content',
    
    # Description functions
    'get_search_files_description',
    'get_file_content_description',
    
    # Schema models
    'GoogleDriveFile',
    'SearchFilesResponse',
    'GetFileContentResponse',
    
    # Interface
    'GoogleDriveTools',
    'google_drive_tools'
] 