import asyncio
from pydantic_ai import Agent, RunContext
import logging
from src.config import settings


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
    
logger = logging.getLogger(__name__)
async def generate_approval_status_message(input_text: str) -> str:
    lead_message_sender = Agent(  
        'openai:gpt-4o-mini',
        result_type=str,
        system_prompt="""
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
        
        
        NEVER send the product files if the user is not approved.
        Remember: The message should ONLY guide the user on next steps based on their status, without revealing internal system information or explicit status details.
        """
    )
    
    files = get_tabela_files_from_supabase()
    parsed_text_input = f"Here are the product files for price consultation: {files}"
    input_text = f"{input_text}\n\n{parsed_text_input}"
    
    result = await lead_message_sender.run(input_text)
    
    return result.data
