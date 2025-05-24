# Rule Loading Analysis & Optimization Strategy

## Current State Analysis

### ❌ **Critical Issues Discovered**

1. **Missing Frontmatter**: Most rule files lack YAML frontmatter entirely
2. **Inconsistent Loading**: No clear loading strategy for different contexts
3. **Performance Impact**: All rules likely loading always, causing cognitive overload
4. **No Conditional Loading**: Context-sensitive loading not implemented

### 📊 **Current Rule Inventory**

| Rule File | Has Frontmatter | Always Apply | Issues |
|-----------|----------------|--------------|---------|
| 00_agent_mission.mdc | ❌ NO | Should: YES | Missing entirely |
| 01_task_system.mdc | ⚠️ PARTIAL | ✅ YES | Incomplete |
| 02_agent_development.mdc | ❌ NO | Should: NO | Missing entirely |
| 03_project_setup.mdc | ? | Should: NO | Need to check |
| 04_self_improve.mdc | ? | Should: YES | Need to check |
| 05_development_guide.mdc | ? | Should: NO | Need to check |
| 06_memory_system.mdc | ? | Should: NO | Need to check |
| 07_development_workflow.mdc | ? | Should: NO | Need to check |
| 08_api_development.mdc | ⚠️ PARTIAL | Should: NO | Incomplete |
| 09_dependencies.mdc | ? | Should: NO | Need to check |
| 10_database_config.mdc | ? | Should: NO | Need to check |
| 11_quality_testing.mdc | ? | Should: NO | Need to check |
| 12_feature_development.mdc | ? | Should: NO | Need to check |
| 13_performance_optimization.mdc | ❌ NO | Should: NO | Missing entirely |
| 14_rule_organization.mdc | ❌ NO | Should: YES | Missing entirely |

## 🎯 **Optimal Loading Strategy**

### Always-Loaded Foundation (Priority 00-04)
```yaml
# These provide essential context and should ALWAYS load
alwaysApply: true
```

1. **00_agent_mission.mdc** - Core AI agent identity and mission
2. **01_task_system.mdc** - Mandatory Task Master workflow  
3. **04_self_improve.mdc** - Pattern recognition and learning
4. **14_rule_organization.mdc** - Meta rule management

### Context-Sensitive Loading (Priority 05+)
```yaml
# These load based on file patterns and context
alwaysApply: false
globs: ["specific/patterns/**"]
```

## 📁 **Optimized File Pattern Mapping**

### Agent Development Context
```yaml
globs:
  - "**/src/agents/**/*.py"
  - "**/agents/**"
  - "**/*agent*.py"
  - "**/prompts.py"
  - "**/tools.py"
```
**Triggers**: 02_agent_development.mdc, 06_memory_system.mdc

### API Development Context  
```yaml
globs:
  - "**/src/api/**/*.py"
  - "**/*router*.py"
  - "**/*endpoint*.py"
  - "**/src/main.py"
  - "**/src/auth.py"
```
**Triggers**: 08_api_development.mdc, 13_performance_optimization.mdc

### Database/Memory Context
```yaml
globs:
  - "**/src/db/**/*.py"
  - "**/src/memory/**/*.py"
  - "**/*database*.py"
  - "**/*connection*.py"
  - "**/migrations/**"
```
**Triggers**: 06_memory_system.mdc, 10_database_config.mdc

### Tool Development Context
```yaml
globs:
  - "**/src/tools/**/*.py"
  - "**/*tool*.py"
  - "**/integrations/**"
```
**Triggers**: 12_feature_development.mdc, 09_dependencies.mdc

### Testing Context
```yaml
globs:
  - "**/tests/**/*.py"
  - "**/*test*.py"
  - "**/pytest.ini"
  - "**/conftest.py"
```
**Triggers**: 11_quality_testing.mdc

### Project Setup Context
```yaml
globs:
  - "**/scripts/**"
  - "**/setup.py"
  - "**/pyproject.toml"
  - "**/requirements*.txt"
  - "**/Dockerfile"
  - "**/.env*"
```
**Triggers**: 03_project_setup.mdc, 09_dependencies.mdc

### Development Context
```yaml
globs:
  - "**/*.py"
  - "**/src/**"
  - "**/README.md"
  - "**/docs/**"
```
**Triggers**: 05_development_guide.mdc, 07_development_workflow.mdc

## 🚀 **Implementation Priority**

### Phase 1: Critical Foundation (Immediate)
1. Add frontmatter to always-loaded rules (00, 01, 04, 14)
2. Set `alwaysApply: true` for foundation rules
3. Test loading behavior

### Phase 2: Context Rules (Next)
1. Add frontmatter to conditional rules (02, 03, 05-13)
2. Define precise glob patterns for each context
3. Set `alwaysApply: false` for conditional rules

### Phase 3: Optimization (Future)
1. Implement smart loading based on current file context
2. Add dependency relationships between rules
3. Performance monitoring and tuning

## 📋 **Recommended Frontmatter Templates**

### Always-Loaded Foundation Template
```yaml
---
description: "Core context that must always be available"
globs:
  - "**/*"
alwaysApply: true
priority: 0-4
---
```

### Agent Development Template
```yaml
---
description: "Agent creation, extension, and management patterns"
globs:
  - "**/src/agents/**/*.py"
  - "**/*agent*.py"
  - "**/prompts.py"
  - "**/tools.py"
alwaysApply: false
priority: 5
---
```

### API Development Template  
```yaml
---
description: "FastAPI endpoint development and optimization"
globs:
  - "**/src/api/**/*.py"
  - "**/*router*.py"
  - "**/*endpoint*.py"
  - "**/src/main.py"
  - "**/src/auth.py"
alwaysApply: false
priority: 8
---
```

### Performance Optimization Template
```yaml
---
description: "Performance patterns and optimization techniques"
globs:
  - "**/src/**/*.py"
  - "**/src/ai/**"
  - "**/src/memory/**"
  - "**/src/api/**"
alwaysApply: false
priority: 13
---
```

## 💡 **Smart Loading Algorithm**

```python
def determine_rules_to_load(current_file: str, project_context: dict) -> List[str]:
    """Determine which rules to load based on context."""
    
    # Always load foundation rules
    rules = [
        "00_agent_mission.mdc",
        "01_task_system.mdc", 
        "04_self_improve.mdc",
        "14_rule_organization.mdc"
    ]
    
    # Context-sensitive loading
    if matches_pattern(current_file, "**/src/agents/**"):
        rules.extend([
            "02_agent_development.mdc",
            "06_memory_system.mdc"
        ])
    
    if matches_pattern(current_file, "**/src/api/**"):
        rules.extend([
            "08_api_development.mdc",
            "13_performance_optimization.mdc"
        ])
    
    if matches_pattern(current_file, "**/tests/**"):
        rules.append("11_quality_testing.mdc")
    
    if project_context.get("task") == "feature_development":
        rules.append("12_feature_development.mdc")
    
    return rules
```

## 📈 **Expected Performance Improvements**

### Before Optimization
- **All rules loaded**: ~15 files, ~500KB content
- **Cognitive load**: High - irrelevant context always present
- **Loading time**: Slow - all rules parsed every time

### After Optimization  
- **Foundation rules**: 4 files, ~50KB core context
- **Context rules**: 2-4 additional files as needed, ~100-200KB
- **Cognitive load**: Low - only relevant context
- **Loading time**: Fast - intelligent caching and filtering

## ✅ **Next Steps**

1. **Immediate**: Add frontmatter to all rule files
2. **Short-term**: Implement context-sensitive loading
3. **Medium-term**: Add rule dependency management
4. **Long-term**: Performance monitoring and auto-tuning

This analysis provides the foundation for implementing intelligent rule loading that reduces cognitive overhead while ensuring relevant context is always available. 