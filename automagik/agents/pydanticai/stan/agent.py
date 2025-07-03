"""Stan Agent implementation with framework-agnostic architecture.

This module provides a Stan Agent class that uses the new AutomagikAgent framework
for AI backend abstraction and channel handling.
"""
import logging
import traceback
import glob
import os
from typing import Dict, Optional, Any

from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.models.response import AgentResponse
from .specialized.backoffice import backoffice_agent
from .specialized.product import product_agent
from automagik.db.models import Memory
from automagik.db.repository import create_memory
from automagik.db.repository.user import update_user_data
from automagik.memory.message_history import MessageHistory

from automagik.tools import blackpearl
from automagik.tools.blackpearl.tool import get_or_create_contact
from automagik.tools.blackpearl.schema import StatusAprovacaoEnum
from automagik.tools.blackpearl import verificar_cnpj
from automagik.config import settings

logger = logging.getLogger(__name__)

class StanAgent(AutomagikAgent):
    """Stan Agent implementation using framework-agnostic architecture.
    
    This agent provides specialized functionality for customer management
    with multi-state prompts based on approval status and BlackPearl integration.
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize the Stan Agent.
        
        Args:
            config: Dictionary with configuration options
        """
        # Initialize with framework type (defaults to pydanticai)
        super().__init__(config, framework_type="pydanticai")
        
        # Flag to track if we've registered the prompts yet
        self._prompts_registered = False
        
        # Set default prompt to NOT_REGISTERED
        try:
            from .prompts.not_registered import PROMPT
            self._code_prompt_text = PROMPT
        except ImportError:
            logger.warning("Could not load NOT_REGISTERED prompt in constructor")
        
        # Configure dependencies using the convenience method
        self.dependencies = self.create_default_dependencies()
        
        # Set agent_id if available
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        
        # Register default tools (handled automatically by AutomagikAgent)
        self.tool_registry.register_default_tools(self.context)
        
        # Register multimodal analysis tools
        self._register_multimodal_tools()
        
        # Register Stan-specific tools
        self._register_stan_tools()
        
        # Initialize the framework with dependencies
        # This is required for the AI framework to be ready
        try:
            # The framework initialization will be done asynchronously when needed
            # But we need to ensure the dependencies are properly set
            pass
        except Exception as e:
            logger.error(f"Error setting up Stan agent framework preparation: {e}")
        
        logger.info("Stan Agent initialized successfully")

    async def initialize_prompts(self) -> bool:
        """Initialize agent prompts during server startup.
        
        This method registers code-defined prompts for the agent during server startup.
        For StanAgent, we have a custom implementation that loads multiple prompts
        from files.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use our custom method to register all prompts
            await self._register_all_prompts()
            return True
        except Exception as e:
            logger.error(f"Error in StanAgent.initialize_prompts: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Try to fall back to the base implementation
            logger.info("Falling back to base class prompt initialization")
            try:
                # Set a default prompt text if needed
                if not hasattr(self, '_code_prompt_text') or not self._code_prompt_text:
                    # Try to load the NOT_REGISTERED prompt
                    try:
                        from .prompts.not_registered import PROMPT
                        self._code_prompt_text = PROMPT
                    except ImportError:
                        # If that fails, try to load the primary prompt.py
                        try:
                            from .prompts.prompt import AGENT_PROMPT
                            self._code_prompt_text = AGENT_PROMPT
                        except ImportError:
                            logger.error("Failed to load any prompt for StanAgent")
                
                # Call the base implementation
                return await super().initialize_prompts()
            except Exception as e2:
                logger.error(f"Error in base initialize_prompts: {str(e2)}")
                logger.error(traceback.format_exc())
                return False
            
    async def _register_all_prompts(self) -> None:
        """Register all prompts from the prompts directory.
        
        This will load all the prompt files in the prompts directory and register them with
        the appropriate status keys based on the filename.
        """
        if self._prompts_registered:
            return
            
        # Find all prompt files in the prompts directory
        prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
        prompt_files = glob.glob(os.path.join(prompts_dir, "*.py"))
        
        # Keep track of the primary default prompt ID
        primary_default_prompt_id = None
        not_registered_prompt_id = None
        
        for prompt_file in prompt_files:
            filename = os.path.basename(prompt_file)
            status_key = os.path.splitext(filename)[0].upper()  # Use filename without extension as status key, uppercase
            
            # Skip __init__.py or any other non-prompt files
            if status_key.startswith("__") or status_key == "PROMPT":
                continue
                
            # Dynamically import the prompt
            module_name = f".prompts.{status_key.lower()}"
            try:
                from importlib import import_module
                module = import_module(module_name, package=__package__)
                prompt_text = getattr(module, "PROMPT")
                
                # Register this prompt with the appropriate status key
                # If this is the NOT_REGISTERED status, mark it for special handling
                is_primary_default = (status_key == "NOT_REGISTERED")
                
                # Note: We don't overwrite _code_prompt_text here as it should remain NOT_REGISTERED
                
                # Register with the shared method
                prompt_id = await self._register_code_defined_prompt(
                    prompt_text,
                    status_key=status_key,
                    prompt_name=f"StanAgent {status_key} Prompt",
                    is_primary_default=is_primary_default
                )
                
                # Keep track of the NOT_REGISTERED prompt ID for later use
                if status_key == "NOT_REGISTERED" and prompt_id:
                    not_registered_prompt_id = prompt_id
                    
                # If this is actually a "default" status prompt, set it as the primary default
                if status_key == "DEFAULT" and prompt_id:
                    primary_default_prompt_id = prompt_id
                
                logger.info(f"Registered prompt for status key: {status_key} with ID: {prompt_id}")
                
            except (ImportError, AttributeError) as e:
                logger.error(f"Failed to import prompt from {module_name}: {str(e)}")
        
        # Create a "default" status prompt that points to NOT_REGISTERED if it doesn't exist
        # This ensures that the active_default_prompt_id is properly set
        if not primary_default_prompt_id and not_registered_prompt_id and self.db_id:
            try:
                # First, check if a default prompt already exists
                from automagik.db.repository.prompt import get_prompts_by_agent_id, get_prompt_by_id, create_prompt, set_prompt_active
                
                default_prompts = get_prompts_by_agent_id(self.db_id, status_key="default")
                
                if not default_prompts:
                    # Get the NOT_REGISTERED prompt to use its text
                    not_registered_prompt = get_prompt_by_id(not_registered_prompt_id)
                    
                    if not_registered_prompt:
                        # Create a new prompt with status_key="default" using the NOT_REGISTERED prompt text
                        from automagik.db.models import PromptCreate
                        
                        # Create the default prompt
                        default_prompt_data = PromptCreate(
                            agent_id=self.db_id,
                            prompt_text=not_registered_prompt.prompt_text,
                            version=1,
                            is_active=True,  # Make it active
                            is_default_from_code=True,
                            status_key="default",
                            name="StanAgent Default Prompt (maps to NOT_REGISTERED)"
                        )
                        
                        # Create the prompt
                        default_prompt_id = create_prompt(default_prompt_data)
                        logger.info(f"Created default status prompt with ID {default_prompt_id} that maps to NOT_REGISTERED")
                    else:
                        logger.error(f"Could not find NOT_REGISTERED prompt with ID {not_registered_prompt_id}")
                else:
                    # Use the first default prompt
                    default_prompt_id = default_prompts[0].id
                    # Make sure it's active
                    set_prompt_active(default_prompt_id, True)
                    logger.info(f"Set existing default prompt {default_prompt_id} as active")
                
                # Explicitly update the agents table to ensure the active_default_prompt_id is set
                # This is a backup in case the normal flow in set_prompt_active didn't work
                if default_prompt_id or not_registered_prompt_id:
                    prompt_id_to_use = default_prompt_id or not_registered_prompt_id
                    
                    # Update the agent record using repository method
                    from automagik.db.repository.agent import update_agent_active_prompt_id
                    success = update_agent_active_prompt_id(self.db_id, prompt_id_to_use)
                    if success:
                        logger.info(f"Successfully updated agent {self.db_id} with active_default_prompt_id {prompt_id_to_use}")
                    else:
                        logger.error(f"Failed to update agent {self.db_id} with active_default_prompt_id {prompt_id_to_use}")
            except Exception as e:
                logger.error(f"Error setting up default prompt: {str(e)}")
                logger.error(traceback.format_exc())
                
        self._prompts_registered = True
        logger.info("All prompts registered successfully")

    async def _use_prompt_based_on_contact_status(self, status: StatusAprovacaoEnum, contact_id: str) -> bool:
        """Updates the current prompt template based on the contact's approval status.
        
        Args:
            status: The approval status
            contact_id: The contact ID
            
        Returns:
            True if the prompt was loaded successfully, False otherwise
        """
        logger.info(f"Loading prompt for contact {contact_id} with status {status}")
        logger.debug(f"🔍 _use_prompt_based_on_contact_status called with status={status}, contact_id={contact_id}")
        logger.debug(f"🔍 Status type: {type(status)}")
        
        # Convert the status enum to a string to use as the status_key
        status_key = str(status)
        logger.debug(f"🔍 Converted status to string: '{status_key}'")
        
        # Load the appropriate prompt template
        logger.debug(f"🔍 Attempting to load prompt with status_key: '{status_key}'")
        result = await self.load_active_prompt_template(status_key=status_key)
        logger.debug(f"🔍 Prompt load result for '{status_key}': {result}")
        
        if not result:
            # If no prompt for this status, try the default (NOT_REGISTERED)
            logger.warning(f"No prompt found for status {status_key}, falling back to NOT_REGISTERED")
            logger.debug("🔍 Attempting fallback to NOT_REGISTERED prompt")
            result = await self.load_active_prompt_template(status_key="NOT_REGISTERED")
            logger.debug(f"🔍 Fallback prompt load result: {result}")
            
            if not result:
                logger.error(f"Failed to load any prompt for contact {contact_id}")
                logger.debug("🔍 Both primary and fallback prompt loading failed")
                return False
                
        logger.debug(f"🔍 Successfully loaded prompt for status '{status_key}'")
        return True


    def _register_stan_tools(self):
        """Register Stan-specific tools with the agent."""
        
        # Register verificar_cnpj tool
        async def verificar_cnpj_tool(ctx, cnpj: str) -> Dict[str, Any]:
            """Verify a CNPJ in the Blackpearl API.
            
            Args:
                ctx: The run context with dependencies
                cnpj: The CNPJ number to verify (format: xx.xxx.xxx/xxxx-xx or clean numbers)
                
            Returns:
                CNPJ verification result containing validation status and company information if valid
            """
            return await verificar_cnpj(self.context, cnpj)
        
        # Register product agent tool
        async def product_agent_tool(ctx, input_text: str) -> str:
            """Specialized product agent with expertise in product information and catalog management.
            
            Args:
                ctx: The run context with dependencies
                input_text: The user's text query about products
            
            Returns:
                Response from the product agent
            """
            # Ensure evolution_payload is available in context
            if hasattr(ctx, 'deps') and ctx.deps:
                ctx.deps.set_context(self.context)
            return await product_agent(ctx, input_text)
        
        # Register backoffice agent tool
        async def backoffice_agent_tool(ctx, input_text: str) -> str:
            """Specialized backoffice agent with access to BlackPearl and Omie tools.
            
            Args:
                ctx: The run context with dependencies
                input_text: The user's text query about backoffice operations
            
            Returns:
                Response from the backoffice agent
            """
            if hasattr(ctx, 'deps') and ctx.deps:
                ctx.deps.set_context(self.context)
            return await backoffice_agent(ctx, input_text)
        
        # Register tools with the registry
        self.tool_registry.register_tool(verificar_cnpj_tool)
        self.tool_registry.register_tool(product_agent_tool)
        self.tool_registry.register_tool(backoffice_agent_tool)
        
        logger.info("Registered Stan-specific tools")




    async def run(self, input_text: str, *, multimodal_content=None, system_message=None, message_history_obj: Optional[MessageHistory] = None,
                 channel_payload: Optional[dict] = None,
                 message_limit: Optional[int] = 20) -> AgentResponse:
        """Stan agent run implementation using the new framework.
        
        This method now leverages the AutomagikAgent framework to handle:
        - Evolution payload processing
        - Prompt registration and loading
        - Memory initialization
        - BlackPearl contact management
        - Framework execution
        """
        
        logger.debug(f"🔍 Stan.run() started with input: '{input_text[:50]}...'")
        logger.debug(f"🔍 Stan.run() channel_payload present: {channel_payload is not None}")
        if channel_payload:
            logger.debug(f"🔍 Stan.run() channel_payload keys: {list(channel_payload.keys())}")
        
        # Extract user_id from context for BlackPearl operations
        user_id = self.context.get("user_id")
        logger.info(f"Context User ID: {user_id}")
        logger.debug(f"🔍 Stan.run() initial context keys: {list(self.context.keys())}")
        
        # Register prompts if not already done
        if not self._prompts_registered and self.db_id:
            logger.debug(f"🔍 Stan.run() registering prompts for agent {self.db_id}")
            await self._register_all_prompts()
        
        # Process channel payload first to populate context with user information
        if channel_payload:
            logger.debug("🔍 Stan.run() processing channel payload...")
            await self._process_channel_payload(channel_payload)
            logger.debug(f"🔍 Stan.run() context after payload processing: {list(self.context.keys())}")
            logger.debug(f"🔍 Stan.run() WhatsApp user number: {self.context.get('whatsapp_user_number')}")
            logger.debug(f"🔍 Stan.run() WhatsApp user name: {self.context.get('whatsapp_user_name')}")
        
        # Identify or create user if needed
        final_user_id = await self._identify_or_create_user(channel_payload, user_id)
        if final_user_id:
            self.context["user_id"] = final_user_id
        
        # Handle BlackPearl contact management after user identification
        logger.debug("🔍 Stan.run() starting BlackPearl contact management...")
        await self._handle_blackpearl_contact_management(channel_payload, final_user_id)
        
        # Use the framework to handle the execution
        logger.debug("🔍 Stan.run() executing framework run...")
        return await self._run_agent(
            input_text=input_text,
            system_prompt=system_message,
            message_history=message_history_obj.get_formatted_pydantic_messages(limit=message_limit) if message_history_obj else [],
            multimodal_content=multimodal_content,
            channel_payload=channel_payload,
            message_limit=message_limit
        )
    
    async def _handle_blackpearl_contact_management(self, channel_payload: Optional[dict], user_id: Optional[str]) -> None:
        """Handle BlackPearl contact management and prompt selection.
        
        This method manages the Stan-specific BlackPearl contact lookup and 
        approval status-based prompt selection.
        """
        logger.debug("🔍 BlackPearl contact management started")
        logger.debug(f"🔍 channel_payload present: {channel_payload is not None}")
        logger.debug(f"🔍 user_id: {user_id}")
        
        if not channel_payload:
            logger.debug("🔍 No channel_payload, skipping BlackPearl contact management")
            return
            
        # Handle case where no user_id is available (fallback scenario)
        if not user_id:
            logger.warning("🔍 No user_id available for BlackPearl contact management, using NOT_REGISTERED prompt")
            await self.load_active_prompt_template(status_key="NOT_REGISTERED")
            return
        
        # Validate user exists in database before proceeding
        from automagik.db.repository.user import get_user
        import uuid
        try:
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            user = get_user(user_uuid)
            if not user:
                logger.warning(f"🔍 User {user_id} not found in database, using NOT_REGISTERED prompt")
                await self.load_active_prompt_template(status_key="NOT_REGISTERED")
                return
            else:
                logger.debug(f"🔍 User {user_id} found in database")
                # Ensure user has user_data to prevent None errors later
                if user.user_data is None:
                    logger.info(f"🔍 User {user_id} has no user_data, initializing empty dict")
                    update_user_data(user_uuid, {})
        except (ValueError, TypeError) as e:
            logger.error(f"🔍 Invalid user_id format: {user_id}, error: {e}")
            await self.load_active_prompt_template(status_key="NOT_REGISTERED")
            return
            
        try:
            # Extract user information from context (already processed by channel handler)
            user_number = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
            user_name = self.context.get("whatsapp_user_name") or self.context.get("user_name")
            
            logger.debug(f"🔍 Context extraction - whatsapp_user_number: {self.context.get('whatsapp_user_number')}")
            logger.debug(f"🔍 Context extraction - user_phone_number: {self.context.get('user_phone_number')}")
            logger.debug(f"🔍 Context extraction - whatsapp_user_name: {self.context.get('whatsapp_user_name')}")
            logger.debug(f"🔍 Context extraction - user_name: {self.context.get('user_name')}")
            logger.debug(f"🔍 Final extracted - user_number: {user_number}, user_name: {user_name}")
            
            if not user_number:
                logger.debug("🔍 No user number found in context, skipping BlackPearl contact management")
                logger.debug(f"🔍 Available context keys: {list(self.context.keys())}")
                return
                
            logger.debug(f"🔍 Extracted user info from context: number={user_number}, name={user_name}")
            
            # Get or create contact in BlackPearl
            logger.debug(f"🔍 Calling get_or_create_contact with number={user_number}, name={user_name}, user_id={user_id}, agent_id={self.db_id}")
            contato_blackpearl = await get_or_create_contact(
                self.context, 
                user_number, 
                user_name,
                user_id,
                self.db_id
            )
            
            logger.debug(f"🔍 BlackPearl contact result: {contato_blackpearl}")
            
            if contato_blackpearl:
                user_name = contato_blackpearl.get("nome", user_name)
                self.context["blackpearl_contact_id"] = contato_blackpearl.get("id")
                logger.debug(f"🔍 Updated context with blackpearl_contact_id: {contato_blackpearl.get('id')}")
                
                # Get cliente information
                logger.debug(f"🔍 Looking up cliente for contact_id: {contato_blackpearl['id']}")
                cliente_blackpearl = await blackpearl.get_clientes(self.context, contatos_id=contato_blackpearl["id"])
                logger.debug(f"🔍 Cliente lookup result: {cliente_blackpearl}")
                
                if cliente_blackpearl and "results" in cliente_blackpearl and cliente_blackpearl["results"]:
                    cliente_blackpearl = cliente_blackpearl["results"][0]
                    self.context["blackpearl_cliente_id"] = cliente_blackpearl.get("id")
                    self.context["blackpearl_cliente_nome"] = cliente_blackpearl.get("razao_social")
                    self.context["blackpearl_cliente_email"] = cliente_blackpearl.get("email")
                    logger.info(f"BlackPearl Cliente: {self.context['blackpearl_cliente_id']} - {self.context['blackpearl_cliente_nome']}")
                    logger.debug(f"🔍 Updated context with cliente info: id={self.context['blackpearl_cliente_id']}")
                
                # Update user data in database
                logger.debug(f"🔍 Updating user data for user_id: {user_id}")
                try:
                    import uuid
                    user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
                    success = update_user_data(user_uuid, {
                        "blackpearl_contact_id": contato_blackpearl.get("id"), 
                        "blackpearl_cliente_id": self.context.get("blackpearl_cliente_id")
                    })
                    if not success:
                        logger.warning(f"🔍 Failed to update user_data for user {user_id}")
                except Exception as e:
                    logger.error(f"🔍 Error updating user_data for user {user_id}: {str(e)}")
                
                # Select prompt based on approval status
                status_aprovacao_str = contato_blackpearl.get("status_aprovacao", "NOT_REGISTERED")
                logger.debug(f"🔍 Contact approval status: {status_aprovacao_str}")
                logger.debug(f"🔍 Loading prompt for status: {status_aprovacao_str}")
                await self._use_prompt_based_on_contact_status(status_aprovacao_str, contato_blackpearl.get('id'))
                
                # Store user info in memory for templates
                logger.debug(f"🔍 Storing user memory for user_id: {user_id}")
                await self._store_stan_user_memory(user_id, user_name, user_number)
                
                logger.info(f"BlackPearl Contact: {contato_blackpearl.get('id')} - {user_name}")
                logger.debug("🔍 BlackPearl contact management completed successfully")
            else:
                # Use default prompt
                logger.debug("🔍 No BlackPearl contact found, using default NOT_REGISTERED prompt")
                await self.load_active_prompt_template(status_key="NOT_REGISTERED")
                
        except Exception as e:
            logger.error(f"🔍 Error in BlackPearl contact management: {str(e)}")
            logger.error(f"🔍 Exception details: {traceback.format_exc()}")
            # Fallback to default prompt
            logger.debug("🔍 Falling back to NOT_REGISTERED prompt due to error")
            await self.load_active_prompt_template(status_key="NOT_REGISTERED")
    
    async def _store_stan_user_memory(self, user_id: Optional[str], user_name: Optional[str], user_number: Optional[str]) -> None:
        """Store Stan-specific user information in memory."""
        if not self.db_id:
            return
            
        try:
            user_info_for_memory = {
                "user_id": user_id,
                "user_name": user_name,
                "user_number": user_number,
                "blackpearl_contact_id": self.context.get("blackpearl_contact_id"),
                "blackpearl_cliente_id": self.context.get("blackpearl_cliente_id"),
                "blackpearl_cliente_email": self.context.get("blackpearl_cliente_email"),
            }
            # Filter out None values
            user_info_content = {k: v for k, v in user_info_for_memory.items() if v is not None}
            
            # Create memory entry
            memory_to_create = Memory(
                name="user_information",
                content=str(user_info_content),
                user_id=user_id,
                read_mode="system_prompt",
                access="read_write",
                agent_id=self.db_id
            )
            
            create_memory(memory=memory_to_create)
            logger.info(f"Created/Updated user_information memory for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error storing Stan user memory: {str(e)}")
    
    async def _ensure_test_user_exists(self, user_id: str) -> bool:
        """Ensure test user exists in database for development/testing.
        
        Args:
            user_id: The user ID to create
            
        Returns:
            True if user was created or already exists, False on error
        """
        try:
            from automagik.db.repository.user import create_user
            from automagik.db.models import User
            from automagik.config import settings
            import uuid
            from datetime import datetime
            
            # Only create test users in development/test environments
            if settings.ENVIRONMENT.value not in ["development", "test"]:
                logger.warning(f"🔍 Not creating test user {user_id} in {settings.ENVIRONMENT.value} environment")
                return False
            
            # Check if this is a known test UUID
            known_test_uuids = [
                "550e8400-e29b-41d4-a716-446655440000",  # Mock test user
                "123e4567-e89b-12d3-a456-426614174000",  # Another test user
            ]
            
            if user_id not in known_test_uuids:
                logger.warning(f"🔍 User {user_id} is not a known test UUID, not creating")
                return False
            
            # Create test user
            user_uuid = uuid.UUID(user_id)
            test_user = User(
                id=user_uuid,
                email=f"test-{user_id[:8]}@automagik.dev",
                phone_number="+5511999999999",  # Test phone number
                user_data={
                    "test_user": True,
                    "created_by": "stan_agent_auto_creation",
                    "purpose": "development_testing"
                },
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            created_id = create_user(test_user)
            if created_id:
                logger.info(f"🔍 Successfully created test user {user_id}")
                return True
            else:
                logger.error(f"🔍 Failed to create test user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"🔍 Error creating test user {user_id}: {str(e)}")
            return False 
    
    def _register_multimodal_tools(self):
        """Register multimodal analysis tools using common helper."""
        from automagik.agents.common.multimodal_helper import register_multimodal_tools
        register_multimodal_tools(self.tool_registry, self.dependencies)
    
    async def _identify_or_create_user(self, channel_payload: Optional[dict], initial_user_id: Optional[str]) -> Optional[str]:
        """Identify existing user or create new user from WhatsApp context.
        
        Args:
            channel_payload: Channel payload containing user context
            initial_user_id: User ID from request (may be None)
            
        Returns:
            User ID to use for the session, or None if failed
        """
        logger.debug(f"🔍 User identification started - initial_user_id: {initial_user_id}")
        
        # Extract WhatsApp context information
        phone = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
        name = self.context.get("whatsapp_user_name") or self.context.get("user_name")
        
        logger.debug(f"🔍 Extracted context - phone: {phone}, name: {name}")
        
        # 1. Try to find existing user by phone number first (highest priority)
        if phone:
            existing_user = await self._find_user_by_phone(phone)
            if existing_user:
                logger.info(f"🔍 ✅ Found existing user by phone {phone}: {existing_user.id}")
                return str(existing_user.id)
        
        # 2. Try to validate initial_user_id if provided
        if initial_user_id:
            if await self._validate_user_exists(initial_user_id):
                logger.info(f"🔍 ✅ Validated existing user_id: {initial_user_id}")
                return initial_user_id
            else:
                logger.warning(f"🔍 ⚠️ Provided user_id {initial_user_id} not found in database")
        
        # 3. Create new user from WhatsApp context if we have phone number
        if phone:
            new_user_id = await self._create_user_from_whatsapp_context(phone, name)
            if new_user_id:
                logger.info(f"🔍 ✅ Created new user from WhatsApp context: {new_user_id}")
                return new_user_id
        
        # 4. Fallback to test user creation for development (only for known test UUIDs)
        if initial_user_id and settings.ENVIRONMENT.value in ["development", "test"]:
            logger.info(f"🔍 🧪 Attempting test user creation for development: {initial_user_id}")
            success = await self._ensure_test_user_exists(initial_user_id)
            if success:
                return initial_user_id
        
        logger.error(f"🔍 ❌ Could not identify or create user - phone: {phone}, user_id: {initial_user_id}")
        return None
    
    async def _find_user_by_phone(self, phone: str) -> Optional['User']:
        """Find user by phone number in various phone fields.
        
        Args:
            phone: Phone number to search for
            
        Returns:
            User object if found, None otherwise
        """
        try:
            from automagik.db.repository.user import list_users
            
            # Clean phone number for consistent matching
            clean_phone = self._clean_phone_number(phone)
            
            # Search in multiple phone fields
            all_users = list_users()
            for user in all_users:
                # Check phone_number field
                if user.phone_number and self._clean_phone_number(user.phone_number) == clean_phone:
                    return user
                
                # Check user_data for WhatsApp numbers
                if user.user_data:
                    whatsapp_number = user.user_data.get("whatsapp_user_number")
                    if whatsapp_number and self._clean_phone_number(whatsapp_number) == clean_phone:
                        return user
            
            return None
            
        except Exception as e:
            logger.error(f"🔍 Error searching for user by phone {phone}: {e}")
            return None
    
    async def _validate_user_exists(self, user_id: str) -> bool:
        """Validate that a user exists in the database.
        
        Args:
            user_id: User ID to validate
            
        Returns:
            True if user exists, False otherwise
        """
        try:
            from automagik.db.repository.user import get_user
            import uuid
            
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            user = get_user(user_uuid)
            return user is not None
            
        except Exception as e:
            logger.error(f"🔍 Error validating user {user_id}: {e}")
            return False
    
    async def _create_user_from_whatsapp_context(self, phone: str, name: Optional[str]) -> Optional[str]:
        """Create a new user from WhatsApp context information.
        
        Args:
            phone: WhatsApp phone number
            name: WhatsApp display name (optional)
            
        Returns:
            Created user ID, or None if failed
        """
        try:
            from automagik.db.repository.user import create_user
            from automagik.db.models import User
            import uuid
            from datetime import datetime
            
            # Generate clean email based on phone
            clean_phone = self._clean_phone_number(phone)
            email = f"whatsapp-{clean_phone[-4:]}@blackpearl.local"
            
            # Create user with WhatsApp context
            new_user = User(
                id=uuid.uuid4(),
                email=email,
                phone_number=phone,
                user_data={
                    "whatsapp_user_name": name,
                    "whatsapp_user_number": phone,
                    "auto_created": True,
                    "created_by": "stan_agent",
                    "source": "whatsapp_context",
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            created_id = create_user(new_user)
            if created_id:
                logger.info(f"🔍 ✅ Auto-created user {created_id} from WhatsApp context")
                return str(created_id)
            else:
                logger.error(f"🔍 ❌ Failed to create user from WhatsApp context")
                return None
                
        except Exception as e:
            logger.error(f"🔍 Error creating user from WhatsApp context: {e}")
            return None
    
    def _clean_phone_number(self, phone: str) -> str:
        """Clean phone number for consistent matching.
        
        Args:
            phone: Raw phone number
            
        Returns:
            Cleaned phone number (digits only)
        """
        import re
        return re.sub(r'[^\d]', '', phone)
