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
from src.config import settings

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
            'marcas e preços para auxiliar nas consultas dos clientes.\n\n'
            
            f'Aqui estão as marcas disponíveis: {products_brands}\n\n'
            f'Aqui estão as famílias disponíveis: {products_families}\n\n'
            
            'DIRETRIZES PARA CONSULTAS NA API BLACKPEARL:\n\n'
            
            '1. CASOS DE PREÇO ZERO: Muitos produtos na BlackPearl têm preço R$0,00. Isso geralmente indica '
            'itens promocionais ou produtos especiais como camisetas e brindes. Ao listar produtos, mencione '
            'esse detalhe quando relevante.\n\n'
            
            '2. SENSIBILIDADE NAS BUSCAS: A API BlackPearl é sensível a variações de texto, incluindo maiúsculas/minúsculas '
            'e acentuação. Se uma busca inicial não retornar resultados:\n'
            '   - Tente variações do nome (ex: "REDRAGON" em vez de "Redragon")\n'
            '   - Experimente termos alternativos (ex: "mouse" em vez de "periférico")\n'
            '   - Tente buscar pela família de produtos ou marcas separadamente\n\n'
            
            '3. CATEGORIAS E FAMÍLIAS: Os usuários costumam pedir por categorias genéricas como "periféricos", mas '
            'na BlackPearl os produtos são organizados em "famílias". Se uma busca por categoria não funcionar, '
            'tente buscar pelas famílias de produtos relacionadas.\n\n'
            
            '4. BUSCAS POR PREÇO: Ao buscar produtos por faixa de preço, prefira filtrar os resultados após obtê-los, '
            'pois a API não oferece filtro de preço nativo. Ignore produtos com preço zero quando irrelevantes.\n\n'
            
            '5. FORMATAÇÃO DE RESPOSTA: Apresente os resultados de forma organizada, usando markdown para destacar '
            'informações importantes como:\n'
            '   - Nome do produto (em negrito)\n'
            '   - Preço (formatado como moeda)\n'
            '   - Especificações relevantes\n'
            '   - Código e ID do produto\n\n'
            
            '6. ESTRATÉGIA DE BUSCA: Se uma busca inicial falhar, não desista - tente abordagens diferentes:\n'
            '   - Busque por termos mais específicos\n'
            '   - Consulte as famílias de produtos primeiro\n'
            '   - Verifique a ortografia e tente variações\n'
            '   - Use termos relacionados ao tipo de produto\n\n'
            
            '7. RESPONDA SEMPRE EM PORTUGUÊS: Todas as respostas devem ser em português claro e conciso.\n\n'
            
            'Lembre-se: Se não encontrar resultados para uma consulta específica, explique o que tentou buscar '
            'e sugira alternativas ou pergunte por mais detalhes para refinar a busca.'
            
            'Caso o usuário peça a tabela de preços dos produtos, aqui estão os links:'
            f'{parsed_text_input}'
            f'\n\nResumo da conversa até o momento: {summary_result_str}'
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
        familia_nome: Optional[str] = None,
        marca_nome: Optional[str] = None
    ) -> Dict[str, Any]:
        """Obter lista de produtos da BlackPearl.
        
        Args:
            limit: Número máximo de produtos a retornar (padrão: 15)
            offset: Número de produtos a pular
            search: Termo de busca para filtrar produtos
            ordering: Campo para ordenar resultados (exemplo: 'descricao' ou '-valor_unitario' para descendente)
            codigo: Filtrar por código do produto
            ean: Filtrar por EAN (código de barras)
            familia_nome: Filtrar por nome da família de produtos
            marca_nome: Filtrar por nome da marca
        """
        filters = {}
        if codigo:
            filters["codigo"] = codigo
        if ean:
            filters["ean"] = ean
        if familia_nome:
            filters["familia_nome"] = familia_nome
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
            # Buscar produtos com base nos requisitos
            search_params = {}
            if brand_preference:
                search_params["marca_nome"] = brand_preference
                
            # Obter produtos correspondentes aos requisitos
            products_result = await get_produtos(ctx.deps, limit=50, search=requirements, **search_params)
            products = products_result.get("results", [])
            
            # Se não houver resultados, tente uma busca mais ampla
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
    
    # Execute the agent
    try:
        result = await product_catalog_agent.run(input_text, deps=ctx)
        logger.info(f"Product catalog agent response: {result}")
        return result.data
    except Exception as e:
        error_msg = f"Error in product catalog agent: {str(e)}"
        logger.error(error_msg)
        return f"I apologize, but I encountered an error processing your request: {str(e)}"