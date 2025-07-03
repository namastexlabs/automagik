from pydantic_ai import Agent, RunContext
import logging
from typing import Dict, Any, Optional, List
import re

# Import necessary tools for product data
from automagik.tools.blackpearl import (
    get_produtos, get_produto,
    get_familias_de_produtos, get_familia_de_produto,
    get_marcas, get_marca,
    get_imagens_de_produto
)
from automagik.tools.blackpearl.api import fetch_blackpearl_product_details
from automagik.tools.evolution.api import send_evolution_media_logic
from automagik.config import settings

logger = logging.getLogger(__name__)


def get_tabela_files_from_supabase():
    """
    Fetch the latest TABELA files from Supabase database.
    Returns a dictionary with filenames as keys and URLs as values.
    """
    
    # Target files to fetch
    
    # Results dictionary
    result = """
    TABELA_REDRAGON_2025 https://www.dropbox.com/scl/fi/sgmcsv52c2rv45uezak23/TABELA_REDRAGON_2025.xlsx?rlkey=3bih2jip7llmq15csrmzk3s55&dl=0?dl=1
    TABELA_SOLID_MARCAS_2025 https://www.dropbox.com/scl/fi/ia82yfykj9kimlcwai36m/TABELA_SOLID_MARCAS_2025.xlsx?rlkey=0tl9nzwoa9szjjazq21eic5mh&dl=0?dl=1
    """
    return result

                                                                                                                                                                                                                                                                                                            

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
    
    ctx.messages if hasattr(ctx, 'messages') else []
    logger.info(f"User ID: {user_id}")
    logger.info(f"Stan Agent ID: {stan_agent_id}")
    
    # Initialize the agent with appropriate system prompt
    
    files = get_tabela_files_from_supabase()
    # Format files for the prompt
    files_text = "Não há arquivos disponíveis."
    if files:
        # Parse the string into a dictionary if it's a string
        if isinstance(files, str):
            files_dict = {}
            # Split by lines and process each line
            for line in files.strip().split('\n'):
                parts = line.strip().split(' ', 1)
                if len(parts) == 2:
                    name, url = parts
                    files_dict[name] = url
            files_text = "\n".join([f"- {name}: {url}" for name, url in files_dict.items()])
        else:
            # If it's already a dictionary, use it directly
            files_text = "\n".join([f"- {name}: {url}" for name, url in files.items()])
   
    products_brands = await get_marcas(ctx.deps)
    products_families = await get_familias_de_produtos(ctx.deps)
    
    # Extract and format brands for the prompt
    brand_list = "Nenhuma marca disponível."
    if products_brands and "results" in products_brands:
        brands = [brand.get("nome") for brand in products_brands.get("results", []) if brand.get("nome")]
        if brands:
            brand_list = ", ".join(brands)
    
    # Extract and format families for the prompt
    family_list = "Nenhuma família de produtos disponível."
    if products_families and "results" in products_families:
        families = [fam.get("nomeFamilia") for fam in products_families.get("results", []) if fam.get("nomeFamilia")]
        if families:
            family_list = ", ".join(families)
    
    product_catalog_agent = Agent(  
        'openai:gpt-4o',
        deps_type=Dict[str, Any],
        result_type=str,
        system_prompt=(
            'Você é um agente especializado em consulta de produtos na API BlackPearl. '
            'Suas responsabilidades incluem fornecer informações detalhadas sobre produtos, categorias, '
            'marcas e preços para auxiliar nas consultas dos clientes.\n\n'
            
            f'Aqui estão as marcas disponíveis: {brand_list}\n\n'
            f'Aqui estão as famílias disponíveis: {family_list}\n\n'
            
            'DIRETRIZES PARA CONSULTAS NA API BLACKPEARL:\n\n'
            
            '1. BUSCA EFICIENTE: Para evitar erros de servidor, SEMPRE prefira buscar produtos usando:\n'
            '   - **IMPORTANTE:** Se você tiver um código de produto específico (ex: "K671", "M993-RGB", "K552"), **SEMPRE use o parâmetro `codigo` na ferramenta `get_products`. NUNCA use o parâmetro `search` para códigos de produto**, pois isso causa erros na API.\n'
            '   - Use o parâmetro `search` **APENAS** para termos de busca gerais (ex: "teclado gamer", "mouse sem fio", "monitor curvo").\n'
            '   - ID da marca (`marca`) ao invés de nome da marca (`marca_nome`) quando possível.\n'
            '   - ID da família (`familia`) ao invés de nome da família (`familia_nome`) quando possível.\n'
            '   - Evite usar o parâmetro `search` com nomes completos de marcas ou famílias; use os parâmetros `marca_nome` ou `familia_nome` para isso.\n'
            '   - Para marcas populares como Redragon, SEMPRE prefira usar o parâmetro `marca` (com o ID) ou `marca_nome`.\n\n'
            
            # '2. CASOS DE PREÇO ZERO: Muitos produtos na BlackPearl têm preço R$0,00. Isso geralmente indica '
            # 'itens promocionais ou produtos especiais como camisetas e brindes. Ao listar produtos, mencione '
            # 'esse detalhe quando relevante.\n\n'
            '2. PARA OBTER PREÇO CORRETO DE UM PRODUTO: Para consultar o preço correto de um produto, use o parâmetro `tabela_preco` na ferramenta `get_product` e/ou `get_products`.\n'
            '   - O parâmetro `tabela_preco` é um ID de tabela de preços que está contido nas informações do cliente já cadastrado.\n'
            '   - O preço correto do produto esta na chave `precificacao.valor_venda`.\n'

            '3. ESTRATÉGIA DE BUSCA EM DUAS ETAPAS (Marcas/Famílias): Para consultas por marca ou família, use uma abordagem em duas etapas:\n'
            '   - Primeiro, encontre o ID da marca/família usando `get_brands` ou `get_product_families`.\n'
            '   - Depois, use esse ID com o parâmetro `marca` ou `familia` em `get_products`.\n'
            '   - Isso é mais confiável do que usar `marca_nome` ou `familia_nome` diretamente.\n\n'
            
            '4. CATEGORIAS E FAMÍLIAS: Os usuários costumam pedir por categorias genéricas como "periféricos", mas '
            'na BlackPearl os produtos são organizados em "famílias". Se uma busca por categoria não funcionar, '
            'tente buscar pelas famílias de produtos relacionadas usando `get_product_families`.\n\n'
            
            '5. BUSCAS POR PREÇO: Ao buscar produtos por faixa de preço, prefira filtrar os resultados após obtê-los, '
            'pois a API não oferece filtro de preço nativo. Ignore produtos com preço zero quando irrelevantes.\n\n'
            
            '6. FORMATAÇÃO DE RESPOSTA: Apresente os resultados de forma organizada, usando markdown para destacar '
            'informações importantes como:\n'
            '   - Nome do produto (em negrito)\n'
            '   - Preço (formatado como moeda)\n'
            '   - Especificações relevantes\n'
            '   - Código e ID do produto\n\n'
            
            '7. ESTRATÉGIA DE BUSCA (GERAL): Se uma busca inicial falhar, não desista - tente abordagens diferentes:\n'
            '   - Se um código foi fornecido (ex: "K552"), use **APENAS** o parâmetro `codigo` em `get_products`. NÃO use `search` para códigos.\n'
            '   - Se buscando por marca/família, use IDs (`marca`, `familia`) sempre que possível.\n'
            '   - Para buscas gerais, use `search` com termos amplos (ex: "teclado") e combine com `marca` ou `familia` se apropriado.\n'
            '   - Consulte as famílias de produtos (`get_product_families`) se precisar refinar a busca por tipo.\n\n'

            '8. RESPONDA SEMPRE EM PORTUGUÊS: Todas as respostas devem ser em português claro e conciso.\n\n'
           
            # '----------- CATÁLOGO DE PRODUTOS PARA DEMONSTRAÇÃO -----------\n\n'
            
            # 'Os produtos abaixo estão disponíveis no catálogo da Redragon e devem ser priorizados nas demonstrações. '
            # 'Use os códigos exatos **com o parâmetro `codigo` em `get_products`** para encontrar estes produtos específicos:\n\n'
            
            # 'TECLADOS MECÂNICOS:\n'
            # '- K671 (PT-BROWN) - TECLADO MECANICO GAMER REDRAGON SINDRI RAINBOW PRETO\n'
            # '- K636CLO-RGB (PT-BROWN) - TECLADO MECANICO GAMER REDRAGON KITAVA RGB PRETO, BEGE E LARANJA SWITCH MARROM\n\n'
            
            # 'TECLADOS MEMBRANA:\n'
            # '- K513-RGB PT - TECLADO MEMBRANA GAMER REDRAGON ADITYA PRETO\n'
            # '- K502RGB (PT) - TECLADO MEMBRANA RGB PRETO KARURA 2\n\n'
            
            # 'TECLADOS ÓPTICOS:\n'
            # '- K586RGB-PRO (PT-RED) - TECLADO OPTICO GAMER BRAHMA PRO RGB PRETO SWITCH VERMELHO\n'
            # '- K582W-RGB-PRO (PT-BLUE) - TECLADO OPTICO GAMER SURARA PRO RGB BRANCO SWITCH AZUL ABNT2\n\n'
            
            # 'MOUSES:\n'
            # '- M721-PRO - MOUSE GAMER REDRAGON KING PRO HORDA DO WORLD OF WARCRAFT VERMELHO\n'
            # '- M993-RGB - MOUSE GAMER REDRAGON DEVOURER PRETO\n'
            # '- M690-PRO - MOUSE GAMER REDRAGON MIRAGE PRO PRETO\n'
            # '- M802-RGB-1 - MOUSE TITANOBOA 2 CHROMA RGB PTO M802-RGB-1\n\n'
            
            # 'Para buscar qualquer um destes produtos, utilize o código exato **com o parâmetro `codigo`** na ferramenta `get_products`. '
            # '**Não use o parâmetro `search` para estes códigos.**\n'
            # '--------------------------------------------------------------\n\n'
            
            'Lembre-se: Se não encontrar resultados para uma consulta específica (especialmente usando `codigo`), informe ao usuário. '
            'Se a busca por `search` falhar ou retornar erro, explique que tentou buscar por termo geral e sugira alternativas ou peça mais detalhes. Não tente usar `search` com códigos de produto.\n\n'
            
            # 'Caso o usuário peça a tabela de preços dos produtos, aqui estão os links:\n'
            # f'{files_text}\n\n'
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
        marca_nome: Optional[str] = None,
        tabela_preco: Optional[int] = None,
        try_alternate_codes: bool = True
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
            tabela_preco: Filtrar por ID da tabela de preços
            try_alternate_codes: Se deve tentar variações do código de produto caso não encontre resultados inicialmente
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
        if tabela_preco:
            filters["tabela_preco"] = tabela_preco
        
        # First attempt with original parameters
        result = await get_produtos(ctx.deps, limit, offset, search, ordering, **filters)
        
        # If no results found with a product code, try alternate formats
        if try_alternate_codes and codigo and (not result.get("results") or len(result.get("results", [])) == 0):
            logger.info(f"No results found for código: {codigo}. Trying alternate formats...")
            
            # Try without parentheses part, e.g. "K502RGB (PT)" -> "K502RGB"
            if "(" in codigo:
                base_code = codigo.split("(")[0].strip()
                logger.info(f"Trying base code: {base_code}")
                filters["codigo"] = base_code
                alt_result = await get_produtos(ctx.deps, limit, offset, search, ordering, **filters)
                if alt_result.get("results") and len(alt_result.get("results", [])) > 0:
                    logger.info(f"Found results with base code: {base_code}")
                    return alt_result
            
            # Try with just the code part before any spaces or special chars
            if " " in codigo or "-" in codigo:
                simple_code = re.sub(r'[^A-Z0-9]', '', codigo.upper())
                logger.info(f"Trying simplified code: {simple_code}")
                filters["codigo"] = simple_code
                alt_result = await get_produtos(ctx.deps, limit, offset, search, ordering, **filters)
                if alt_result.get("results") and len(alt_result.get("results", [])) > 0:
                    logger.info(f"Found results with simplified code: {simple_code}")
                    return alt_result
            
            # If all code searches fail, try using it as a search term
            logger.info(f"All code searches failed. Trying as search term: {codigo}")
            search_result = await get_produtos(ctx.deps, limit, offset, codigo, ordering)
            if search_result.get("results") and len(search_result.get("results", [])) > 0:
                logger.info(f"Found results using code as search term: {codigo}")
                return search_result
        
        return result
    
    @product_catalog_agent.tool
    async def get_product(ctx: RunContext[Dict[str, Any]], product_id: int, tabela_preco: Optional[int] = None) -> Dict[str, Any]:
        """Obter detalhes de um produto específico da BlackPearl.
        
        Args:
            product_id: ID do produto
        """
        return await get_produto(ctx.deps, product_id, tabela_preco)
    
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
            # Convert to integer if it's not already
            try:
                if isinstance(produto, str) and produto.isdigit():
                    produto = int(produto)
                filters["produto"] = produto
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid product ID format: {produto}, error: {e}")
                return {"error": f"ID de produto inválido: {produto}", "results": []}
            
        return await get_imagens_de_produto(ctx.deps, limit, offset, search, ordering, **filters)
    
    @product_catalog_agent.tool
    async def recommend_products(
        ctx: RunContext[Dict[str, Any]], 
        requirements: str,
        budget: Optional[float] = None,
        brand_preference: Optional[str] = None,
        tabela_preco: Optional[int] = None,
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
            if tabela_preco:
                search_params["tabela_preco"] = tabela_preco
            
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
                logger.info("Tentando busca apenas pela marca_id sem search term")
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
        product_ids: List[int],
        tabela_preco: Optional[int] = None
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
                    product_details = await get_produto(ctx.deps, product_id, tabela_preco)
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
                
                precificacao = product.get("precificacao", None)
                if precificacao:
                    valor_venda = precificacao.get("valor_venda", None)
                else:
                    valor_venda = None
                
                # Preços
                comparison["pricing"].append({
                    "valor_venda": valor_venda,
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
        # Convert product_id to integer if it's a string
        try:
            if isinstance(product_id, str) and product_id.isdigit():
                product_id = int(product_id)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid product ID format: {product_id}, error: {e}")
            return f"Erro: ID de produto inválido: {product_id}"
            
        # Try multiple approaches to get the evolution_payload
        evolution_payload = None
        
        # First try accessing it directly from ctx.evolution_payload (if our wrapper set it)
        if hasattr(ctx, 'evolution_payload'):
            evolution_payload = ctx.evolution_payload
            logger.info("[DEBUG] Found evolution_payload directly on ctx")
            
        # Then try from ctx.deps directly (if our wrapper set it)
        if not evolution_payload and hasattr(ctx, 'deps') and hasattr(ctx.deps, 'evolution_payload'):
            evolution_payload = ctx.deps.evolution_payload
            logger.info("[DEBUG] Found evolution_payload on ctx.deps")
        
        # Next try from ctx.deps.context
        if not evolution_payload and hasattr(ctx.deps, 'context') and ctx.deps.context:
            evolution_payload = ctx.deps.context.get("evolution_payload")
            logger.info("[DEBUG] Found evolution_payload in ctx.deps.context")
            
        # If not found, try from ctx.parent_context if available
        if not evolution_payload and hasattr(ctx, 'parent_context') and isinstance(ctx.parent_context, dict):
            evolution_payload = ctx.parent_context.get("evolution_payload")
            logger.info("[DEBUG] Found evolution_payload in ctx.parent_context")
        
        # Try other attributes that might contain context
        if not evolution_payload and hasattr(ctx.deps, 'get_context') and callable(ctx.deps.get_context):
            try:
                context_from_method = ctx.deps.get_context()
                if isinstance(context_from_method, dict) and "evolution_payload" in context_from_method:
                    evolution_payload = context_from_method["evolution_payload"]
                    logger.info("[DEBUG] Found evolution_payload via ctx.deps.get_context()")
            except Exception as e:
                logger.error(f"Error getting context via get_context(): {str(e)}")
                
        if not evolution_payload:
            # Log detailed information to help debug
            logger.error("Tool 'send_product_image_to_user': Evolution payload not found in any context.")
            return "Erro: Dados de evolução não encontrados no contexto. Não foi possível enviar a imagem."
            
        # Get the full JID using the method
        user_jid = evolution_payload.get_user_jid()
        # Access the instance directly as a property
        evolution_instance_name = evolution_payload.instance if hasattr(evolution_payload, 'instance') else None

        if not user_jid:
            logger.error("Tool 'send_product_image_to_user': User JID not found in context.")
            return "Erro: JID do usuário não encontrado no contexto. Não foi possível enviar a imagem."
            
        if not evolution_instance_name:
            # Fallback to settings value
            evolution_instance_name = settings.EVOLUTION_INSTANCE
            logger.warning(f"Tool 'send_product_image_to_user': Evolution instance name not found in context, using '{evolution_instance_name}'.")

        logger.info(f"Tool 'send_product_image_to_user' called for product_id={product_id}, user={user_jid}, instance={evolution_instance_name}")

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

        # 3. Send image via Evolution API using the full JID
        success, message = await send_evolution_media_logic(
            instance_name=evolution_instance_name,
            number=user_jid,  # Use the full JID obtained from get_user_jid()
            media_url=image_url,
            media_type="image",  # Explicitly image
            caption=caption
        )

        if success:
            return f"Imagem do produto '{caption}' (ID: {product_id}) enviada com sucesso. Status: {message}"
        else:
            return f"Falha ao enviar imagem para o produto ID {product_id}. Motivo: {message}"
    
    @product_catalog_agent.tool
    async def send_multiple_product_images(
        ctx: RunContext[Dict[str, Any]],
        product_ids: List[int],
        caption_overrides: Optional[Dict[int, str]] = None
    ) -> str:
        """Busca imagens de múltiplos produtos da BlackPearl e envia para o usuário via WhatsApp.

        Args:
            product_ids: Lista de IDs de produtos BlackPearl para enviar
            caption_overrides: Dicionário opcional com IDs dos produtos como chaves e legendas personalizadas como valores

        Returns:
            Mensagem de confirmação ou erro
        """
        if not product_ids:
            return "Erro: Nenhum ID de produto fornecido para envio de imagens."
            
        # Ensure all product IDs are integers
        processed_ids = []
        for pid in product_ids:
            try:
                # Convert string numeric IDs to integers if needed
                if isinstance(pid, str) and pid.isdigit():
                    processed_ids.append(int(pid))
                else:
                    processed_ids.append(pid)
            except (ValueError, TypeError):
                logger.warning(f"Invalid product ID format: {pid}, skipping")
                
        if not processed_ids:
            return "Erro: Nenhum ID de produto válido fornecido para envio de imagens."
            
        # Debug context info
        logger.info(f"[DEBUG] Context type: {type(ctx)}")
        logger.info(f"[DEBUG] Deps type: {type(ctx.deps) if hasattr(ctx, 'deps') else 'No deps'}")
        logger.info(f"[DEBUG] Has ctx.parent_context? {hasattr(ctx, 'parent_context')}")
        logger.info(f"[DEBUG] Has ctx.evolution_payload? {hasattr(ctx, 'evolution_payload')}")
        logger.info(f"[DEBUG] Has ctx.deps.evolution_payload? {hasattr(ctx.deps, 'evolution_payload') if hasattr(ctx, 'deps') else False}")
        
        # Try multiple approaches to get the evolution_payload
        evolution_payload = None
        
        # First try accessing it directly from ctx.evolution_payload (if our wrapper set it)
        if hasattr(ctx, 'evolution_payload'):
            evolution_payload = ctx.evolution_payload
            logger.info("[DEBUG] Found evolution_payload directly on ctx")
            
        # Then try from ctx.deps directly (if our wrapper set it)
        if not evolution_payload and hasattr(ctx, 'deps') and hasattr(ctx.deps, 'evolution_payload'):
            evolution_payload = ctx.deps.evolution_payload
            logger.info("[DEBUG] Found evolution_payload on ctx.deps")
        
        # Next try from ctx.deps.context
        if not evolution_payload and hasattr(ctx.deps, 'context') and ctx.deps.context:
            evolution_payload = ctx.deps.context.get("evolution_payload")
            logger.info("[DEBUG] Found evolution_payload in ctx.deps.context")
            
        # If not found, try from ctx.parent_context if available
        if not evolution_payload and hasattr(ctx, 'parent_context') and isinstance(ctx.parent_context, dict):
            evolution_payload = ctx.parent_context.get("evolution_payload")
            logger.info("[DEBUG] Found evolution_payload in ctx.parent_context")
        
        # Try other attributes that might contain context
        if not evolution_payload and hasattr(ctx.deps, 'get_context') and callable(ctx.deps.get_context):
            try:
                context_from_method = ctx.deps.get_context()
                if isinstance(context_from_method, dict) and "evolution_payload" in context_from_method:
                    evolution_payload = context_from_method["evolution_payload"]
                    logger.info("[DEBUG] Found evolution_payload via ctx.deps.get_context()")
            except Exception as e:
                logger.error(f"Error getting context via get_context(): {str(e)}")
                
        if not evolution_payload:
            # Log detailed information to help debug
            logger.error("Tool 'send_multiple_product_images': Evolution payload not found in any context.")
            logger.error(f"Context attributes available: {dir(ctx) if hasattr(ctx, '__dict__') else 'None'}")
            logger.error(f"Deps attributes available: {dir(ctx.deps) if hasattr(ctx.deps, '__dict__') else 'None'}")
            logger.error(f"Context.deps.context: {ctx.deps.context if hasattr(ctx.deps, 'context') else 'None'}")
            
            # Try to use environment variables or config as last resort
            # This is not ideal but at least provides some fallback
            try:
                from automagik.config import settings
                if hasattr(settings, 'DEFAULT_EVOLUTION_INSTANCE') and hasattr(settings, 'DEFAULT_WHATSAPP_NUMBER'):
                    logger.warning("Using default values from settings as fallback for send_multiple_product_images")
                    return await _send_product_images_with_fallback(
                        ctx, processed_ids, caption_overrides, 
                        settings.DEFAULT_WHATSAPP_NUMBER, 
                        settings.DEFAULT_EVOLUTION_INSTANCE
                    )
            except Exception as e:
                logger.error(f"Failed to use settings fallback: {str(e)}")
                
            return "Erro: Dados de evolução não encontrados no contexto. Não foi possível enviar as imagens."
            
        # Get the full JID using the method
        user_jid = evolution_payload.get_user_jid()
        # Access the instance directly as a property
        evolution_instance_name = evolution_payload.instance if hasattr(evolution_payload, 'instance') else None

        if not user_jid:
            logger.error("Tool 'send_multiple_product_images': User JID not found in context.")
            return "Erro: JID do usuário não encontrado no contexto. Não foi possível enviar as imagens."
            
        if not evolution_instance_name:
            # Fallback to settings value
            evolution_instance_name = settings.EVOLUTION_INSTANCE
            logger.warning(f"Tool 'send_multiple_product_images': Evolution instance name not found in context, using '{evolution_instance_name}'.")

        # Initialize result tracking
        results = []
        successful_count = 0
        failed_count = 0
        
        # Process each product ID
        for product_id in processed_ids:
            try:
                # Fetch product details from Black Pearl
                product_data = await fetch_blackpearl_product_details(product_id)
                if not product_data:
                    results.append(f"Erro: Não foi possível obter detalhes para o produto com ID {product_id}.")
                    failed_count += 1
                    continue

                # Extract image URL
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
                    results.append(f"Erro: Não foi encontrada imagem para o produto com ID {product_id}.")
                    failed_count += 1
                    continue

                # Determine caption
                caption_override = caption_overrides.get(product_id) if caption_overrides else None
                caption = caption_override if caption_override else product_data.get("descricao", f"Produto ID {product_id}")
                
                # Add price if available
                if not caption_override and "valor_unitario" in product_data and product_data["valor_unitario"] > 0:
                    price = product_data.get("valor_unitario")
                    caption = f"{caption}\nPreço: R$ {price:.2f}".replace(".", ",")

                # Send image via Evolution API
                success, message = await send_evolution_media_logic(
                    instance_name=evolution_instance_name,
                    number=user_jid,
                    media_url=image_url,
                    media_type="image",
                    caption=caption
                )

                if success:
                    results.append(f"Produto '{product_data.get('descricao', f'ID {product_id}')}': Imagem enviada com sucesso.")
                    successful_count += 1
                else:
                    results.append(f"Produto ID {product_id}: Falha ao enviar imagem. Motivo: {message}")
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing product ID {product_id}: {str(e)}")
                results.append(f"Erro ao processar produto ID {product_id}: {str(e)}")
                failed_count += 1

        # Create summary message
        summary = f"Processamento de imagens concluído. {successful_count} imagem(ns) enviada(s) com sucesso, {failed_count} falha(s)."
        
        # Include detailed results if needed
        if len(results) <= 5:
            # For a small number of products, include all details
            return f"{summary}\n\nDetalhes:\n" + "\n".join(f"- {result}" for result in results)
        else:
            # For many products, just return the summary
            return f"{summary} Use a ferramenta de envio individual para mais detalhes sobre produtos específicos."
    
    # Execute the agent
    try:
        result = await product_catalog_agent.run(input_text, deps=ctx)
        logger.info(f"Product catalog agent response: {result}")
        return result.output
    except Exception as e:
        error_msg = f"Error in product catalog agent: {str(e)}"
        logger.error(error_msg)
        return f"I apologize, but I encountered an error processing your request: {str(e)}"

# Helper function for fallback sending
async def _send_product_images_with_fallback(
    ctx: RunContext[Dict[str, Any]],
    product_ids: List[int],
    caption_overrides: Optional[Dict[int, str]],
    fallback_number: str,
    fallback_instance: str
) -> str:
    """Process product images with fallback information when evolution_payload is missing."""
    logger.warning(f"Using fallback values for WhatsApp: number={fallback_number}, instance={fallback_instance}")
    
    # Initialize result tracking
    results = []
    successful_count = 0
    failed_count = 0
    
    # Process each product ID
    for product_id in product_ids:
        try:
            # Fetch product details from Black Pearl
            product_data = await fetch_blackpearl_product_details(product_id)
            if not product_data:
                results.append(f"Erro: Não foi possível obter detalhes para o produto com ID {product_id}.")
                failed_count += 1
                continue

            # Extract image URL
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
                results.append(f"Erro: Não foi encontrada imagem para o produto com ID {product_id}.")
                failed_count += 1
                continue

            # Determine caption
            caption_override = caption_overrides.get(product_id) if caption_overrides else None
            caption = caption_override if caption_override else product_data.get("descricao", f"Produto ID {product_id}")
            
            # Add price if available
            if not caption_override and "valor_unitario" in product_data and product_data["valor_unitario"] > 0:
                price = product_data.get("valor_unitario")
                caption = f"{caption}\nPreço: R$ {price:.2f}".replace(".", ",")

            # Send image via Evolution API using fallback values
            success, message = await send_evolution_media_logic(
                instance_name=fallback_instance,
                number=fallback_number,
                media_url=image_url,
                media_type="image",
                caption=caption
            )

            if success:
                results.append(f"Produto '{product_data.get('descricao', f'ID {product_id}')}': Imagem enviada com sucesso (usando valores padrão).")
                successful_count += 1
            else:
                results.append(f"Produto ID {product_id}: Falha ao enviar imagem. Motivo: {message}")
                failed_count += 1
                
        except Exception as e:
            logger.error(f"Error processing product ID {product_id} with fallback: {str(e)}")
            results.append(f"Erro ao processar produto ID {product_id}: {str(e)}")
            failed_count += 1

    # Create summary message
    summary = f"Processamento de imagens concluído usando valores de fallback. {successful_count} imagem(ns) enviada(s) com sucesso, {failed_count} falha(s)."
    
    # Include detailed results if needed
    if len(results) <= 5:
        # For a small number of products, include all details
        return f"{summary}\n\nDetalhes:\n" + "\n".join(f"- {result}" for result in results)
    else:
        # For many products, just return the summary
        return f"{summary} Use a ferramenta de envio individual para mais detalhes sobre produtos específicos."