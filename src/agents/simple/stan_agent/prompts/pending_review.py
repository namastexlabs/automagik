from .prompt import agent_persona, solid_info, communication_guidelines
PROMPT = f"""
{agent_persona}
{solid_info}
{communication_guidelines}

Seu cadastro foi enviado para análise. Assim que a verificação for concluída, entrarei em contato com você. Se precisar de alguma informação adicional durante esse período, me avise!
"""
