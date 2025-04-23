from .prompt import agent_persona, solid_info, communication_guidelines
PROMPT = f"""
{agent_persona}
{solid_info}
{communication_guidelines}

Estamos verificando seus dados. Aguarde um instante, por favor. Assim que tivermos uma resposta, informarei o próximo passo.
"""
