# Multimodal Processing

This document describes the multimodal processing capabilities available in Automagik Agents, allowing agents to process and understand images alongside text.

## Overview

Both **Simple** and **Sofia** agents support multimodal processing, enabling them to:

- Process images from HTTP/HTTPS URLs
- Handle multiple images in a single request
- Convert images to PydanticAI-compatible formats
- Provide graceful fallback for legacy formats
- Support presigned S3/MinIO URLs

## Supported Agents

| Agent | Multimodal Support | Image Types | Multiple Images |
|-------|-------------------|-------------|-----------------|
| **Simple** | ✅ Full | HTTP/S URLs, S3 URLs | ✅ Yes |
| **Sofia** | ✅ Full | HTTP/S URLs, S3 URLs | ✅ Yes |

## Usage

### API Request Format

Send multimodal content using the `multimodal_content` parameter:

```json
{
  "user_input": "What do you see in these images?",
  "multimodal_content": {
    "images": [
      {
        "data": "https://example.com/image1.jpg",
        "mime_type": "image/jpeg"
      },
      {
        "data": "https://s3.amazonaws.com/bucket/image2.png",
        "mime_type": "image/png"
      }
    ]
  }
}
```

### Python SDK Usage

```python
from src.agents.simple.simple.agent import SimpleAgent

agent = SimpleAgent({"model_name": "openai:gpt-4.1"})

multimodal_content = {
    "images": [
        {
            "data": "https://example.com/photo.jpg",
            "mime_type": "image/jpeg"
        }
    ]
}

response = await agent.run(
    "Describe this image",
    multimodal_content=multimodal_content
)
```

### CLI Usage

```bash
# Using automagik CLI with multimodal content
automagik agents run simple \
  --input "Analyze this image" \
  --multimodal-content '{"images":[{"data":"https://example.com/image.jpg","mime_type":"image/jpeg"}]}'
```

## Image Format Support

### Supported Image Types

- **JPEG** (`image/jpeg`)
- **PNG** (`image/png`)
- **WebP** (`image/webp`)
- **GIF** (`image/gif`)

### Supported URL Types

1. **HTTP/HTTPS URLs**
   ```json
   {
     "data": "https://example.com/image.jpg",
     "mime_type": "image/jpeg"
   }
   ```

2. **Presigned S3/MinIO URLs**
   ```json
   {
     "data": "https://s3.amazonaws.com/bucket/image.png?X-Amz-Algorithm=...",
     "mime_type": "image/png"
   }
   ```

3. **Base64 Data URLs** (Future support)
   ```json
   {
     "data": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",
     "mime_type": "image/jpeg"
   }
   ```

## Technical Implementation

### PydanticAI Integration

Both agents convert image URLs to PydanticAI `ImageUrl` objects:

```python
from pydantic_ai import ImageUrl

def _convert_image_payload_to_pydantic(self, multimodal_content: Dict[str, Any]) -> List[Any]:
    """Convert multimodal content to PydanticAI format."""
    converted_content = []
    
    if "images" in multimodal_content:
        for image in multimodal_content["images"]:
            image_data = image.get("data", "")
            
            if image_data.startswith(("http://", "https://")):
                try:
                    converted_content.append(ImageUrl(url=image_data))
                except Exception as e:
                    # Fallback to dict format
                    converted_content.append(image)
            else:
                converted_content.append(image)
    
    return converted_content
```

### Graceful Fallback

If PydanticAI types are not available or conversion fails, agents fall back to dictionary format:

```python
# Fallback format
{
    "data": "https://example.com/image.jpg",
    "mime_type": "image/jpeg"
}
```

### Multiple Image Processing

Agents can process multiple images in a single request:

```python
user_input = [
    "Analyze these images and compare them:",
    ImageUrl(url="https://example.com/image1.jpg"),
    ImageUrl(url="https://example.com/image2.jpg")
]
```

## Model Requirements

### Compatible Models

Multimodal processing requires vision-capable models:

| Provider | Model | Multimodal Support |
|----------|-------|-------------------|
| **OpenAI** | `gpt-4.1` | ✅ Full |
| **OpenAI** | `gpt-4.1-mini` | ✅ Full |
| **OpenAI** | `gpt-4-vision-preview` | ✅ Full |
| **Google** | `gemini-1.5-pro` | ✅ Full |
| **Google** | `gemini-1.5-flash` | ✅ Full |
| **Anthropic** | `claude-3-opus` | ✅ Full |
| **Anthropic** | `claude-3-sonnet` | ✅ Full |

### Configuration

Configure multimodal-capable models in agent initialization:

```python
config = {
    "model_name": "openai:gpt-4.1",  # Vision-capable model
    "max_tokens": "1000"
}
agent = SimpleAgent(config)
```

## Error Handling

### Common Errors

1. **Invalid Image URL**
   ```json
   {
     "error": "Failed to load image from URL",
     "details": "HTTP 404: Image not found"
   }
   ```

2. **Unsupported Format**
   ```json
   {
     "error": "Unsupported image format",
     "details": "Format 'image/tiff' not supported"
   }
   ```

3. **Model Limitations**
   ```json
   {
     "error": "Model does not support vision",
     "details": "gpt-3.5-turbo cannot process images"
   }
   ```

### Error Recovery

Agents handle errors gracefully:

```python
try:
    result = await agent.run(
        "Describe this image",
        multimodal_content=multimodal_content
    )
except Exception as e:
    # Agent returns error response instead of crashing
    return AgentResponse(
        text=f"Error processing image: {e}",
        success=False,
        error_message=str(e)
    )
```

## Best Practices

### Image Optimization

1. **Use appropriate image sizes** (max 20MB per image)
2. **Optimize for web delivery** (compressed JPEG/PNG)
3. **Use CDN URLs** for better performance
4. **Provide descriptive mime_type** for better processing

### Multiple Images

1. **Limit concurrent images** (max 10 per request recommended)
2. **Use clear descriptions** when analyzing multiple images
3. **Consider image order** in analysis requests

### URL Management

1. **Use HTTPS URLs** for security
2. **Ensure URL accessibility** from agent environment
3. **Handle presigned URL expiration** appropriately
4. **Validate URLs** before sending to agent

## Examples

### Single Image Analysis

```python
response = await agent.run(
    "What's in this image?",
    multimodal_content={
        "images": [{
            "data": "https://example.com/photo.jpg",
            "mime_type": "image/jpeg"
        }]
    }
)
```

### Multiple Image Comparison

```python
response = await agent.run(
    "Compare these two images and highlight the differences",
    multimodal_content={
        "images": [
            {
                "data": "https://example.com/before.jpg",
                "mime_type": "image/jpeg"
            },
            {
                "data": "https://example.com/after.jpg", 
                "mime_type": "image/jpeg"
            }
        ]
    }
)
```

### Document Analysis

```python
response = await agent.run(
    "Extract text and analyze the content of this document",
    multimodal_content={
        "images": [{
            "data": "https://example.com/document.png",
            "mime_type": "image/png"
        }]
    }
)
```

## Troubleshooting

### Debug Logging

Enable debug logging to trace multimodal processing:

```python
import logging
logging.getLogger('src.agents').setLevel(logging.DEBUG)
```

### Common Issues

1. **Images not loading**: Check URL accessibility and network connectivity
2. **Poor image quality**: Ensure images are clear and high-resolution
3. **Model errors**: Verify model supports vision capabilities
4. **Format issues**: Confirm image format is supported

### Testing

Test multimodal functionality:

```bash
# Run multimodal tests
python -m pytest tests/agents/simple/test_multimodal.py -v

# Test specific image processing
python -m pytest tests/agents/simple/test_multimodal.py::TestSimpleAgentMultimodal::test_multimodal_processing_with_images -v
```

## Future Enhancements

- **Base64 image support** for embedded images
- **Image preprocessing** and optimization
- **Batch image processing** for large datasets
- **Image generation** capabilities
- **Video frame extraction** and analysis 