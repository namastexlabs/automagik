import os
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
import logging
from typing import Dict, Any, Optional, List

# Import necessary tools for product data
from src.tools.blackpearl import (
    get_produtos, get_produto,
    get_familias_de_produtos, get_familia_de_produto,
    get_marcas, get_marca,
    get_imagens_de_produto
)
from src.tools.blackpearl.api import fetch_blackpearl_product_details
from src.tools.evolution.api import send_evolution_media_logic
from src.config import settings
from src.db.repository.user import get_user

logger = logging.getLogger(__name__)

load_dotenv()


def get_tabela_files_from_supabase():
    """
    Fetch the latest TABELA files from Supabase database.
    Returns a dictionary with filenames as keys and URLs as values.
    """
    from supabase import create_client, Client
    
    # Target files to fetch
    target_files = [
        'TABELA_REDRAGON_2025.xlsx',
        'TABELA_SOLID_MARCAS_2025.xlsx'
    ]
    
    # Results dictionary
    result = {}
    
    try:
        # Initialize Supabase client using settings
        supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        
        # Query the database
        response = supabase.table('product_files').select('*').execute()
        
        if not response.data:
            print("No files found in database")
            return result
            
        # Filter for target files and add to result
        for link in response.data:
            filename = link.get('file_name')
            if filename in target_files:
                url = link.get('file_url')
                
                # Ensure URL has dl=1 parameter for direct download
                if url.endswith('dl=0'):
                    url = url.replace('dl=0', 'dl=1')
                elif not url.endswith('dl=1'):
                    url = f"{url}&dl=1" if '?' in url else f"{url}?dl=1"
                    
                result[filename] = url
                
        if not result:
            print("No target files found in database")
            
        return result
        
    except Exception as e:
        print(f"Error fetching files from Supabase: {str(e)}")
        return result
 

async def make_conversation_summary(message_history) -> str:
    """Make a summary of the conversation focused on product interests."""
    if len(message_history) > 0:
        summary_agent = Agent(
            'google-gla:gemini-2.0-flash-exp',
            deps_type=Dict[str, Any],
            result_type=str,
            system_prompt=(
                'You are a specialized summary agent with expertise in summarizing product-related conversations. '
                'Condense all conversation information into a few bullet points with all relevant product inquiries, '
                'interests, and requirements the customer has mentioned.'
            ),
        )
        
        # Convert message history to string for summarization
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

async def product_agent(ctx: RunContext[Dict[str, Any]], input_text: str) -> str:
    """Specialized product agent with access to BlackPearl product catalog tools.
    
    Args:
        input_text: User input text
        context: Optional context dictionary
        
    Returns:
        Response from the agent
    """
    if ctx is None:
        ctx = {}
    
    user_id = ctx.deps.get("user_id") if isinstance(ctx.deps, dict) else None
    stan_agent_id = ctx.deps.get("_agent_id_numeric") if isinstance(ctx.deps, dict) else None
    
    message_history = ctx.messages if hasattr(ctx, 'messages') else []
    logger.info(f"User ID: {user_id}")
    logger.info(f"Stan Agent ID: {stan_agent_id}")
    
    summary_result_str = await make_conversation_summary(message_history)
    
    # Initialize the agent with appropriate system prompt
    
    files = get_tabela_files_from_supabase()
    parsed_text_input = f"Here are the product files for price consultation: {files}"
   
    products_brands = await get_marcas(ctx.deps)
    products_families = await get_familias_de_produtos(ctx.deps)
    
    product_catalog_agent = Agent(  
        'openai:gpt-4o',
        deps_type=Dict[str, Any],
        result_type=str,
        system_prompt=(
            'Você é um agente especializado em consulta de produtos na API BlackPearl. '
            'Suas responsabilidades incluem fornecer informações detalhadas sobre produtos, categorias, '
            'marcas e preços para auxiliar nas consultas dos clientes.\\n\\n'
            
            f'Aqui estão as marcas disponíveis: {products_brands}\\n\\n'
            f'Aqui estão as famílias disponíveis: {products_families}\\n\\n'
            
            'DIRETRIZES PARA CONSULTAS NA API BLACKPEARL:\\n\\n'
            
            '1. BUSCA EFICIENTE: Para evitar erros de servidor, SEMPRE prefira buscar produtos usando:\\n'
            '   - **IMPORTANTE:** Se você tiver um código de produto específico (ex: "K671", "M993-RGB", "K552"), **SEMPRE use o parâmetro `codigo` na ferramenta `get_products`. NUNCA use o parâmetro `search` para códigos de produto**, pois isso causa erros na API.\\n'
            '   - Use o parâmetro `search` **APENAS** para termos de busca gerais (ex: "teclado gamer", "mouse sem fio", "monitor curvo").\\n'
            '   - ID da marca (`marca`) ao invés de nome da marca (`marca_nome`) quando possível.\\n'
            '   - ID da família (`familia`) ao invés de nome da família (`familia_nome`) quando possível.\\n'
            '   - Evite usar o parâmetro `search` com nomes completos de marcas ou famílias; use os parâmetros `marca_nome` ou `familia_nome` para isso.\\n'
            '   - Para marcas populares como Redragon, SEMPRE prefira usar o parâmetro `marca` (com o ID) ou `marca_nome`.\\n\\n'
            
            '2. CASOS DE PREÇO ZERO: Muitos produtos na BlackPearl têm preço R$0,00. Isso geralmente indica '
            'itens promocionais ou produtos especiais como camisetas e brindes. Ao listar produtos, mencione '
            'esse detalhe quando relevante.\\n\\n'
            
            '3. ESTRATÉGIA DE BUSCA EM DUAS ETAPAS (Marcas/Famílias): Para consultas por marca ou família, use uma abordagem em duas etapas:\\n'
            '   - Primeiro, encontre o ID da marca/família usando `get_brands` ou `get_product_families`.\\n'
            '   - Depois, use esse ID com o parâmetro `marca` ou `familia` em `get_products`.\\n'
            '   - Isso é mais confiável do que usar `marca_nome` ou `familia_nome` diretamente.\\n\\n'
            
            '4. CATEGORIAS E FAMÍLIAS: Os usuários costumam pedir por categorias genéricas como "periféricos", mas '
            'na BlackPearl os produtos são organizados em "famílias". Se uma busca por categoria não funcionar, '
            'tente buscar pelas famílias de produtos relacionadas usando `get_product_families`.\\n\\n'
            
            '5. BUSCAS POR PREÇO: Ao buscar produtos por faixa de preço, prefira filtrar os resultados após obtê-los, '
            'pois a API não oferece filtro de preço nativo. Ignore produtos com preço zero quando irrelevantes.\\n\\n'
            
            '6. FORMATAÇÃO DE RESPOSTA: Apresente os resultados de forma organizada, usando markdown para destacar '
            'informações importantes como:\\n'
            '   - Nome do produto (em negrito)\\n'
            '   - Preço (formatado como moeda)\\n'
            '   - Especificações relevantes\\n'
            '   - Código e ID do produto\\n\\n'
            
            '7. ESTRATÉGIA DE BUSCA (GERAL): Se uma busca inicial falhar, não desista - tente abordagens diferentes:\\n'
            '   - Se um código foi fornecido (ex: "K552"), use **APENAS** o parâmetro `codigo` em `get_products`. NÃO use `search` para códigos.\\n'
            '   - Se buscando por marca/família, use IDs (`marca`, `familia`) sempre que possível.\\n'
            '   - Para buscas gerais, use `search` com termos amplos (ex: "teclado") e combine com `marca` ou `familia` se apropriado.\\n'
            '   - Consulte as famílias de produtos (`get_product_families`) se precisar refinar a busca por tipo.\\n\\n'

            '8. RESPONDA SEMPRE EM PORTUGUÊS: Todas as respostas devem ser em português claro e conciso.\\n\\n'
            
            '9. IMAGENS DE PRODUTOS: Quando o usuário pedir para ver um produto, utilize a ferramenta '
            '   `send_product_image_to_user` para enviar uma imagem do produto. Esta ferramenta envia a '
            '   imagem diretamente para o WhatsApp do usuário.\\n\\n'
            
            '----------- CATÁLOGO DE PRODUTOS PARA DEMONSTRAÇÃO -----------\\n\\n'
            
            'Os produtos abaixo estão disponíveis no catálogo da Redragon e devem ser priorizados nas demonstrações. '
            'Use os códigos exatos **com o parâmetro `codigo` em `get_products`** para encontrar estes produtos específicos:\\n\\n'
            
            'TECLADOS MECÂNICOS:\\n'
            '- K671 (PT-BROWN) - TECLADO MECANICO GAMER REDRAGON SINDRI RAINBOW PRETO\\n'
            '- K636CLO-RGB (PT-BROWN) - TECLADO MECANICO GAMER REDRAGON KITAVA RGB PRETO, BEGE E LARANJA SWITCH MARROM\\n\\n'
            
            'TECLADOS MEMBRANA:\\n'
            '- K513-RGB PT - TECLADO MEMBRANA GAMER REDRAGON ADITYA PRETO\\n'
            '- K502RGB (PT) - TECLADO MEMBRANA RGB PRETO KARURA 2\\n\\n'
            
            'TECLADOS ÓPTICOS:\\n'
            '- K586RGB-PRO (PT-RED) - TECLADO OPTICO GAMER BRAHMA PRO RGB PRETO SWITCH VERMELHO\\n'
            '- K582W-RGB-PRO (PT-BLUE) - TECLADO OPTICO GAMER SURARA PRO RGB BRANCO SWITCH AZUL ABNT2\\n\\n'
            
            'MOUSES:\\n'
            '- 6975763145197 - MOUSE GAMER REDRAGON KING PRO HORDA DO WORLD OF WARCRAFT VERMELHO\\n'
            '- M993-RGB - MOUSE GAMER REDRAGON DEVOURER PRETO\\n'
            '- M690-PRO - MOUSE GAMER REDRAGON MIRAGE PRO PRETO\\n'
            '- M802-RGB-1 - MOUSE TITANOBOA 2 CHROMA RGB PTO M802-RGB-1\\n\\n'
            
            'Para buscar qualquer um destes produtos, utilize o código exato **com o parâmetro `codigo`** na ferramenta `get_products`. '
            '**Não use o parâmetro `search` para estes códigos.**\\n'
            '--------------------------------------------------------------\\n\\n'
            
            'Lembre-se: Se não encontrar resultados para uma consulta específica (especialmente usando `codigo`), informe ao usuário. '
            'Se a busca por `search` falhar ou retornar erro, explique que tentou buscar por termo geral e sugira alternativas ou peça mais detalhes. Não tente usar `search` com códigos de produto.\\n'
            
            'Caso o usuário peça a tabela de preços dos produtos, aqui estão os links:'
            f'{parsed_text_input}'
            f'\\n\\nResumo da conversa até o momento: {summary_result_str}'
        ),
    )
    
    # Register product catalog tools
    @product_catalog_agent.tool
    async def get_products(
        ctx: RunContext[Dict[str, Any]], 
        limit: Optional[int] = 15, 
        offset: Optional[int] = None,
        search: Optional[str] = None, 
        ordering: Optional[str] = None,
        codigo: Optional[str] = None,
        ean: Optional[str] = None,
        familia: Optional[int] = None,
        familia_nome: Optional[str] = None,
        marca: Optional[int] = None,
        marca_nome: Optional[str] = None
    ) -> Dict[str, Any]:
        """Obter lista de produtos da BlackPearl.
        
        Args:
            limit: Número máximo de produtos a retornar (padrão: 15)
            offset: Número de produtos a pular
            search: Termo de busca para filtrar produtos (use apenas para termos genéricos)
            ordering: Campo para ordenar resultados (exemplo: 'descricao' ou '-valor_unitario' para descendente)
            codigo: Filtrar por código do produto
            ean: Filtrar por EAN (código de barras)
            familia: Filtrar por ID da família de produtos (preferido para melhor desempenho)
            familia_nome: Filtrar por nome da família de produtos
            marca: Filtrar por ID da marca (preferido para melhor desempenho)
            marca_nome: Filtrar por nome da marca
        """
        filters = {}
        if codigo:
            filters["codigo"] = codigo
        if ean:
            filters["ean"] = ean
        if familia:
            filters["familia"] = familia
        if familia_nome:
            filters["familia_nome"] = familia_nome
        if marca:
            filters["marca"] = marca
        if marca_nome:
            filters["marca_nome"] = marca_nome
            
        return await get_produtos(ctx.deps, limit, offset, search, ordering, **filters)
    
    @product_catalog_agent.tool
    async def get_product(ctx: RunContext[Dict[str, Any]], product_id: int) -> Dict[str, Any]:
        """Obter detalhes de um produto específico da BlackPearl.
        
        Args:
            product_id: ID do produto
        """
        return await get_produto(ctx.deps, product_id)
    
    @product_catalog_agent.tool
    async def get_product_families(
        ctx: RunContext[Dict[str, Any]], 
        limit: Optional[int] = None, 
        offset: Optional[int] = None,
        search: Optional[str] = None, 
        ordering: Optional[str] = None,
        nome_familia: Optional[str] = None
    ) -> Dict[str, Any]:
        """Obter lista de famílias de produtos da BlackPearl.
        
        Args:
            limit: Número máximo de famílias a retornar
            offset: Número de famílias a pular
            search: Termo de busca para filtrar famílias
            ordering: Campo para ordenar resultados
            nome_familia: Filtrar por nome da família
        """
        filters = {}
        if nome_familia:
            filters["nomeFamilia"] = nome_familia
            
        return await get_familias_de_produtos(ctx.deps, limit, offset, search, ordering, **filters)
    
    @product_catalog_agent.tool
    async def get_product_family(ctx: RunContext[Dict[str, Any]], family_id: int) -> Dict[str, Any]:
        """Obter detalhes de uma família de produtos específica da BlackPearl.
        
        Args:
            family_id: ID da família de produtos
        """
        return await get_familia_de_produto(ctx.deps, family_id)
    
    @product_catalog_agent.tool
    async def get_brands(
        ctx: RunContext[Dict[str, Any]], 
        limit: Optional[int] = None, 
        offset: Optional[int] = None,
        search: Optional[str] = None, 
        ordering: Optional[str] = None,
        nome: Optional[str] = None
    ) -> Dict[str, Any]:
        """Obter lista de marcas da BlackPearl.
        
        Args:
            limit: Número máximo de marcas a retornar
            offset: Número de marcas a pular
            search: Termo de busca para filtrar marcas
            ordering: Campo para ordenar resultados
            nome: Filtrar por nome da marca
        """
        filters = {}
        if nome:
            filters["nome"] = nome
            
        return await get_marcas(ctx.deps, limit, offset, search, ordering, **filters)
    
    @product_catalog_agent.tool
    async def get_brand(ctx: RunContext[Dict[str, Any]], brand_id: int) -> Dict[str, Any]:
        """Obter detalhes de uma marca específica da BlackPearl.
        
        Args:
            brand_id: ID da marca
        """
        return await get_marca(ctx.deps, brand_id)
    
    @product_catalog_agent.tool
    async def get_product_images(
        ctx: RunContext[Dict[str, Any]], 
        limit: Optional[int] = None, 
        offset: Optional[int] = None,
        search: Optional[str] = None, 
        ordering: Optional[str] = None,
        produto: Optional[int] = None
    ) -> Dict[str, Any]:
        """Obter imagens de produtos da BlackPearl.
        
        Args:
            limit: Número máximo de imagens a retornar
            offset: Número de imagens a pular
            search: Termo de busca para filtrar imagens
            ordering: Campo para ordenar resultados
            produto: Filtrar por ID do produto
        """
        filters = {}
        if produto:
            filters["produto"] = produto
            
        return await get_imagens_de_produto(ctx.deps, limit, offset, search, ordering, **filters)
    
    @product_catalog_agent.tool
    async def recommend_products(
        ctx: RunContext[Dict[str, Any]], 
        requirements: str,
        budget: Optional[float] = None,
        brand_preference: Optional[str] = None,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """Recomendar produtos com base nos requisitos do usuário.
        
        Esta é uma ferramenta de alto nível que usa as outras ferramentas para encontrar produtos
        e recomenda as melhores opções com base nos requisitos.
        
        Args:
            requirements: Descrição do que o usuário precisa
            budget: Orçamento máximo (opcional)
            brand_preference: Preferência de marca (opcional)
            max_results: Número máximo de recomendações a retornar (padrão: 5)
        """
        try:
            # Inicializar parâmetros de busca
            search_params = {}
            
            # Se houver preferência de marca, primeiro obtenha o ID da marca
            if brand_preference:
                try:
                    # Buscar marca pelo nome para obter o ID
                    brand_result = await get_marcas(ctx.deps, search=brand_preference)
                    brands = brand_result.get("results", [])
                    
                    # Se encontrou a marca, use o ID em vez do nome
                    if brands:
                        # Encontre a marca que melhor corresponde à preferência
                        matched_brand = None
                        for brand in brands:
                            if brand.get("nome", "").lower() == brand_preference.lower():
                                matched_brand = brand
                                break
                        
                        if not matched_brand and brands:
                            matched_brand = brands[0]  # Use a primeira marca se não houver correspondência exata
                            
                        if matched_brand:
                            search_params["marca"] = matched_brand.get("id")
                            logger.info(f"Usando marca ID: {matched_brand.get('id')} para '{brand_preference}'")
                        else:
                            # Fallback para o nome da marca se não conseguir encontrar o ID
                            search_params["marca_nome"] = brand_preference
                    else:
                        # Fallback para o nome da marca se não conseguir encontrar resultados
                        search_params["marca_nome"] = brand_preference
                        
                except Exception as e:
                    logger.error(f"Erro ao buscar marca '{brand_preference}': {str(e)}")
                    search_params["marca_nome"] = brand_preference
                
            # Obter produtos correspondentes aos requisitos
            products_result = await get_produtos(ctx.deps, limit=50, search=requirements, **search_params)
            products = products_result.get("results", [])
            
            # Se não houver resultados, tente uma busca alternativa sem o termo de pesquisa
            if not products and "marca" in search_params:
                logger.info(f"Tentando busca apenas pela marca_id sem search term")
                products_result = await get_produtos(ctx.deps, limit=50, **search_params)
                products = products_result.get("results", [])
            
            # Se ainda não houver resultados, tente uma busca mais ampla
            if not products:
                # Tente extrair palavras-chave dos requisitos e pesquise cada uma
                for word in requirements.split():
                    if len(word) > 3:  # Considere apenas palavras com 4+ caracteres
                        word_search = await get_produtos(ctx.deps, limit=10, search=word, **search_params)
                        word_results = word_search.get("results", [])
                        products.extend(word_results)
            
            # Remover duplicatas
            unique_products = {}
            for product in products:
                product_id = product.get("id")
                if product_id not in unique_products:
                    unique_products[product_id] = product
            
            products = list(unique_products.values())
            
            # Filtrar produtos por orçamento, se fornecido
            if budget is not None:
                filtered_products = [p for p in products if float(p.get("valor_unitario", 0)) <= budget 
                                   and float(p.get("valor_unitario", 0)) > 0]  # Excluir itens com preço zero
                products = filtered_products
            
            # Ordenar por preço (do mais alto para o mais baixo)
            products.sort(key=lambda x: x.get("valor_unitario", 0), reverse=True)
            
            # Pegar os principais resultados
            recommendations = products[:max_results]
            
            # Adicionar imagens para cada produto recomendado
            for product in recommendations:
                product_id = product.get("id")
                if product_id:
                    images_result = await get_imagens_de_produto(ctx.deps, produto=product_id, limit=1)
                    images = images_result.get("results", [])
                    if images:
                        product["primary_image"] = images[0].get("imagem")
            
            return {
                "success": True,
                "recommendations": recommendations,
                "total_matches": len(products),
                "message": f"Encontrados {len(recommendations)} produtos recomendados baseados nos seus requisitos."
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Falha ao gerar recomendações de produtos."
            }
    
    @product_catalog_agent.tool
    async def compare_products(
        ctx: RunContext[Dict[str, Any]], 
        product_ids: List[int]
    ) -> Dict[str, Any]:
        """Comparar múltiplos produtos lado a lado.
        
        Args:
            product_ids: Lista de IDs de produtos para comparar
        """
        try:
            products = []
            
            # Recuperar detalhes para cada produto
            for product_id in product_ids:
                try:
                    product_details = await get_produto(ctx.deps, product_id)
                    products.append(product_details)
                except Exception as e:
                    logger.error(f"Erro ao recuperar produto {product_id}: {str(e)}")
                    # Continuar com outros produtos
            
            if not products:
                return {
                    "success": False,
                    "error": "Nenhum produto válido encontrado para comparação",
                    "message": "Não foi possível encontrar os produtos especificados."
                }
            
            # Extrair pontos-chave de comparação
            comparison = {
                "basic_info": [],
                "pricing": [],
                "specifications": [],
                "brands": []
            }
            
            for product in products:
                # Informações básicas
                comparison["basic_info"].append({
                    "id": product.get("id"),
                    "codigo": product.get("codigo"),
                    "descricao": product.get("descricao"),
                    "ean": product.get("ean"),
                })
                
                # Preços
                comparison["pricing"].append({
                    "valor_unitario": product.get("valor_unitario"),
                })
                
                # Especificações
                comparison["specifications"].append({
                    "peso_bruto": product.get("peso_bruto"),
                    "peso_liq": product.get("peso_liq"),
                    "largura": product.get("largura"),
                    "altura": product.get("altura"),
                    "profundidade": product.get("profundidade"),
                    "especificacoes": product.get("especificacoes"),
                })
                
                # Marca
                comparison["brands"].append({
                    "marca": product.get("marca", {}).get("nome") if product.get("marca") else None,
                    "familia": product.get("familia", {}).get("nomeFamilia") if product.get("familia") else None,
                })
            
            return {
                "success": True,
                "comparison": comparison,
                "products": products,
                "message": f"Comparação de {len(products)} produtos concluída."
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Falha ao gerar comparação de produtos."
            }
    
    @product_catalog_agent.tool
    async def send_product_image_to_user(
        ctx: RunContext[Dict[str, Any]],
        product_id: int,
        caption_override: Optional[str] = None
    ) -> str:
        """Busca uma imagem de produto da BlackPearl e envia para o usuário via WhatsApp.

        Args:
            product_id: ID do produto BlackPearl
            caption_override: Legenda opcional para substituir o nome do produto

        Returns:
            Mensagem de confirmação ou erro
        """
        # Extract user_id from context
        user_id = None
        if hasattr(ctx.deps, 'get'):
            user_id = ctx.deps.get("user_id")
        elif hasattr(ctx, 'context') and isinstance(ctx.context, dict):
            user_id = ctx.context.get("user_id")
        
        if not user_id:
            logger.error("Tool 'send_product_image_to_user': User ID not found in context.")
            return "Erro: ID do usuário não encontrado no contexto. Não foi possível enviar a imagem."
            
        # Retrieve user data from database to get WhatsApp ID
        try:
            user_info = get_user(user_id)
            if not user_info or not hasattr(user_info, 'user_data') or not user_info.user_data:
                logger.error(f"Tool 'send_product_image_to_user': User data not found for user ID {user_id}")
                return f"Erro: Dados do usuário não encontrados para o ID {user_id}. Não foi possível enviar a imagem."
                
            # Extract WhatsApp ID from user_data
            whatsapp_id = user_info.user_data.get("whatsapp_id")
            if not whatsapp_id:
                logger.error(f"Tool 'send_product_image_to_user': WhatsApp ID not found in user data for user ID {user_id}")
                return f"Erro: ID do WhatsApp não encontrado nos dados do usuário. Não foi possível enviar a imagem."
                
            # If WhatsApp ID contains "@s.whatsapp.net", remove it to get just the phone number
            if "@s.whatsapp.net" in whatsapp_id:
                user_phone_number = whatsapp_id.split("@")[0]
            else:
                user_phone_number = whatsapp_id
                
            logger.info(f"Tool 'send_product_image_to_user': Found WhatsApp number: {user_phone_number} for user ID {user_id}")
        except Exception as e:
            logger.error(f"Tool 'send_product_image_to_user': Error retrieving user data: {str(e)}")
            return f"Erro ao recuperar dados do usuário: {str(e)}"
            
        # Get Evolution instance name
        evolution_instance_name = os.getenv("EVOLUTION_INSTANCE", "default")
        logger.info(f"Tool 'send_product_image_to_user' called for product_id={product_id}, user={user_phone_number}, instance={evolution_instance_name}")

        # 1. Fetch product details from Black Pearl
        product_data = await fetch_blackpearl_product_details(product_id)
        if not product_data:
            return f"Erro: Não foi possível obter detalhes para o produto com ID {product_id} da BlackPearl."

        # 2. Extract image URL and determine caption
        image_url = product_data.get("imagem")
        if not image_url:
            # Try to get product images if main image not available
            try:
                images_result = await get_imagens_de_produto(ctx.deps, produto=product_id, limit=1)
                images = images_result.get("results", [])
                if images:
                    image_url = images[0].get("imagem")
            except Exception as e:
                logger.error(f"Error retrieving product images: {str(e)}")

        if not image_url:
            return f"Erro: Não foi encontrada imagem para o produto com ID {product_id}."

        # Determine caption
        caption = caption_override if caption_override else product_data.get("descricao", f"Produto ID {product_id}")
        
        # Add price if available
        if not caption_override and "valor_unitario" in product_data and product_data["valor_unitario"] > 0:
            price = product_data.get("valor_unitario")
            caption = f"{caption}\nPreço: R$ {price:.2f}".replace(".", ",")

        # 3. Send image via Evolution API
        success, message = await send_evolution_media_logic(
            instance_name=evolution_instance_name,
            number=user_phone_number,
            media_url=image_url,
            media_type="image", # Explicitly image
            caption=caption
        )

        if success:
            return f"Imagem do produto '{caption}' (ID: {product_id}) enviada com sucesso. Status: {message}"
        else:
            return f"Falha ao enviar imagem para o produto ID {product_id}. Motivo: {message}"
    
    # Execute the agent
    try:
        result = await product_catalog_agent.run(input_text, deps=ctx)
        logger.info(f"Product catalog agent response: {result}")
        return result.data
    except Exception as e:
        error_msg = f"Error in product catalog agent: {str(e)}"
        logger.error(error_msg)
        return f"I apologize, but I encountered an error processing your request: {str(e)}"