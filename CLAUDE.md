# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automagik Agents is a production-ready AI agent framework built on Pydantic AI by Namastex Labs that provides:
- 🤖 Extensible agent system with template-based creation
- 💾 Persistent memory with PostgreSQL and optional Neo4j/Graphiti knowledge graphs
- 🔧 Production-ready FastAPI with authentication and health monitoring
- 🔗 Multi-LLM support (OpenAI, Gemini, Claude, Groq)
- 📦 Zero-config deployment via Docker or systemd
- 🛠️ Comprehensive CLI for agent management and interaction
- 🔌 MCP (Model Context Protocol) integration for tool discovery

## 🎯 Core Development Principles

### Primary Objectives
- Develop, maintain, and extend automagik-agents framework following established patterns
- Always **EXTEND** `AutomagikAgent`, never modify base classes
- Follow patterns from existing agents in `src/agents/simple/`
- Use provided tools/infrastructure vs reinventing

### Critical Procedures

#### 1. **ALWAYS Search Memory First**
Before starting any task, search for established patterns and preferences:
```bash
# Search for task-specific patterns and preferences
agent-memory_search_memory_nodes --query "task keywords" --entity "Procedure"
agent-memory_search_memory_nodes --query "preferences" --entity "Preference"
agent-memory_search_memory_facts --query "dependencies relationships"
```

#### 2. **Use Linear for Task Management** 
Create Linear tasks for all development work and use Linear IDs in branch names and commits.

#### 3. **Store Successful Patterns**
After implementing solutions, store them in memory for future reuse:
```bash
agent-memory_add_memory --name "Pattern: [Name]" --episode_body "pattern details" --source "text"
```

## Memories

- **learn from your memory add mistake**: Always verify and validate memory entries to prevent errors in documentation and knowledge storage.

## Quick Start

[Rest of the document remains the same as in the previous version]