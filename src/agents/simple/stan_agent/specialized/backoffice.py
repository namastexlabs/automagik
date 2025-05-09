import os
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
import logging
from typing import Dict, Any, Optional

# Import Blackpearl tools
from src.db.repository.user import get_user, update_user_data
from src.tools.blackpearl import (
    get_clientes, get_cliente, create_cliente, update_cliente,
    get_contatos, get_contato
)

# Import Blackpearl schema
from src.tools.blackpearl.schema import (
    Cliente, Contato, StatusAprovacaoEnum, TipoOperacaoEnum
)

# Import Omie tools
from src.tools.blackpearl.tool import update_contato, verificar_cnpj
from src.tools.omie import (
    search_clients, 
    search_client_by_cnpj
)

# Import Gmail tools
from src.tools.gmail import (
    send_email,
    SendEmailInput
)

# Import necessary schemas
from src.tools.omie.schema import ClientSearchInput

logger = logging.getLogger(__name__)

load_dotenv()

ENVIRIONMENT_MODE = os.getenv("AM_ENV")

async def make_conversation_summary(message_history) -> str:
    """Make a summary of the conversation."""
    if len(message_history) > 0:
        summary_agent = Agent(
            'google-gla:gemini-2.0-flash-exp',
            deps_type=Dict[str, Any],
            result_type=str,
            system_prompt=(
                'You are a specialized summary agent with expertise in summarizing information.'
                'Condense all conversation information into a few bullet points with all relevand lead information.'
            ),
        )
        
        # Convert message history to string for summarization
        # Convert message history to a string format for summarization
        # Handle different message types (text, tool calls, etc.)
        message_history_str = ""
        for msg in message_history:
            if hasattr(msg, 'role') and hasattr(msg, 'content'):
                # Standard text messages
                message_history_str += f"{msg.role}: {msg.content}\n"
            elif hasattr(msg, 'tool_name') and hasattr(msg, 'args'):
                # Tool call messages
                message_history_str += f"tool_call ({msg.tool_name}): {msg.args}\n"
            elif hasattr(msg, 'part_kind') and msg.part_kind == 'text':
                # Text part messages
                message_history_str += f"assistant: {msg.content}\n"
            else:
                # Other message types
                message_history_str += f"message: {str(msg)}\n"
        # Run the summary agent with the message history
        summary_result = await summary_agent.run(user_prompt=message_history_str)
        summary_result_str = summary_result.data
        logger.info(f"Summary result: {summary_result_str}")
        return summary_result_str
    else:
        return ""


async def make_lead_email(lead_information: str, extra_context: str = None) -> str:
    """Make a lead email."""
    """Format lead information into a properly formatted HTML email.
    
    Args:
        lead_information: Information about the lead
        
    Returns:
        Formatted HTML email content
    """
    email_agent = Agent(
        'openai:o3-mini',
        deps_type=Dict[str, Any],
        result_type=str,
        system_prompt=(
            'You are a specialized email formatting agent with expertise in creating professional HTML emails.'
            'Your task is to take lead information and format it into a clean, professional HTML email in Portuguese.'
            'The email should have proper styling, clear sections, and be easy to read.'
            'Use appropriate HTML tags, styling, and formatting to create a visually appealing email.'
            'Ensure all information is properly organized and highlighted.'
            'The email should be suitable for business communication and maintain a professional tone.'
        )
    )
    
    # Run the email formatting agent with the lead information
    email_prompt = (
        f"Format the following lead information into a professional HTML email in Portuguese:\n\n"
        f"{lead_information}\n\n"
        f"Use the cnpj_verification tool to grab more relevant information about the company."
        f"The email should include:\n"
        f"- A clear header with the Solid logo or name\n"
        f"- Well-organized sections for different types of information\n"
        f"- Proper styling (colors, fonts, spacing)\n"
        f"- A professional closing\n"
        f"- Any contact information highlighted\n"
        f"Please provide only the HTML code without explanations."
        f"Here is some extra context that might be relevant to the lead: {extra_context}"
        f"It should follow some structure, like: "
        f"BlackPearl Cliente ID: 1234567890"
        f"Nome: João Silva"
        f"CNPJ: 12.345.678/0001-00"
        f"Email: joao.silva@exemplo.com"
        f"Telefone: +5511987654321"
        f"Empresa: Exemplo Ltda."
        f"Endereço: Rua Exemplo, 123 - São Paulo/SP"
        f"Detalhes: Algumas informações adicionais"
        f"Interesses: Algumas informações sobre os interesses do lead"
    )
    
    email_result = await email_agent.run(user_prompt=email_prompt)
    formatted_email = email_result.data
    
    logger.info("Email formatted successfully")
    return formatted_email

async def backoffice_agent(ctx: RunContext[Dict[str, Any]], input_text: str) -> str:
    """Specialized backoffice agent with access to BlackPearl and Omie tools.
    
    Args:
        input_text: User input text
        context: Optional context dictionary
        
    Returns:
        Response from the agent
    """
    if ctx is None:
        ctx = {}
    
    user_id = ctx.deps.user_id
    stan_agent_id = ctx.deps._agent_id_numeric
    
    message_history = ctx.messages
    logger.info(f"User ID: {user_id}")
    logger.info(f"Stan Agent ID: {stan_agent_id}")
    
    summary_result_str = await make_conversation_summary(message_history)
    
    EXTRA_PROMPT = ""

    # Initialize the agent with appropriate system prompt
    backoffice_agent = Agent(  
        'openai:gpt-4o',
        deps_type=Dict[str, Any],
        result_type=str,
        system_prompt=(
            'You are a specialized backoffice agent with expertise in BlackPearl and Omie APIs, working in direct support of STAN. '
            'Your primary responsibilities include:\n'
            '1. Managing client information - finding, creating, and updating client records\n'
            '2. Processing lead information when received from STAN\n'
            '3. Creating BlackPearl client records with complete information\n'
            '4. Retrieving and providing product information\n'
            '5. Managing orders and sales processes\n'
            'Always use the most appropriate BlackPearl or Omie tool based on the specific request from STAN. '
            'Provide complete yet concise information, focusing on exactly what STAN needs. '
            'Respond in a professional, straightforward manner without unnecessary explanations or apologies. '
            'Your role is to be efficient, accurate, and helpful in managing backend business operations.\n\n'
            'Any problem that you encounter, please add as much information as possible to the error message so it can be fixed.'
            'If info is missing, ask for it. If you dont have the info, say so.'
            'If you need to verify a CNPJ, use the bp_get_info_cnpj tool.'

            f'Here is a summary of the conversation so far: {summary_result_str}'
        ),
    )
    
    # Register BlackPearl client tools
    @backoffice_agent.tool
    async def bp_get_clientes(
        ctx: RunContext[Dict[str, Any]], 
        limit: Optional[int] = None, 
        offset: Optional[int] = None,
        search: Optional[str] = None, 
        ordering: Optional[str] = None,
        cidade: Optional[str] = None,
        estado: Optional[str] = None,
        cnpj: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get list of clients from BlackPearl.
        
        Args:
            limit: Maximum number of clients to return
            offset: Number of clients to skip
            search: Search term to filter clients
            ordering: Field to order results by (example: 'nome' or '-nome' for descending)
            cidade: Filter by city name
            estado: Filter by state code (2 letters)
            cnpj: Filter by CNPJ number
        """
        filters = {}
        if cidade:
            filters["cidade"] = cidade
        if estado:
            filters["estado"] = estado
        if cnpj:
            filters["cnpj"] = cnpj
            
        return await get_clientes(ctx.deps, limit, offset, search, ordering, **filters)
    
    @backoffice_agent.tool
    async def bp_get_cliente(ctx: RunContext[Dict[str, Any]], cliente_id: int) -> Dict[str, Any]:
        """Get specific client details from BlackPearl.
        
        Args:
            cliente_id: The client ID
        """
        return await get_cliente(ctx.deps, cliente_id)
    
    @backoffice_agent.tool
    async def bp_get_info_cnpj(ctx: RunContext[Dict[str, Any]], cnpj: str) -> Dict[str, Any]:
        """Get up to date information about a CNPJ. Before creating a new client record, use this tool to verify if the CNPJ is valid and up to date.
        
        Args:
            cnpj: The CNPJ number to verify (format: xx.xxx.xxx/xxxx-xx or clean numbers)
        """
        return await verificar_cnpj(ctx.deps, cnpj)
    
    @backoffice_agent.tool
    async def bp_create_cliente(
        ctx: RunContext[Dict[str, Any]], 
        razao_social: str,
        nome_fantasia: str,
        email: str,
        telefone_comercial: str,
        cnpj: str = None,
        inscricao_estadual: str = None,
        endereco: str = None,
        endereco_numero: str = None,
        endereco_complemento: str = None,
        bairro: str = None,
        cidade: str = None,
        estado: str = None,
        cep: str = None,
        numero_funcionarios:int = None,
        tipo_operacao: TipoOperacaoEnum = None,
        observacao: str = None
    ) -> Dict[str, Any]:
        """Create a new client in BlackPearl. 
           This tool should be used as soon as we have all the information about the client.
           When creating a new client, the tool will automatically send a lead email to the solid team.
        
        Args:
            razao_social: Company legal name
            nome_fantasia: Company trading name
            email: Client email
            telefone_comercial: Client commercial phone number, numbers only, no formatting
            cnpj: Client CNPJ Numbers only, no formatting
            inscricao_estadual: Client state registration [Obligatory]
            endereco: Street address [Obligatory]
            endereco_numero: Address number [Obligatory]
            endereco_complemento: Address complement
            bairro: Neighborhood
            cidade: Client city 
            estado: Client state 
            cep: Client postal code 
            numero_funcionarios: Number of employees
            tipo_operacao: Operation type
            contatos: List of contact IDs associated with this client
            observacao: Additional notes about the client 
        """
        # Criar dicionário com os dados diretamente, sem usar o modelo Cliente
        cliente_data = {
            "razao_social": razao_social,
            "nome_fantasia": nome_fantasia,
            "email": email,
            "telefone_comercial": telefone_comercial,
            "status_aprovacao": StatusAprovacaoEnum.PENDING_REVIEW  # Passa a string direto
        }
        
        # Add optional fields if provided
        if cnpj:
            cliente_data["cnpj"] = cnpj
        if inscricao_estadual:
            cliente_data["inscricao_estadual"] = inscricao_estadual
        else:
            # Inscrição Estadual is required for registration
            return {"error": "Inscrição Estadual é obrigatória para o cadastro. Por favor, forneça este dado."}
        if endereco:
            cliente_data["endereco"] = endereco
        if endereco_numero:
            cliente_data["endereco_numero"] = endereco_numero
        if endereco_complemento:
            cliente_data["endereco_complemento"] = endereco_complemento
        if bairro:
            cliente_data["bairro"] = bairro
        if cidade:
            cliente_data["cidade"] = cidade
        if estado:
            cliente_data["estado"] = estado
        if cep:
            cliente_data["cep"] = cep
        if numero_funcionarios is not None:
            cliente_data["numero_funcionarios"] = numero_funcionarios
        if tipo_operacao:
            cliente_data["tipo_operacao"] = tipo_operacao
        if observacao:
            cliente_data["observacao"] = observacao
            
        # Get user information and add contact if available
        blackpearl_contact_id = None
        if user_id:
            user_info = get_user(user_id)
            if user_info:
                user_data = user_info.user_data
                blackpearl_contact_id = user_data.get("blackpearl_contact_id")
                if blackpearl_contact_id:
                    cliente_data["contatos_ids"] = [blackpearl_contact_id]
        
        # Criar objeto Cliente corretamente
        cliente = Cliente(**cliente_data)
        cliente_created = await create_cliente(ctx.deps, cliente)
        logger.info(f"Cliente criado: {cliente_created}")
        
        if blackpearl_contact_id:
            updated_contato = Contato(
                id=blackpearl_contact_id,
                status_aprovacao=StatusAprovacaoEnum.PENDING_REVIEW,
                detalhes_aprovacao="Cliente criado, aguardando aprovação."
            )
            await update_contato(ctx.deps, blackpearl_contact_id, updated_contato)
        
        lead_information = f"BlackPearl Cliente ID: {cliente_created['id']}\n"
        lead_information += f"Nome: {cliente_created['razao_social']}\n"
        lead_information += f"Email: {cliente_created['email']}\n"
        lead_information += f"Telefone: {cliente_created['telefone_comercial']}\n"
        lead_information += f"Empresa: {cliente_created['razao_social']}\n"
        lead_information += f"Endereço: {cliente_created['endereco']} {cliente_created['endereco_numero']} {cliente_created['endereco_complemento']} {cliente_created['bairro']} {cliente_created['cidade']} {cliente_created['estado']} {cliente_created['cep']}\n"
        lead_information += f"CNPJ: {cliente_created['cnpj']}\n"
        lead_information += f"Inscrição Estadual: {cliente_created['inscricao_estadual']}\n"
        lead_information += f"Número de Funcionários: {cliente_created['numero_funcionarios']}\n"
        lead_information += f"Tipo de Operação: {cliente_created['tipo_operacao']}\n"
        lead_information += f"Detalhes: {summary_result_str}\n"
        
        # Send lead email
        await send_lead_email(ctx, lead_information=lead_information)
        
        # Set bp_analysis_email_message_sent to False in user data if a user is associated
        if user_id:
            user_info = get_user(user_id)
            if user_info:
                # Update only the bp_analysis_email_message_sent field while preserving all other data
                update_user_data(
                    user_id=user_id,
                    data_updates={"bp_analysis_email_message_sent": False}
                )
                logger.info(f"Set bp_analysis_email_message_sent=False for user {user_id}")
                
        return cliente_created
    
    @backoffice_agent.tool
    async def bp_update_cliente(
        ctx: RunContext[Dict[str, Any]], 
        cliente_id: int,
        razao_social: Optional[str] = None,
        nome_fantasia: Optional[str] = None,
        email: Optional[str] = None,
        telefone_comercial: Optional[str] = None,
        cnpj: Optional[str] = None,
        inscricao_estadual: Optional[str] = None,
        endereco: Optional[str] = None,
        endereco_numero: Optional[str] = None,
        endereco_complemento: Optional[str] = None,
        bairro: Optional[str] = None,
        cidade: Optional[str] = None,
        estado: Optional[str] = None,
        cep: Optional[str] = None,
        numero_funcionarios: Optional[int] = None,
        tipo_operacao: Optional[str] = None,
        status_aprovacao: Optional[str] = None,
        contatos_ids: Optional[list] = None,
        observacao: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update a client in BlackPearl.
        
        Args:
            cliente_id: The client ID
            razao_social: Company legal name (optional)
            nome_fantasia: Company trading name (optional)
            email: Client email (optional)
            telefone_comercial: Client commercial phone number (optional)
            cnpj: Client CNPJ (optional)
            inscricao_estadual: Client state registration (optional)
            endereco: Street address (optional)
            endereco_numero: Address number (optional)
            endereco_complemento: Address complement (optional)
            bairro: Neighborhood (optional)
            cidade: Client city (optional)
            estado: Client state (optional)
            cep: Client postal code (optional)
            numero_funcionarios: Number of employees (optional)
            tipo_operacao: Operation type (optional)
            status_aprovacao: Approval status (NOT_REGISTERED, REJECTED, APPROVED, VERIFYING) (optional)
            contatos_ids: List of contact IDs associated with this client (optional)
            observacao: Additional notes (optional)
        """
        try:
            # First get the current client data
            current_cliente = await get_cliente(ctx.deps, cliente_id)
            
            # Update with new values if provided
            cliente_data = {}
            for key, value in current_cliente.items():
                if key != "id" and key != "created_at" and key != "updated_at":
                    cliente_data[key] = value
                    
            # Update fields with new values if provided
            if razao_social:
                cliente_data["razao_social"] = razao_social
            if nome_fantasia:
                cliente_data["nome_fantasia"] = nome_fantasia
            if email:
                cliente_data["email"] = email
            if telefone_comercial:
                cliente_data["telefone_comercial"] = telefone_comercial
            if cnpj:
                cliente_data["cnpj"] = cnpj
            if inscricao_estadual:
                cliente_data["inscricao_estadual"] = inscricao_estadual
            if endereco:
                cliente_data["endereco"] = endereco
            if endereco_numero:
                cliente_data["endereco_numero"] = endereco_numero
            if endereco_complemento:
                cliente_data["endereco_complemento"] = endereco_complemento
            if bairro:
                cliente_data["bairro"] = bairro
            if cidade:
                cliente_data["cidade"] = cidade
            if estado:
                cliente_data["estado"] = estado
            if cep:
                cliente_data["cep"] = cep
            if numero_funcionarios is not None:
                cliente_data["numero_funcionarios"] = numero_funcionarios
            if tipo_operacao:
                cliente_data["tipo_operacao"] = tipo_operacao
            if status_aprovacao:
                # Simplesmente passa a string diretamente
                cliente_data["status_aprovacao"] = status_aprovacao
            if contatos_ids:
                cliente_data["contatos_ids"] = contatos_ids
            if observacao:
                cliente_data["observacao"] = observacao
                
            # Get user information and add contact if not already present
            if user_id and not contatos_ids:
                user_info = get_user(user_id)
                if user_info:
                    user_data = user_info.user_data
                    blackpearl_contact_id = user_data.get("blackpearl_contact_id")
                    if blackpearl_contact_id:
                        cliente_data["contatos_ids"] = [blackpearl_contact_id]
            
            # Criar objeto Cliente corretamente
            cliente = Cliente(**cliente_data)
            return await update_cliente(ctx.deps, cliente_id, cliente)
            
        except Exception as e:
            logger.error(f"Erro ao atualizar cliente: {str(e)}")
            return {"error": str(e)}
    
    # Register BlackPearl contact tools
    @backoffice_agent.tool
    async def bp_get_contatos(
        ctx: RunContext[Dict[str, Any]], 
        limit: Optional[int] = None, 
        offset: Optional[int] = None,
        search: Optional[str] = None, 
        ordering: Optional[str] = None,
        telefone: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get list of contacts from BlackPearl.
        
        Args:
            limit: Maximum number of contacts to return
            offset: Number of contacts to skip
            search: Search term to filter contacts (searches in name and email)
            ordering: Field to order results by (example: 'nome' or '-nome' for descending)
            telefone: Filter by phone number
        """
        filters = {}
        if telefone:
            filters["telefone"] = telefone
            
        return await get_contatos(ctx.deps, limit, offset, search, ordering, **filters)
    
    @backoffice_agent.tool
    async def bp_get_contato(ctx: RunContext[Dict[str, Any]], contato_id: int) -> Dict[str, Any]:
        """Get specific contact details from BlackPearl.
        
        Args:
            contato_id: The contact ID
        """
        return await get_contato(ctx.deps, contato_id)
    
    # Register Omie tools
    @backoffice_agent.tool
    async def omie_search_clients(
        ctx: RunContext[Dict[str, Any]],
        email: Optional[str] = None,
        razao_social: Optional[str] = None,
        nome_fantasia: Optional[str] = None,
        pagina: int = 1,
        registros_por_pagina: int = 50
    ) -> Dict[str, Any]:
        """Search for clients in Omie with various search options.
        
        Args:
            email: Client email
            razao_social: Company name
            nome_fantasia: Trading name
            pagina: Page number (default: 1)
            registros_por_pagina: Results per page (default: 50)
        """
        search_input = {
            "pagina": pagina,
            "registros_por_pagina": registros_por_pagina
        }
        
        # Add search filters if provided
        if email:
            search_input["email"] = email
        if razao_social:
            search_input["razao_social"] = razao_social
        if nome_fantasia:
            search_input["nome_fantasia"] = nome_fantasia
            
        input_obj = ClientSearchInput(**search_input)
        return await search_clients(ctx, input_obj)
    
    @backoffice_agent.tool
    async def omie_search_client_by_cnpj(ctx: RunContext[Dict[str, Any]], cnpj: str) -> Dict[str, Any]:
        """Search for a client by CNPJ in Omie.
        
        Args:
            cnpj: The CNPJ to search for (format: xx.xxx.xxx/xxxx-xx or clean numbers)
        """
        return await search_client_by_cnpj(ctx, cnpj)

    async def send_lead_email(
        ctx: RunContext[Dict[str, Any]],
        lead_information: str
    ) -> Dict[str, Any]:
        """Send an email with lead information to the solid team.
           Consolidate all information in a proper format, in portuguese, and send to the solid team.
           Example: 

                BlackPearl Cliente ID: 100
                Nome: João Silva
                Email: joao.silva@exemplo.com
                Telefone: +5511987654321
                Empresa: Exemplo Ltda.
                Detalhes: Algumas informações adicionais
                Interesses: Algumas informações sobre os interesses do lead
                CNPJ: 12.345.678/0001-00
                Endereço: Rua Exemplo, 123 - São Paulo/SP 
        
        Args:
            lead_information: Information about the lead
        """
        
        # Construct the email
        subject = f"[STAN] - Novo Lead"
        
        # Format the message properly in Portuguese
        message = "<html><body>"
        
        # Convert simple line breaks to HTML paragraphs
        
        email_body = await make_lead_email(lead_information, extra_context=summary_result_str)
        
        message += email_body
        
        message += "</body></html>"
        
        plain_text = email_body.replace("<html><body>", "").replace("</body></html>", "")
        # Determine recipient email
        recipient = "cezar@namastex.ai"
        
        # Create email input with HTML formatting
        email_input = SendEmailInput(
            cc=['andre@theroscreations.com', 'marcos@theroscreations.com', 'chris@theroscreations.com'],
            #cc=['cezar@namastex.ai'],
            to=recipient,
            subject=subject,
            message=message,
            content_type="text/html",
            plain_text_alternative=plain_text
        )
        
        # Send the email using Gmail API
        try:
            result = await send_email(ctx, email_input)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Informações do lead foram enviadas para a equipe da Solid",
                    "email_id": result["message_id"]
                }
            else:
                return {
                    "success": False,
                    "error": f"Falha ao enviar email do lead: {result['error']}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Erro ao enviar email do lead: {str(e)}"
            }

    # Execute the agent
    try:
        result = await backoffice_agent.run(input_text, deps=ctx)
        logger.info(f"Backoffice agent response: {result}")
        return result.data
    except Exception as e:
        error_msg = f"Error in backoffice agent: {str(e)}"
        logger.error(error_msg)
        return f"I apologize, but I encountered an error processing your request: {str(e)}"