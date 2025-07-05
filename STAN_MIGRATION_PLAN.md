# Stan Agents Migration Plan

## Overview
Migrate Stan agents from core framework to external agent pattern, removing client-specific dependencies.

## Current State
- Stan agents live in `/automagik/agents/pydanticai/stan/` and `/automagik/agents/pydanticai/stan_email/`
- BlackPearl integration hardcoded in core
- Client-specific env vars in `.env.example` and `config.py`
- Tools scattered across core framework

## Target State
- Stan agents in isolated `stan_agents/` directory
- Works as external agent via `AUTOMAGIK_EXTERNAL_AGENTS_DIR`
- All client-specific code/config removed from core
- Self-contained with own tools and utils

## Migration Steps

### Phase 1: Prepare Directory Structure
```bash
stan_agents/
├── README.md
├── .env.example          # Stan-specific env vars
├── requirements.txt      # Stan-specific dependencies
├── __init__.py
├── base_stan_agent.py    # Base class for Stan agents
├── stan/
│   ├── __init__.py
│   ├── agent.py
│   ├── prompts/
│   │   ├── approved.py
│   │   ├── not_registered.py
│   │   ├── pending_review.py
│   │   └── rejected.py
│   └── specialized/
│       ├── backoffice.py
│       ├── order.py
│       └── product.py
├── stan_email/
│   ├── __init__.py
│   ├── agent.py
│   ├── prompts/
│   │   └── prompt.py
│   └── specialized/
│       └── approval_status_message_generator.py
├── tools/
│   ├── __init__.py
│   ├── blackpearl/
│   │   ├── __init__.py
│   │   ├── provider.py
│   │   ├── interface.py
│   │   ├── tool.py
│   │   └── schema.py
│   └── gmail/
│       ├── __init__.py
│       └── tool.py
└── utils/
    ├── __init__.py
    ├── contact_manager.py
    └── prompt_loader.py
```

### Phase 2: Remove from Core Framework

1. **Environment Variables to Remove:**
   - From `.env.example`:
     ```
     BLACKPEARL_TOKEN
     BLACKPEARL_API_URL
     BLACKPEARL_DB_URI
     DISCORD_BOT_TOKEN
     AIRTABLE_TOKEN
     AIRTABLE_DEFAULT_BASE_ID
     AIRTABLE_TEST_BASE_ID
     AIRTABLE_TEST_TABLE
     MEETING_BOT_URL
     NOTION_TOKEN
     ```

2. **Config.py Changes:**
   - Remove BlackPearl fields
   - Remove Discord fields
   - Remove Airtable fields
   - Remove Meeting Bot fields
   - Remove Notion fields

3. **Files to Move:**
   - `/automagik/agents/pydanticai/stan/` → `/stan_agents/stan/`
   - `/automagik/agents/pydanticai/stan_email/` → `/stan_agents/stan_email/`
   - `/automagik/tools/blackpearl/` → `/stan_agents/tools/blackpearl/`
   - Any Gmail tools used by Stan → `/stan_agents/tools/gmail/`

### Phase 3: Update Code

1. **Create BaseStanAgent:**
   ```python
   from agents_examples.base_external_agent import BaseExternalAgent
   
   class BaseStanAgent(BaseExternalAgent):
       EXTERNAL_API_KEYS = [
           ("BLACKPEARL_TOKEN", "BlackPearl API token"),
           ("GMAIL_APP_PASSWORD", "Gmail app password"),
       ]
       EXTERNAL_URLS = [
           ("BLACKPEARL_API_URL", "BlackPearl API URL"),
       ]
   ```

2. **Update Imports:**
   - Change absolute imports to relative
   - Update tool imports to use local tools directory
   - Fix prompt loading to use local prompts

3. **Update Agent Classes:**
   - Extend BaseStanAgent instead of AutomagikAgent
   - Remove core framework dependencies
   - Use self-contained utilities

### Phase 4: Create Stan-specific Files

1. **stan_agents/.env.example:**
   ```env
   # Stan Agent Configuration
   BLACKPEARL_TOKEN=
   BLACKPEARL_API_URL=https://blackpearl.talbitz.com
   BLACKPEARL_DB_URI=
   
   # Gmail Configuration (for lead emails)
   GMAIL_SENDER_EMAIL=
   GMAIL_APP_PASSWORD=
   
   # Evolution API (WhatsApp)
   EVOLUTION_API_URL=
   EVOLUTION_API_TOKEN=
   ```

2. **stan_agents/requirements.txt:**
   ```
   # Stan-specific dependencies
   httpx>=0.24.0
   # Any other Stan-specific packages
   ```

3. **stan_agents/README.md:**
   - Installation instructions
   - Configuration guide
   - Usage examples
   - BlackPearl integration docs

### Phase 5: Testing & Validation

1. **Test External Loading:**
   ```bash
   export AUTOMAGIK_EXTERNAL_AGENTS_DIR=./stan_agents
   automagik api start
   # Verify Stan agents appear in agent list
   ```

2. **Test Functionality:**
   - WhatsApp message handling
   - BlackPearl contact creation
   - Status-based prompt loading
   - Email generation

3. **Test Isolation:**
   - Core framework starts without Stan env vars
   - Stan agents fail gracefully if BlackPearl unavailable

### Phase 6: Documentation

1. **Update Core Docs:**
   - Remove Stan references from main README
   - Update agent list documentation
   - Add external agent examples

2. **Create Stan Docs:**
   - Complete setup guide
   - BlackPearl integration guide
   - WhatsApp/Evolution setup
   - Troubleshooting guide

## Success Criteria

✅ Stan agents work as external agents
✅ No client-specific code in core framework
✅ Clean separation of concerns
✅ Easy to distribute Stan agents separately
✅ Core framework works without Stan dependencies

## Timeline

- Phase 1-2: 2 hours (directory setup, file moves)
- Phase 3-4: 3 hours (code updates, configuration)
- Phase 5: 2 hours (testing, validation)
- Phase 6: 1 hour (documentation)

**Total: ~8 hours**

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing Stan deployments | High | Provide migration guide |
| Missing dependencies | Medium | Thorough testing |
| Tool discovery issues | Low | Use same pattern as Flashinho |