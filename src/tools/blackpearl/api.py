import httpx # Using httpx for async requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Black Pearl API base URL
BLACK_PEARL_API_URL = "https://blackpearl.talbitz.com/api/v1/catalogo"

async def fetch_blackpearl_product_details(
    product_id: int
) -> Optional[Dict[str, Any]]:
    """Core async logic to fetch product details from Black Pearl API."""
    product_url = f"{BLACK_PEARL_API_URL}/produtos/{product_id}/"
    logger.info(f"Fetching product details for ID: {product_id} from {product_url}")
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(product_url)
            response.raise_for_status() # Raise exception for 4xx/5xx status
            product_data = response.json()
            logger.info(f"Successfully fetched product details for ID: {product_id}")
            return product_data
    except httpx.HTTPStatusError as e:
        logger.error(f"Error fetching product {product_id} from Black Pearl (HTTP Status {e.response.status_code}): {e.response.text}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Error fetching product {product_id} from Black Pearl (Request Error): {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error fetching product {product_id} from Black Pearl: {e}")
        return None

async def fetch_blackpearl_product_image_url(product_id: int) -> Optional[str]:
    """Fetches product details and returns the primary image URL."""
    product_data = await fetch_blackpearl_product_details(product_id)
    if product_data:
        image_url = product_data.get("imagem")
        if image_url:
            logger.info(f"Found primary image URL for product {product_id}: {image_url}")
            return image_url
        else:
            logger.warning(f"No primary image URL ('imagem' field) found for product {product_id} in data: {product_data}")
            return None
    return None

# Add other Black Pearl API interaction functions here as needed...
