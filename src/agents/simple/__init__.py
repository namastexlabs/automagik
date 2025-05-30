"""Deprecation shim for the simple namespace.

This module provides backward compatibility for the old 'simple' namespace
which has been moved to 'pydanticai'. All imports will issue a deprecation
warning and redirect to the new location.
"""

import warnings
from src.agents.pydanticai import *

# Issue deprecation warning on import
warnings.warn(
    "The 'src.agents.simple' namespace is deprecated and will be removed in a future version. "
    "Please update your imports to use 'src.agents.pydanticai' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export all public names from the new location
__all__ = [
    'discord',
    'estruturar', 
    'flashinho',
    'prompt_maker',
    'simple',
    'sofia',
    'stan',
    'stan_email',
    'summary',
]