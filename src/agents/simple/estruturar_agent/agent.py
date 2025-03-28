"""SimpleAgent implementation with PydanticAI.

This module provides a SimpleAgent class that uses PydanticAI for LLM integration
and inherits common functionality from AutomagikAgent.
"""
import logging
import traceback
import json
from typing import Dict, Optional, List, Union, Any

from pydantic_ai import Agent
from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.models.response import AgentResponse
from src.memory.message_history import MessageHistory

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

# Import Evolution tools
from src.tools.evolution import (
    send_business_contact,
    send_personal_contact
)

logger = logging.getLogger(__name__)

# Define the whitelist configuration
class WhitelistConfig:
    """Configuration for phone number whitelist."""
    
    def __init__(self):
        """Initialize the whitelist configuration."""
        # Default whitelist phone numbers (without country code)
        self._whitelist = [
            # Add your whitelisted numbers here (format: "5511999999999")
            "5531995400658", "351913034963", "5531997110019", "5531972465316", "5531999911072", "5538998806612",
            "5538999766612", "5531999286612", "5531998852688", "5531984597690", "5531998227449",
            "5531995324579", "17814967681", "5531997174121", "5531999923252", "5531992936659",
            "5531995587304", "5531999552655", "5531995128972", "5531999760420", "5538999868512",
            "5531996018154", "5531971819210", "5531999862792", "5511984047855", "5535999732815",
            "5531999698052", "5535984435710", "5531996024087", "5531997774130", "5531971802601",
            "5531996606947", "5531982169954", "5531995452182", "5535984460072", "5531984816224",
            "5535999504860", "5548996331826", "5531998752512", "5531994874620", "5512991186670",
            "5531999155352", "5531997714239", "5531999562760", "5535998396581", "5531997673031",
            "5535999719189", "5535998481957", "5512981472259", "5516991252858", "5535997459566",
            "5531997442499", "5531997279437", "5531995084900", "5531988619630", "5531997281729",
            "5538998913783", "5531997746887", "5531985804618", "5531996489909", "5538999930501",
            "5531971525840", "5531998270262", "5531996295460", "5535997052218", "5531988753828",
            "5531997275288", "5531997627474", "5531999465814", "5531995606163", "5531997571637",
            "5531993798965", "5535998060654", "5531996303065", "5531997714557", "5531999274715",
            "5531997970138", "5527998722679", "5527997482360", "556291352860"
        ]
        
    @property
    def whitelist(self) -> List[str]:
        """Get the whitelist of phone numbers."""
        return self._whitelist
        
    def is_whitelisted(self, phone_number: str) -> bool:
        """Check if a phone number is in the whitelist.
        
        Args:
            phone_number: The phone number to check (can include @s.whatsapp.net or other formatting)
            
        Returns:
            bool: True if whitelisted, False otherwise
        """
        # Clean the phone number to extract just the digits
        cleaned_number = self._clean_phone_number(phone_number)
        
        # Check if the cleaned number is in the whitelist
        return cleaned_number in self._whitelist
    
    def _clean_phone_number(self, phone_number: str) -> str:
        """Clean a phone number to standard format.
        
        Args:
            phone_number: The phone number to clean
            
        Returns:
            str: Cleaned phone number
        """
        # Remove any non-digit characters
        import re
        digits_only = re.sub(r'\D', '', phone_number)
        
        return digits_only


class EstruturarAgent(AutomagikAgent):
    """EstruturarAgent implementation using PydanticAI.
    
    This agent provides a basic implementation that follows the PydanticAI
    conventions for multimodal support and tool calling.
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize the EstruturarAgent.
        
        Args:
            config: Dictionary with configuration options
        """
        from src.agents.simple.estruturar_agent.prompts.prompt import ESTRUTURAR_AGENT_PROMPT
        
        # Initialize the base agent
        super().__init__(config, ESTRUTURAR_AGENT_PROMPT)
        
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
        
        # Initialize whitelist configuration
        self.whitelist_config = WhitelistConfig()
        
        # Register contact tools - each tool only once
        self._register_contact_tools()
        
        logger.info("EstruturarAgent initialized successfully")
    
    def _register_contact_tools(self) -> None:
        """Register the Evolution contact tools for sending contacts via WhatsApp."""
        # Check if tools are already registered to prevent duplicates
        existing_tools = set()
        if hasattr(self, 'tool_registry') and self.tool_registry:
            # Get registered tools from the get_registered_tools method instead of accessing 'tools' attribute
            registered_tools = self.tool_registry.get_registered_tools()
            existing_tools = set(registered_tools.keys())
        
        # Register send_business_contact tool if not already registered
        if 'send_business_contact' not in existing_tools:
            self.register_tool(send_business_contact)
            logger.info("Registered business contact tool")
        
        # Register send_personal_contact tool if not already registered
        if 'send_personal_contact' not in existing_tools:
            self.register_tool(send_personal_contact)
            logger.info("Registered personal contact tool")
    
    async def _initialize_agent(self) -> None:
        """Initialize the underlying PydanticAI agent."""
        if self._agent_instance is not None:
            return
            
        # Get model configuration
        model_name = self.dependencies.model_name
        model_settings = create_model_settings(self.dependencies.model_settings)
        
        # Convert tools to PydanticAI format
        tools = self.tool_registry.convert_to_pydantic_tools()
        logger.info(f"Prepared {len(tools)} tools for PydanticAI agent")
                    
        try:
            # Create agent instance
            self._agent_instance = Agent(
                model=model_name,
                system_prompt=self.system_prompt,
                tools=tools,
                model_settings=model_settings,
                deps_type=AutomagikAgentsDependencies
            )
            
            logger.info(f"Initialized agent with model: {model_name} and {len(tools)} tools")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {str(e)}")
            raise
    
    def _check_whitelist(self, message_payload: Dict[str, Any]) -> bool:
        """Check if the sender is in the whitelist.
        
        Args:
            message_payload: The message payload containing sender information
            
        Returns:
            bool: True if whitelisted or if no remoteJid found, False otherwise
        """
        try:
            # Extract remoteJid based on standard Evolution API structure
            remote_jid = None
            
            # First check for data.key.remoteJid structure (default Evolution API format)
            if isinstance(message_payload, dict):
                data = message_payload.get('data', {})
                if isinstance(data, dict) and 'key' in data:
                    remote_jid = data.get('key', {}).get('remoteJid')
            
            # If not found, look for message_content.whatsapp_raw_payload structure
            if not remote_jid and isinstance(message_payload, dict):
                whatsapp_payload = message_payload.get('message_content', {}).get('whatsapp_raw_payload', {})
                if isinstance(whatsapp_payload, dict):
                    data = whatsapp_payload.get('data', {})
                    if isinstance(data, dict) and 'key' in data:
                        remote_jid = data.get('key', {}).get('remoteJid')
            
            # If remoteJid is found, check against whitelist
            if remote_jid:
                logger.info(f"Checking if {remote_jid} is in whitelist")
                return self.whitelist_config.is_whitelisted(remote_jid)
            else:
                # If no remoteJid found, assume whitelisted (for compatibility with non-WhatsApp inputs)
                logger.warning("No remoteJid found in message payload, assuming whitelisted")
                return True
                
        except Exception as e:
            logger.error(f"Error checking whitelist: {str(e)}")
            # Default to allowing the message through in case of error
            return True
            
    async def run(self, input_text: str, *, multimodal_content=None, system_message=None, message_history_obj: Optional[MessageHistory] = None, channel_payload: Optional[Dict] = None, message_limit: Optional[int] = None) -> AgentResponse:
        """Run the agent with the given input.
        
        Args:
            input_text: Text input for the agent
            multimodal_content: Optional multimodal content
            system_message: Optional system message for this run (ignored in favor of template)
            message_history_obj: Optional MessageHistory instance for DB storage
            channel_payload: Optional payload from the messaging channel (e.g., WhatsApp webhook)
            message_limit: Optional limit for the number of messages to process
            
        Returns:
            AgentResponse object with result and metadata
        """
        # Add channel_payload to context if provided
        if channel_payload:
            self.update_context({"channel_payload": channel_payload})
            
            # Try to extract Evolution credentials from payload and add to context
            evolution_data = self._extract_evolution_data(channel_payload)
            if evolution_data:
                self.update_context({"evolution": evolution_data})
                
            # Extract the sender's number
            sender_number = self._extract_sender_number(channel_payload)
            is_whitelisted = self._check_whitelist(channel_payload)
            
            # Check if this is a webhook event for a message we sent (to avoid loops)
            if isinstance(channel_payload, dict):
                event_type = channel_payload.get("event", "")
                # Ignore send.message events for contacts we sent
                if event_type == "send.message" and "contactMessage" in str(channel_payload.get("data", {}).get("message", {})):
                    logger.info("Ignoring webhook for contact we just sent")
                    return AgentResponse(
                        text="AUTOMAGIK:IGNORE_CONTACT_EVENT",
                        success=True,
                        metadata={
                            "is_whitelisted": True,
                            "sender_number": sender_number,
                            "action": "ignored_contact_webhook",
                            "should_ignore": True
                        }
                    )
                # Also ignore message status updates
                elif event_type == "messages.update":
                    logger.info("Ignoring message status update webhook")
                    return AgentResponse(
                        text="AUTOMAGIK:IGNORE_STATUS_UPDATE",
                        success=True,
                        metadata={
                            "is_whitelisted": True,
                            "sender_number": sender_number,
                            "action": "ignored_status_update",
                            "should_ignore": True
                        }
                    )
                # Only process messages.upsert that are not from us
                elif event_type == "messages.upsert":
                    data = channel_payload.get("data", {})
                    key = data.get("key", {})
                    from_me = key.get("fromMe", False)
                    
                    if from_me:
                        logger.info("Ignoring message sent by us")
                        return AgentResponse(
                            text="AUTOMAGIK:IGNORE_SELF_MESSAGE",
                            success=True,
                            metadata={
                                "is_whitelisted": True,
                                "sender_number": sender_number,
                                "action": "ignored_self_message",
                                "should_ignore": True
                            }
                        )
            
            # If whitelisted, send business contact information
            if is_whitelisted:
                logger.info(f"Sender {sender_number} is in whitelist, sending business contact")
                
                # Initialize the agent to ensure tools are registered
                await self._initialize_agent()
                
                # Directly call the send_business_contact function without using the agent
                try:
                    # Extract Evolution API credentials from channel_payload
                    evolution_data = self._extract_evolution_data(channel_payload) or {}
                    
                    # Get Evolution API credentials
                    api_key = evolution_data.get("api_key", "5E03C326135F-440A-931B-CC472B5BFDEF")
                    base_url = evolution_data.get("base_url", "http://localhost:8080")
                    instance_name = evolution_data.get("instance_name", "raphael")
                    
                    # Get contact information
                    contact_name = "Rafael Pereira - Engenheiro Civil"
                    contact_phone = "5535997463187"
                    contact_display = "+55 35 99746-3187"
                    
                    # Clean recipient number
                    clean_recipient = sender_number.split("@")[0] if "@" in sender_number else sender_number
                    if "@s.whatsapp.net" not in clean_recipient:
                        clean_recipient = f"{clean_recipient}@s.whatsapp.net"
                    
                    # Import necessary functions
                    from src.tools.evolution.contact_tool import send_contact
                    from src.tools.evolution.tool import send_message
                    from pydantic_ai import RunContext
                    
                    # Create minimal RunContext just to satisfy the function signature
                    ctx = RunContext({},
                        model={
                            "name": "evolution-contact",
                            "id": "evolution-contact",
                            "max_tokens": 4000,
                            "temperature": 0.7
                        },
                        usage={
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0
                        },
                        prompt="Contact tool"
                    )
                    
                    # First send a text message
                    welcome_message = "Olá, tudo bem? Esse número de telefone é utilizado exclusivamente para fins comerciais da Estruturar Engenharia. Por gentileza, contate Rafael através deste contato para assuntos pessoais."
                    
                    # Send the welcome message directly using Evolution API REST call
                    logger.info(f"Sending welcome message to {clean_recipient}")
                    try:
                        # Format base URL
                        formatted_base_url = base_url.rstrip('/')
                        if not formatted_base_url.startswith(('http://', 'https://')):
                            formatted_base_url = f"http://{formatted_base_url}"
                        
                        # Prepare the recipient (remove @s.whatsapp.net if present)
                        formatted_recipient = clean_recipient
                        if "@" in formatted_recipient:
                            formatted_recipient = formatted_recipient.split("@")[0]
                        
                        # Create the Evolution API request
                        message_url = f"{formatted_base_url}/message/sendText/{instance_name}"
                        message_headers = {
                            "apikey": api_key,
                            "Content-Type": "application/json"
                        }
                        message_payload = {
                            "number": formatted_recipient,
                            "text": welcome_message
                        }
                        
                        # Import requests
                        import requests
                        
                        # Send the message request
                        logger.info(f"Sending text message via Evolution API to {formatted_recipient}")
                        message_response = requests.post(
                            message_url,
                            headers=message_headers,
                            json=message_payload
                        )
                        message_response.raise_for_status()
                        logger.info(f"Welcome message sent successfully: {message_response.text}")
                        
                        # Add a small delay before sending the contact
                        import asyncio
                        await asyncio.sleep(1)
                    except Exception as msg_error:
                        logger.error(f"Error sending welcome message: {str(msg_error)}")
                    
                    # Call send_contact directly 
                    logger.info(f"Directly sending personal contact to {clean_recipient}")
                    contact_result = await send_contact(
                        ctx=ctx,
                        instance_name=instance_name,
                        api_key=api_key,
                        base_url=base_url,
                        recipient_number=clean_recipient,
                        full_name=contact_name,
                        whatsapp_id=contact_phone,
                        phone_number=contact_display,
                        organization="",
                        email="",
                        url=""
                    )
                    
                    # Log the result
                    logger.info(f"Contact sending result: {contact_result}")
                    
                    # Create tool call record
                    tool_calls = [{
                        "name": "send_personal_contact",
                        "arguments": {"recipient_number": sender_number}
                    }]
                    
                    tool_outputs = [{
                        "name": "send_personal_contact",
                        "content": str(contact_result)
                    }]
                    
                    # Return response with EMPTY text to avoid duplicate messages
                    return AgentResponse(
                        text="AUTOMAGIK:CONTACT_SENT_SUCCESSFULLY",
                        success=True,
                        tool_calls=tool_calls,
                        tool_outputs=tool_outputs,
                        raw_message=all_messages,
                        metadata={
                            "is_whitelisted": True,
                            "sender_number": sender_number,
                            "action": "sent_business_contact_directly",
                            "should_ignore": False  # We actually want a response to confirm contact was sent
                        }
                    )
                except Exception as e:
                    logger.error(f"Error sending personal contact directly: {str(e)}")
                    logger.error(traceback.format_exc())
                    
                    # Fallback response if the tool call fails - sending empty message to avoid duplicate texts
                    return AgentResponse(
                        text="AUTOMAGIK:ERROR_SENDING_CONTACT",
                        success=False,
                        metadata={
                            "is_whitelisted": True,
                            "sender_number": sender_number,
                            "error": str(e),
                            "action": "silent_fallback",
                            "should_ignore": True
                        }
                    )
            else:
                # Not whitelisted - don't respond
                logger.info(f"Sender {sender_number} is not in whitelist, not responding")
                return AgentResponse(
                    text="AUTOMAGIK:IGNORE_NON_WHITELISTED_USER",  # Special code for omni-hub to identify
                    success=True,
                    metadata={
                        "is_whitelisted": False,
                        "sender_number": sender_number,
                        "action": "no_response",
                        "should_ignore": True
                    }
                )
        
        # Ensure memory variables are initialized
        if self.db_id:
            await self.initialize_memory_variables(getattr(self.dependencies, 'user_id', None))
                
        # Initialize the agent
        await self._initialize_agent()
        
        # Get message history in PydanticAI format
        pydantic_message_history = []
        if message_history_obj:
            if message_limit:
                pydantic_message_history = message_history_obj.get_formatted_pydantic_messages(limit=message_limit)
            else:
                pydantic_message_history = message_history_obj.get_formatted_pydantic_messages(limit=20)
        
        # Prepare user input (handle multimodal content)
        user_input = input_text
        if multimodal_content:
            if hasattr(self.dependencies, 'configure_for_multimodal'):
                self.dependencies.configure_for_multimodal(True)
            user_input = {"text": input_text, "multimodal_content": multimodal_content}
        
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
                text=result.data,
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
    
    def _extract_evolution_data(self, message_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract Evolution API credentials and details from message payload.
        
        Args:
            message_payload: The message payload from Omni-hub
            
        Returns:
            Dict with Evolution API credentials or None if not found
        """
        try:
            # Initialize empty Evolution data
            evolution_data = {}
            
            # Check for Evolution data in the payload
            if isinstance(message_payload, dict):
                # Direct evolution data
                if "evolution" in message_payload:
                    return message_payload.get("evolution", {})
                    
                # Check for separate credential keys
                api_key = message_payload.get("evolution_api_key") or message_payload.get("api_key")
                base_url = message_payload.get("evolution_base_url") or message_payload.get("base_url")
                instance_name = message_payload.get("evolution_instance") or message_payload.get("instance_name")
                
                if api_key:
                    evolution_data["api_key"] = api_key
                if base_url:
                    evolution_data["base_url"] = base_url
                if instance_name:
                    evolution_data["instance_name"] = instance_name
                    
                # Check in whatsapp_payload or message_content
                for key in ["whatsapp_payload", "message_content"]:
                    nested_payload = message_payload.get(key, {})
                    if isinstance(nested_payload, dict):
                        if "evolution" in nested_payload:
                            nested_evolution = nested_payload.get("evolution", {})
                            # Only use values that aren't already set
                            if not evolution_data.get("api_key") and "api_key" in nested_evolution:
                                evolution_data["api_key"] = nested_evolution["api_key"]
                            if not evolution_data.get("base_url") and "base_url" in nested_evolution:
                                evolution_data["base_url"] = nested_evolution["base_url"]
                            if not evolution_data.get("instance_name") and "instance_name" in nested_evolution:
                                evolution_data["instance_name"] = nested_evolution["instance_name"]
            
            # Return the data if we found any, otherwise None
            return evolution_data if evolution_data else None
                
        except Exception as e:
            logger.error(f"Error extracting Evolution data: {str(e)}")
            return None
    
    def _extract_sender_number(self, message_payload: Dict[str, Any]) -> str:
        """Extract the sender's phone number from the message payload.
        
        Args:
            message_payload: The message payload containing sender information
            
        Returns:
            str: The extracted phone number or a default value
        """
        try:
            # Extract remoteJid based on standard Evolution API structure
            remote_jid = None
            
            # First check for data.key.remoteJid structure (default Evolution API format)
            if isinstance(message_payload, dict):
                data = message_payload.get('data', {})
                if isinstance(data, dict) and 'key' in data:
                    remote_jid = data.get('key', {}).get('remoteJid')
            
            # If not found, look for message_content.whatsapp_raw_payload structure
            if not remote_jid and isinstance(message_payload, dict):
                whatsapp_payload = message_payload.get('message_content', {}).get('whatsapp_raw_payload', {})
                if isinstance(whatsapp_payload, dict):
                    data = whatsapp_payload.get('data', {})
                    if isinstance(data, dict) and 'key' in data:
                        remote_jid = data.get('key', {}).get('remoteJid')
            
            # Clean the phone number (remove @s.whatsapp.net if present)
            if remote_jid:
                import re
                cleaned_number = re.sub(r'@.*$', '', remote_jid)
                return cleaned_number
            
            return "unknown_number"
                
        except Exception as e:
            logger.error(f"Error extracting sender number: {str(e)}")
            return "unknown_number" 