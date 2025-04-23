from .prompt import agent_persona, solid_info, communication_guidelines
PROMPT = f"""
{agent_persona}
{solid_info}
{communication_guidelines}


Infelizmente, seu cadastro não pôde ser aprovado neste momento. Caso queira revisar ou corrigir algum dado, por favor, me envie as informações atualizadas e tentaremos novamente.
"""
