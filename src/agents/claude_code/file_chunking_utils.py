"""File chunking utilities to handle large files and avoid Claude CLI chunking errors.

This module provides utilities to check file sizes and implement chunked reading
strategies to avoid the "Separator is not found, and chunk exceed the limit" error
when working with large files (>50KB).
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Generator, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# File size thresholds
MAX_SAFE_FILE_SIZE = 50 * 1024  # 50KB - safe threshold for Claude CLI
CHUNK_SIZE = 25 * 1024  # 25KB - conservative chunk size
MAX_LINES_PER_CHUNK = 1000  # Maximum lines per chunk


@dataclass
class FileInfo:
    """Information about a file's size and read strategy."""
    path: str
    size_bytes: int
    line_count: Optional[int] = None
    requires_chunking: bool = False
    recommended_strategy: str = "direct"  # direct, chunked, summary


@dataclass
class FileChunk:
    """Represents a chunk of a file."""
    content: str
    start_line: int
    end_line: int
    chunk_number: int
    total_chunks: int
    is_last: bool = False


def get_file_info(file_path: Union[str, Path]) -> FileInfo:
    """Get information about a file's size and determine read strategy.
    
    Args:
        file_path: Path to the file to analyze
        
    Returns:
        FileInfo object with size and strategy information
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    size_bytes = path.stat().st_size
    requires_chunking = size_bytes > MAX_SAFE_FILE_SIZE
    
    # Determine recommended strategy
    if size_bytes <= MAX_SAFE_FILE_SIZE:
        strategy = "direct"
    elif size_bytes <= MAX_SAFE_FILE_SIZE * 3:  # Up to 150KB
        strategy = "chunked"
    else:
        strategy = "summary"  # Very large files need summarization
        
    return FileInfo(
        path=str(path),
        size_bytes=size_bytes,
        requires_chunking=requires_chunking,
        recommended_strategy=strategy
    )


def count_lines_in_file(file_path: Union[str, Path]) -> int:
    """Count the number of lines in a file efficiently.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Number of lines in the file
    """
    try:
        with open(file_path, 'rb') as f:
            line_count = sum(1 for _ in f)
        return line_count
    except Exception as e:
        logger.warning(f"Could not count lines in {file_path}: {e}")
        return 0


def read_file_chunked(file_path: Union[str, Path], 
                     max_lines_per_chunk: int = MAX_LINES_PER_CHUNK) -> Generator[FileChunk, None, None]:
    """Read a file in chunks to avoid CLI limitations.
    
    Args:
        file_path: Path to the file to read
        max_lines_per_chunk: Maximum lines per chunk
        
    Yields:
        FileChunk objects containing portions of the file
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # First, count total lines
    total_lines = count_lines_in_file(path)
    total_chunks = (total_lines + max_lines_per_chunk - 1) // max_lines_per_chunk
    
    logger.info(f"Reading {path} in {total_chunks} chunks ({total_lines} lines total)")
    
    chunk_number = 1
    current_line = 1
    
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            while True:
                lines = []
                start_line = current_line
                
                # Read up to max_lines_per_chunk lines
                for _ in range(max_lines_per_chunk):
                    line = f.readline()
                    if not line:  # EOF
                        break
                    lines.append(line.rstrip('\n\r'))
                    current_line += 1
                
                if not lines:  # No more content
                    break
                
                end_line = current_line - 1
                is_last = end_line >= total_lines
                
                chunk = FileChunk(
                    content='\n'.join(lines),
                    start_line=start_line,
                    end_line=end_line,
                    chunk_number=chunk_number,
                    total_chunks=total_chunks,
                    is_last=is_last
                )
                
                yield chunk
                chunk_number += 1
                
                if is_last:
                    break
                    
    except Exception as e:
        logger.error(f"Error reading file {path}: {e}")
        raise


def get_file_summary(file_path: Union[str, Path], max_lines: int = 50) -> str:
    """Get a summary of a large file (first few lines, structure info, etc.).
    
    Args:
        file_path: Path to the file
        max_lines: Maximum lines to include in summary
        
    Returns:
        String summary of the file
    """
    path = Path(file_path)
    file_info = get_file_info(path)
    
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                lines.append(f"{i+1:4d}→{line.rstrip()}")
        
        summary = f"""File: {path}
Size: {file_info.size_bytes:,} bytes
Lines: {count_lines_in_file(path):,} (showing first {min(max_lines, len(lines))})

{chr(10).join(lines)}

... (file continues for {count_lines_in_file(path) - len(lines):,} more lines)"""
        
        return summary
        
    except Exception as e:
        return f"Error reading file {path}: {e}"


def safe_read_file(file_path: Union[str, Path], 
                  offset: int = 0, 
                  limit: Optional[int] = None) -> Dict[str, Union[str, int, bool]]:
    """Safely read a file with automatic chunking strategy.
    
    Args:
        file_path: Path to the file to read
        offset: Line number to start reading from (0-based)
        limit: Maximum number of lines to read
        
    Returns:
        Dictionary with content, metadata, and chunking info
    """
    try:
        file_info = get_file_info(file_path)
        
        result = {
            'file_path': str(file_path),
            'size_bytes': file_info.size_bytes,
            'requires_chunking': file_info.requires_chunking,
            'strategy': file_info.recommended_strategy,
            'content': '',
            'truncated': False,
            'chunk_info': None
        }
        
        if file_info.recommended_strategy == "direct":
            # File is small enough to read directly
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                if offset > 0:
                    # Skip to offset
                    for _ in range(offset):
                        if not f.readline():
                            break
                
                lines = []
                for i, line in enumerate(f):
                    if limit and i >= limit:
                        result['truncated'] = True
                        break
                    lines.append(f"{offset + i + 1:4d}→{line.rstrip()}")
                
                result['content'] = '\n'.join(lines)
                
        elif file_info.recommended_strategy == "chunked":
            # Use chunked reading
            total_lines = count_lines_in_file(file_path)
            effective_limit = limit or MAX_LINES_PER_CHUNK
            
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                # Skip to offset
                for _ in range(offset):
                    if not f.readline():
                        break
                
                lines = []
                for i, line in enumerate(f):
                    if i >= effective_limit:
                        result['truncated'] = True
                        break
                    lines.append(f"{offset + i + 1:4d}→{line.rstrip()}")
                
                result['content'] = '\n'.join(lines)
                result['chunk_info'] = {
                    'start_line': offset + 1,
                    'end_line': offset + len(lines),
                    'total_lines': total_lines,
                    'suggested_next_offset': offset + len(lines)
                }
                
        else:  # summary strategy
            result['content'] = get_file_summary(file_path, limit or 50)
            result['chunk_info'] = {
                'is_summary': True,
                'total_lines': count_lines_in_file(file_path)
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error in safe_read_file for {file_path}: {e}")
        return {
            'file_path': str(file_path),
            'error': str(e),
            'content': f"Error reading file: {e}",
            'requires_chunking': False,
            'strategy': 'error'
        }


def batch_check_files(file_paths: List[Union[str, Path]]) -> Dict[str, FileInfo]:
    """Check multiple files for size and determine read strategies.
    
    Args:
        file_paths: List of file paths to check
        
    Returns:
        Dictionary mapping file paths to FileInfo objects
    """
    results = {}
    
    for file_path in file_paths:
        try:
            results[str(file_path)] = get_file_info(file_path)
        except Exception as e:
            logger.warning(f"Could not analyze {file_path}: {e}")
            results[str(file_path)] = FileInfo(
                path=str(file_path),
                size_bytes=0,
                requires_chunking=False,
                recommended_strategy="error"
            )
    
    return results


def suggest_reading_strategy(file_paths: List[Union[str, Path]]) -> Dict[str, Dict[str, Union[str, int]]]:
    """Suggest reading strategies for a list of files.
    
    Args:
        file_paths: List of file paths to analyze
        
    Returns:
        Dictionary with reading suggestions for each file
    """
    file_infos = batch_check_files(file_paths)
    suggestions = {}
    
    for path, info in file_infos.items():
        if info.recommended_strategy == "direct":
            suggestions[path] = {
                "action": "read_normally",
                "reason": f"File is {info.size_bytes:,} bytes (under {MAX_SAFE_FILE_SIZE:,} byte limit)"
            }
        elif info.recommended_strategy == "chunked":
            suggestions[path] = {
                "action": "read_with_offset_limit",
                "reason": f"File is {info.size_bytes:,} bytes, use offset/limit parameters",
                "suggested_limit": MAX_LINES_PER_CHUNK
            }
        elif info.recommended_strategy == "summary":
            suggestions[path] = {
                "action": "read_summary_only", 
                "reason": f"File is {info.size_bytes:,} bytes, too large for full reading",
                "suggested_limit": 50
            }
        else:
            suggestions[path] = {
                "action": "skip_or_error",
                "reason": "File could not be analyzed"
            }
    
    return suggestions


# Convenience functions for common use cases
def is_file_too_large(file_path: Union[str, Path]) -> bool:
    """Check if a file is too large for safe reading."""
    try:
        return get_file_info(file_path).requires_chunking
    except:
        return False


def get_safe_read_params(file_path: Union[str, Path]) -> Dict[str, Union[int, None]]:
    """Get recommended offset/limit parameters for safe file reading.
    
    Returns:
        Dictionary with 'offset' and 'limit' keys, or empty dict for direct reading
    """
    try:
        info = get_file_info(file_path)
        
        if info.recommended_strategy == "direct":
            return {}  # No special parameters needed
        elif info.recommended_strategy == "chunked":
            return {"offset": 0, "limit": MAX_LINES_PER_CHUNK}
        else:  # summary
            return {"offset": 0, "limit": 50}
            
    except:
        return {"offset": 0, "limit": 100}  # Conservative fallback