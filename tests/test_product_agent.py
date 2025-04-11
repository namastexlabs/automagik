#!/usr/bin/env python
"""
Teste do agente de produtos.
Este script testa a capacidade do agente de produtos de lidar com consultas relacionadas a produtos.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from pydantic_ai import RunContext
from typing import Dict, Any

from src.agents.simple.stan_agent.specialized.product import product_agent

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

async def test_product_query():
    """Testar o agente de produtos com consultas em português."""
    # Criar um contexto simulado
    ctx = RunContext(
        deps={"user_id": 1, "_agent_id_numeric": 1},
        messages=[],
        prompt="",
        model="openai:gpt-4o-mini",
        usage={}
    )
    
    # Testar com várias consultas em português
    queries = [
        "Mostre produtos da marca REDRAGON",
        "Quero ver produtos da família PELÚCIA",
        "Preciso de informações sobre o produto com código 0000000000412",
        "Quais produtos custam menos de R$50?",
        "Busque produtos relacionados a mouse gaming",
        "Compare os produtos com IDs 4913 e 4935"
    ]
    
    for query in queries:
        try:
            logger.info(f"Testando consulta: {query}")
            response = await product_agent(ctx, query)
            logger.info(f"Resposta: {response}")
        except Exception as e:
            logger.error(f"Erro ao processar consulta '{query}': {str(e)}")
        
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(test_product_query()) 