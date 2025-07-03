"""
Universal Node.js Detection Utility

This module provides dynamic Node.js detection that works across different
installation methods including NVM, system installs, nodeenv, Volta, etc.

Maintains security while being universally compatible.
"""

import os
import shutil
import glob
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class NodeJSDetector:
    """Universal Node.js installation detector"""
    
    def __init__(self):
        self._node_path = None
        self._npm_path = None
        self._npx_path = None
        self._detection_attempted = False
    
    def find_node_installation(self) -> Optional[Dict[str, str]]:
        """
        Find Node.js installation dynamically across different installation methods.
        
        Returns:
            Dict with 'node', 'npm', 'npx' paths or None if not found
        """
        if self._detection_attempted and self._node_path:
            return {
                'node': self._node_path,
                'npm': self._npm_path,
                'npx': self._npx_path
            }
        
        self._detection_attempted = True
        
        # Strategy 1: Check if already in PATH
        node_path = shutil.which('node')
        if node_path:
            npm_path = shutil.which('npm')
            npx_path = shutil.which('npx')
            if npm_path and npx_path:
                self._node_path = node_path
                self._npm_path = npm_path
                self._npx_path = npx_path
                logger.info(f"Found Node.js in PATH: {node_path}")
                return {
                    'node': node_path,
                    'npm': npm_path,
                    'npx': npx_path
                }
        
        # Strategy 2: Check common installation patterns
        installation_patterns = self._get_installation_patterns()
        
        for pattern_name, patterns in installation_patterns.items():
            logger.debug(f"Checking {pattern_name} patterns...")
            for pattern in patterns:
                try:
                    expanded_pattern = os.path.expanduser(pattern)
                    matches = glob.glob(expanded_pattern)
                    
                    for match in matches:
                        if os.path.isfile(match) and os.access(match, os.X_OK):
                            # Found node binary, check for npm/npx in same directory
                            bin_dir = os.path.dirname(match)
                            npm_path = os.path.join(bin_dir, 'npm')
                            npx_path = os.path.join(bin_dir, 'npx')
                            
                            if os.path.isfile(npm_path) and os.path.isfile(npx_path):
                                self._node_path = match
                                self._npm_path = npm_path
                                self._npx_path = npx_path
                                logger.info(f"Found Node.js via {pattern_name}: {match}")
                                return {
                                    'node': match,
                                    'npm': npm_path,
                                    'npx': npx_path
                                }
                except Exception as e:
                    logger.debug(f"Error checking pattern {pattern}: {e}")
                    continue
        
        logger.warning("No Node.js installation found")
        return None
    
    def _get_installation_patterns(self) -> Dict[str, List[str]]:
        """Get Node.js installation patterns for different managers"""
        return {
            'nvm': [
                '~/.nvm/versions/node/*/bin/node',
                '~/.nvm/current/bin/node',
                '~/.nvm/alias/default/bin/node'
            ],
            'system': [
                '/usr/bin/node',
                '/usr/local/bin/node',
                '/opt/node/bin/node',
                '/opt/nodejs/bin/node'
            ],
            'nodeenv': [
                '~/.nodeenv/*/bin/node',
                '~/nodeenv/*/bin/node'
            ],
            'volta': [
                '~/.volta/bin/node',
                '~/.volta/tools/image/node/*/bin/node'
            ],
            'fnm': [
                '~/.fnm/node-versions/*/installation/bin/node',
                '~/.fnm/current/bin/node'
            ],
            'n': [
                '~/n/versions/node/*/bin/node',
                '/usr/local/n/versions/node/*/bin/node'
            ],
            'homebrew': [
                '/opt/homebrew/bin/node',
                '/usr/local/Cellar/node/*/bin/node'
            ],
            'snap': [
                '/snap/node/current/bin/node'
            ]
        }
    
    def ensure_node_in_path(self) -> bool:
        """
        Ensure Node.js is discoverable in PATH.
        
        Returns:
            True if Node.js is available, False otherwise
        """
        # Check if already available
        if shutil.which('node'):
            return True
        
        # Try to find and add to PATH
        installation = self.find_node_installation()
        if installation:
            bin_dir = os.path.dirname(installation['node'])
            current_path = os.environ.get('PATH', '')
            
            if bin_dir not in current_path:
                os.environ['PATH'] = f"{bin_dir}:{current_path}"
                logger.info(f"Added Node.js bin directory to PATH: {bin_dir}")
            
            return True
        
        return False
    
    def get_security_paths(self) -> Optional[Dict[str, str]]:
        """
        Get Node.js paths for security allowlist configuration.
        
        Returns:
            Dict with paths for security configuration or None if not found
        """
        installation = self.find_node_installation()
        if installation:
            return {
                'node_path': installation['node'],
                'npm_path': installation['npm'], 
                'npx_path': installation['npx']
            }
        return None

# Global detector instance
_detector = NodeJSDetector()

def find_node_installation() -> Optional[Dict[str, str]]:
    """Global function to find Node.js installation"""
    return _detector.find_node_installation()

def ensure_node_in_path() -> bool:
    """Global function to ensure Node.js is in PATH"""
    return _detector.ensure_node_in_path()

def get_security_paths() -> Optional[Dict[str, str]]:
    """Global function to get security paths"""
    return _detector.get_security_paths()