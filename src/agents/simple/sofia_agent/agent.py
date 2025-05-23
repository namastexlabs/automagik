"""SofiaAgent implementation with PydanticAI.

This module provides a SofiaAgent class that uses PydanticAI for LLM integration
and inherits common functionality from AutomagikAgent.
"""
import logging
import traceback
from typing import Dict, Any, Optional, Union

from pydantic_ai import Agent
from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.models.response import AgentResponse
from src.memory.message_history import MessageHistory
from src.config import settings

# Import only necessary utilities
from src.agents.common.message_parser import (
    extract_tool_calls, 
    extract_tool_outputs,
    extract_all_messages
)
from src.agents.common.dependencies_helper import (
    parse_model_settings,
    create_model_settings,
    create_usage_limits,
    get_model_name,
    add_system_message_to_history
)

# Evolution payload helper (shared across agents)
from src.agents.common.evolution import EvolutionMessagePayload

# For typing wrappers
from pydantic_ai import RunContext
from src.agents.simple.sofia_agent.specialized.airtable import run_airtable_assistant 

logger = logging.getLogger(__name__)

class SofiaAgent(AutomagikAgent):
    """SofiaAgent implementation using PydanticAI.
    
    This agent provides a basic implementation that follows the PydanticAI
    conventions for multimodal support and tool calling.
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize the SofiaAgent.
        
        Args:
            config: Dictionary with configuration options
        """
        # First initialize the base agent without a system prompt
        super().__init__(config)
        
        # Load and register the code-defined prompt
        from src.agents.simple.sofia_agent.prompts.prompt import AGENT_PROMPT
        
        # Register the code-defined prompt for this agent
        # This call is asynchronous but we're in a synchronous __init__,
        # so we'll register the prompt later during the first run
        self._prompt_registered = False
        self._code_prompt_text = AGENT_PROMPT
        
        # PydanticAI-specific agent instance
        self._agent_instance: Optional[Agent] = None
        
        # Configure dependencies
        self.dependencies = AutomagikAgentsDependencies(
            model_name=get_model_name(config),
            model_settings=parse_model_settings(config)
        )
        
        # Set agent_id if available
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        
        # Set usage limits if specified in config
        usage_limits = create_usage_limits(config)
        if usage_limits:
            self.dependencies.set_usage_limits(usage_limits)
        
        # Register default tools
        self.tool_registry.register_default_tools(self.context)
        
        # Register additional tools
        
        # Register additional Evolution tools with context-aware wrappers
        self.tool_registry.register_tool(self._create_send_reaction_wrapper())
        self.tool_registry.register_tool(self._create_send_text_wrapper())
        # Register specialized Airtable sub-agent as a tool
        self.tool_registry.register_tool(self._create_airtable_agent_wrapper())  # NEW LINE
        
        logger.info("SofiaAgent initialized successfully")
    
    async def _initialize_pydantic_agent(self) -> None:
        """Initialize the underlying PydanticAI agent."""
        if self._agent_instance is not None:
            return
            
        # Get model configuration
        model_name = "google-gla:gemini-2.5-pro-preview-05-06"
        # model_name = get_model_name(self.dependencies.model_settings)
        model_settings = create_model_settings(self.dependencies.model_settings)
        
        # Convert tools to PydanticAI format
        tools = self.tool_registry.convert_to_pydantic_tools()
        logger.info(f"Prepared {len(tools)} tools for PydanticAI agent")
                    
        try:
            # Create agent instance - system_prompt will be passed in message history
            self._agent_instance = Agent(
                model=model_name,
                tools=tools,
                model_settings=model_settings,
                deps_type=AutomagikAgentsDependencies
            )
            
            logger.info(f"Initialized agent with model: {model_name} and {len(tools)} tools")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {str(e)}")
            raise
        
    async def run(self, input_text: str, *, multimodal_content=None, system_message=None, message_history_obj: Optional[MessageHistory] = None,
                 channel_payload: Optional[Dict] = None,
                 message_limit: Optional[int] = 20) -> AgentResponse:
        """Run the agent with the given input.
        
        Args:
            input_text: Text input for the agent
            multimodal_content: Optional multimodal content
            system_message: Optional system message for this run (ignored in favor of template)
            message_history_obj: Optional MessageHistory instance for DB storage
            
        Returns:
            AgentResponse object with result and metadata
        """
      
        # -------------------------------------------------------------
        # Evolution (WhatsApp) channel payload handling
        # -------------------------------------------------------------
        evolution_payload = None  # type: Optional[EvolutionMessagePayload]
        if channel_payload:
            try:
                # Convert raw dict coming from webhook into the Pydantic model
                evolution_payload = EvolutionMessagePayload(**channel_payload)
                logger.debug(
                    "Successfully converted channel_payload to EvolutionMessagePayload"
                )
            except Exception as e:
                logger.error(
                    f"Failed to convert channel_payload to EvolutionMessagePayload: {str(e)}"
                )

        if evolution_payload is not None:
            # Make it available in context/dependencies
            self.context["evolution_payload"] = evolution_payload

            if hasattr(self.dependencies, 'set_context'):
                combined_ctx = {**getattr(self.dependencies, 'context', {}), "evolution_payload": evolution_payload}
                self.dependencies.set_context(combined_ctx)

            # Extract basic user info from the payload
            user_number: Optional[str] = None
            user_name: Optional[str] = None

            try:
                user_number = evolution_payload.get_user_number()
                user_name = evolution_payload.get_user_name()
                logger.debug(
                    f"Extracted user info from evolution_payload: number={user_number}, name={user_name}"
                )
            except Exception as e:
                logger.error(f"Error extracting user info from evolution_payload: {str(e)}")

            
            # Detect if we are in a group chat
            if evolution_payload.is_group_chat():
                self.context["is_group_chat"] = True
                self.context["group_jid"] = evolution_payload.get_group_jid()
            else:
                self.context.pop("is_group_chat", None)
                self.context.pop("group_jid", None)
                
            # Persist user information into memory so it can be injected into the
            # system prompt via the {{user_information}} template variable (same
            # pattern used by StanAgent).
            if self.db_id and (user_number or user_name):
                try:
                    from src.db.models import Memory
                    from src.db.repository import create_memory

                    # Build info dict without None values
                    info_dict: Dict[str, Any] = {
                        k: v for k, v in {
                            "user_name": user_name,
                            "user_number": user_number,
                        }.items() if v is not None
                    }

                    if info_dict:
                        memory_to_create = Memory(
                            name="user_information",
                            content=str(info_dict),
                            user_id=self.context.get("user_id"),
                            agent_id=self.db_id,
                            read_mode="system_prompt",
                            access="read_write",
                        )

                        create_memory(memory=memory_to_create)
                        logger.info("Created/Updated user_information memory for SofiaAgent run")
                except Exception as e:
                    logger.error(f"Failed to create user_information memory: {str(e)}")

        
          # Register the code-defined prompt if not already done
        await self._check_and_register_prompt()
        
        # Load the active prompt template for this agent
        await self.load_active_prompt_template(status_key="default")
        
        # Ensure memory variables are initialized
        if self.db_id:
            await self.initialize_memory_variables(getattr(self.dependencies, 'user_id', None))
                
        # Initialize the agent
        await self._initialize_pydantic_agent()
        
        # Get message history in PydanticAI format
        pydantic_message_history = []
        if message_history_obj:
            pydantic_message_history = message_history_obj.get_formatted_pydantic_messages(limit=message_limit)
        
        # Prepare user input (handle multimodal content)
        user_input = input_text # Default to text-only

        if multimodal_content:
            # This call is a placeholder in dependencies, but good to keep for intent
            if hasattr(self.dependencies, 'configure_for_multimodal'):
                self.dependencies.configure_for_multimodal(True)
            
            # Attempt to import the rich multimodal types from *pydantic_ai*.
            # We fall back gracefully if running with an older/stripped version
            # of the library.
            try:
                from pydantic_ai import ImageUrl, BinaryContent  # type: ignore
            except ImportError:
                ImageUrl = None  # type: ignore
                BinaryContent = None  # type: ignore

            pydantic_ai_input_list: list[Any] = [input_text] # Start with the text prompt
            successfully_converted_at_least_one = False

            def _convert_image_payload_to_pydantic(image_item_payload: Dict[str, Any]) -> Any:
                nonlocal successfully_converted_at_least_one
                if not ImageUrl: # PydanticAI types not available
                    return image_item_payload

                # image_item_payload is expected to be like {'data': 'url_or_base64', 'mime_type': 'image/jpeg'}
                data_content = image_item_payload.get("data")
                mime_type = image_item_payload.get("mime_type", "")

                if isinstance(data_content, str) and mime_type.startswith("image/"):
                    # ------------------------------------------------------------------
                    # Remote image (HTTP/S)  →  download & wrap as BinaryContent
                    # ------------------------------------------------------------------
                    # Attempt to download the image (also works for presigned MinIO/S3 URLs)
                    if data_content.lower().startswith("http"):
                        try:
                            from src.utils.image_utils import download_image

                            img_path, detected_mime = download_image(data_content)
                            # Prefer explicit payload mime over detected one
                            mime_for_bc = mime_type or detected_mime

                            with open(img_path, "rb") as _fh:
                                img_bytes = _fh.read()

                            # Some models (e.g., Google Gemini) reject raw binary inputs. Maintain a
                            # small blacklist of substrings to detect unsupported models.
                            _UNSUPPORTED_BINARY_MODELS = [
                                "google-gla:gemini-2.5-pro-preview-05-06",          # All Gemini variants
                                # "gpt-4o-mini",     # hypothetical example
                            ]

                            current_model_name = str(getattr(self._agent_instance, "model", "")).lower()
                            binary_not_supported = any(k in current_model_name for k in _UNSUPPORTED_BINARY_MODELS)

                            if binary_not_supported or BinaryContent is None:
                                logger.debug(
                                    f"Model '{current_model_name}' does not support binary images – sending ImageUrl."
                                )
                                successfully_converted_at_least_one = True
                                return ImageUrl(url=data_content)

                            logger.debug(
                                f"Downloaded image URL and converted to BinaryContent (size={len(img_bytes)} bytes)"
                            )
                            successfully_converted_at_least_one = True
                            return BinaryContent(data=img_bytes, media_type=mime_for_bc)
                        except Exception as e:
                            logger.warning(
                                f"Failed to convert image URL to BinaryContent – falling back to ImageUrl: {e}"
                            )
                        # Fallback: send as ImageUrl (requires remote fetch by model)
                        if ImageUrl is not None:
                            logger.debug(
                                f"Converting image URL to ImageUrl object: {data_content[:100]}…"
                            )
                            successfully_converted_at_least_one = True
                            return ImageUrl(url=data_content)
                
                logger.debug(
                    f"Image payload not converted to ImageUrl/BinaryContent: {str(image_item_payload)[:100]}…"
                )
                return image_item_payload # Return original if not a convertible image URL or recognized format

            # Process the 'images' list from the multimodal_content dictionary
            if isinstance(multimodal_content, dict) and "images" in multimodal_content:
                image_list = multimodal_content.get("images", [])
                if isinstance(image_list, list):
                    for item_payload in image_list:
                        if isinstance(item_payload, dict): # Ensure item in list is a dict
                            converted_obj = _convert_image_payload_to_pydantic(item_payload)
                            pydantic_ai_input_list.append(converted_obj)
                        else:
                            pydantic_ai_input_list.append(item_payload) # Append as-is if not a dict
            # TODO: Add elif clauses here to handle other direct multimodal_content structures if necessary,
            # e.g., if multimodal_content could be a list of URLs or a single URL string directly.
            # For now, focusing on the {'images': [...]} structure from the API controller.
            
            if successfully_converted_at_least_one:
                user_input = pydantic_ai_input_list
                logger.debug(f"Using PydanticAI list format for user_input: {str(user_input)[:200]}")
            else:
                # Fallback if no items were successfully converted to PydanticAI objects
                user_input = {"text": input_text, "multimodal_content": multimodal_content}
                logger.debug(f"Using legacy dict format for user_input: {str(user_input)[:200]}")
        
        try:
            # Get filled system prompt
            filled_system_prompt = await self.get_filled_system_prompt(
                user_id=getattr(self.dependencies, 'user_id', None)
            )
            
            # Add system prompt to message history
            if filled_system_prompt:
                pydantic_message_history = add_system_message_to_history(
                    pydantic_message_history, 
                    filled_system_prompt
                )
            
            # Update dependencies with context
            if hasattr(self.dependencies, 'set_context'):
                self.dependencies.set_context(self.context)
        
            # Run the agent
            result = await self._agent_instance.run(
                user_input,
                message_history=pydantic_message_history,
                usage_limits=getattr(self.dependencies, "usage_limits", None),
                deps=self.dependencies
            )
            
            # Extract tool calls and outputs
            all_messages = extract_all_messages(result)
            tool_calls = []
            tool_outputs = []
            
            # Process each message to extract tool calls and outputs
            for msg in all_messages:
                tool_calls.extend(extract_tool_calls(msg))
                tool_outputs.extend(extract_tool_outputs(msg))
            
            # Create response
            return AgentResponse(
                text=result.output,
                success=True,
                tool_calls=tool_calls,
                tool_outputs=tool_outputs,
                raw_message=all_messages,
                system_prompt=filled_system_prompt,
            )
        except Exception as e:
            logger.error(f"Error running agent: {str(e)}")
            logger.error(traceback.format_exc())
            return AgentResponse(
                text=f"Error: {str(e)}",
                success=False,
                error_message=str(e),
                raw_message=pydantic_message_history if 'pydantic_message_history' in locals() else None
            ) 

    # ------------------------------------------------------------------
    # Evolution tool wrappers
    # ------------------------------------------------------------------

    def _create_send_reaction_wrapper(self):
        """Wrap send_reaction to auto-fill JIDs from evolution payload."""
        from src.tools.evolution.tool import send_reaction as evo_send_reaction

        async def send_reaction_wrapper(
            ctx: RunContext[AutomagikAgentsDependencies],
            reaction: str,
        ) -> Dict[str, Any]:
            # Try multiple locations to mirror product.py logic
            evo_payload = None
            if hasattr(ctx, "evolution_payload"):
                evo_payload = ctx.evolution_payload
            if not evo_payload and hasattr(ctx, "deps") and hasattr(ctx.deps, "evolution_payload"):
                evo_payload = ctx.deps.evolution_payload
            if not evo_payload and hasattr(ctx, "deps") and hasattr(ctx.deps, "context") and ctx.deps.context:
                evo_payload = ctx.deps.context.get("evolution_payload")
            if not evo_payload and hasattr(ctx, "parent_context") and isinstance(ctx.parent_context, dict):
                evo_payload = ctx.parent_context.get("evolution_payload")

            if not evo_payload:
                return {"success": False, "error": "evolution_payload not found in context"}

            try:
                # -----------------------------
                # 1. Locate message key safely
                # -----------------------------
                key_obj = None
                if hasattr(evo_payload, "data") and hasattr(evo_payload.data, "key"):
                    key_obj = evo_payload.data.key  # new structure
                elif hasattr(evo_payload, "output") and hasattr(evo_payload.output, "key"):
                    key_obj = evo_payload.output.key  # legacy structure

                if not key_obj:
                    return {"success": False, "error": "Message key not found in payload"}

                remote_jid = getattr(key_obj, "remoteJid", None)
                message_id = getattr(key_obj, "id", None)
                if not remote_jid or not message_id:
                    return {"success": False, "error": "Missing remote_jid or message_id"}

                # -----------------------------
                # 2. Credentials / config
                # -----------------------------
                instance_name = getattr(evo_payload, "instance", None) or getattr(settings, "EVOLUTION_INSTANCE", "default")
                api_url       = getattr(evo_payload, "server_url", None) or getattr(settings, "EVOLUTION_API_URL", None)
                api_key       = getattr(evo_payload, "apikey", None)      or getattr(settings, "EVOLUTION_API_KEY", None)

                # -----------------------------
                # 3. Call evolution tool
                # -----------------------------
                return await evo_send_reaction(
                    ctx,
                    remote_jid,
                    message_id,
                    reaction,
                    instance=instance_name,
                    api_url=api_url,
                    api_key=api_key,
                )
            except Exception as e:
                logger.error(f"send_reaction_wrapper error: {e}")
                return {"success": False, "error": str(e)}

        # Add metadata for tool registration
        send_reaction_wrapper.__name__ = "send_reaction"
        send_reaction_wrapper.__doc__ = "Send a reaction (emoji) to the last user message via Evolution. Auto-detects JID and message ID from context."
        return send_reaction_wrapper

    def _create_send_text_wrapper(self):
        """Wrap send_message tool to auto-fill phone number and instance."""
        from src.tools.evolution.tool import send_message as evo_send_text

        async def send_text_wrapper(
            ctx: RunContext[AutomagikAgentsDependencies],
            text: str,
        ) -> Dict[str, Any]:
            # Get evolution payload
            evo_payload = None
            if hasattr(ctx, "evolution_payload"):
                evo_payload = ctx.evolution_payload
            if not evo_payload and hasattr(ctx, "deps") and hasattr(ctx.deps, "evolution_payload"):
                evo_payload = ctx.deps.evolution_payload
            if not evo_payload and hasattr(ctx, "deps") and hasattr(ctx.deps, "context") and ctx.deps.context:
                evo_payload = ctx.deps.context.get("evolution_payload")
            if not evo_payload and hasattr(ctx, "parent_context") and isinstance(ctx.parent_context, dict):
                evo_payload = ctx.parent_context.get("evolution_payload")

            if not evo_payload:
                return {"success": False, "error": "evolution_payload not found"}

            try:
                phone_number = evo_payload.get_user_number()
                if not phone_number:
                    return {"success": False, "error": "Could not determine user number"}

                # Prefer credentials from payload, else config
                instance_name = getattr(evo_payload, "instance", None) or getattr(settings, "EVOLUTION_INSTANCE", "default")
                api_url       = getattr(evo_payload, "server_url", None) or getattr(settings, "EVOLUTION_API_URL", None)
                api_key       = getattr(evo_payload, "apikey", None)      or getattr(settings, "EVOLUTION_API_KEY", None)

                return await evo_send_text(
                    ctx,
                    phone=phone_number,
                    message=text,
                    instance=instance_name,
                    api_url=api_url,
                    token=api_key,
                )
            except Exception as e:
                logger.error(f"send_text_wrapper error: {e}")
                return {"success": False, "error": str(e)}

        send_text_wrapper.__name__ = "send_text_to_user"
        send_text_wrapper.__doc__ = "Send plain text to the current user via Evolution API. Auto-fills phone number."
        return send_text_wrapper 

    # ------------------------------------------------------------------
    # Airtable specialized sub-agent wrapper
    # ------------------------------------------------------------------

    def _create_airtable_agent_wrapper(self):
        """Create a wrapper for the Airtable specialized agent (run_airtable_assistant).

        This exposes the entire Airtable Assistant as a single callable tool so the
        main SofiaAgent can delegate complex, multi-step Airtable workflows such as
        creating/updating tasks, sending accountability messages, or resolving
        blockers. The wrapper ensures the Evolution payload (WhatsApp context) is
        forwarded into the sub-agent, mirroring the pattern used by other wrappers.
        """
        # Capture a reference to the parent context at creation time
        parent_ctx = self.context

        async def airtable_agent_wrapper(
            ctx: RunContext[AutomagikAgentsDependencies],
            input_text: str,
        ) -> str:
            """Delegate Airtable-related queries to the specialized Airtable Assistant.

            Args:
                ctx: RunContext propagated by PydanticAI during tool execution.
                input_text: The user's question or instruction regarding Airtable
                    (tasks, milestones, team members, blockers, etc.).

            Returns:
                Natural-language response produced by the Airtable Assistant.
            """
            # Ensure Evolution payload is passed down for WhatsApp utilities
            if ctx.deps and parent_ctx and "evolution_payload" in parent_ctx:
                evo_payload = parent_ctx["evolution_payload"]
                # 1. Attach directly to deps
                ctx.deps.evolution_payload = evo_payload  # type: ignore
                # 2. Merge into deps.context dict
                merged = dict(ctx.deps.context) if hasattr(ctx.deps, "context") and ctx.deps.context else {}
                merged["evolution_payload"] = evo_payload
                ctx.deps.set_context(merged)
                # 3. Keep reference on RunContext for downstream convenience
                ctx.__dict__["evolution_payload"] = evo_payload  # type: ignore
                ctx.__dict__["parent_context"] = parent_ctx      # type: ignore

            # Delegate to the specialized agent
            return await run_airtable_assistant(ctx, input_text)

        # Tool metadata for the LLM
        airtable_agent_wrapper.__name__ = "airtable_assistant"
        airtable_agent_wrapper.__doc__ = (
            "High-level Airtable Assistant capable of multi-step workflows across "
            "the Tasks, projetos, and Team Members tables. Use this to create or "
            "update tasks, send WhatsApp notifications, or resolve blockers when "
            "a single CRUD call is insufficient. Accepts free-form instructions in "
            "Portuguese and returns a natural-language answer after performing the "
            "necessary Airtable tool calls."
        )

        return airtable_agent_wrapper 