---
description: Guidelines for creating and maintaining Cursor rules to ensure consistency and effectiveness.
globs: .cursor/rules/*.md
alwaysApply: true
---

# Rule Authoring Guide

## 📋 Rule Structure Template

**Reference**: [Cursor Rules Documentation](https://docs.cursor.com/context/rules)

```markdown
---
description: Clear, one-line description of what the rule enforces
globs: **/* or specific/path/*.ext
alwaysApply: true|false
---

# Rule Title

## Section Headers

- **Main Points in Bold**
  - Sub-points with details and examples
  - Code examples where appropriate

---

**Remember**: Brief closing reminder or key takeaway.
```

## 🎛️ YAML Header Fields

**Required**:
- `description`: One-line explanation of rule's purpose
- `globs`: File patterns where rule applies (`**/*` for all files)
- `alwaysApply`: Loading strategy (see below)

**Loading Strategy**:
- `alwaysApply: true` - Always loaded (mission-critical rules only)
- `alwaysApply: false` - Loaded on request or pattern match

## 📁 File References

- Use `[filename](mdc:path/to/file)` ([filename](mdc:filename)) to reference files
- Example: [01_task_system.md](mdc:.cursor/rules/01_task_system.md) for rule references
- Example: [main.py](mdc:src/main.py) for code references

## 💻 Code Examples

- Use language-specific code blocks
```python
# ✅ DO: Show good examples
class GoodPattern(AutomagikAgent):
    pass

# ❌ DON'T: Show anti-patterns  
class BadPattern:
    pass
```

```typescript
// ✅ DO: Show good examples
const goodExample = true;

// ❌ DON'T: Show anti-patterns
const badExample = false;
```

## ✍️ Content Guidelines

**Structure**:
- Start with high-level overview
- Use bullet points for clarity
- Include specific, actionable requirements
- Show examples of correct implementation
- Reference existing code when possible
- Keep rules DRY by referencing other rules

**Best Practices**:
- Keep descriptions concise
- Reference actual codebase examples
- Include both DO and DON'T patterns
- Use consistent formatting
- Cross-reference related rules

## 🔧 Rule Maintenance

**Update Rules When**:
- New patterns emerge in codebase
- Better examples become available
- Implementation details change
- Patterns become outdated
- Add examples from actual codebase
- Remove outdated patterns
- Cross-reference related rules

**Quality Checks**:
- Rules are actionable and specific
- Examples reflect actual code
- References are current
- Formatting is consistent
- Use bullet points for clarity
- Reference actual code over theoretical examples

---

**Remember**: Rules guide consistent development - keep them clear, current, and actionable. 