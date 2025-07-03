"""Model Discovery Service for fetching available models from providers."""

import httpx
import logging
from typing import List
from automagik.config import settings

logger = logging.getLogger(__name__)


class ModelDiscoveryService:
    """Fetch available models from providers based on API keys."""
    
    def __init__(self):
        self.settings = settings
    
    async def get_available_models(self) -> List[str]:
        """Returns flat list of model strings like 'openai:gpt-4'."""
        models = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # OpenAI models
            if self.settings.OPENAI_API_KEY:
                try:
                    response = await client.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {self.settings.OPENAI_API_KEY}"}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        for model in data.get('data', []):
                            model_id = model['id']
                            # Filter out non-chat models
                            if any(x in model_id for x in ['gpt', 'o1', 'o3', 'o4', 'chatgpt']):
                                models.append(f"openai:{model_id}")
                except Exception as e:
                    logger.error(f"Failed to fetch OpenAI models: {e}")
            
            # Anthropic models
            if self.settings.ANTHROPIC_API_KEY:
                try:
                    response = await client.get(
                        "https://api.anthropic.com/v1/models",
                        headers={
                            "x-api-key": self.settings.ANTHROPIC_API_KEY,
                            "anthropic-version": "2023-06-01"
                        }
                    )
                    if response.status_code == 200:
                        data = response.json()
                        models.extend([f"anthropic:{m['id']}" for m in data.get('data', [])])
                except Exception as e:
                    logger.error(f"Failed to fetch Anthropic models: {e}")
            
            # Google Gemini models
            if self.settings.GEMINI_API_KEY:
                try:
                    response = await client.get(
                        f"https://generativelanguage.googleapis.com/v1beta/models?key={self.settings.GEMINI_API_KEY}"
                    )
                    if response.status_code == 200:
                        data = response.json()
                        for m in data.get('models', []):
                            # Only include generation models, not embeddings
                            if 'generateContent' in m.get('supportedGenerationMethods', []):
                                model_name = m['name'].replace('models/', '')
                                models.append(f"google:{model_name}")
                except Exception as e:
                    logger.error(f"Failed to fetch Gemini models: {e}")
        
        return sorted(list(set(models)))  # Return sorted unique models