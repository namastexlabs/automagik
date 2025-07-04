# Tools for External Agents

This directory contains tools and utilities that can be used by multiple external agents, avoiding code duplication and making maintenance easier.

## Structure

```
tools/
├── flashed/          # Flashed API integration tools
│   ├── tool.py       # Main tool definitions
│   ├── provider.py   # API client implementation
│   ├── auth_utils.py # Authentication utilities
│   └── ...          # Other utilities
└── evolution/        # Evolution API integration tools
    └── api.py        # WhatsApp messaging tools
```

## Usage

External agents can import these tools by adding the parent directory to the Python path:

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools import (
    get_user_data, 
    get_user_score,
    FlashedProvider,
    # ... other tools
)
```

## Configuration

The tools use the extensible settings system. External agents must register their API keys in their `__init__` method:

```python
from automagik.config import get_settings

settings = get_settings()
settings.add_external_api_key("FLASHED_API_KEY", os.environ.get("FLASHED_API_KEY"))
settings.add_external_url("FLASHED_API_URL", os.environ.get("FLASHED_API_URL"))
```

## Benefits

1. **Single Source of Truth**: Tool implementations exist in one place
2. **Easier Maintenance**: Updates to tools automatically affect all agents
3. **Consistent Behavior**: All agents use the same tool implementations
4. **Reduced Duplication**: No need to copy tools between agents

## Adding New Tools

1. Create a new directory under `tools/` for your tool category
2. Implement your tools following the existing patterns
3. Export them in `tools/__init__.py`
4. Update external agents to import from tools

## Environment Variables

The following environment variables should be set for the tools:

- `FLASHED_API_KEY`: API key for Flashed integration
- `FLASHED_API_URL`: Base URL for Flashed API
- `EVOLUTION_API_KEY`: API key for Evolution/WhatsApp integration
- `EVOLUTION_API_URL`: Base URL for Evolution API