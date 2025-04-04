# Task: Database and API Enhancements
**Status**: In Progress
**Priority**: High

## Analysis
- [x] Requirements
  - [x] Change User.id from integer to UUID
  - [x] Add auto-user creation to agent run API
  - [x] Add system_prompt override option to agent run API
- [x] Challenges
  - [x] Database migration needed for User.id type change
  - [x] Maintain backward compatibility
  - [x] Handle UUID conversion throughout codebase
- [x] Dependencies
  - User model in `src/db/models.py`
  - Database functions in `src/db/repository/user.py`
  - API routes in `src/api/routes/agent_routes.py`
  - API controllers in `src/api/controllers/agent_controller.py`
  - Agent run request model in `src/api/models.py`

## Plan
- [x] Step 1: Change User.id from integer to UUID
  - [x] Create database migration for User.id type change
    - [x] Create a new migration file in `src/db/migrations/`
    - [x] Write migration SQL to alter User.id column
  - [x] Update User model in `src/db/models.py`
    - [x] Change id field from Optional[int] to Optional[uuid.UUID]
  - [x] Modify user repository functions in `src/db/repository/user.py`
    - [x] Update get_user(), create_user(), update_user() functions
    - [x] Handle UUID conversion in queries
  - [x] Update references to User.id across codebase
    - [x] Search for functions taking user_id as integer and update

- [x] Step 2: Add auto-user creation to agent run API
  - [x] Modify agent controller in `src/api/controllers/agent_controller.py`
    - [x] Add function to get or create user by ID
    - [x] Update handle_agent_run() to create user if not exists
  - [x] Enhance AgentRunRequest model in `src/api/models.py`
    - [x] Add user field for passing user data (email, phone, user_data)

- [x] Step 3: Add system_prompt override to agent run API
  - [x] Update AgentRunRequest model in `src/api/models.py`
    - [x] Add system_prompt field (Optional[str])
  - [x] Modify agent controller in `src/api/controllers/agent_controller.py`
    - [x] Pass system_prompt to agent.process_message()
  - [x] Update AutomagikAgent.process_message() to handle prompt override

## Execution
- [x] Implementation 1: Database Migration
  - [x] Create UUID extension if not exists
  - [x] Add temporary column for UUID migration
  - [x] Convert existing IDs to UUIDs
  - [x] Update foreign key references
  - [x] Drop old column and rename new one

- [x] Implementation 2: User Model Updates
  - [x] Update User model with UUID field
  - [x] Modify repository functions
  - [x] Update references to user_id across codebase

- [x] Implementation 3: API Enhancements
  - [x] Add user creation functionality to agent run endpoint
  - [x] Implement system_prompt override

## Summary
- [x] Files modified:
  - [x] src/db/models.py (User model)
  - [x] src/db/repository/user.py (User repository functions)
  - [x] src/api/models.py (AgentRunRequest model)
  - [x] src/api/controllers/agent_controller.py (agent_run handling)
  - [x] src/agents/models/automagik_agent.py (system_prompt handling)
  - [x] src/agents/common/session_manager.py (UUID handling)
- [x] New files created:
  - [x] src/db/migrations/20250404_195012_change_user_id_to_uuid.sql
- [x] Dependencies affected:
  - [x] All code paths that reference user_id
  - [x] Agent run API functionality
  - [x] User creation and lookup
- [x] Edge cases considered:
  - [x] Existing records with integer IDs
  - [x] API clients expecting integer user IDs
  - [x] Backward compatibility during transition 