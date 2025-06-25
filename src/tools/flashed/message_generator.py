"""LLM message generator for Flashinho agents.

This module provides utilities for generating personalized messages using LLM,
specifically for Evolution/WhatsApp communications during workflow processing.
"""
import logging
from pydantic_ai import Agent
from typing import Optional

logger = logging.getLogger(__name__)


async def generate_math_processing_message(
    user_name: Optional[str] = None,
    math_context: str = "",
    user_message: str = ""
) -> str:
    """Generate a customized message for student problem processing.
    
    This function uses an LLM to create a personalized, engaging message
    in Brazilian Portuguese to inform the user that their educational problem
    (math, physics, chemistry, etc.) is being processed.
    
    Args:
        user_name: User's name (optional)
        math_context: Context about the problem detected (can be any subject)
        user_message: Original user message (optional, for context)
        
    Returns:
        Generated message in Brazilian Portuguese
    """
    try:
        message_generator = Agent(
            'openai:gpt-4o-mini',
            result_type=str,
            system_prompt="""
            Você é o Flashinho, um assistente educacional brasileiro super animado e amigável. 
            Sua missão é gerar uma mensagem curta e envolvente em português brasileiro para avisar 
            que está processando um problema educacional (matemática, física, química, biologia, história, etc.).
            
            Diretrizes importantes:
            - Use português brasileiro casual (como a geração Z fala)
            - Seja motivador e encorajador
            - Inclua emojis estrategicamente (mas não exagere)
            - SEMPRE mencione que vai explicar em 3 PASSOS CLAROS
            - Seja breve (máximo 2 frases)
            - Use gírias brasileiras quando apropriado
            - Se conseguir identificar a matéria, mencione brevemente
            - Mantenha o tom otimista e confiante
            - Varie entre: "3 passos", "3 etapas", "3 partes" para soar natural
            
            A mensagem deve soar natural e personalizada, não genérica.
            Evite soar robótico ou formal demais.
            """
        )
        
        # Prepare the prompt with available context
        prompt_parts = []
        
        if user_name:
            prompt_parts.append(f"Nome do usuário: {user_name}")
        
        if math_context:
            prompt_parts.append(f"Contexto do problema: {math_context}")
        
        if user_message:
            prompt_parts.append(f"Mensagem original do usuário: {user_message}")
        
        if not prompt_parts:
            prompt_parts.append("O usuário enviou um problema educacional para análise")
        
        prompt = "\n".join(prompt_parts) + "\n\nGere uma mensagem de processamento para este usuário."
        
        logger.info("Generating personalized processing message")
        result = await message_generator.run(prompt)
        
        generated_message = result.data
        logger.info(f"Generated message: {generated_message}")
        
        return generated_message
        
    except Exception as e:
        logger.error(f"Error generating math processing message: {str(e)}")
        
        # Fallback to a predefined message if LLM fails
        fallback_name = user_name or "mano"
        return (f"📚 Oi {fallback_name}! Vi que você enviou um problema pra resolver! "
                f"Deixa comigo, vou analisar e te explicar tudo em 3 passos bem claros "
                f"pra você entender direitinho! ⏳✨")


async def generate_workflow_completion_message(
    user_name: Optional[str] = None,
    success: bool = True,
    problem_type: str = ""
) -> str:
    """Generate a message for workflow completion.
    
    Args:
        user_name: User's name (optional)
        success: Whether the workflow completed successfully
        problem_type: Type of problem that was solved
        
    Returns:
        Generated completion message
    """
    try:
        message_generator = Agent(
            'openai:gpt-4o-mini',
            result_type=str,
            system_prompt="""
            Você é o Flashinho, um assistente educacional brasileiro. 
            Gere uma mensagem curta para informar sobre a conclusão do processamento
            de um problema matemático.
            
            Diretrizes:
            - Use português brasileiro casual
            - Seja motivador se deu certo, ou encorajador se deu errado
            - Inclua emojis apropriados
            - Mantenha breve (1 frase)
            - Se foi sucesso, celebre um pouco
            - Se falhou, seja compreensivo e sugira tentar novamente
            """
        )
        
        status = "com sucesso" if success else "com alguns problemas"
        prompt = f"""
        Nome do usuário: {user_name or "usuário"}
        Status do processamento: {status}
        Tipo de problema: {problem_type}
        
        Gere uma mensagem de conclusão apropriada.
        """
        
        result = await message_generator.run(prompt)
        return result.data
        
    except Exception as e:
        logger.error(f"Error generating completion message: {str(e)}")
        
        if success:
            return f"🎉 Pronto, {user_name or 'mano'}! Consegui resolver e explicar tudinho pra você!"
        else:
            return f"😅 Ops, {user_name or 'mano'}! Tive um probleminha. Pode tentar enviar de novo?"


async def generate_pro_feature_message(
    user_name: Optional[str] = None,
    feature_name: str = "resolução de problemas matemáticos"
) -> str:
    """Generate a message explaining Pro features to non-Pro users.
    
    Args:
        user_name: User's name (optional)
        feature_name: Name of the Pro feature being accessed
        
    Returns:
        Generated Pro feature explanation message
    """
    try:
        message_generator = Agent(
            'openai:gpt-4o-mini',
            result_type=str,
            system_prompt="""
            Você é o Flashinho, um assistente educacional brasileiro.
            Gere uma mensagem explicando que uma funcionalidade é exclusiva para usuários Pro,
            mas de forma amigável e motivadora.
            
            Diretrizes:
            - Use português brasileiro casual
            - Seja amigável, não comercial
            - Explique o benefício da funcionalidade Pro
            - Sugira como o usuário pode obter acesso Pro
            - Mantenha o tom positivo e não exclua o usuário
            - Inclua emojis apropriados
            - Seja breve mas informativo
            """
        )
        
        prompt = f"""
        Nome do usuário: {user_name or "usuário"}
        Funcionalidade Pro: {feature_name}
        
        Gere uma mensagem explicando esta funcionalidade Pro de forma amigável.
        """
        
        result = await message_generator.run(prompt)
        return result.data
        
    except Exception as e:
        logger.error(f"Error generating Pro feature message: {str(e)}")
        
        return (f"🌟 Oi {user_name or 'mano'}! A {feature_name} é uma funcionalidade "
                f"exclusiva pra usuários Pro. Com o Flashinho Pro, você tem acesso "
                f"a explicações super detalhadas e personalizadas! 🚀")


async def generate_error_message(
    user_name: Optional[str] = None,
    error_context: str = "",
    suggestion: str = ""
) -> str:
    """Generate a user-friendly error message.
    
    Args:
        user_name: User's name (optional)
        error_context: Context about what went wrong
        suggestion: Suggestion for the user (optional)
        
    Returns:
        Generated error message
    """
    try:
        message_generator = Agent(
            'openai:gpt-4o-mini',
            result_type=str,
            system_prompt="""
            Você é o Flashinho, um assistente educacional brasileiro.
            Gere uma mensagem de erro amigável e útil, sem assustar o usuário.
            
            Diretrizes:
            - Use português brasileiro casual
            - Seja compreensivo e não culpe o usuário
            - Ofereça soluções quando possível
            - Mantenha o tom positivo
            - Use emojis para suavizar
            - Seja breve mas útil
            - Evite detalhes técnicos
            """
        )
        
        prompt = f"""
        Nome do usuário: {user_name or "usuário"}
        Contexto do erro: {error_context}
        Sugestão: {suggestion}
        
        Gere uma mensagem de erro amigável e útil.
        """
        
        result = await message_generator.run(prompt)
        return result.data
        
    except Exception as e:
        logger.error(f"Error generating error message: {str(e)}")
        
        return (f"😅 Ops, {user_name or 'mano'}! Tive um probleminha aqui. "
                f"Pode tentar novamente? Se continuar dando erro, me manda "
                f"uma mensagem que eu tento ajudar de outro jeito!")


async def generate_conversation_code_reminder(
    user_name: Optional[str] = None,
    attempt_count: int = 1
) -> str:
    """Generate a conversation code request message.
    
    Args:
        user_name: User's name (optional)
        attempt_count: Number of times user has been asked for code
        
    Returns:
        Generated conversation code request message
    """
    try:
        message_generator = Agent(
            'openai:gpt-4o-mini',
            result_type=str,
            system_prompt="""
            Você é o Flashinho, um assistente educacional brasileiro.
            Gere uma mensagem pedindo o código de conversa do usuário.
            
            Diretrizes:
            - Use português brasileiro casual
            - Seja amigável e explique porque precisa do código
            - Se é a primeira vez, seja mais explicativo
            - Se é uma tentativa repetida, seja mais direto mas ainda amigável
            - Inclua emojis apropriados
            - Mantenha motivador
            """
        )
        
        prompt = f"""
        Nome do usuário: {user_name or "usuário"}
        Tentativa número: {attempt_count}
        
        Gere uma mensagem pedindo o código de conversa.
        """
        
        result = await message_generator.run(prompt)
        return result.data
        
    except Exception as e:
        logger.error(f"Error generating conversation code reminder: {str(e)}")
        
        if attempt_count == 1:
            return ("E aí! 👋 Pra eu conseguir te dar aquela força nos estudos de forma "
                    "personalizada, preciso do seu código de conversa! 🔑\n\n"
                    "Manda aí seu código pra gente começar com tudo! 🚀✨")
        else:
            return (f"Oi {user_name or 'mano'}! 😊 Ainda preciso do seu código de conversa "
                    f"pra te ajudar melhor. Pode mandar pra mim? 🔑")


# Test function for message generation
async def test_message_generation():
    """Test function for message generators."""
    try:
        print("=== Testando Geração de Mensagens ===\n")
        
        # Test math processing message
        print("1. Mensagem de processamento de matemática:")
        math_msg = await generate_math_processing_message(
            user_name="João",
            math_context="equação do segundo grau",
            user_message="como resolve x² + 5x + 6 = 0?"
        )
        print(f"   {math_msg}\n")
        
        # Test completion message
        print("2. Mensagem de conclusão (sucesso):")
        completion_msg = await generate_workflow_completion_message(
            user_name="Maria",
            success=True,
            problem_type="álgebra"
        )
        print(f"   {completion_msg}\n")
        
        # Test Pro feature message
        print("3. Mensagem de funcionalidade Pro:")
        pro_msg = await generate_pro_feature_message(
            user_name="Carlos",
            feature_name="análise de imagens matemáticas"
        )
        print(f"   {pro_msg}\n")
        
        # Test error message
        print("4. Mensagem de erro:")
        error_msg = await generate_error_message(
            user_name="Ana",
            error_context="falha ao processar imagem",
            suggestion="enviar imagem mais clara"
        )
        print(f"   {error_msg}\n")
        
        print("=== Teste Concluído ===")
        
    except Exception as e:
        print(f"Erro no teste: {str(e)}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_message_generation())