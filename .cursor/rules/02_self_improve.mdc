---
description: Rule improvement triggers, pattern recognition, and quality checklist for automagik-agents development
globs: 
alwaysApply: true
---
# Self-Improvement Rules

## 🎯 Rule Evolution Philosophy

**Related**: [cursor_rules.md](mdc:.cursor/rules/cursor_rules.md) - Rule formatting guidelines

Rules evolve based on real development experience, captured patterns, and memory insights creating feedback loops for improved efficiency.

## 🚨 Rule Improvement Triggers

### **Pattern Recognition Signals**
- **New code patterns** not covered (3+ files using same pattern)
- **Repeated implementations** across components
- **Common error patterns** preventable with rules
- **New libraries/tools** used consistently
- **Memory node patterns** revealing preferences/procedures
- **Linear issue patterns** showing recurring challenges

### **Memory-Driven Insights**
```bash
# Search for improvement opportunities
agent-memory_search_memory_nodes --query "pattern implementation workflow" --entity "Procedure"
agent-memory_search_memory_nodes --query "preference coding style" --entity "Preference"
agent-memory_search_memory_facts --query "error caused by solution prevented"
```

### **Linear Analysis**
- **Subtask failure patterns**: Common implementation sticking points
- **Successful sequences**: Consistently working patterns
- **Dependency issues**: Recurring management problems

## 🔍 Enhanced Pattern Recognition

### **AutomagikAgent Patterns**
```python
# Repeated pattern:
class MyAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)
        self._code_prompt_text = AGENT_PROMPT  # Pattern
        self.dependencies = AutomagikAgentsDependencies(...)
        self.tool_registry.register_default_tools(self.context)
```

### **API Endpoint Patterns**
```python
# Repeated pattern:
@router.post("/action", response_model=ActionResponse)
async def perform_action(request: ActionRequest, api_key: str = Depends(verify_api_key)):
    try:
        result = await process_action(request)
        return ActionResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### **Memory Template Patterns**
```python
# Repeated pattern:
SYSTEM_PROMPT = """You are an agent.
User: {{user_name}} | Context: {{recent_context}}
Preferences: {{user_preferences}}"""
```

## 📊 Analysis Process

### **1. Pattern Detection**
- **Search memory for procedures**: Established workflows to document
- **Search for preferences**: User/team coding preferences
- **Identify relationships**: Component dependencies via facts
- **Cross-reference Linear**: Issue comments for lessons learned

### **2. Memory Integration Analysis**
```bash
# Find optimization patterns
agent-memory_search_memory_facts --query "optimization improved performance"

# Find error solutions
agent-memory_search_memory_nodes --query "error solution workaround" --entity "Procedure"

# Find preferences
agent-memory_search_memory_nodes --query "prefers style approach" --entity "Preference"
```

### **3. Code Pattern Analysis**
- **Agent Patterns**: AutomagikAgent extension approaches
- **Tool Patterns**: Tool implementation structures
- **API Patterns**: FastAPI endpoint designs
- **Memory Patterns**: Template variable usage
- **Testing Patterns**: Test structure and coverage

## 🎯 Quality Checklist

### **Rule Content Standards**
- [ ] **Rules are actionable** with clear implementation steps
- [ ] **Examples from actual code** in automagik-agents project
- [ ] **References up to date** and accessible
- [ ] **Patterns consistently enforced** across codebase
- [ ] **Cross-references** to related rules included
- [ ] **Memory searches** confirm recurring patterns
- [ ] **Both positive/negative examples** (✅ DO / ❌ DON'T)

### **Rule Update Criteria**
**Add New Rules When:**
- Technology/pattern used in 3+ files
- Common bugs preventable by rule
- Code reviews mention same feedback repeatedly
- Memory reveals repeated procedures/preferences

**Modify Existing Rules When:**
- Better examples exist in codebase
- Edge cases discovered
- Implementation details changed
- Memory analysis reveals better approaches

## 🔄 Continuous Improvement Process

### **Weekly Rule Review**
1. **Search memory nodes**: 
   ```bash
   agent-memory_search_memory_nodes --query "pattern discovered implementation" --max_nodes 20
   agent-memory_search_memory_facts --query "caused by prevented solved"
   ```
2. **Analyze Linear**: `linear_list_issues --limit 50`
3. **Review code changes** for new patterns
4. **Update rules** based on findings
5. **Record changes** in memory

### **Monthly Pattern Analysis**
1. **Comprehensive memory search** for accumulated patterns
2. **Cross-reference** with existing rules for gaps
3. **Identify deprecated patterns** for removal
4. **Update priorities** based on usage frequency

## 🧠 Memory Integration

### **Record Rule Changes**
```bash
# After updating rules
agent-memory_add_memory \
  --name "Rule Update: Agent Pattern" \
  --episode_body "Updated agent rules with new AutomagikAgent extension pattern including tool registration sequence" \
  --source "text" \
  --source_description "Rule improvement documentation"

# Record discoveries
agent-memory_add_memory \
  --name "API Pattern Discovery" \
  --episode_body "{\"pattern\": \"API authentication\", \"usage_count\": 4, \"files\": [\"auth.py\", \"middleware.py\"]}" \
  --source "json" \
  --source_description "Pattern analysis results"
```

### **Search for Rule Gaps**
```bash
# Find missing documentation
agent-memory_search_memory_nodes --query "missing unclear confusing documentation"

# Find repeated questions
agent-memory_search_memory_facts --query "asked about repeatedly"
```

### **Track Effectiveness**
```bash
# Search for positive feedback
agent-memory_search_memory_nodes --query "helped solved clear pattern" --entity "Preference"

# Find successful procedures
agent-memory_search_memory_nodes --query "procedure worked successfully" --entity "Procedure"
```

## 📊 Success Metrics

### **Health Indicators**
- **Reduced repeated questions** in memory searches
- **More procedures documented** as memory nodes
- **Preferences captured** and respected
- **Fewer errors** in Linear issue implementations
- **More consistent code** across project

### **Quantitative Metrics**
- **Pattern consistency rate**: % following established patterns
- **Rule coverage**: Recurring patterns documented
- **Memory utilization**: Procedures/preferences stored
- **Task completion speed**: Faster subtask completion

## 🔄 Implementation Workflow

### **Task Completion Workflow**
**Before completing any major work:**
1. **Search memory for patterns**: 
   ```bash
   agent-memory_search_memory_nodes --query "pattern procedure workflow"
   ```
2. **Check Linear status**: `linear_list_issues --limit 20`
3. **Close completed tasks**: Update status to "Done" for finished work
4. **Cancel redundant tasks**: Mark as "Canceled" with explanation comment
5. **Store new patterns** in memory

### **Discovering New Patterns**
1. **Document in memory immediately**:
   ```bash
   agent-memory_add_memory --name "New Pattern: [Name]" --episode_body "description" --source "text"
   ```
2. **Check 3+ instances** exist in codebase
3. **Search existing rules** for gaps
4. **Create/update rules** with real examples
5. **Cross-reference** related rules
6. **Record as procedure** if it's a workflow

### **Updating Existing Rules**
1. **Search memory** for better examples:
   ```bash
   agent-memory_search_memory_nodes --query "pattern example implementation"
   ```
2. **Review codebase** for pattern evolution
3. **Update examples** with current code
4. **Verify cross-references** still valid
5. **Document changes** in memory

## 📝 Rule Lifecycle Management

### **Rule Creation from Memory**
```bash
# When memory reveals repeated procedure
agent-memory_search_memory_nodes --query "procedure deploy test" --entity "Procedure"
# If found 3+ times -> Create rule

# When preferences emerge
agent-memory_search_memory_nodes --query "prefers style format" --entity "Preference"  
# If consistent -> Document in rules
```

### **Rule Deprecation Process**
- **Search for usage**: Check if pattern still used
- **Mark outdated patterns** with migration paths
- **Remove inapplicable rules**
- **Update references** in other rules
- **Document breaking changes** in memory

---

**Remember**: Rules are living documents evolving with codebase. Use memory searches and Linear analysis for improvement opportunities. Base updates on real development patterns. The knowledge graph is your source of truth for preferences and procedures.
