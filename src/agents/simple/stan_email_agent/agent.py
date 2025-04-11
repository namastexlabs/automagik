"""StanAgentAgent implementation with PydanticAI.

This module provides a StanAgentAgent class that uses PydanticAI for LLM integration
and inherits common functionality from AutomagikAgent.
"""
import datetime
import logging
import traceback
from typing import Dict, Optional

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
                
            user_info = None
                
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
                    black_pearl_client = await blackpearl.get_cliente(ctx=self.context, cliente_id=email_agent_result.data.black_pearl_client_id)
                    black_pearl_contact = await blackpearl.get_contato(ctx=self.context, contato_id=black_pearl_client.contatos[0])
                    
                    thread['extracted_info'] = email_agent_result.data
                    thread['black_pearl_client'] = black_pearl_client
                    thread['black_pearl_contact'] = black_pearl_contact
                    
                    # Update contato and cliente with extracted information
                    black_pearl_contact.status_aprovacao = email_agent_result.data.approval_status
                    black_pearl_client.status_aprovacao = email_agent_result.data.approval_status
                    black_pearl_client.valor_limite_credito = email_agent_result.data.credit_score
                    black_pearl_contact.detalhes_aprovacao = email_agent_result.data.extra_information
                    
                    # Extract user_id from wpp_session_id which has format "userid_agentid"
                    user_id = black_pearl_contact.wpp_session_id.split('_')[0] if black_pearl_contact.wpp_session_id else None
                    agent_id = black_pearl_contact.wpp_session_id.split('_')[1] if black_pearl_contact.wpp_session_id else None
                    user_id = int(user_id)
                    agent_id = int(agent_id)
                    
                    user = get_user(user_id=user_id) if user_id else None
                    user.email = black_pearl_client.email
                    
                    # Check if we've already sent a BP analysis email to this user
                    if hasattr(user, 'user_data') and user.user_data and user.user_data.get('bp_analysis_email_message_sent'):
                        logger.info(f"User {user_id} has already received BP analysis email. Skipping message.")
                        # Still mark the thread as processed
                        thread['processed'] = True
                        continue
                    
                    
                    # Prepare string with user information and approval status
                    user_info = f"Nome: {black_pearl_contact.nome} Email: {black_pearl_client.email} Telefone: {user.phone_number}"
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
                  
                    if black_pearl_contact.status_aprovacao == StatusAprovacaoEnum.APPROVED:
                        data_aprovacao = datetime.datetime.now()
                        black_pearl_contact.data_aprovacao = data_aprovacao
                        black_pearl_client.data_aprovacao = data_aprovacao
                        
                        # Check if cliente already has codigo_cliente_omie before finalizing
                        if not black_pearl_client.codigo_cliente_omie:
                            logger.info(f"Finalizing client registration for client_id: {black_pearl_client.id}")
                            await blackpearl.finalizar_cadastro(ctx=self.context, cliente_id=black_pearl_client.id)
                        else:
                            logger.info(f"Client already has codigo_cliente_omie: {black_pearl_client.codigo_cliente_omie}, skipping finalization")
                    
                    try:
                        await blackpearl.update_contato(ctx=self.context, contato_id=black_pearl_contact.id, contato=black_pearl_contact)
                    except Exception as e:
                        logger.error(f"Error updating contact: {str(e)}")
                    
                    try:
                        await blackpearl.update_cliente(ctx=self.context, cliente_id=black_pearl_client.id, cliente=black_pearl_client)
                        
                    except Exception as e:
                        logger.error(f"Error updating client: {str(e)}")
                    
                    try:
                        update_user(user=user)
                    except Exception as e:
                        logger.error(f"Error updating user: {str(e)}")
                        
                    if not user.user_data.get('bp_analysis_email_message_sent', False):
                        await evolution.send_message(ctx=self.context, phone=user.user_data['whatsapp_id'], message=message)
                        
                        update_user_data(user_id=user.id, data_updates={
                            "blackpearl_contact_id": black_pearl_contact.id,
                            "blackpearl_cliente_id": black_pearl_client.id,
                            "bp_analysis_email_message_sent": True
                            
                        })
                        logger.info(f"Updated user_data with bp_analysis_email_message_sent flag for user ID: {user.id}")                   
                    # Mark the thread as processed
                    thread['processed'] = True
                    
            # For each processed thread mark the email as read
            for thread in self.context['unread_threads']:
                if thread['processed']:
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
            if processed_count > 0:
                message_summary += "\n\nDetalhes dos emails processados:"
                for thread in self.context['unread_threads']:
                    if thread.get('processed', False):
                        # Extract useful information from the thread
                        subject = thread.get('messages', [{}])[0].get('subject', 'Sem assunto')
                        sender = thread.get('messages', [{}])[0].get('from', 'Remetente desconhecido')
                        user_info = user_info
                        user_name = black_pearl_contact.nome
                        user_phone = black_pearl_contact.telefone
                        status_aprovacao = black_pearl_client.status_aprovacao
                        
                        message_summary += f"\n- Email: '{subject}' de {sender}"
                        message_summary += f"\n  Usuário: {user_name} ({user_phone})"
                        message_summary += f"\n  Status: {status_aprovacao}"


            create_memory(
                user_id=user_id,
                agent_id=agent_id,
                content=message_summary,
                type="recent_approval_email_message"
            )
            
            
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
    