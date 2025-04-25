"""StanAgentAgent implementation with PydanticAI.

This module provides a StanAgentAgent class that uses PydanticAI for LLM integration
and inherits common functionality from AutomagikAgent.
"""
import datetime
import logging
import traceback
from typing import Dict, Optional, List, Any, Union

from pydantic_ai import Agent
from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.models.response import AgentResponse
from src.agents.simple.stan_email_agent.prompts.prompt import AGENT_PROMPT
from src.agents.simple.stan_email_agent.specialized import aproval_status_message_generator
from src.db.repository import create_memory, list_messages, list_sessions, update_user
from src.db.repository.user import get_user, update_user_data
from src.memory.message_history import MessageHistory

from src.agents.common.dependencies_helper import (
    parse_model_settings,
    create_model_settings,
    create_usage_limits,
    get_model_name
)
from src.tools import blackpearl, evolution
from src.tools.blackpearl.schema import StatusAprovacaoEnum
from src.tools.gmail import fetch_emails, mark_emails_read
from src.tools.gmail.schema import FetchEmailsInput
from src.tools.gmail.tool import fetch_all_emails_from_thread_by_email_id

# Import Memory class 
from src.db.models import Memory

logger = logging.getLogger(__name__)

class StanEmailAgent(AutomagikAgent):
    """StanEmailAgent implementation using PydanticAI.
    
    This agent provides a basic implementation that follows the PydanticAI
    conventions for multimodal support and tool calling.
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize the StanEmailAgent.
        
        Args:
            config: Dictionary with configuration options
        """
        from src.agents.simple.stan_email_agent.prompts.prompt import AGENT_PROMPT
        
        # Initialize the base agent
        super().__init__(config, AGENT_PROMPT)
        
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
        
        logger.info("StanEmailAgent initialized successfully")
    
    async def _initialize_pydantic_agent(self) -> None:
        """Initialize the underlying PydanticAI agent."""
        if self._agent_instance is not None:
            return
            
        # Get model configuration
        model_name = self.dependencies.model_name
        model_settings = create_model_settings(self.dependencies.model_settings)
        
        from pydantic import BaseModel, Field
        
        class ExtractedLeadEmailInfo(BaseModel):
            """Pydantic model for storing extracted information from Stan lead emails."""
            
            black_pearl_client_id: str = Field(
                description="The client ID from Black Pearl system"
            )
            approval_status: StatusAprovacaoEnum = Field(
                description="Current approval status of the lead"
            )
            credit_score: int = Field(
                description="Credit score of the lead as mentioned in the email"
            )
            need_extra_user_info: bool = Field(
                description="Flag indicating if additional information is needed from the user",
                default=False
            )
            extra_information: str = Field(
                description="Any additional relevant information extracted from the email",
                default=""
            )
            
            
        try:
            # Create agent instance
            self._agent_instance = Agent(
                model="google-gla:gemini-2.0-flash",
                system_prompt=self.system_prompt,
                result_type=ExtractedLeadEmailInfo,
                model_settings=model_settings,
                deps_type=AutomagikAgentsDependencies
            )
            
            logger.info(f"Initialized agent with model: {model_name} ")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {str(e)}")
            raise
    
    def _extract_contact_id(self, client_data: Any) -> Optional[Union[int, str]]:
        """Helper method to extract contact ID from client data.
        
        This handles both the old 'contatos' and new 'contatos_ids' field names,
        and works with both dictionary and object responses.
        
        Args:
            client_data: The client data (dict or object) from BlackPearl
            
        Returns:
            The contact ID or None if not found
        """
        # Initialize contact ID to None
        contact_id = None
        
        # Log the input for debugging
        logger.info(f"Extracting contact ID from client data type: {type(client_data)}")
        if client_data is None:
            logger.warning("Client data is None")
            return None
            
        try:
            # Handle dictionary-style responses
            if isinstance(client_data, dict):
                logger.info(f"Client data is dictionary with keys: {list(client_data.keys())}")
                
                # Check if we have contatos field in the response (API response)
                if 'contatos' in client_data and client_data['contatos']:
                    contacts = client_data['contatos']
                    logger.info(f"Found 'contatos' field with {len(contacts)} contacts")
                    
                    if contacts and len(contacts) > 0:
                        contact = contacts[0]  # Take the first contact
                        logger.info(f"First contact type: {type(contact)}, value: {contact}")
                        
                        if isinstance(contact, dict) and 'id' in contact:
                            contact_id = contact['id']
                            logger.info(f"Extracted contact ID from dictionary: {contact_id}")
                        elif hasattr(contact, 'id'):  # Handle Pydantic model case
                            contact_id = getattr(contact, 'id')
                            logger.info(f"Extracted contact ID from Pydantic model: {contact_id}")
                        else:
                            contact_id = contact
                            logger.info(f"Using contact as ID directly: {contact_id}")
                            
                # Check if we have contatos_ids field (new field name)
                elif 'contatos_ids' in client_data and client_data['contatos_ids']:
                    contact_ids = client_data['contatos_ids']
                    logger.info(f"Found 'contatos_ids' field: {contact_ids}")
                    
                    if contact_ids and len(contact_ids) > 0:
                        contact_id = contact_ids[0]
                        logger.info(f"Extracted contact ID from contatos_ids: {contact_id}")
            
            # Handle object-style responses (Pydantic model)
            else:
                logger.info(f"Client data is object with attributes: {dir(client_data)}")
                
                # First priority: check for contatos attribute (now that we have this field)
                if hasattr(client_data, 'contatos') and getattr(client_data, 'contatos'):
                    contacts = getattr(client_data, 'contatos')
                    logger.info(f"Found 'contatos' attribute with value type: {type(contacts)}")
                    
                    if contacts and len(contacts) > 0:
                        contact = contacts[0]  # Take the first contact
                        logger.info(f"First contact type: {type(contact)}, value: {contact}")
                        
                        if isinstance(contact, dict) and 'id' in contact:
                            contact_id = contact['id']
                            logger.info(f"Extracted contact ID from object's dictionary: {contact_id}")
                        elif hasattr(contact, 'id'):  # Handle Pydantic model case
                            contact_id = getattr(contact, 'id')
                            logger.info(f"Extracted contact ID from object's Pydantic model: {contact_id}")
                        else:
                            contact_id = contact
                            logger.info(f"Using object's contact as ID directly: {contact_id}")
                
                # Second priority: check for contatos_ids attribute 
                elif hasattr(client_data, 'contatos_ids') and getattr(client_data, 'contatos_ids'):
                    contact_ids = getattr(client_data, 'contatos_ids')
                    logger.info(f"Found 'contatos_ids' attribute with value: {contact_ids}")
                    
                    if contact_ids and len(contact_ids) > 0:
                        contact_id = contact_ids[0]
                        logger.info(f"Extracted contact ID from model's contatos_ids: {contact_id}")
                
        except Exception as e:
            logger.error(f"Error extracting contact ID: {str(e)}")
            logger.error(traceback.format_exc())
            
        logger.info(f"Final extracted contact ID: {contact_id}")
        return contact_id

    def _safe_get_attribute(self, obj: Any, attr: str, default: Any = None) -> Any:
        """Safely get an attribute from either a dictionary or an object.
        
        Args:
            obj: The object or dictionary to get the attribute from
            attr: The attribute or key name
            default: Default value if the attribute is not found
            
        Returns:
            The attribute value or default
        """
        if obj is None:
            return default
            
        # If it's a dictionary, use dictionary access
        if isinstance(obj, dict):
            return obj.get(attr, default)
            
        # If it's an object, use getattr
        if hasattr(obj, attr):
            return getattr(obj, attr)
            
        return default
        
    def _safe_set_attribute(self, obj: Any, attr: str, value: Any) -> None:
        """Safely set an attribute on either a dictionary or an object.
        
        Args:
            obj: The object or dictionary to set the attribute on
            attr: The attribute or key name
            value: The value to set
        """
        if obj is None:
            return
            
        # If it's a dictionary, use dictionary access
        if isinstance(obj, dict):
            obj[attr] = value
            return
            
        # If it's an object, use setattr
        setattr(obj, attr, value)
        
    async def run(self, input_text: str, *, multimodal_content=None, system_message=None, message_history_obj: Optional[MessageHistory] = None,
                 channel_payload: Optional[dict] = None,
                 message_limit: Optional[int] = 20) -> AgentResponse:
        """Run the agent with the given input.
        
        Args:
            input_text: The text input from the user
            multimodal_content: Optional multimodal content
            system_message: Optional system message override
            message_history_obj: Optional message history object
            channel_payload: Optional channel-specific payload
            message_limit: Maximum number of messages to include in history
            
        Returns:
            AgentResponse with the agent's response
        """
        
        # Create fetch emails input
        fetch_input = FetchEmailsInput(
            subject_filter="[STAN] - Novo Lead",
            max_results=10
        )
        
        # Call the fetch_emails function
        logger.info("Fetching Stan lead emails...")
        tool_calls = []
        
        # Record the tool call
        fetch_tool_call = {
            "name": "fetch_emails",
            "parameters": fetch_input.dict(),
            "id": "fetch_emails_1"
        }
        tool_calls.append(fetch_tool_call)
        
        # Execute the tool
        email_agent_result = await fetch_emails(None, fetch_input)
        
        # Initialize user variables
        current_user_id = None
        current_agent_id = None
        current_user_info = None
        current_contact = None
        current_client = None
        
        # Process the results - extract threads for each unread email
        if email_agent_result.get('success', False):
            emails = email_agent_result.get('emails', [])
            logger.info(f"Found {len(emails)} unread Stan lead emails")
                
            if len(emails) == 0:
                return AgentResponse(
                    text="Nenhum email encontrado",
                    success=True,
                    tool_calls=tool_calls,
                    tool_outputs=[],
                    raw_message=email_agent_result,
                    system_prompt=AGENT_PROMPT,
                )
                
            # Collect all threads
            all_threads = []
            processed_thread_ids = set()  # Track already processed thread IDs
            
            # Process each unread email
            for email in emails:
                email_id = email.get('id')
                subject = email.get('subject')
                thread_id = email.get('thread_id')
                
                # Skip if we've already processed this thread
                if thread_id in processed_thread_ids:
                    logger.info(f"Skipping duplicate thread ID: {thread_id}")
                    continue
                
                logger.info(f"Fetching thread for email ID: {email_id}, Subject: {subject}, Thread ID: {thread_id}")
                
                # Fetch all emails in this thread
                thread_result = await fetch_all_emails_from_thread_by_email_id(None, email_id)
                
                if thread_result.get('success', False):
                    thread_emails = thread_result.get('emails', [])
                    logger.info(f"Found {len(thread_emails)} emails in thread")
                    
                    # Sort emails by date to maintain conversation order
                    thread_emails.sort(key=lambda x: x.get('date'))
                    
                    thread_info = {
                        'subject': subject,
                        'email_id': email_id,
                        'thread_id': thread_id,
                        'messages': []
                    }
                    
                    # Extract text from each email in the thread
                    for thread_email in thread_emails:
                        thread_info['messages'].append({
                            'email_id': thread_email.get('id'),
                            'from': thread_email.get('from_email'),
                            'date': thread_email.get('date'),
                            'body': thread_email.get('body'),
                            'subject': subject,
                            'labels': thread_email.get('raw_data', {}).get('labels', []),
                        })
                    
                    # Join all thread emails into a single string ordered by date
                    thread_info['full_thread_body'] = '\n'.join([msg['body'] for msg in thread_info['messages']])
                    
                    all_threads.append(thread_info)
                    processed_thread_ids.add(thread_id)  # Mark this thread as processed
                else:
                    logger.error(f"Failed to fetch thread for email {email_id}: {thread_result.get('error')}")

            # Add the thread information to the context
            self.context['unread_threads'] = all_threads
            logger.info(f"Processed {len(all_threads)} unique email threads in total")
        else:
            logger.error(f"Failed to fetch emails: {email_agent_result.get('error')}")

        
        # Initialize the agent
        await self._initialize_pydantic_agent()
        
        try:
            
            # Process each thread
            for thread in self.context['unread_threads']:
                thread_info = thread['full_thread_body']
                email_agent_result = await self._agent_instance.run(
                    user_prompt=f"Extract information from the following email thread: {thread_info}"
                )
                    
                # Update the thread with extracted information
                black_pearl_client = None
                if email_agent_result.data and email_agent_result.data.black_pearl_client_id: 
                    try:
                        black_pearl_client = await blackpearl.get_cliente(ctx=self.context, cliente_id=email_agent_result.data.black_pearl_client_id)
                        
                        # Log the response for debugging
                        logger.info(f"Got BlackPearl client response of type: {type(black_pearl_client)}")
                        if isinstance(black_pearl_client, dict):
                            logger.info(f"Client as dict with keys: {list(black_pearl_client.keys())}")
                            if 'contatos' in black_pearl_client:
                                logger.info(f"Raw contatos value: {black_pearl_client['contatos']}")
                        else:
                            # For Pydantic models or other objects
                            logger.info(f"Client attributes: {dir(black_pearl_client)}")
                            if hasattr(black_pearl_client, 'contatos'):
                                logger.info(f"Raw contatos value: {getattr(black_pearl_client, 'contatos')}")
                        
                        # Extract contact ID using the helper method
                        contact_id = self._extract_contact_id(black_pearl_client)
                        
                        if not contact_id:
                            logger.warning(f"No contacts found for client ID: {self._safe_get_attribute(black_pearl_client, 'id')}")
                            thread['processed'] = False
                            continue
                        
                        black_pearl_contact = await blackpearl.get_contato(ctx=self.context, contato_id=contact_id)
                        
                        thread['extracted_info'] = email_agent_result.data
                        thread['black_pearl_client'] = black_pearl_client
                        thread['black_pearl_contact'] = black_pearl_contact
                        
                        # Update contato and cliente with extracted information
                        self._safe_set_attribute(black_pearl_contact, 'status_aprovacao', email_agent_result.data.approval_status)
                        self._safe_set_attribute(black_pearl_client, 'status_aprovacao', email_agent_result.data.approval_status)
                        self._safe_set_attribute(black_pearl_client, 'valor_limite_credito', email_agent_result.data.credit_score)
                        self._safe_set_attribute(black_pearl_contact, 'detalhes_aprovacao', email_agent_result.data.extra_information)
                        
                        # Track current client and contact for summary
                        current_client = black_pearl_client
                        current_contact = black_pearl_contact
                        
                        # Extract user_id from wpp_session_id which has format "userid_agentid"
                        # Handle case where wpp_session_id may contain non-numeric parts
                        user_id = None
                        agent_id = None
                        
                        wpp_session_id = self._safe_get_attribute(black_pearl_contact, 'wpp_session_id')
                        if wpp_session_id:
                            try:
                                session_parts = wpp_session_id.split('_')
                                if len(session_parts) >= 2:
                                    # Only try to convert to int if it looks like a number
                                    if session_parts[0].isdigit():
                                        user_id = int(session_parts[0])
                                    else:
                                        user_id = session_parts[0]
                                        
                                    if session_parts[1].isdigit():
                                        agent_id = int(session_parts[1])
                                    else:
                                        agent_id = session_parts[1]
                                        
                                # Track current user ID and agent ID for later use
                                current_user_id = user_id
                                current_agent_id = agent_id
                            except Exception as e:
                                logger.warning(f"Error parsing wpp_session_id: {str(e)}")
                    
                        user = get_user(user_id=user_id) if user_id else None
                        if user:
                            user.email = self._safe_get_attribute(black_pearl_client, 'email')
                            current_user_info = user
                        
                            # Check if we've already sent a BP analysis email to this user
                            if hasattr(user, 'user_data') and user.user_data and user.user_data.get('bp_analysis_email_message_sent'):
                                logger.info(f"User {user_id} has already received BP analysis email. Skipping message.")
                                # Still mark the thread as processed
                                thread['processed'] = True
                                continue
                            
                            # Prepare string with user information and approval status
                            user_info = (f"Nome: {self._safe_get_attribute(black_pearl_contact, 'nome')} "
                                        f"Email: {self._safe_get_attribute(black_pearl_client, 'email')} "
                                        f"Telefone: {user.phone_number}")
                            approval_status_info = f"Status de aprovação: {email_agent_result.data.approval_status}"
                            credit_score_info = f"Pontuação de crédito: {email_agent_result.data.credit_score}"
                            extra_information = f"Informações extras: {email_agent_result.data.extra_information}"
                            
                            user_sessions = list_sessions(user_id=user_id, agent_id=agent_id)
                            user_message_history = []
                            
                            for session in user_sessions:
                                # Get all messages for this session
                                session_messages = list_messages(session_id=session.id)
                                user_message_history.extend(session_messages)
                            
                            # Format the conversation history
                            earlier_conversations = "\n".join([f"{message.role}: {message.text_content}" 
                                                            for message in user_message_history 
                                                            if message and message.text_content and hasattr(message, 'role') and hasattr(message, 'text_content')])
                            
                            message_text = f"<history>Este é o histórico de conversas do usuário:\n\n\n{earlier_conversations}</history>\n\n\n"
                            message_text += f"<current_user_info>Informações do usuário e status de aprovação:\n{user_info}\n{approval_status_info}\n{credit_score_info}\n{extra_information}</current_user_info>"
                            message = await aproval_status_message_generator.generate_approval_status_message(message_text)
                        
                            client_status_aprovacao = self._safe_get_attribute(black_pearl_contact, 'status_aprovacao')
                            if client_status_aprovacao == StatusAprovacaoEnum.APPROVED:
                                data_aprovacao = datetime.datetime.now()
                                self._safe_set_attribute(black_pearl_contact, 'data_aprovacao', data_aprovacao)
                                self._safe_set_attribute(black_pearl_client, 'data_aprovacao', data_aprovacao)
                                
                                # Check if cliente already has codigo_cliente_omie before finalizing
                                if not self._safe_get_attribute(black_pearl_client, 'codigo_cliente_omie'):
                                    client_id = self._safe_get_attribute(black_pearl_client, 'id')
                                    logger.info(f"Finalizing client registration for client_id: {client_id}")
                                    await blackpearl.finalizar_cadastro(ctx=self.context, cliente_id=client_id)
                                else:
                                    codigo_cliente = self._safe_get_attribute(black_pearl_client, 'codigo_cliente_omie')
                                    logger.info(f"Client already has codigo_cliente_omie: {codigo_cliente}, skipping finalization")
                            
                            try:
                                contact_id = self._safe_get_attribute(black_pearl_contact, 'id')
                                await blackpearl.update_contato(ctx=self.context, contato_id=contact_id, contato=black_pearl_contact)
                            except Exception as e:
                                logger.error(f"Error updating contact: {str(e)}")
                            
                            try:
                                client_id = self._safe_get_attribute(black_pearl_client, 'id')
                                await blackpearl.update_cliente(ctx=self.context, cliente_id=client_id, cliente=black_pearl_client)
                                
                            except Exception as e:
                                logger.error(f"Error updating client: {str(e)}")
                            
                            try:
                                update_user(user=user)
                            except Exception as e:
                                logger.error(f"Error updating user: {str(e)}")
                                
                            if not user.user_data.get('bp_analysis_email_message_sent', False):
                                await evolution.send_message(ctx=self.context, phone=user.user_data['whatsapp_id'], message=message)
                                
                                update_user_data(user_id=user.id, data_updates={
                                    "blackpearl_contact_id": self._safe_get_attribute(black_pearl_contact, 'id'),
                                    "blackpearl_cliente_id": self._safe_get_attribute(black_pearl_client, 'id'),
                                    "bp_analysis_email_message_sent": True
                                    
                                })
                                logger.info(f"Updated user_data with bp_analysis_email_message_sent flag for user ID: {user.id}")
                        else:
                            logger.warning(f"No user found for user_id: {user_id}")
                            
                        # Mark the thread as processed
                        thread['processed'] = True
                        
                    except Exception as e:
                        logger.error(f"Error processing client or contact: {str(e)}")
                        thread['processed'] = False
                        continue
                    
            # For each processed thread mark the email as read
            for thread in self.context['unread_threads']:
                if thread.get('processed', True):
                    # Extract message IDs from the thread's messages
                    message_ids = [message.get('email_id') for message in thread.get('messages', []) if message.get('email_id')]
                    # Mark all messages in the thread as read
                    await mark_emails_read(ctx=self.context, message_ids=message_ids)

            # Final message summary with what was processed
            processed_count = len([t for t in self.context['unread_threads'] if t.get('processed', False)])
            total_count = len(self.context['unread_threads'])
            
            # Create a more detailed summary with email information
            message_summary = f"Processados {processed_count} de {total_count} threads de email."
            
            # Add details about each processed thread
            if processed_count > 0 and current_contact and current_client:
                message_summary += "\n\nDetalhes dos emails processados:"
                for thread in self.context['unread_threads']:
                    if thread.get('processed', False):
                        # Extract useful information from the thread
                        subject = thread.get('messages', [{}])[0].get('subject', 'Sem assunto')
                        sender = thread.get('messages', [{}])[0].get('from', 'Remetente desconhecido')
                        user_name = self._safe_get_attribute(current_contact, 'nome', 'Nome não encontrado')
                        user_phone = self._safe_get_attribute(current_contact, 'telefone', 'Telefone não encontrado')
                        status_aprovacao = self._safe_get_attribute(current_client, 'status_aprovacao', 'Status não encontrado')
                        
                        message_summary += f"\n- Email: '{subject}' de {sender}"
                        message_summary += f"\n  Usuário: {user_name} ({user_phone})"
                        message_summary += f"\n  Status: {status_aprovacao}"

            # Create a Memory object only if we have user_id
            if current_user_id:
                approval_memory = Memory(
                    name="recent_approval_email_message",
                    content=message_summary,
                    user_id=current_user_id,
                    agent_id=current_agent_id,
                    read_mode="private",
                    access="read_write"
                )
                
                # Create the memory
                create_memory(approval_memory)
            
            # Create response
            return AgentResponse(
                text=message_summary,
                success=True,
                tool_calls=tool_calls,
                tool_outputs=[],
                raw_message=self.context['unread_threads'],
                system_prompt=AGENT_PROMPT,
            )
        except Exception as e:
            logger.error(f"Error running agent: {str(e)}")
            logger.error(traceback.format_exc())
            return AgentResponse(
                text=f"Error: {str(e)}",
                success=False,
                error_message=str(e),
                raw_message={"context": self.context}
            )
    