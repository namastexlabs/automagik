from fastapi import APIRouter
from .user_routes import user_router
from .session_routes import session_router
from .agent_routes import agent_router
from .message_routes import message_router
from src.api.memory_routes import memory_router

# Create main router
main_router = APIRouter()

# Include all sub-routers
main_router.include_router(agent_router)
main_router.include_router(session_router)
main_router.include_router(user_router)
main_router.include_router(memory_router)
main_router.include_router(message_router) 