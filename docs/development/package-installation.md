# Package Installation Best Practices

## Development vs Production Installations

### The Problem
When developing packages that are used by other projects, changes to the source code may not be reflected in dependent projects if the package is installed normally (not in editable mode).

### Development Setup (Editable Install)

For active development where you want changes to be reflected immediately:

```bash
# In the dependent project (e.g., automagik_flashed)
uv pip install -e /path/to/automagik-dev/automagik-dev-1

# Or in pyproject.toml:
dependencies = [
    "automagik @ file:///home/cezar/automagik-dev/automagik-dev-1#egg=automagik",
]
```

**Note**: The `#egg=automagik` suffix hints to pip/uv to install in editable mode.

### Production Setup (Regular Install)

For production or when you want a specific version:

```bash
# Install from built package
uv pip install automagik==0.6.1

# Or from source at a specific commit
uv pip install git+https://github.com/org/repo.git@v0.6.1
```

### Clearing Build Caches

When `uv` caches builds and doesn't pick up changes:

```bash
# Clear uv cache
uv cache clean

# Force rebuild by removing and reinstalling
uv pip uninstall automagik
uv pip install automagik@ file:///path/to/source --force-reinstall

# Or manually remove cached packages
rm -rf ~/.cache/uv/built-wheels/*/automagik-*
```

### Version Detection in Packages

For packages that need to detect their version at runtime:

```python
# automagik/utils/version.py
import os
from pathlib import Path
import tomllib

def _get_version():
    """Get version with multiple fallback mechanisms"""
    # 1. Try from pyproject.toml (development)
    try:
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            return data["project"]["version"]
    except Exception:
        pass
    
    # 2. Try from package metadata (installed package)
    try:
        from importlib import metadata
        return metadata.version("automagik")
    except Exception:
        pass
    
    # 3. Environment variable override
    env_version = os.environ.get("AUTOMAGIK_VERSION")
    if env_version:
        return env_version
    
    # 4. Hardcoded fallback
    return "0.6.1"  # Update this with each release
```

### Recommendations

1. **For active development**: Use editable installs to see changes immediately
2. **For testing**: Use regular installs to test the actual package distribution
3. **For CI/CD**: Always use fresh installs without cache
4. **Version management**: Use `importlib.metadata` for reliable version detection in installed packages