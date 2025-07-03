from fastapi import APIRouter
from .user_routes import user_router
from .session_routes import session_router
from .agent_routes import agent_router
from .message_routes import message_router
from .prompt_routes import prompt_router
from .mcp_routes import router as mcp_router
from .tool_routes import tool_router
from .claude_code_routes import claude_code_router
from .analytics_routes import router as analytics_router
from .model_routes import router as model_router
from automagik.api.memory_routes import memory_router

# Create main router
main_router = APIRouter()

# Include all sub-routers
# The order no longer matters since paths don't conflict
main_router.include_router(claude_code_router)
main_router.include_router(agent_router)
main_router.include_router(prompt_router)
main_router.include_router(session_router)
main_router.include_router(user_router)
main_router.include_router(memory_router)
main_router.include_router(message_router)
main_router.include_router(mcp_router)
main_router.include_router(tool_router)
main_router.include_router(analytics_router)
main_router.include_router(model_router, tags=["models"])
