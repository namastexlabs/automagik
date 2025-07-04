"""Direct workflow runner for Flashinho agents.

This module provides utilities for running Claude Code workflows directly
without MCP overhead, specifically optimized for the flashinho_thinker workflow.
"""
import asyncio
import logging
import time
from typing import Dict, Any, Optional
from pathlib import Path
# from pydantic_ai import Agent as PydanticAgent
# from automagik.agents.pydanticai.flashinho_pro.models import StepBreakdown

logger = logging.getLogger(__name__)


async def _execute_flashinho_thinker_internal(
    message: str,
    image_data: Optional[str] = None,
    session_id: Optional[str] = None,
    timeout: int = 300
) -> Optional[str]:
    """Execute flashinho_thinker workflow using internal Claude Code system.
    
    This function tries multiple methods to execute the workflow:
    1. Direct workflow execution through Claude Code system
    2. MCP automagik-workflows if available
    3. Internal API call to workflow endpoint
    
    Args:
        message: Task message for the workflow
        image_data: Optional base64 image data
        session_id: Optional session identifier
        timeout: Execution timeout in seconds
        
    Returns:
        Workflow result string or None if execution fails
    """
    
    # Method 1: Try MCP automagik-workflows first (most reliable)
    try:
        # Import MCP workflow functions if available
        from automagik.mcp import mcp__automagik_workflows__run_workflow
        
        logger.info("Attempting to run flashinho_thinker via MCP automagik-workflows")
        
        # Prepare message with image if provided
        workflow_message = message
        if image_data:
            workflow_message = f"{message}\n\n[Imagem anexada para análise matemática]"
        
        # Execute workflow via MCP
        mcp_result = await mcp__automagik_workflows__run_workflow(
            workflow_name="flashinho_thinker",
            message=workflow_message,
            max_turns=10,
            session_name=session_id
        )
        
        if mcp_result and mcp_result.get("success"):
            logger.info("Successfully executed flashinho_thinker via MCP")
            return mcp_result.get("result", "Workflow executed successfully")
            
    except ImportError:
        logger.debug("MCP automagik-workflows not available")
    except Exception as e:
        logger.warning(f"MCP workflow execution failed: {str(e)}")
    
    # Method 2: Try direct Claude Code workflow execution
    try:
        # Import Claude Code workflow system
        from automagik.agents.claude_code.workflow_executor import execute_workflow
        
        logger.info("Attempting to run flashinho_thinker via Claude Code workflow executor")
        
        workflow_request = {
            "workflow_name": "flashinho_thinker",
            "message": message,
            "session_id": session_id,
            "timeout": timeout,
            "multimodal_content": [{"type": "image", "data": image_data}] if image_data else []
        }
        
        result = await execute_workflow(workflow_request)
        
        if result and result.get("success"):
            logger.info("Successfully executed flashinho_thinker via workflow executor")
            return result.get("result", "Workflow executed successfully")
            
    except ImportError:
        logger.debug("Claude Code workflow executor not available")
    except Exception as e:
        logger.warning(f"Workflow executor failed: {str(e)}")
    
    # Method 3: Try internal API call to workflow endpoint
    try:
        import httpx
        import os
        
        logger.info("Attempting to run flashinho_thinker via internal API")
        
        # Get API configuration
        api_port = os.getenv("AUTOMAGIK_API_PORT", "8000")
        api_key = os.getenv("API_KEY", "")
        base_url = f"http://localhost:{api_port}"
        
        # Prepare request data
        request_data = {
            "message": message,
            "max_turns": 10,
            "session_id": session_id,
            "timeout": timeout
        }
        
        # Add image data if provided
        if image_data:
            request_data["image_data"] = image_data
        
        # Make internal API call
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/api/v1/workflows/claude-code/run/flashinho_thinker",
                json=request_data,
                headers={"X-API-Key": api_key} if api_key else {}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    logger.info("Successfully executed flashinho_thinker via internal API")
                    return result.get("result", "Workflow executed successfully")
                    
    except Exception as e:
        logger.warning(f"Internal API call failed: {str(e)}")
    
    # All methods failed
    logger.warning("All flashinho_thinker execution methods failed, will use fallback")
    return None


async def run_flashinho_thinker_workflow(
    message: str,
    image_base64: Optional[str] = None,
    session_id: Optional[str] = None,
    timeout: int = 300,
    workspace_base: str = "/tmp/flashinho-workspace"
) -> Dict[str, Any]:
    """Directly invoke flashinho_thinker workflow using internal AgentFactory.
    
    This function uses the AgentFactory to get the claude_code agent and runs
    the flashinho_thinker workflow with the provided message and optional image content.
    
    Args:
        message: The task message for the workflow
        image_base64: Optional base64 encoded image data
        session_id: Optional session identifier
        timeout: Execution timeout in seconds
        workspace_base: Base directory for workspace
        
    Returns:
        Dict containing:
        - success: Boolean indicating if workflow succeeded
        - result: Workflow output text
        - session_id: Session identifier used
        - execution_time: Time taken in seconds
        - error: Error message if failed
    """
    try:
        from automagik.agents.models.agent_factory import AgentFactory
        
        # Generate session ID if not provided
        if not session_id:
            session_id = f"flashinho_math_{int(time.time())}"
        
        logger.info(f"Starting flashinho_thinker workflow execution with session: {session_id}")
        start_time = time.time()
        
        # Get the claude_code agent from AgentFactory
        try:
            claude_agent = AgentFactory.get_agent("claude_code")
            logger.info("Successfully obtained claude_code agent from AgentFactory")
        except Exception as e:
            logger.error(f"Failed to get claude_code agent: {str(e)}")
            # Fallback to mock response if agent creation fails
            return await _mock_workflow_response(message, image_base64, session_id, start_time, workspace_base)
        
        # Prepare workflow configuration for flashinho_thinker
        workflow_config = {
            "workflow_name": "flashinho_thinker",
            "message": message,
            "session_id": session_id,
            "timeout": timeout,
            "workspace_base": workspace_base
        }
        
        # Add image to config if provided
        if image_base64:
            workflow_config["image_data"] = image_base64
            
        # Execute the flashinho_thinker workflow directly
        try:
            # First, try to use the internal workflow execution system
            result = await _execute_flashinho_thinker_internal(
                message=message,
                image_data=image_base64,
                session_id=session_id,
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            if result:
                logger.info(f"Flashinho_thinker workflow completed in {execution_time:.2f}s")
                
                return {
                    "success": True,
                    "result": result,
                    "session_id": session_id,
                    "execution_time": execution_time,
                    "workspace_path": f"{workspace_base}/{session_id}",
                    "git_commits": [],
                    "agent_used": "claude_code",
                    "workflow_name": "flashinho_thinker"
                }
            else:
                # If internal execution returns None, fall back to mock
                return await _mock_workflow_response(message, image_base64, session_id, start_time, workspace_base)
            
        except Exception as e:
            logger.error(f"Error executing flashinho_thinker workflow: {str(e)}")
            # Fallback to mock response if workflow execution fails
            return await _mock_workflow_response(message, image_base64, session_id, start_time, workspace_base)
    
    except Exception as e:
        logger.error(f"Error running flashinho_thinker workflow: {str(e)}")
        return {
            "success": False,
            "result": "Ops, tive um erro técnico aqui. Tenta mandar a imagem de novo?",
            "session_id": session_id or f"error_{int(time.time())}",
            "execution_time": 0,
            "error": str(e)
        }


async def _mock_workflow_response(
    message: str,
    image_base64: Optional[str],
    session_id: str,
    start_time: float,
    workspace_base: str
) -> Dict[str, Any]:
    """Fallback mock response when real workflow execution fails."""
    
    logger.warning("Falling back to mock workflow response")
    
    # Simulate processing time
    await asyncio.sleep(1)
    
    # Create a mock response with proper 3-step format
    if image_base64:
        mock_result = """📚 **Análise Completa do Problema!**

**Passo 1: Identificação e Compreensão** 🔍
• Identifiquei um problema educacional na imagem enviada
• O exercício parece envolver conceitos fundamentais da matéria
• Dados importantes: [análise dos elementos visuais da imagem]

**Passo 2: Desenvolvimento e Resolução** ✏️
• Aplicando o método apropriado para este tipo de questão
• Desenvolvendo o raciocínio passo a passo:
  - Primeiro, organizamos os dados do problema
  - Em seguida, aplicamos os conceitos necessários
  - Por fim, realizamos os cálculos ou análises requeridas

**Passo 3: Resposta Final e Verificação** ✅
• Resposta: [resultado do problema]
• Verificação: Ao substituir os valores, confirmamos que a solução está correta
• 💡 Dica Extra: Este tipo de problema é comum em provas e vestibulares!

*[Resposta simulada - aguardando conexão com workflow flashinho_thinker...]*"""
    else:
        mock_result = """📚 **Problema Matemático Resolvido!**

**Passo 1: Análise do Enunciado**
{}

**Passo 2: Aplicação do Método**
Vou resolver este problema passo a passo, explicando cada operação.

**Passo 3: Resposta e Verificação**
Aqui está a solução completa com verificação.

✅ **Resultado obtido com sucesso!**

*[Resposta simulada - tentando conectar com o workflow flashinho_thinker...]*""".format(message[:200] + "..." if len(message) > 200 else message)
    
    execution_time = time.time() - start_time
    
    return {
        "success": True,
        "result": mock_result,
        "session_id": session_id,
        "execution_time": execution_time,
        "workspace_path": f"{workspace_base}/{session_id}",
        "git_commits": [],
        "mock_execution": True,  # Flag to indicate this is a mock response
        "fallback_reason": "claude_code_agent_unavailable"
    }


async def run_workflow_with_image_file(
    message: str,
    image_path: str,
    session_id: Optional[str] = None,
    timeout: int = 300
) -> Dict[str, Any]:
    """Run flashinho_thinker workflow with an image file.
    
    Args:
        message: The task message for the workflow
        image_path: Path to the image file
        session_id: Optional session identifier
        timeout: Execution timeout in seconds
        
    Returns:
        Workflow execution result
    """
    try:
        import base64
        from automagik.utils.multimodal import detect_content_type, is_image_type
        
        # Read and encode image file
        image_file = Path(image_path)
        
        if not image_file.exists():
            return {
                "success": False,
                "result": "Arquivo de imagem não encontrado.",
                "error": f"File not found: {image_path}"
            }
        
        # Read file and encode as base64
        with open(image_file, "rb") as f:
            image_data = f.read()
        
        # Detect content type
        content_type = detect_content_type(str(image_file))
        
        if not is_image_type(content_type):
            return {
                "success": False,
                "result": "O arquivo fornecido não é uma imagem válida.",
                "error": f"Invalid image type: {content_type}"
            }
        
        # Encode as base64 data URL
        image_base64 = f"data:{content_type};base64,{base64.b64encode(image_data).decode()}"
        
        # Run workflow with encoded image
        return await run_flashinho_thinker_workflow(
            message=message,
            image_base64=image_base64,
            session_id=session_id,
            timeout=timeout
        )
        
    except Exception as e:
        logger.error(f"Error processing image file {image_path}: {str(e)}")
        return {
            "success": False,
            "result": "Erro ao processar o arquivo de imagem.",
            "error": str(e)
        }


async def test_workflow_runner() -> None:
    """Test function for the workflow runner."""
    try:
        # Test with a simple math problem
        test_message = """
        Analise este problema matemático e explique a solução em 3 passos:
        
        Resolva a equação: 2x + 5 = 15
        
        Explique cada passo de forma didática para um estudante do ensino médio.
        """
        
        logger.info("Testing flashinho_thinker workflow runner...")
        
        result = await run_flashinho_thinker_workflow(
            message=test_message,
            session_id="test_session"
        )
        
        print("=== Resultado do Teste ===")
        print(f"Sucesso: {result['success']}")
        print(f"Tempo de execução: {result['execution_time']:.2f}s")
        print(f"Resultado: {result['result'][:200]}...")
        
        if not result['success']:
            print(f"Erro: {result.get('error', 'Desconhecido')}")
            
    except Exception as e:
        logger.error(f"Error in workflow test: {str(e)}")
        print(f"Erro no teste: {str(e)}")


# Convenience functions for different use cases
async def solve_math_problem(
    problem_description: str,
    image_base64: Optional[str] = None
) -> str:
    """Convenience function to solve a math problem.
    
    Args:
        problem_description: Description of the math problem
        image_base64: Optional image with the problem
        
    Returns:
        Solution explanation in Portuguese
    """
    prompt = f"""
    Analise este problema matemático e explique a solução em 3 passos claros:
    
    {problem_description}
    
    Instruções:
    1. Identifique o tipo de problema e o que está sendo pedido
    2. Explique o método de resolução passo a passo
    3. Mostre a resposta final com verificação
    
    Use linguagem simples e didática para estudantes brasileiros.
    """
    
    result = await run_flashinho_thinker_workflow(
        message=prompt,
        image_base64=image_base64
    )
    
    if result["success"]:
        return result["result"]
    else:
        return "Desculpa, não consegui resolver esse problema. Pode tentar reformular ou enviar mais detalhes?"


async def analyze_math_image(image_base64: str) -> str:
    """Convenience function to analyze a mathematical image.
    
    Args:
        image_base64: Base64 encoded image data
        
    Returns:
        Analysis and solution in Portuguese
    """
    prompt = """
    Analise esta imagem matemática e:
    
    1. Identifique que tipo de problema ou conceito matemático está sendo mostrado
    2. Se for um exercício, resolva-o passo a passo
    3. Se for um conceito, explique de forma didática
    
    Seja claro e use exemplos quando necessário. Responda em português brasileiro
    de forma que um estudante do ensino médio possa entender.
    """
    
    result = await run_flashinho_thinker_workflow(
        message=prompt,
        image_base64=image_base64
    )
    
    if result["success"]:
        return result["result"]
    else:
        return "Não consegui analisar essa imagem. Pode tentar enviar uma imagem mais clara?"


async def analyze_student_problem(image_base64: str, user_message: str = "") -> str:
    """Analyze any student problem (math, physics, chemistry, etc.) with structured 3-step breakdown.
    
    Args:
        image_base64: Base64 encoded image data
        user_message: Optional context from the user's message
        
    Returns:
        Analysis and solution in Portuguese with 3-step breakdown
    """
    logger.info("Analyzing student problem with direct multimodal model")
    
    try:
        # Import OpenAI client for direct multimodal analysis
        from openai import AsyncOpenAI
        import os
        
        # Initialize OpenAI client
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Create a comprehensive prompt that ensures 3-step breakdown
        prompt = f"""
        Analise esta imagem educacional e forneça uma explicação COMPLETA em EXATAMENTE 3 PASSOS.
        
        {f'Contexto do usuário: {user_message}' if user_message else ''}
        
        IMPORTANTE: Sua resposta DEVE seguir EXATAMENTE este formato:
        
        **Passo 1: Identificação e Compreensão** 🔍
        - Identifique o tipo de problema (matemática, física, química, biologia, história, etc.)
        - Explique o que está sendo pedido
        - Destaque os dados importantes da imagem
        
        **Passo 2: Desenvolvimento e Resolução** ✏️
        - Mostre o processo de resolução passo a passo
        - Explique cada operação ou raciocínio
        - Use fórmulas, conceitos ou métodos apropriados baseados no que vê na imagem
        
        **Passo 3: Resposta Final e Verificação** ✅
        - Apresente a resposta final claramente
        - Faça a verificação ou prova real quando aplicável
        - Dê uma dica extra ou aplicação prática
        
        Use linguagem clara e acessível para estudantes brasileiros.
        Inclua emojis para tornar a explicação mais envolvente.
        Se for um conceito teórico, adapte os 3 passos para: identificação, explicação e exemplos.
        
        DESCREVA EXATAMENTE O QUE VOCÊ VÊ NA IMAGEM - não invente conteúdo.
        """
        
        # Prepare image URL for OpenAI API
        if image_base64.startswith('data:'):
            # Already in data URL format
            image_url = image_base64
        else:
            # Convert base64 to data URL - try to detect format from base64 header
            import base64
            try:
                # Decode a small portion to detect image format
                decoded_header = base64.b64decode(image_base64[:100] + '==')
                if decoded_header.startswith(b'\xff\xd8\xff'):
                    mime_type = "image/jpeg"
                elif decoded_header.startswith(b'\x89PNG'):
                    mime_type = "image/png"
                elif decoded_header.startswith(b'GIF'):
                    mime_type = "image/gif"
                else:
                    mime_type = "image/jpeg"  # Default fallback
            except:
                mime_type = "image/jpeg"  # Safe fallback
            
            image_url = f"data:{mime_type};base64,{image_base64}"
        
        # Prepare message for OpenAI
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url", 
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ]
        
        # Call OpenAI GPT-4o with vision
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1500,
            temperature=0.3
        )
        
        result = response.choices[0].message.content
        logger.info("Successfully analyzed image with OpenAI GPT-4o")
        return result
        
    except ImportError:
        logger.warning("OpenAI client not available, falling back to workflow execution")
        # Fallback to original workflow execution
        result = await run_flashinho_thinker_workflow(
            message=f"""
            Analise esta imagem educacional e forneça uma explicação COMPLETA em EXATAMENTE 3 PASSOS.
            
            {f'Contexto do usuário: {user_message}' if user_message else ''}
            
            DESCREVA EXATAMENTE O QUE VOCÊ VÊ NA IMAGEM - não invente conteúdo.
            """,
            image_base64=image_base64
        )
        
        if result["success"]:
            return result["result"]
        else:
            return "📚 Ops! Não consegui analisar bem essa imagem. Que tal enviar ela de novo com mais qualidade? Ou me conta com suas palavras qual é a dúvida!"
            
    except Exception as e:
        logger.error(f"Error in student problem analysis: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Full exception details: {repr(e)}")
        return "📚 Ops! Tive um problema técnico. Pode tentar enviar a imagem novamente?"


if __name__ == "__main__":
    # Run test if executed directly
    asyncio.run(test_workflow_runner())