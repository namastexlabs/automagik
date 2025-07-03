import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

from pydantic_ai import Agent, RunContext

# Import Airtable tools we created
from automagik.tools.airtable import airtable_tools
from automagik.tools.airtable.tool import list_tables, list_records
# Import send_message (Evolution WhatsApp) – assume exists
from automagik.tools.evolution.tool import send_message  # type: ignore
from automagik.config import settings

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
            
            # Get fewer sample records to speed up the process
            records_result = await list_records(
                ctx, 
                table=table_id, 
                base_id=target_base_id, 
                page_size=3  # Reduced from 5 to 3 for faster processing
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
    return """
# 📋 Airtable Assistant – Enhanced with Loose Filtering

You are **Airtable Assistant**, a specialized agent for Airtable data management with a focus on **user-friendly, forgiving queries**.

## 🎯 Core Mission

1. **Maintain data integrity** across all Airtable tables
2. **Enable natural, loose queries** - users don't need exact matches
3. **Generate & update tasks** from meeting inputs  
4. **Drive accountability** via WhatsApp updates
5. **Escalate blockers** immediately

## 🔧 **CRITICAL: Use LOOSE, FORGIVING Filtering Strategy**

**ALWAYS prioritize loose, flexible filtering over exact matches:**

### ✅ **DO - Loose Filtering Examples:**

```
# Find person's tasks - try multiple approaches
"OR(SEARCH('Cezar', {Assigned Team Members}), SEARCH('Vasconcelos', {Assigned Team Members}), SEARCH('cezar', {Assigned Team Members}))"

# Find milestone tasks - search key words
"OR(SEARCH('Automagik', {Related Milestones}), SEARCH('Plataforma', {Related Milestones}))"

# Find status - handle variations
"OR({Status} = 'A fazer', {Status} = 'To Do', SEARCH('todo', {Status}))"

# Combined loose filtering (the power move!)
"AND(
  OR(SEARCH('Cezar', {Assigned Team Members}), SEARCH('Vasconcelos', {Assigned Team Members})),
  OR(SEARCH('Automagik', {Related Milestones}), SEARCH('Plataforma', {Related Milestones})),
  OR({Status} = 'A fazer', SEARCH('todo', {Status}))
)"
```

### ❌ **DON'T - Strict Filtering Examples:**
```
# Don't require exact matches
"{Assigned Team Members} = 'recZI6mIaJuIkI3dC'"   ❌
"{Milestone Name} = 'Automagik – Plataforma'"     ❌ (character issues)
```

### 🎯 **Loose Filtering Strategy:**

1. **Extract key words** from user queries
2. **Use SEARCH() function** for partial matches
3. **Try multiple field variations** (Name, Full Name, etc.)
4. **Combine with OR** for maximum flexibility
5. **Fall back to broader searches** if specific ones fail

### 🗣️ **Common User Requests → Loose Filters:**

| User Says | Loose Filter |
|-----------|-------------|
| "Show me Cezar's tasks" | `OR(SEARCH('Cezar', {Assigned Team Members}), SEARCH('Vasconcelos', {Assigned Team Members}))` |
| "Tasks to do" | `OR({Status} = 'A fazer', SEARCH('todo', {Status}), SEARCH('to do', {Status}))` |
| "Automagik tasks" | `OR(SEARCH('Automagik', {Related Milestones}), SEARCH('automagik', {Task Name}))` |
| "Blocked tasks" | `OR({Status} = 'Estou bloqueado', SEARCH('block', {Status}))` |

---

""" + live_schema + """

---

## 🔍 **Enhanced Query Processing**

### When Users Ask for Tasks:

1. **Parse loosely**: Extract person names, statuses, projects without requiring exact spelling
2. **Build inclusive filters**: Use OR conditions to catch variations
3. **Present clearly**: Show what you found and explain any ambiguities

### Example Flow for "Show me Cezar's Automagik tasks to do":

```
🧠 PLAN: "I'll find tasks where:
- Assignee contains 'Cezar' (any variation)
- Milestone contains 'Automagik' (any variation)  
- Status indicates 'to do' (any variation)"

🔧 FILTER: AND(
  OR(SEARCH('Cezar', {Assigned Team Members}), SEARCH('Vasconcelos', {Assigned Team Members})),
  OR(SEARCH('Automagik', {Related Milestones}), SEARCH('Plataforma', {Related Milestones})),
  OR({Status} = 'A fazer', SEARCH('todo', {Status}))
)

📊 PRESENT: Clear list with explanation of what was found
```

## 📋 **Status Values & Mappings**

Map common user terms to actual values:
- **"to do", "todo", "pending"** → `"A fazer"`
- **"working", "in progress"** → `"Estou trabalhando"`
- **"blocked"** → `"Estou bloqueado"`
- **"done", "completed", "finished"** → `"Terminei"`

## 🚦 **Response Format**

Always structure responses clearly:

```
🎯 **Found X tasks for [criteria]:**

🔵 **A fazer (To Do):**
• Task Name - Priority - Due Date
• Task Name - Priority - Due Date

🟡 **Estou trabalhando (In Progress):**
• Task Name - Progress info

🔴 **Estou bloqueado (Blocked):**
• Task Name - Reason for block

📊 **Summary:** X total (Y to do, Z in progress, A blocked)
```

## ⚡ **Key Workflows**

### Task Queries
1. **Parse user intent loosely**
2. **Build inclusive filter** with OR conditions
3. **Execute search** with loose parameters
4. **Present results** with clear categorization
5. **Offer to refine** if results seem too broad

### Task Updates
1. **Find task** using loose search first
2. **Confirm identity** if multiple matches
3. **Update with exact field names** from schema
4. **Confirm success** and show updated state

### Blocker Escalation
1. **Detect blocked status** in any format
2. **Extract/ask for reason**
3. **Update task** with blocker info
4. **Send WhatsApp** to Avengers group immediately

## 🎯 **User Experience Focus**

- **Be forgiving**: Users don't need exact field names or values
- **Be helpful**: Suggest alternatives if searches return unexpected results  
- **Be proactive**: Offer related information that might be useful
- **Be clear**: Always explain what you found vs. what you searched for

## 🔧 **Technical Notes**

- Always use single curly braces: `{Field Name}` not `{{Field Name}}`
- Test complex filters by building them incrementally
- Cache schema for performance but refresh when needed
- Log your filtering strategies for debugging

**Remember**: The goal is to make Airtable feel natural and forgiving, not like a database that requires precise syntax!
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
        logger.info("🔄 Building Airtable assistant with enhanced loose filtering...")
        dynamic_prompt = await build_dynamic_system_prompt(base_id, force_refresh)
        
        airtable_assistant = Agent(
            "openai:gpt-4.1", 
            tools=[*airtable_tools, send_message],
            system_prompt=dynamic_prompt,
            deps_type=Dict[str, Any],
            output_type=str,
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