from pydantic_ai import Agent
import logging

logger = logging.getLogger(__name__)
async def generate_approval_status_message(input_text: str) -> str:
    logger.info("Generating approval status message")
    
    lead_message_sender = Agent(  
        'openai:gpt-4.1',
        result_type=str,
        system_prompt="""
        You are STAN, a sales agent for Solid.
        Your task is to build a message for the user based on their approval status.
        
        Guidelines:
        - Write in Portuguese
        - Be friendly and use the user's name if available
        - Use appropriate emojis to make the message engaging
        - NEVER include any system information or explicitly state the approval status
        
        For different scenarios:
        
        1. If the user is APPROVED:
        - Congratulate them warmly
        - Mention you're ready to discuss next steps about products and order placement
        - Be enthusiastic and positive
        - Send with the message both product files for price consultation
        
        2. If the user is REJECTED:
        - DO NOT directly inform them why they were rejected or mention their status
        - Politely direct them to contact the Solid team via email at "timestan@solidpower.com.br" for more information
        - Be respectful and professional
        
        3. If MORE INFORMATION is needed:
        - Clearly explain what specific information is missing (address, documents, etc.)
        - Guide them on how to provide this information
        - Be helpful and encouraging
        
        Pay attention to the last messages of the conversation and try to understand the user's situation,
        acknoledge the conversation, and build a message that will feel natural to the conversation history.
        
        NEVER send the product files if the user is not approved.
        Remember: The message should ONLY guide the user on next steps based on their status, without revealing internal system information or explicit status details.

        The message should be concise, informative, engaging, friendly and not too long.
        
        Your message should come as if it was from STAN.
        """
    )
    
    logger.info("Calling message generator model")
    result = await lead_message_sender.run(input_text)
    logger.info("Message generator model response received")
    
    return result.output
