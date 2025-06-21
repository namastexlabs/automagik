# Flashinho V2 Agent

Flashinho V2 is an advanced multimodal Brazilian educational assistant powered by Google Gemini 2.5 Pro model. It provides personalized coaching for Brazilian high school students with authentic Generation Z Portuguese style and complete integration with the Flashed educational gaming platform.

## Features

- **🎓 Educational Coaching**: Specialized Brazilian high school tutoring with focus on Biology and other subjects
- **🧠 Memory System**: Persistent user preferences and conversation history across sessions
- **🖼️ Multimodal Support**: Process images, audio, and documents for educational content
- **🔐 Secure Authentication**: Conversation code-based authentication with Flashed API integration
- **🇧🇷 Cultural Authenticity**: Native Brazilian Portuguese Generation Z communication style
- **⚡ Dynamic Model Selection**: Pro users get enhanced capabilities with Gemini 2.5 Pro

## Architecture

### Authentication Flow

1. **Initial Request**: User provides conversation code (e.g., "ABC123XYZ")
2. **Flashed API Lookup**: System validates code and retrieves user profile
3. **User Creation/Sync**: Creates or syncs user in local database with UUID matching
4. **Session Persistence**: Subsequent requests in same session don't require re-authentication
5. **Memory Loading**: User preferences and educational data loaded for personalization

### Session Management

- **Session Continuity**: Once authenticated, users can continue conversations without re-entering codes
- **Memory Integration**: Stores user preferences, study history, and conversation context
- **UUID Synchronization**: Ensures user IDs match between local database and Flashed platform

### Model Selection

- **Free Users**: Google Gemini 2.5 Flash (fast, efficient)
- **Pro Users**: Google Gemini 2.5 Pro (enhanced capabilities)
- **Multimodal**: Automatically switches to vision-capable models for image processing

## API Usage

### Base Endpoint
```
POST /api/v1/agent/flashinho_v2/run
```

### Headers
```json
{
  "Content-Type": "application/json",
  "X-API-Key": "your-api-key"
}
```

### Authentication Request

```json
{
  "message_content": "ABC123XYZ",
  "session_name": "user-study-session-001"
}
```

### Text Conversation

```json
{
  "message_content": "Preciso de ajuda com divisão celular em biologia",
  "session_name": "user-study-session-001",
  "message_type": "text"
}
```

### Multimodal Request (Image)

```json
{
  "message_content": "O que você pode me falar sobre esta imagem de célula?",
  "session_name": "user-study-session-001",
  "message_type": "image",
  "media_contents": [
    {
      "mime_type": "image/jpeg",
      "media_url": "https://example.com/cell-diagram.jpg",
      "width": 800,
      "height": 600,
      "alt_text": "Diagrama de célula animal"
    }
  ]
}
```

### Multimodal Request (Base64 Image)

```json
{
  "message_content": "Analise esta imagem do meu experimento de biologia",
  "session_name": "user-study-session-001",
  "message_type": "image",
  "media_contents": [
    {
      "mime_type": "image/png",
      "data": "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/...",
      "width": 400,
      "height": 300,
      "alt_text": "Foto do experimento"
    }
  ]
}
```

### Audio Request

```json
{
  "message_content": "Transcreva e me ajude com esta pergunta de biologia",
  "session_name": "user-study-session-001",
  "message_type": "audio",
  "media_contents": [
    {
      "mime_type": "audio/mp3",
      "media_url": "https://example.com/question.mp3",
      "duration_seconds": 15.5,
      "transcript": "Como funciona a fotossíntese?"
    }
  ]
}
```

## Response Format

```json
{
  "message": "E aí! 👋 Demais que você quer entender sobre divisão celular! 🧬...",
  "session_id": "fa2cabec-eec3-43a7-9fd1-53c5ce5c1186",
  "success": true,
  "tool_calls": [],
  "tool_outputs": [],
  "usage": {
    "framework": "pydantic_ai",
    "model": "google-gla:gemini-2.5-flash-preview-05-20",
    "total_requests": 1,
    "request_tokens": 6761,
    "response_tokens": 242,
    "total_tokens": 7195
  }
}
```

## Testing Examples

### Complete Flow Test

1. **Authentication**:
```bash
curl -X POST http://localhost:18881/api/v1/agent/flashinho_v2/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "message_content": "ABC123XYZ",
    "session_name": "test-session-001"
  }'
```

2. **Conversation**:
```bash
curl -X POST http://localhost:18881/api/v1/agent/flashinho_v2/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "message_content": "Gosto de programação em Python",
    "session_name": "test-session-001"
  }'
```

3. **Memory Test**:
```bash
curl -X POST http://localhost:18881/api/v1/agent/flashinho_v2/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "message_content": "Do que eu gosto?",
    "session_name": "test-session-001"
  }'
```

4. **Multimodal Test**:
```bash
curl -X POST http://localhost:18881/api/v1/agent/flashinho_v2/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "message_content": "Explique esta imagem de biologia",
    "session_name": "test-session-001",
    "message_type": "image",
    "media_contents": [
      {
        "mime_type": "image/jpeg",
        "media_url": "https://via.placeholder.com/400x300.jpg?text=Cell+Diagram",
        "width": 400,
        "height": 300,
        "alt_text": "Diagrama celular"
      }
    ]
  }'
```

## Configuration

### Environment Variables

```env
# Flashed API Integration (required)
FLASHED_API_KEY=your-flashed-api-key
FLASHED_API_URL=https://api.flashed.tech/admin

# LLM Models (required)
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key  # for multimodal fallback

# Database (required)
DATABASE_URL=sqlite:///./data/automagik_agents.db
```

### Agent Configuration

The agent automatically configures itself with:
- **Default Model**: `google-gla:gemini-2.5-flash-preview-05-20`
- **Vision Model**: `google-gla:gemini-2.5-flash-preview-05-20` (upgrades to Pro for Pro users)
- **Supported Media**: `["image", "audio", "document"]`
- **Memory Integration**: Automatic user preference and context storage

## Error Handling

### Common Errors

1. **Authentication Required**: Returns request for conversation code
2. **Invalid Code**: Returns error message in Portuguese
3. **Network Issues**: Graceful fallback with retry logic
4. **Multimodal Errors**: Falls back to text-only processing

### Example Error Response

```json
{
  "message": "E aí! 👋 Pra eu conseguir te dar aquela força nos estudos de forma personalizada, preciso do seu código de conversa! 🔑",
  "session_id": "new-session-id",
  "success": true,
  "tool_calls": [],
  "tool_outputs": [],
  "usage": {...}
}
```

## Development

### File Structure

```
flashinho_v2/
├── README.md                 # This documentation
├── __init__.py              # Agent factory function
├── agent.py                 # Main agent implementation
├── identification.py       # User identification utilities
├── memories.py             # Memory management
├── session_utils.py        # Session persistence utilities
├── api_client.py           # Flashed API client
└── prompts/
    ├── __init__.py
    ├── free.py             # Free user prompt
    └── pro.py              # Pro user prompt
```

### Key Classes

- **`FlashinhoV2`**: Main agent class extending AutomagikAgent
- **`UserStatusChecker`**: Handles conversation code validation
- **`FlashinhoMemories`**: Manages user preference storage
- **`FlashinhoAPI`**: Flashed platform integration

### Memory Variables

The agent uses these memory variables for personalization:

- `name`: User's full name
- `levelOfEducation`: Education level (e.g., "3º ano do Ensino Médio")
- `preferredSubject`: Favorite subject (e.g., "Biologia")
- `flashinhoEnergy`: Current energy points
- `sequence`: Study streak
- `dailyProgress`: Daily progress percentage
- `starsBalance`: Star points balance
- `roadmap`: Personalized study roadmap

## Security Notes

- Never commit API keys or conversation codes to version control
- Use environment variables for all sensitive configuration
- Conversation codes are single-use and expire after authentication
- User data is encrypted and stored securely in the database
- All API communications use HTTPS encryption

## Troubleshooting

### Authentication Issues
1. Verify conversation code is valid and not expired
2. Check Flashed API connectivity
3. Ensure database is properly initialized

### Session Issues
1. Use consistent `session_name` across requests
2. Check database user persistence
3. Verify UUID synchronization completed

### Multimodal Issues
1. Verify image URLs are accessible
2. Check base64 encoding for binary data
3. Ensure proper MIME type specification
4. Verify vision model availability

## Support

For technical support or feature requests, please refer to the main project documentation or contact the development team.