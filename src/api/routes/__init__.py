from fastapi import APIRouter
from .user_routes import user_router
from .session_routes import session_router
from .agent_routes import agent_router
from .message_routes import message_router
from .prompt_routes import prompt_router
from .mcp_routes import router as mcp_router
from .claude_code_routes import claude_code_router
from .claude_code_websocket import ws_router as claude_code_ws_router
from .genie_routes import router as genie_router
from src.api.memory_routes import memory_router

# Create main router
main_router = APIRouter()

# Include all sub-routers
main_router.include_router(agent_router)
main_router.include_router(claude_code_router)
main_router.include_router(claude_code_ws_router)
main_router.include_router(genie_router, prefix="/agent/genie", tags=["genie"])
main_router.include_router(prompt_router)
main_router.include_router(session_router)
main_router.include_router(user_router)
main_router.include_router(memory_router)
main_router.include_router(message_router)
main_router.include_router(mcp_router)