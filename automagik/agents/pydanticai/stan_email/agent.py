"""Enhanced StanEmail Agent implementation using new framework patterns.

This demonstrates the dramatic reduction possible when using specialized agent classes
and centralized BlackPearl tools for email processing workflows.
"""
import logging
import datetime
import asyncio
from typing import Dict, Optional, Any

from pydantic import BaseModel, Field
from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.common.tool_wrapper_factory import ToolWrapperFactory
from automagik.agents.models.response import AgentResponse
from automagik.memory.message_history import MessageHistory
from automagik.db.models import Memory
from automagik.db.repository import create_memory, list_messages, list_sessions, update_user
from automagik.db.repository.user import get_user, update_user_data
from automagik.tools import blackpearl, evolution
from automagik.tools.blackpearl.schema import StatusAprovacaoEnum
from automagik.tools.gmail import fetch_emails, mark_emails_read
from automagik.tools.gmail.schema import FetchEmailsInput
from automagik.tools.gmail.tool import fetch_all_emails_from_thread_by_email_id
from .specialized import aproval_status_message_generator
from .prompts.prompt import AGENT_PROMPT

logger = logging.getLogger(__name__)


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


class StanEmailAgent(AutomagikAgent):
    """Enhanced StanEmail Agent with specialized email processing capabilities.
    
    Dramatically reduces verbosity from 679 lines while maintaining all
    BlackPearl integration, email processing, and user notification logic.
    """
    
    # Configuration - replaces extensive boilerplate
    default_model = "google-gla:gemini-2.0-flash"
    result_type = ExtractedLeadEmailInfo
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize StanEmail Agent with automatic setup."""
        if config is None:
            config = {}

        config.setdefault("enable_multi_prompt", True)

        super().__init__(config)

        # set primary prompt; MultiPromptManager will load by status later
        self._code_prompt_text = AGENT_PROMPT

        # dependencies & default tools
        self.dependencies = self.create_default_dependencies()
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        self.tool_registry.register_default_tools(self.context)
        
        # Register multimodal analysis tools
        self._register_multimodal_tools()
        
        # Register specialized email processing tools
        self._register_email_tools()
        
        logger.info("Enhanced StanEmail Agent initialized")
    
    def _register_email_tools(self) -> None:
        """Register email-specific tools using the wrapper factory."""
        email_tools = {
            'fetch_emails': fetch_emails,
            'mark_emails_read': mark_emails_read,
            'fetch_all_emails_from_thread_by_email_id': fetch_all_emails_from_thread_by_email_id,
            'aproval_status_message_generator': aproval_status_message_generator.generate_approval_status_message
        }
        
        for tool_name, tool_func in email_tools.items():
            wrapper = ToolWrapperFactory.create_context_wrapper(tool_func, self.context)
            self.tool_registry.register_tool(wrapper)
    
    def _extract_contact_id(self, client_data: Any) -> Optional[int]:
        """Helper method to extract contact ID from client data."""
        if not client_data:
            return None
            
        try:
            # Handle dictionary responses
            if isinstance(client_data, dict):
                if 'contatos' in client_data and client_data['contatos']:
                    contacts = client_data['contatos']
                    if contacts and len(contacts) > 0:
                        contact = contacts[0]
                        return contact.get('id') if isinstance(contact, dict) else contact
                        
                elif 'contatos_ids' in client_data and client_data['contatos_ids']:
                    return client_data['contatos_ids'][0]
            
            # Handle object responses
            else:
                if hasattr(client_data, 'contatos') and getattr(client_data, 'contatos'):
                    contacts = getattr(client_data, 'contatos')
                    if contacts and len(contacts) > 0:
                        contact = contacts[0]
                        return contact.id if hasattr(contact, 'id') else contact
                        
                elif hasattr(client_data, 'contatos_ids') and getattr(client_data, 'contatos_ids'):
                    return getattr(client_data, 'contatos_ids')[0]
                    
        except Exception as e:
            logger.error(f"Error extracting contact ID: {str(e)}")
            
        return None
    
    def _safe_get_attribute(self, obj: Any, attr: str, default: Any = None) -> Any:
        """Safely get an attribute from either a dictionary or an object."""
        if obj is None:
            return default
        return obj.get(attr, default) if isinstance(obj, dict) else getattr(obj, attr, default)
    
    def _safe_set_attribute(self, obj: Any, attr: str, value: Any) -> None:
        """Safely set an attribute on either a dictionary or an object."""
        if obj is None:
            return
        if isinstance(obj, dict):
            obj[attr] = value
        else:
            setattr(obj, attr, value)
    
    async def _fetch_and_process_email_threads(self) -> list:
        """Fetch and process Stan lead email threads."""
        # Create fetch emails input
        fetch_input = FetchEmailsInput(
            subject_filter="[STAN] - Novo Lead",
            max_results=10
        )
        
        # Fetch emails
        logger.info("Fetching Stan lead emails...")
        email_result = await fetch_emails(None, fetch_input)
        
        if not email_result.get('success', False):
            logger.error(f"Failed to fetch emails: {email_result.get('error')}")
            return []
        
        emails = email_result.get('emails', [])
        logger.info(f"Found {len(emails)} unread Stan lead emails")
        
        if not emails:
            return []
        
        # Process email threads
        all_threads = []
        processed_thread_ids = set()
        
        for email in emails:
            email_id = email.get('id')
            subject = email.get('subject')
            thread_id = email.get('thread_id')
            
            if thread_id in processed_thread_ids:
                continue
            
            logger.info(f"Processing thread: {thread_id}")
            
            # Fetch thread details
            thread_result = await fetch_all_emails_from_thread_by_email_id(None, email_id)
            
            if thread_result.get('success', False):
                thread_emails = thread_result.get('emails', [])
                thread_emails.sort(key=lambda x: x.get('date'))
                
                thread_info = {
                    'subject': subject,
                    'email_id': email_id,
                    'thread_id': thread_id,
                    'messages': [
                        {
                            'email_id': email.get('id'),
                            'from': email.get('from_email'),
                            'date': email.get('date'),
                            'body': email.get('body'),
                            'subject': subject,
                            'labels': email.get('raw_data', {}).get('labels', [])
                        }
                        for email in thread_emails
                    ]
                }
                
                thread_info['full_thread_body'] = '\n'.join([msg['body'] for msg in thread_info['messages']])
                all_threads.append(thread_info)
                processed_thread_ids.add(thread_id)
        
        return all_threads
    
    async def _process_thread_with_llm(self, thread: dict) -> Optional[ExtractedLeadEmailInfo]:
        """Process a single email thread with LLM extraction."""
        try:
            result = await self._agent_instance.run(
                user_prompt=f"Extract information from the following email thread: {thread['full_thread_body']}"
            )
            return result.output
        except Exception as e:
            logger.error(f"Error processing thread with LLM: {str(e)}")
            return None
    
    async def _update_blackpearl_entities(self, extracted_info: ExtractedLeadEmailInfo, 
                                        client: Any, contact: Any) -> None:
        """Update BlackPearl client and contact entities with extracted information."""
        # Set attributes
        self._safe_set_attribute(contact, 'status_aprovacao', extracted_info.approval_status)
        self._safe_set_attribute(client, 'status_aprovacao', extracted_info.approval_status)
        self._safe_set_attribute(client, 'valor_limite_credito', extracted_info.credit_score)
        self._safe_set_attribute(contact, 'detalhes_aprovacao', extracted_info.extra_information)
        
        # Handle approval date for approved status
        if extracted_info.approval_status == StatusAprovacaoEnum.APPROVED:
            data_aprovacao = datetime.datetime.now()
            self._safe_set_attribute(contact, 'data_aprovacao', data_aprovacao)
            self._safe_set_attribute(client, 'data_aprovacao', data_aprovacao)
            
            # Finalize registration if needed
            if not self._safe_get_attribute(client, 'codigo_cliente_omie'):
                client_id = self._safe_get_attribute(client, 'id')
                await blackpearl.finalizar_cadastro(ctx=self.context, cliente_id=client_id)
        
        # Update both entities in parallel
        contact_id = self._safe_get_attribute(contact, 'id')
        client_id = self._safe_get_attribute(client, 'id')
        
        try:
            await asyncio.gather(
                blackpearl.update_contato(ctx=self.context, contato_id=contact_id, contato=contact),
                blackpearl.update_cliente(ctx=self.context, cliente_id=client_id, cliente=client),
                return_exceptions=True
            )
            logger.info(f"Updated BlackPearl entities for client {client_id}")
        except Exception as e:
            logger.error(f"Error updating BlackPearl entities: {str(e)}")
    
    async def _send_approval_message(self, user: Any, extracted_info: ExtractedLeadEmailInfo,
                                   contact: Any, client: Any) -> None:
        """Send approval status message to user via WhatsApp."""
        if user.user_data.get('bp_analysis_email_message_sent', False):
            logger.info(f"User {user.id} already received BP analysis email. Skipping.")
            return
        
        # Prepare user information
        user_info = (f"Nome: {self._safe_get_attribute(contact, 'nome')} "
                    f"Email: {self._safe_get_attribute(client, 'email')} "
                    f"Telefone: {user.phone_number}")
        
        approval_status_info = f"Status de aprovação: {extracted_info.approval_status}"
        credit_score_info = f"Pontuação de crédito: {extracted_info.credit_score}"
        extra_information = f"Informações extras: {extracted_info.extra_information}"
        
        # Get conversation history
        user_sessions = list_sessions(user_id=user.id, agent_id=self.db_id)
        user_message_history = []
        
        for session in user_sessions:
            session_messages = list_messages(session_id=session.id)
            user_message_history.extend(session_messages)
        
        earlier_conversations = "\n".join([
            f"{message.role}: {message.text_content}" 
            for message in user_message_history 
            if message and message.text_content and hasattr(message, 'role')
        ])
        
        # Generate and send message
        message_text = f"<history>{earlier_conversations}</history>\n\n<current_user_info>{user_info}\n{approval_status_info}\n{credit_score_info}\n{extra_information}</current_user_info>"
        message = await aproval_status_message_generator.generate_approval_status_message(message_text)
        
        await evolution.send_message(ctx=self.context, phone=user.user_data['whatsapp_id'], message=message)
        
        # Update flag
        update_user_data(user_id=user.id, data_updates={"bp_analysis_email_message_sent": True})
        logger.info(f"Sent approval message to user {user.id}")
    
    async def run(
        self, 
        input_text: str, 
        *, 
        multimodal_content=None, 
        system_message=None, 
        message_history_obj: Optional[MessageHistory] = None,
        channel_payload: Optional[dict] = None,
        message_limit: Optional[int] = 20
    ) -> AgentResponse:
        """StanEmail agent run implementation with enhanced email processing."""
        
        # Register prompt and initialize agent
        await self._check_and_register_prompt()
        await self.load_active_prompt_template(status_key="default")
        await self._initialize_pydantic_agent()
        
        try:
            # Fetch and process email threads
            all_threads = await self._fetch_and_process_email_threads()
            
            if not all_threads:
                return AgentResponse(
                    text="Nenhum email encontrado",
                    success=True,
                    tool_calls=[],
                    tool_outputs=[],
                    raw_message={},
                    system_prompt=AGENT_PROMPT
                )
            
            # Process each thread
            processed_count = 0
            current_user_id = None
            
            for thread in all_threads:
                try:
                    # Extract information using LLM
                    extracted_info = await self._process_thread_with_llm(thread)
                    if not extracted_info or not extracted_info.black_pearl_client_id:
                        continue
                    
                    # Get BlackPearl entities
                    client = await blackpearl.get_cliente(ctx=self.context, cliente_id=extracted_info.black_pearl_client_id)
                    contact_id = self._extract_contact_id(client)
                    
                    if not contact_id:
                        continue
                    
                    contact = await blackpearl.get_contato(ctx=self.context, contato_id=contact_id)
                    
                    # Update BlackPearl entities
                    await self._update_blackpearl_entities(extracted_info, client, contact)
                    
                    # Handle user updates and messaging
                    wpp_session_id = self._safe_get_attribute(contact, 'wpp_session_id')
                    if wpp_session_id:
                        user_id = wpp_session_id.split('_')[0] if '_' in wpp_session_id else None
                        if user_id and user_id.isdigit():
                            user_id = int(user_id)
                            current_user_id = user_id
                            
                            user = get_user(user_id=user_id)
                            if user:
                                user.email = self._safe_get_attribute(client, 'email')
                                update_user(user=user)
                                
                                # Update user data
                                update_user_data(user_id=user.id, data_updates={
                                    "blackpearl_contact_id": self._safe_get_attribute(contact, 'id'),
                                    "blackpearl_cliente_id": self._safe_get_attribute(client, 'id')
                                })
                                
                                # Send approval message
                                await self._send_approval_message(user, extracted_info, contact, client)
                    
                    # Mark thread as processed
                    thread['processed'] = True
                    processed_count += 1
                    
                    # Mark emails as read
                    message_ids = [msg.get('email_id') for msg in thread.get('messages', []) if msg.get('email_id')]
                    if message_ids:
                        await mark_emails_read(ctx=self.context, message_ids=message_ids)
                        
                except Exception as e:
                    logger.error(f"Error processing thread: {str(e)}")
                    continue
            
            # Create summary
            total_count = len(all_threads)
            message_summary = f"Processados {processed_count} de {total_count} threads de email."
            
            # Store memory if we have a user
            if current_user_id:
                approval_memory = Memory(
                    name="recent_approval_email_message",
                    content=message_summary,
                    user_id=current_user_id,
                    agent_id=self.db_id,
                    read_mode="private",
                    access="read_write"
                )
                create_memory(approval_memory)
            
            return AgentResponse(
                text=message_summary,
                success=True,
                tool_calls=[],
                tool_outputs=[],
                raw_message=all_threads,
                system_prompt=AGENT_PROMPT
            )
            
        except Exception as e:
            logger.error(f"Error running StanEmail agent: {str(e)}")
            return AgentResponse(
                text=f"Error: {str(e)}",
                success=False,
                error_message=str(e),
                raw_message={"context": self.context}
            )

    # ------------------------------------------------------------------
    # BlackPearl helpers (shared with StanAgent)
    # ------------------------------------------------------------------

    async def handle_contact_management(
        self,
        channel_payload: Optional[Dict],
        user_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if not channel_payload:
            return None

        try:
            user_number = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
            user_name = self.context.get("whatsapp_user_name") or self.context.get("user_name")

            if not user_number:
                logger.debug("No user number found; skipping BlackPearl contact management")
                return None

            contact = await self._get_or_create_blackpearl_contact(user_number, user_name, user_id)

            if contact:
                self._update_context_with_contact_info(contact)

                status = contact.get("status_aprovacao", "NOT_REGISTERED")
                await self.load_prompt_by_status(status)

                await self._store_user_memory(user_id, user_name, user_number, contact)

                logger.info(f"BlackPearl Contact: {contact.get('id')} - {user_name}")
                return contact

            await self.load_prompt_by_status("NOT_REGISTERED")
        except Exception as exc:
            logger.error(f"BlackPearl contact management error: {exc}")
            await self.load_prompt_by_status("NOT_REGISTERED")

        return None

    async def _get_or_create_blackpearl_contact(
        self,
        user_number: str,
        user_name: Optional[str],
        user_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        # delegate to existing util
        return await blackpearl.get_or_create_contact(
            self.context,
            user_number,
            user_name,
            user_id,
            self.db_id,
        )

    def _update_context_with_contact_info(self, contact: Dict[str, Any]) -> None:
        self.context["blackpearl_contact_id"] = contact.get("id")

    async def _store_user_memory(
        self,
        user_id: Optional[str],
        user_name: Optional[str],
        user_number: Optional[str],
        contact: Dict[str, Any],
    ) -> None:
        if not self.db_id:
            return

        try:
            info = {
                "user_id": user_id,
                "user_name": user_name,
                "user_number": user_number,
                "blackpearl_contact_id": contact.get("id"),
            }

            from automagik.db.models import Memory
            from automagik.db.repository import create_memory

            memory = Memory(
                name="user_information",
                content=str({k: v for k, v in info.items() if v is not None}),
                user_id=user_id,
                read_mode="system_prompt",
                access="read_write",
                agent_id=self.db_id,
            )
            create_memory(memory=memory)
        except Exception as exc:
            logger.error(f"Error storing StanEmail memory: {exc}")

    def _register_multimodal_tools(self):
        """Register multimodal analysis tools using common helper."""
        from automagik.agents.common.multimodal_helper import register_multimodal_tools
        register_multimodal_tools(self.tool_registry, self.dependencies)


def create_agent(config: Dict[str, str]) -> StanEmailAgent:
    """Factory function to create enhanced StanEmail agent."""
    try:
        return StanEmailAgent(config)
    except Exception as e:
        logger.error(f"Failed to create Enhanced StanEmail Agent: {e}")
        from automagik.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)