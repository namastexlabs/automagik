"""Git integration service for workflow run tracking.

This service provides utilities for extracting git information from workspaces
and integrating with the workflow_runs tracking system.
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GitDiffStats:
    """Git diff statistics."""
    added_lines: int = 0
    removed_lines: int = 0
    files_changed: int = 0
    detailed_stats: Dict[str, Dict[str, int]] = None
    
    def __post_init__(self):
        if self.detailed_stats is None:
            self.detailed_stats = {}


@dataclass
class GitInfo:
    """Complete git repository information."""
    repository_url: Optional[str] = None
    current_branch: Optional[str] = None
    current_commit_hash: Optional[str] = None
    is_dirty: bool = False
    diff_stats: Optional[GitDiffStats] = None


class GitService:
    """Service for git operations and information extraction."""
    
    def __init__(self, timeout: int = 10):
        """Initialize git service.
        
        Args:
            timeout: Timeout for git commands in seconds
        """
        self.timeout = timeout
    
    def get_git_info(self, workspace_path: Path) -> GitInfo:
        """Get comprehensive git information from a workspace.
        
        Args:
            workspace_path: Path to the git repository
            
        Returns:
            GitInfo object with repository information
        """
        if not workspace_path.exists() or not (workspace_path / '.git').exists():
            logger.debug(f"No git repository found at {workspace_path}")
            return GitInfo()
        
        try:
            return GitInfo(
                repository_url=self._get_repository_url(workspace_path),
                current_branch=self._get_current_branch(workspace_path),
                current_commit_hash=self._get_current_commit_hash(workspace_path),
                is_dirty=self._is_repository_dirty(workspace_path),
                diff_stats=self._get_diff_stats(workspace_path)
            )
        except Exception as e:
            logger.warning(f"Failed to get git info from {workspace_path}: {e}")
            return GitInfo()
    
    def get_diff_between_commits(self, workspace_path: Path, 
                                initial_commit: str, final_commit: str) -> GitDiffStats:
        """Get diff statistics between two commits.
        
        Args:
            workspace_path: Path to the git repository
            initial_commit: Initial commit hash
            final_commit: Final commit hash
            
        Returns:
            GitDiffStats with difference information
        """
        if not workspace_path.exists() or not (workspace_path / '.git').exists():
            return GitDiffStats()
        
        try:
            # Get overall diff stats
            cmd = ['git', 'diff', '--stat', f'{initial_commit}..{final_commit}']
            result = subprocess.run(
                cmd,
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                logger.warning(f"Git diff failed: {result.stderr}")
                return GitDiffStats()
            
            return self._parse_diff_stats(result.stdout)
            
        except Exception as e:
            logger.warning(f"Failed to get diff between commits {initial_commit}..{final_commit}: {e}")
            return GitDiffStats()
    
    def _get_repository_url(self, workspace_path: Path) -> Optional[str]:
        """Get the repository URL."""
        try:
            result = subprocess.run(
                ['git', 'config', '--get', 'remote.origin.url'],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None
    
    def _get_current_branch(self, workspace_path: Path) -> Optional[str]:
        """Get the current branch name."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None
    
    def _get_current_commit_hash(self, workspace_path: Path) -> Optional[str]:
        """Get the current commit hash."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None
    
    def _is_repository_dirty(self, workspace_path: Path) -> bool:
        """Check if the repository has uncommitted changes."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            return bool(result.stdout.strip()) if result.returncode == 0 else False
        except Exception:
            return False
    
    def _get_diff_stats(self, workspace_path: Path) -> GitDiffStats:
        """Get diff statistics for uncommitted changes."""
        try:
            result = subprocess.run(
                ['git', 'diff', '--stat'],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                return self._parse_diff_stats(result.stdout)
            
        except Exception:
            pass
        
        return GitDiffStats()
    
    def _parse_diff_stats(self, diff_output: str) -> GitDiffStats:
        """Parse git diff --stat output into structured data.
        
        Args:
            diff_output: Output from git diff --stat
            
        Returns:
            GitDiffStats object with parsed information
        """
        lines = diff_output.strip().split('\n')
        if not lines or not lines[-1]:
            return GitDiffStats()
        
        # Parse the summary line (last line)
        summary_line = lines[-1].strip()
        
        # Extract overall stats
        added_lines = 0
        removed_lines = 0
        files_changed = 0
        
        # Parse patterns like "3 files changed, 45 insertions(+), 12 deletions(-)"
        import re
        
        # Files changed
        files_match = re.search(r'(\d+)\s+files?\s+changed', summary_line)
        if files_match:
            files_changed = int(files_match.group(1))
        
        # Insertions
        insertions_match = re.search(r'(\d+)\s+insertions?\(\+\)', summary_line)
        if insertions_match:
            added_lines = int(insertions_match.group(1))
        
        # Deletions
        deletions_match = re.search(r'(\d+)\s+deletions?\(-\)', summary_line)
        if deletions_match:
            removed_lines = int(deletions_match.group(1))
        
        # Parse detailed per-file stats
        detailed_stats = {}
        for line in lines[:-1]:  # Exclude summary line
            if '|' in line:
                # Parse lines like " file.py | 23 +++++++++++++++"
                parts = line.split('|')
                if len(parts) >= 2:
                    filename = parts[0].strip()
                    changes_part = parts[1].strip()
                    
                    # Extract number and count +/- symbols
                    number_match = re.search(r'(\d+)', changes_part)
                    if number_match:
                        total_changes = int(number_match.group(1))
                        plus_count = changes_part.count('+')
                        minus_count = changes_part.count('-')
                        
                        detailed_stats[filename] = {
                            'total_changes': total_changes,
                            'added_lines': plus_count,
                            'removed_lines': minus_count
                        }
        
        return GitDiffStats(
            added_lines=added_lines,
            removed_lines=removed_lines,
            files_changed=files_changed,
            detailed_stats=detailed_stats
        )


# Singleton service instance
_git_service = None


def get_git_service() -> GitService:
    """Get the singleton git service instance."""
    global _git_service
    if _git_service is None:
        _git_service = GitService()
    return _git_service


def extract_git_info_from_workspace(workspace_path: Path) -> Dict[str, Any]:
    """Extract git information from a workspace for workflow run tracking.
    
    Args:
        workspace_path: Path to the workspace
        
    Returns:
        Dictionary with git information suitable for workflow_runs table
    """
    service = get_git_service()
    git_info = service.get_git_info(workspace_path)
    
    return {
        'git_repo': git_info.repository_url,
        'git_branch': git_info.current_branch,
        'initial_commit_hash': git_info.current_commit_hash,
        'git_diff_added_lines': git_info.diff_stats.added_lines if git_info.diff_stats else 0,
        'git_diff_removed_lines': git_info.diff_stats.removed_lines if git_info.diff_stats else 0,
        'git_diff_files_changed': git_info.diff_stats.files_changed if git_info.diff_stats else 0,
        'git_diff_stats': git_info.diff_stats.detailed_stats if git_info.diff_stats else {},
        'is_dirty': git_info.is_dirty
    }


def extract_commit_diff_stats(workspace_path: Path, initial_commit: str, 
                             final_commit: str) -> Dict[str, Any]:
    """Extract diff statistics between two commits.
    
    Args:
        workspace_path: Path to the workspace
        initial_commit: Initial commit hash
        final_commit: Final commit hash
        
    Returns:
        Dictionary with diff statistics for workflow_runs table
    """
    service = get_git_service()
    diff_stats = service.get_diff_between_commits(workspace_path, initial_commit, final_commit)
    
    return {
        'git_diff_added_lines': diff_stats.added_lines,
        'git_diff_removed_lines': diff_stats.removed_lines,
        'git_diff_files_changed': diff_stats.files_changed,
        'git_diff_stats': diff_stats.detailed_stats
    }