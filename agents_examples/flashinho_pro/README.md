# Flashinho Pro Agent

Advanced multimodal Brazilian educational assistant with Pro subscription features and comprehensive Flashed API integration.

## Features

- Advanced multimodal capabilities (images, audio, documents)
- Brazilian Portuguese educational assistance with Generation Z style
- Complete Flashed API integration for user data and gamification
- Pro subscription status checking and feature gating
- Educational problem detection and workflow orchestration
- Evolution API integration for messaging
- User identification and authentication management

## Configuration

The agent uses Google Gemini 2.5 Pro for premium users and requires:

- `GEMINI_API_KEY` environment variable
- Flashed API access for user data integration
- Evolution API access for messaging features

## Tools

### Flashed API Tools
- `get_user_data` - Get user profile information
- `get_user_score` - Get user progress and energy
- `get_user_roadmap` - Get study roadmap
- `get_user_objectives` - Get learning objectives
- `get_last_card_round` - Get last study session data
- `get_user_energy` - Get current energy level
- `get_user_by_pretty_id` - Get user by conversation code

### Authentication & User Management
- `UserStatusChecker` - Check Pro subscription status
- `identify_user_comprehensive` - Comprehensive user identification
- `analyze_student_problem` - Educational problem analysis workflow
- Message generation utilities for different contexts

### Evolution API Tools
- `send_text_message` - Send messages via Evolution API

## Usage

```python
from agents_examples.flashinho_pro import FlashinhoPro

agent = FlashinhoPro(config={
    "model": "google:gemini-2.5-pro",
    "temperature": 0.7
})

response = await agent.run(
    "Preciso de ajuda com esta questão de matemática", 
    multimodal_content={"image_data": "base64_image"}
)
```

## Client-Specific Features

This agent is designed for premium Brazilian educational platform integration and includes:

- Pro vs Free user feature differentiation
- Mathematical problem detection in images
- Workflow orchestration for complex educational tasks
- Real-time messaging integration
- User session persistence and authentication