from .prompt import agent_persona, solid_info, communication_guidelines
PROMPT = f"""
{agent_persona}
{solid_info}
{communication_guidelines}

Parabéns! Seu cadastro foi aprovado com sucesso. Agora você pode acessar todos os benefícios de ser um parceiro Solid. Caso precise de suporte ou queira conhecer nossos produtos, estou à disposição!
"""
