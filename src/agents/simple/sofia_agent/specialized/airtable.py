import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple

from pydantic_ai import Agent, RunContext

# Import Airtable tools we created
from src.tools.airtable import airtable_tools
from src.tools.airtable.tool import list_bases, list_tables, list_records
# Import send_message (Evolution WhatsApp) – assume exists
from src.tools.evolution.tool import send_message  # type: ignore
from src.config import settings

logger = logging.getLogger(__name__)

# --------------------- Schema Caching -----------------------------

# Global cache for schema information
_schema_cache: Dict[str, Tuple[str, datetime]] = {}
SCHEMA_CACHE_TTL_MINUTES = 30  # Cache schema for 30 minutes


def _is_cache_valid(base_id: str) -> bool:
    """Check if cached schema is still valid."""
    if base_id not in _schema_cache:
        return False
    
    _, cached_time = _schema_cache[base_id]
    expiry_time = cached_time + timedelta(minutes=SCHEMA_CACHE_TTL_MINUTES)
    return datetime.now() < expiry_time


def _get_cached_schema(base_id: str) -> Optional[str]:
    """Get schema from cache if valid."""
    if _is_cache_valid(base_id):
        schema, _ = _schema_cache[base_id]
        logger.info(f"📋 Using cached schema for base {base_id}")
        return schema
    return None


def _cache_schema(base_id: str, schema: str) -> None:
    """Cache schema with timestamp."""
    _schema_cache[base_id] = (schema, datetime.now())
    logger.info(f"💾 Cached schema for base {base_id}")


# --------------------- Dynamic Schema Fetching -----------------------------

async def fetch_airtable_schema(base_id: Optional[str] = None, force_refresh: bool = False) -> str:
    """Fetch actual Airtable schema and format it for the prompt.
    
    Args:
        base_id: Airtable base ID (uses default from config if None)
        force_refresh: If True, bypass cache and fetch fresh schema
    """
    
    # Use provided base_id or get from config
    target_base_id = base_id or settings.AIRTABLE_DEFAULT_BASE_ID
    
    if not target_base_id:
        return "⚠️ **No Airtable base configured. Please set AIRTABLE_DEFAULT_BASE_ID.**"
    
    # Check cache first (unless force refresh)
    if not force_refresh:
        cached_schema = _get_cached_schema(target_base_id)
        if cached_schema:
            return cached_schema
    
    try:
        # Create dummy context for tool calls
        ctx = {}
        
        # Get base information
        logger.info(f"🔍 Fetching fresh schema for base: {target_base_id}")
        
        # Get all tables in the base
        tables_result = await list_tables(ctx, base_id=target_base_id)
        
        if not tables_result.get("success"):
            error_msg = f"⚠️ **Error fetching tables: {tables_result.get('error')}**"
            return error_msg
        
        tables = tables_result.get("tables", [])
        
        if not tables:
            return "⚠️ **No tables found in the configured base.**"
        
        # Build schema documentation
        schema_parts = [
            "## 🗂 **Live Airtable Schema** (Auto-Generated)",
            f"📊 **Base ID:** `{target_base_id}`",
            f"📅 **Schema fetched:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"⏰ **Cache TTL:** {SCHEMA_CACHE_TTL_MINUTES} minutes",
            ""
        ]
        
        # For each table, get sample records to understand field structure
        for table in tables:
            table_id = table.get("id")
            table_name = table.get("name")
            
            logger.info(f"📋 Analyzing table: {table_name} ({table_id})")
            
            # Get a few sample records to understand field types
            records_result = await list_records(
                ctx, 
                table=table_id, 
                base_id=target_base_id, 
                page_size=5  # Just need a few samples
            )
            
            schema_parts.append(f"### 📋 Table: `{table_name}` (ID: `{table_id}`)")
            
            if records_result.get("success"):
                records = records_result.get("records", [])
                
                if records:
                    # Analyze fields from sample records
                    all_fields = set()
                    field_examples = {}
                    
                    for record in records:
                        fields = record.get("fields", {})
                        for field_name, field_value in fields.items():
                            all_fields.add(field_name)
                            if field_name not in field_examples:
                                field_examples[field_name] = field_value
                    
                    if all_fields:
                        schema_parts.append("| Field | Type | Sample Value |")
                        schema_parts.append("|-------|------|--------------|")
                        
                        for field_name in sorted(all_fields):
                            sample_value = field_examples.get(field_name)
                            field_type = _infer_field_type(sample_value)
                            
                            # Truncate long sample values
                            sample_str = str(sample_value)
                            if len(sample_str) > 50:
                                sample_str = sample_str[:47] + "..."
                            
                            # Escape pipe characters in sample values
                            sample_str = sample_str.replace("|", "\\|")
                            
                            schema_parts.append(f"| `{field_name}` | {field_type} | `{sample_str}` |")
                    else:
                        schema_parts.append("*No fields found in sample records*")
                else:
                    schema_parts.append("*Table appears to be empty*")
            else:
                error_msg = records_result.get("error", "Unknown error")
                schema_parts.append(f"*Error fetching records: {error_msg}*")
            
            schema_parts.append("")  # Empty line between tables
        
        # Add helpful notes
        schema_parts.extend([
            "---",
            "### 🔧 **Schema Notes:**",
            "- Use exact field names from above tables when creating/updating records",
            "- For linked fields, use record IDs or names as appropriate",
            "- Always verify current data with `airtable_list_records` before making changes",
            "- Field types are inferred from sample data and may vary",
            "- Schema is cached for performance (use force_refresh=True to update)",
            ""
        ])
        
        schema_text = "\n".join(schema_parts)
        
        # Cache the result
        _cache_schema(target_base_id, schema_text)
        
        return schema_text
        
    except Exception as e:
        logger.error(f"Error fetching Airtable schema: {e}")
        return f"⚠️ **Error fetching schema: {str(e)}**"


def _infer_field_type(value: Any) -> str:
    """Infer Airtable field type from sample value."""
    if value is None:
        return "empty"
    elif isinstance(value, str):
        if len(value) > 100:
            return "long text"
        else:
            return "text"
    elif isinstance(value, (int, float)):
        return "number"
    elif isinstance(value, bool):
        return "checkbox"
    elif isinstance(value, list):
        if value and isinstance(value[0], dict):
            return "linked records"
        else:
            return "multiple select"
    elif isinstance(value, dict):
        if "url" in value:
            return "attachment"
        else:
            return "formula/lookup"
    else:
        return "unknown"


async def build_dynamic_system_prompt(base_id: Optional[str] = None, force_refresh: bool = False) -> str:
    """Build the complete system prompt with dynamic schema information.
    
    Args:
        base_id: Airtable base ID (uses default from config if None)
        force_refresh: If True, bypass schema cache and fetch fresh data
    """
    
    # Get the live schema (with caching)
    live_schema = await fetch_airtable_schema(base_id, force_refresh)
    
    # Build the complete prompt
    return f"""
# 📋 Airtable Agent – System Prompt

Purpose: empower a specialised sub-agent (GPT-4.1) to keep our Airtable base in sync with real-world execution and to drive visibility through automated WhatsApp updates.
Audience: internal orchestration layer – do **not** show end-users.

---

## 🔑 Role & Objective

You are **Airtable Assistant**, a persistent autonomous agent.  Your mission:

1. **Maintain data integrity** across all tables in our Airtable base.
2. **Generate & update tasks** from meeting inputs.
3. **Drive daily accountability** by sending contextual WhatsApp messages (checkpoint + daily digest).
4. **Escalate blockers** instantly to the *Avengers* group.

### Persistence Reminder
> *You are an agent — keep going until the current query or scheduled job is fully resolved before yielding control.*

### Tool-Calling Reminder
* Use `airtable.<action>` **whenever** you need ground-truth data; never guess.
* Use `send_message` to reach WhatsApp (DM or group).
* If you lack parameters, ask the orchestrator for exactly what you need.

### Planning Reminder
*Before every function call*: think step-by-step and state your plan in natural language.  *After every call*: reflect on the outcome and verify success.

---

{live_schema}

---

## 🚦 Common Status Values & Vocabulary
Based on your table data, here are commonly used values:

* **Task Status**: `A fazer`, `Estou trabalhando`, `Estou bloqueado`, `Terminei`
* **Priority**: `Para tudo e faz` (P0 – critical), `Alta` (P1), `Média` (P2), `Baixa` (P3)

---

## ⚙️ Workflows
### 1 · Reactive Actions
| Trigger | Steps |
| --- | --- |
| **Create task from meeting** | 1) Parse meeting summary/transcript. 2) Use exact field names from schema above. 3) `airtable_create_records` with at minimum the required fields. 4) Infer/ask for missing: linked records, assignees, dates, priority (default =Média), status (default =`A fazer`). |
| **Update task attributes** | `airtable_update_records` matching by record ID or unique field. Use exact field names from schema. |
| **Status → Estou bloqueado** | 1) Ensure *reason* present: ask if missing. 2) Update description field with `🛑 BLOQUEIO:` line. 3) `send_message` to **Avengers group**. |

### 2 · Proactive Jobs
| Schedule (America/Sao_Paulo) | Job | Behaviour |
| --- | --- | --- |
| **Daily 09:00** | Individual checkpoint | For each team member with open tasks, compile a personal list and `send_message` (DM). |
| **Daily 18:00** | Daily digest | Gather grouped task lists by status, totals and imminent deadlines; `send_message` to **Avengers group**. |

---

**Important**: Always use the exact field names shown in the schema above. The schema is live-fetched and cached for performance.

Always echo a concise natural-language plan before every tool call and reflect after.
"""

# --------------------- Agent initialisation -----------------------

# Global agent instance - will be initialized dynamically
airtable_assistant: Optional[Agent] = None


async def get_airtable_assistant(base_id: Optional[str] = None, force_refresh: bool = False) -> Agent:
    """Get or create the Airtable assistant with dynamic prompt.
    
    Args:
        base_id: Airtable base ID (uses default from config if None)
        force_refresh: If True, bypass schema cache and rebuild agent with fresh data
    """
    global airtable_assistant
    
    # Check if we need to rebuild (force refresh or no cached agent)
    target_base_id = base_id or settings.AIRTABLE_DEFAULT_BASE_ID
    should_rebuild = (
        force_refresh or 
        airtable_assistant is None or 
        not _is_cache_valid(target_base_id or "")
    )
    
    if should_rebuild:
        logger.info("🔄 Building Airtable assistant with fresh schema...")
        dynamic_prompt = await build_dynamic_system_prompt(base_id, force_refresh)
        
        airtable_assistant = Agent(
            "openai:gpt-4o", 
            tools=[*airtable_tools, send_message],
            system_prompt=dynamic_prompt,
            deps_type=Dict[str, Any],
            result_type=str,
        )
    else:
        logger.info("♻️ Using cached Airtable assistant")
    
    return airtable_assistant


async def run_airtable_assistant(
    ctx: RunContext[Dict[str, Any]], 
    user_input: str, 
    base_id: Optional[str] = None,
    force_refresh: bool = False
) -> str:
    """Entry point for Sofia specialized Airtable agent.
    
    Args:
        ctx: Runtime context
        user_input: User query or instruction
        base_id: Airtable base ID (uses default from config if None)
        force_refresh: If True, fetch fresh schema and rebuild agent
    """
    assistant = await get_airtable_assistant(base_id, force_refresh)
    result = await assistant.run(user_input, deps=ctx.deps if ctx else None)
    return result.output


# --------------------- Cache Management Functions -----------------------

def clear_schema_cache(base_id: Optional[str] = None) -> None:
    """Clear schema cache for a specific base or all bases."""
    global _schema_cache
    
    if base_id:
        if base_id in _schema_cache:
            del _schema_cache[base_id]
            logger.info(f"🗑️ Cleared schema cache for base: {base_id}")
    else:
        _schema_cache.clear()
        logger.info("🗑️ Cleared all schema cache")


def get_cache_info() -> Dict[str, Any]:
    """Get information about current schema cache state."""
    cache_info = {}
    
    for base_id, (_, cached_time) in _schema_cache.items():
        expiry_time = cached_time + timedelta(minutes=SCHEMA_CACHE_TTL_MINUTES)
        is_valid = datetime.now() < expiry_time
        time_remaining = expiry_time - datetime.now() if is_valid else timedelta(0)
        
        cache_info[base_id] = {
            "cached_at": cached_time.isoformat(),
            "expires_at": expiry_time.isoformat(),
            "is_valid": is_valid,
            "time_remaining_minutes": time_remaining.total_seconds() / 60
        }
    
    return cache_info 