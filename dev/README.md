# Development Scripts

Simple organization to prevent script folder graveyards while keeping development productive.

## 📁 **Two Simple Zones**

### `dev/` - All Development Scripts
- **Put here**: Experiments, debugging, testing, tools, anything development-related
- **No review needed**
- **Keep as long as you want**

### `dev/temp/` - Auto-Cleanup Zone  
- **Put here**: Very temporary scripts, quick tests
- **Auto-deleted after 30 days** ⚠️
- **No recovery possible**

### `scripts/` - Production Only (PROTECTED)
- **Put here**: Only reviewed, documented, production utilities
- **Examples**: monitoring, database setup, project management
- **Requires**: Code review and documentation

## 🚫 Simple Rules

### ❌ **NEVER put development scripts in `scripts/`**
- No test scripts, debug scripts, experiments
- Only production-ready utilities

### ✅ **Always put development work in `dev/`**
- Start in `dev/temp/` if very temporary
- Move to `dev/` if you want to keep it
- Promote to `scripts/` only if it becomes a production utility

## 🗑️ Auto-Cleanup
- `dev/temp/` files older than 30 days are automatically deleted
- Run `python scripts/cleanup_dev_temp.py --dry-run` to preview
- Run `python scripts/cleanup_dev_temp.py` to execute

---

**That's it!** When in doubt: use `dev/` for development, `scripts/` for production. 