"""Matching agent for product folder matcher."""

import os
import time
from typing import Dict, List, Any
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.models.openai import OpenAIModel
from rich.console import Console

from scripts.solid_stan.product_folder_matcher.models import BlackpearlProduct, DriveFolder, MatchResult
from scripts.solid_stan.product_folder_matcher.tools import ProductFolderMatcherTools
from scripts.solid_stan.product_folder_matcher.observability import (
    log_agent_request, log_agent_response, log_match_result, log_error
)

# Initialize console for rich output
console = Console()

class MatchingAgent:
    """Agent for matching Blackpearl products with Drive folders."""
    
    def __init__(self, tools: ProductFolderMatcherTools, model_name: str = "openai:gpt-4o"):
        """Initialize the matching agent.
        
        Args:
            tools: Tools for the agent to use
            model_name: Name of the model to use
        """
        self.tools = tools
        self.model_name = model_name
        
        # Initialize the model
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            console.print("[red]Error: OPENAI_API_KEY not found in environment variables[/red]")
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # Initialize the model with increased timeout
        self.model = OpenAIModel(api_key=api_key, model_name=model_name)
        
        # Initialize the agent
        self.agent = PydanticAgent(
            "openai:gpt-4o",
            system_prompt=SYSTEM_PROMPT,
            result_type=MatchResult
        )
        
        console.print(f"[green]Initialized matching agent with model: {model_name}[/green]")
    
    async def find_best_match(self, product: BlackpearlProduct, folders: List[DriveFolder]) -> MatchResult:
        """Find the best matching folder for a product.
        
        Args:
            product: Blackpearl product
            folders: List of Drive folders to match against
            
        Returns:
            Match result
        """
        try:
            # Format the user prompt
            user_prompt = self._format_user_prompt(product, folders)
            
            # Record start time for timing
            start_time = time.time()
            
            # Log the agent request
            log_agent_request(user_prompt, product.id, product.marca)
            
            # Run the agent
            result = await self.agent.run(user_prompt)
            
            # === Add explicit type check ===
            if not isinstance(result.data, MatchResult):
                # Log the unexpected response for debugging
                logger.log_warning(f"[Agent] Model response did not match expected MatchResult structure for product {product.id}. Response: {result.data!r}")
                raise UnexpectedModelBehavior(f"Model response for product {product.id} did not match expected MatchResult structure.")
            # === End explicit type check ===
            
            # Calculate timing
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Log the agent response
            log_agent_response(result.data.model_dump(), product.id, product.marca, elapsed_ms)
            
            # Create warning flags if needed
            warning_flags = []
            if result.data.confidence_score >= 0.8 and result.data.confidence_score < 0.9:
                warning_flags.append("Medium confidence match")
            
            # Update match result with warnings
            result.data.warning_flags = warning_flags if warning_flags else None
            
            # Log the match result
            log_match_result(result.data.model_dump(), 0.8)
            
            console.print(f"[green]Match found for {product.descricao} with confidence {result.data.confidence_score:.2f}[/green]")
            
            return result.data
        except (ModelRetry, UnexpectedModelBehavior) as e:
            # Catch specific pydantic-ai errors
            console.print(f"[red]Agent Error (Retry/Behavior) for product {product.id}: {repr(e)}[/red]")
            log_error(f"Agent Error for product {product.id}: {str(e)} ({repr(e)})", "find_match_error", {
                "product_id": product.id,
                "product_descricao": product.descricao,
                "brand": product.marca,
                "error_type": type(e).__name__
            })
            # Return default "no match"
            return MatchResult(
                product_id=product.id,
                drive_folder_id="",
                product_descricao=product.descricao,
                folder_name="",
                folder_path="",
                confidence_score=0.0,
                reasoning=f"Error during matching: {str(e)}",
                warning_flags=["Error during matching process"]
            )
        except Exception as e:
            # Catch any other unexpected errors
            console.print(f"[red]Unexpected Error finding match for product {product.id}: {repr(e)}[/red]")
            log_error(f"Unexpected error finding match for product {product.id}: {str(e)} ({repr(e)})", "find_match_error", {
                "product_id": product.id,
                "product_descricao": product.descricao,
                "brand": product.marca
            })
            
            # Return a default "no match" result
            return MatchResult(
                product_id=product.id,
                drive_folder_id="",
                product_descricao=product.descricao,
                folder_name="",
                folder_path="",
                confidence_score=0.0,
                reasoning=f"Error during matching: {str(e)}",
                warning_flags=["Error during matching process"]
            )
    
    def _format_user_prompt(self, product: BlackpearlProduct, folders: List[DriveFolder]) -> str:
        """Format the user prompt for the agent.
        
        Args:
            product: Blackpearl product
            folders: List of Drive folders to match against
            
        Returns:
            Formatted user prompt
        """
        # Format product details
        product_details = f"""
PRODUCT DETAILS:
- ID: {product.id}
- Name: {product.descricao}
- Code: {product.codigo or 'N/A'}
- Brand: {product.marca}
- Family: {product.familia or 'N/A'}
- Price: {f"R$ {product.valor_unitario:.2f}" if product.valor_unitario else 'N/A'}
- Specifications: {product.especificacoes or 'N/A'}
- Detailed Description: {product.descr_detalhada or 'N/A'}
"""

        # Format folder options
        folder_options = "\nPOTENTIAL FOLDER MATCHES:\n"
        
        for i, folder in enumerate(folders, 1):
            folder_options += f"{i}. Path: {folder.full_path}\n   ID: {folder.drive_id}\n"
        
        # Format available tools
        tools_description = """
AVAILABLE TOOLS:
1. read_folder_contents(folder_id: str) - Get the contents of a specific folder
2. examine_product_files(folder_id: str, pattern: str = None) - Examine files in a folder that might contain product details
3. extract_product_info_from_path(folder_path: str) - Extract potential product information from a folder path

You can use these tools by calling them like:
TOOL: read_folder_contents
PARAMETERS: {"folder_id": "folder_id_here"}

When you're ready to make a decision, provide your answer in this format:
ANSWER:
{
  "product_id": 123,
  "drive_folder_id": "folder_id_here",
  "product_descricao": "Product name",
  "folder_name": "Folder name",
  "folder_path": "Full folder path",
  "confidence_score": 0.95,
  "reasoning": "Detailed explanation of why this is a match"
}
"""

        # Combine everything
        prompt = f"""
You need to find the best matching Google Drive folder for this product from our database.

{product_details}

{folder_options}

{tools_description}

Please analyze the product details and folder options, and determine if there's a match. Use the tools if needed to gather more information.

If you're confident in a match, provide the details in the specified format with a confidence score between 0.0 and 1.0, where:
- 0.9-1.0: Very high confidence match
- 0.8-0.9: Good match with minor uncertainties
- Below 0.8: Uncertain match, significant differences

IMPORTANT: When you provide your final answer, return ONLY the JSON object matching the `MatchResult` structure. Do not include any other text, explanations, or conversational filler before or after the JSON.

If no match is found, return an empty folder_id with a confidence score of 0.0.

Begin your analysis now.
"""
        return prompt
    
    async def process_tool_call(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process a tool call from the agent.
        
        Args:
            tool_name: Name of the tool to call
            parameters: Parameters for the tool
            
        Returns:
            Tool result
        """
        try:
            if tool_name == "read_folder_contents":
                if "folder_id" not in parameters:
                    return {"error": "Missing required parameter: folder_id"}
                
                return self.tools.read_folder_contents(folder_id=parameters["folder_id"])
            
            elif tool_name == "examine_product_files":
                if "folder_id" not in parameters:
                    return {"error": "Missing required parameter: folder_id"}
                
                pattern = parameters.get("pattern")
                return self.tools.examine_product_files(folder_id=parameters["folder_id"], pattern=pattern)
            
            elif tool_name == "extract_product_info_from_path":
                if "folder_path" not in parameters:
                    return {"error": "Missing required parameter: folder_path"}
                
                return self.tools.extract_product_info_from_path(folder_path=parameters["folder_path"])
            
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            error_msg = f"Error in tool call {tool_name}: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            log_error(error_msg, "tool_call_error", {
                "tool_name": tool_name,
                "parameters": str(parameters)
            })
            return {"error": str(e)}


# System prompt for the agent
SYSTEM_PROMPT = """
You are a specialized product matching expert tasked with matching products from a database to folders in Google Drive.

Your goal is to determine if a product from our database corresponds to a specific folder in our Drive catalog.

You'll be given:
1. Details about a product from our database
2. A list of potential folder matches from Drive

You should analyze the information and determine if there's a match between the product and one of the folders.

You have access to these tools:
- read_folder_contents(folder_id: str) - Reads contents of a specific folder
- examine_product_files(folder_id: str, pattern: str = None) - Examines files in a folder that might contain product details
- extract_product_info_from_path(folder_path: str) - Extracts potential product information from a folder path

Guidelines:
- Look for matching product names, codes, or descriptions
- Pay attention to EAN/barcode numbers which often appear in folder names
- Consider product categories and families
- Be thorough but efficient in your analysis
- Assign an appropriate confidence score based on the strength of the match

IMPORTANT: When you provide your final answer, return ONLY the JSON object matching the `MatchResult` structure. Do not include any other text, explanations, or conversational filler before or after the JSON.

When you've determined the best match (or that there is no match), return the result in the required format.
""" 