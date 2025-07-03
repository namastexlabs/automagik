import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

from pydantic_ai import Agent, RunContext

# Import Airtable tools we created
from automagik.tools.airtable import airtable_tools
from automagik.tools.airtable.tool import list_tables, list_records
# Import send_message (Evolution WhatsApp)
from automagik.tools.evolution.tool import send_message  # type: ignore
from automagik.config import settings

logger = logging.getLogger(__name__)

# --------------------- Schema Caching (Original + Enhanced) -----------------------------

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


# --------------------- Enhanced Schema Fetching -----------------------------

async def fetch_airtable_schema(base_id: Optional[str] = None, force_refresh: bool = False) -> str:
    """Fetch actual Airtable schema with GPT-4.1 enhancements.
    
    Balances between detailed information and prompt size efficiency.
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
        
        logger.info(f"🔍 Fetching fresh schema for base: {target_base_id}")
        
        # Get all tables in the base - use identifiersOnly for efficiency
        tables_result = await list_tables(ctx, base_id=target_base_id, detailLevel="identifiersOnly")
        
        if not tables_result.get("success"):
            error_msg = f"⚠️ **Error fetching tables: {tables_result.get('error')}**"
            return error_msg
        
        tables = tables_result.get("tables", [])
        
        if not tables:
            return "⚠️ **No tables found in the configured base.**"
        
        # Build focused schema documentation
        schema_parts = [
            "## 🗂 **Airtable Schema** (Live Data)",
            f"📊 **Base ID:** `{target_base_id}`",
            f"📅 **Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "### 📋 Available Tables"
        ]
        
        # Get detailed info for key tables only (Tasks, Team Members, Milestones)
        key_tables = ["Tasks", "Team Members", "Milestones", "Meetings"]
        
        for table in tables:
            table_id = table.get("id")
            table_name = table.get("name")
            
            # Add basic info for all tables
            schema_parts.append(f"\n**{table_name}** (`{table_id}`)")
            
            # Get detailed info only for key tables
            if table_name in key_tables:
                # Get sample records to understand field structure
                records_result = await list_records(
                    ctx, 
                    table=table_id, 
                    base_id=target_base_id, 
                    page_size=2  # Just 2 records for efficiency
                )
                
                if records_result.get("success") and records_result.get("records"):
                    records = records_result.get("records", [])
                    
                    # Extract field info from samples
                    all_fields = set()
                    field_examples = {}
                    
                    for record in records:
                        fields = record.get("fields", {})
                        for field_name, field_value in fields.items():
                            all_fields.add(field_name)
                            if field_name not in field_examples:
                                field_examples[field_name] = field_value
                    
                    if all_fields:
                        schema_parts.append("| Field | Type | Example |")
                        schema_parts.append("|-------|------|---------|")
                        
                        # Focus on most important fields
                        priority_fields = ["Name", "Task Name", "Status", "Assigned Team Members", 
                                         "Related Milestones", "Due Date", "Priority", "Email"]
                        
                        # Show priority fields first
                        for field_name in sorted(all_fields):
                            if any(pf in field_name for pf in priority_fields):
                                sample_value = field_examples.get(field_name)
                                field_type = _infer_field_type(sample_value)
                                sample_str = _format_sample_value(sample_value)
                                schema_parts.append(f"| `{field_name}` | {field_type} | {sample_str} |")
                else:
                    schema_parts.append("*Unable to fetch field details*")
            
            schema_parts.append("")
        
        # Add practical filtering examples (kept from original)
        schema_parts.extend([
            "---",
            "### 🔧 **Filter Examples**",
            "```airtable",
            "// Find person's tasks (loose matching)",
            "OR(SEARCH('Cezar', {Assigned Team Members}), SEARCH('cezar', {Assigned Team Members}))",
            "",
            "// Status filtering (Portuguese + English)",
            "OR({Status} = 'A fazer', {Status} = 'To Do', SEARCH('todo', {Status}))",
            "",
            "// Combined filters",
            "AND(",
            "  OR(SEARCH('João', {Assigned Team Members})),",
            "  OR({Status} = 'Estou bloqueado', {Status} = 'Blocked')",
            ")",
            "```",
            "",
            "### 📝 **Important Notes**",
            "- Status values: 'A fazer', 'Estou trabalhando', 'Terminei', 'Estou bloqueado', 'Em review'",
            "- Formula fields cannot be created with this MCP (Airtable API limitation)",
            "- Use SEARCH() for flexible text matching",
            "- Always verify data before updates",
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
    """Infer Airtable field type from sample value (from original)."""
    if value is None:
        return "empty"
    elif isinstance(value, str):
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


def _format_sample_value(value: Any) -> str:
    """Format sample value for display."""
    if value is None:
        return "*empty*"
    
    sample_str = str(value)
    if len(sample_str) > 40:
        sample_str = sample_str[:37] + "..."
    
    # Escape pipe characters
    sample_str = sample_str.replace("|", "\\|")
    
    return f"`{sample_str}`"


# --------------------- GPT-4.1 Optimized System Prompt ---------------------

async def build_dynamic_system_prompt(base_id: Optional[str] = None, force_refresh: bool = False) -> str:
    """Build system prompt following GPT-4.1 best practices while maintaining original functionality."""
    
    # Get the live schema
    live_schema = await fetch_airtable_schema(base_id, force_refresh)
    
    return f"""# Airtable Data Management Agent

## Role and Objective
You are Bella, an Airtable Data Management Agent specialized in helping users interact with their Airtable data using natural language. Make Airtable feel accessible and forgiving while maintaining data integrity.

## Instructions

### Tool Usage (Critical)
- You MUST continue working until the user's request is completely resolved
- Always use tools to verify data - do NOT guess or make assumptions
- If unsure about data structure, use tools to explore before proceeding
- Only end your turn when the task is complete or you need user input

### Filtering Strategy
ALWAYS prioritize loose, flexible filtering:
- Use SEARCH() function for partial text matches
- Try multiple variations (uppercase, lowercase, partial names)
- Combine with OR() for maximum flexibility
- If no results, progressively broaden your search
- Common Portuguese status values: "A fazer", "Estou trabalhando", "Terminei", "Estou bloqueado", "Em review"

### Planning Before Actions
Before each tool call, think through:
1. What is the user trying to achieve?
2. Which table and fields are relevant?
3. What's the most forgiving filter strategy?
4. What fallbacks can I use if this doesn't work?

## Reasoning Steps

### Query Processing Workflow
1. **Parse Intent**: Understand what the user wants (list, search, update, create)
2. **Build Filter**: Create loose, inclusive filters using SEARCH() and OR()
3. **Execute Search**: Run the query and check results
4. **Handle Results**: 
   - If found: Present clearly
   - If none: Try broader search
   - If many: Help user refine

### Update Workflow
1. Find records using loose search
2. If multiple matches, show user and ask which one
3. Validate the update makes sense
4. Execute with exact field names
5. Confirm success with details

### Blocker Escalation
When a task is marked as blocked:
1. Update the task status to "Estou bloqueado"
2. Ask for or extract the reason
3. Send WhatsApp notification to Avengers group immediately
4. Confirm escalation to user

## Output Format

### For Queries
```
🎯 **Found [X] tasks matching your criteria:**

🔵 **A fazer (To Do):** [count]
• [Task Name] - [Assignee] - [Due Date if set]

🟡 **Estou trabalhando (In Progress):** [count]
• [Task Name] - [Assignee] - [Progress info]

🔴 **Estou bloqueado (Blocked):** [count]
• [Task Name] - [Reason] - ⚠️ Needs attention

📊 **Summary:** [Total] tasks ([X] to do, [Y] in progress, [Z] blocked)
```

### For Updates
```
✅ **Successfully updated: [Task/Record Name]**
Changed [field]: "[old value]" → "[new value]"
```

### For Errors
```
🔍 **Couldn't find exact matches for "[search term]"**

Let me try a broader search...
[Results from broader search]

💡 **Tip:** Try searching by first name only or check the exact spelling
```

## Examples

### Example: Finding Tasks
User: "show me Cezar's tasks"
Assistant thinking: Extract "Cezar", build loose filter
Tool call: filterByFormula = "OR(SEARCH('Cezar', {{Assigned Team Members}}), SEARCH('cezar', {{Assigned Team Members}}), SEARCH('Vasconcelos', {{Assigned Team Members}}))"

### Example: Status + Project
User: "automagik tasks that are blocked"
Assistant thinking: Project name + status combination
Tool call: filterByFormula = "AND(OR(SEARCH('Automagik', {{Related Milestones}}), SEARCH('automagik', {{Task Name}})), {{Status}} = 'Estou bloqueado')"

## Context - Live Schema
{live_schema}

## Error Recovery

If a search returns no results:
1. Remove AND conditions and try each part separately
2. Use only the first word of names
3. Try without status filters
4. Show recent records as fallback

Never give up without trying multiple approaches!

## Final Reminders
- Loose matching is a feature, not a bug - embrace it
- Always explain what you searched vs what you found
- Portuguese status values are primary, but accept English too
- When updating, double-check field names from schema
- For blocked tasks, escalate immediately via WhatsApp"""


# --------------------- Enhanced Error Handling ---------------------

async def handle_search_error(ctx: Dict[str, Any], error: Exception, 
                            original_filter: str, table_id: str, base_id: str) -> Dict[str, Any]:
    """Handle search errors with progressive recovery strategies."""
    
    logger.warning(f"Search error with filter '{original_filter}': {error}")
    
    # Strategy 1: If it's a formula error, try simpler syntax
    if "formula" in str(error).lower():
        # Remove complex AND/OR structures
        if "SEARCH(" in original_filter:
            # Extract just the search term
            import re
            match = re.search(r"SEARCH\('([^']+)'", original_filter)
            if match:
                search_term = match.group(1)
                simple_filter = f"SEARCH('{search_term}', {{Name}})"
                logger.info(f"Trying simplified filter: {simple_filter}")
                
                try:
                    result = await list_records(
                        ctx, 
                        table=table_id, 
                        base_id=base_id,
                        filterByFormula=simple_filter,
                        page_size=10
                    )
                    return {
                        "recovered": True,
                        "records": result.get("records", []),
                        "message": "Used simplified search after formula error"
                    }
                except Exception:
                    pass
    
    # Strategy 2: Fall back to unfiltered list
    logger.info("Falling back to unfiltered recent records")
    try:
        result = await list_records(
            ctx,
            table=table_id,
            base_id=base_id,
            page_size=20
        )
        return {
            "recovered": True,
            "records": result.get("records", []),
            "message": "Showing recent records (couldn't apply filter)"
        }
    except Exception as e:
        return {
            "recovered": False,
            "error": str(e),
            "message": "Unable to retrieve records"
        }


# --------------------- Agent Creation (Simplified) ---------------------

# Global agent instance
airtable_assistant: Optional[Agent] = None


async def get_airtable_assistant(base_id: Optional[str] = None, force_refresh: bool = False) -> Agent:
    """Get or create the Airtable assistant with GPT-4.1 best practices."""
    global airtable_assistant
    
    # Check if we need to rebuild
    target_base_id = base_id or settings.AIRTABLE_DEFAULT_BASE_ID
    should_rebuild = (
        force_refresh or 
        airtable_assistant is None or 
        not _is_cache_valid(target_base_id or "")
    )
    
    if should_rebuild:
        logger.info("🔄 Building Airtable assistant with GPT-4.1 optimizations...")
        dynamic_prompt = await build_dynamic_system_prompt(base_id, force_refresh)
        
        airtable_assistant = Agent(
            "openai:gpt-4.1", 
            tools=[*airtable_tools, send_message],
            system_prompt=dynamic_prompt,
            deps_type=Dict[str, Any],
            result_type=str,
            # GPT-4.1 recommended settings
            retries=2,
            result_retries=3
        )
        
        logger.info("✅ Airtable assistant ready with fresh schema")
    else:
        logger.info("♻️ Using cached Airtable assistant")
    
    return airtable_assistant


async def run_airtable_assistant(
    ctx: RunContext[Dict[str, Any]], 
    user_input: str, 
    base_id: Optional[str] = None,
    force_refresh: bool = False
) -> str:
    """Entry point for Airtable agent - keeping original simplicity."""
    try:
        assistant = await get_airtable_assistant(base_id, force_refresh)
        result = await assistant.run(user_input, deps=ctx.deps if ctx else {})
        return result.output
    except Exception as e:
        logger.error(f"Error in Airtable assistant: {e}")
        return f"""⚠️ **Something went wrong**

Error: {str(e)}

Please try:
- Rephrasing your request
- Checking if the Airtable base is accessible
- Contacting support if the issue persists"""


# --------------------- Cache Management (Original functions) -----------------------

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