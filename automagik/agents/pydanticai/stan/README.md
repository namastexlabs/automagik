# STAN Agent Documentation

## Overview

STAN is a sophisticated WhatsApp-based sales agent for Solid, a hardware distribution company specializing in gaming peripherals. STAN handles customer interactions, manages registrations, and coordinates with specialized agents for backend operations.

## Architecture

### Core Components

1. **Main Agent** (`/stan/__init__.py`)
   - Entry point for all WhatsApp messages
   - Manages user context and session state
   - Coordinates with specialized agents

2. **Prompt System** (`/prompts/`)
   - Dynamic prompt loading based on user status
   - Status-specific conversation flows
   - Template variable support

3. **Specialized Agents** (`/specialized/`)
   - **Backoffice Agent**: Handles BlackPearl API operations
   - **Product Agent**: Manages product catalog and images

4. **Channel Handlers** (`/channels/`)
   - WhatsApp message processing
   - Evolution API integration

## How STAN Works

### 1. Message Flow

```
WhatsApp Message → Evolution API → STAN API Endpoint → STAN Agent → Response
                                                           ↓
                                                    Specialized Agents
                                                           ↓
                                                    BlackPearl/Gmail
```

### 2. Contact & Status Management

STAN uses BlackPearl API to manage contacts with the following statuses:
- `NOT_REGISTERED`: New users, need to complete registration
- `PENDING_REVIEW`: Registration submitted, awaiting approval
- `APPROVED`: Can access prices and place orders
- `REJECTED`: Registration denied
- `VERIFYING`: Under verification process

### 3. Dynamic Prompt Loading

STAN loads different prompts based on user status:

```python
# Status determines which prompt file to load
NOT_REGISTERED → prompts/NOT_REGISTERED.md
PENDING_REVIEW → prompts/PENDING_REVIEW.md
APPROVED → prompts/APPROVED.md
```

Each prompt file contains:
- Status-specific instructions
- Appropriate conversation flow
- Business rules for that status

## Testing STAN

### Basic Test Payload

```json
{
  "message_content": "Oi, qual status do meu cadastro?",
  "message_limit": 100,
  "user_id": "4f25505d-b707-4fe2-9a32-1db18683cf18",
  "message_type": "text",
  "session_name": "stan-prod-555197285829"
}
```

### Complete WhatsApp Payload Example

```json
{
  "message_content": "Quero me cadastrar para revender",
  "message_limit": 100,
  "user_id": "unique-user-id-here",
  "message_type": "text",
  "session_name": "stan-prod-5511999999999",
  "channel_type": "whatsapp",
  "evolution_payload": {
    "data": {
      "key": {
        "remoteJid": "5511999999999@s.whatsapp.net",
        "fromMe": false,
        "id": "message-id-123"
      },
      "message": {
        "conversation": "Quero me cadastrar para revender"
      },
      "messageType": "conversation",
      "pushName": "João Silva",
      "owner": "evolution-instance-name"
    },
    "instance": "evolution-instance-name"
  }
}
```

### Testing Different Scenarios

#### 1. New User Registration
```json
{
  "message_content": "Olá, quero vender produtos da Solid",
  "user_id": "new-user-id",
  "message_type": "text",
  "session_name": "stan-test-5511999999999"
}
```

#### 2. Status Check
```json
{
  "message_content": "qual status do meu cadastro?",
  "user_id": "existing-user-id",
  "message_type": "text",
  "session_name": "stan-test-5511999999999"
}
```

#### 3. Product Inquiry
```json
{
  "message_content": "quais teclados vocês tem?",
  "user_id": "approved-user-id",
  "message_type": "text",
  "session_name": "stan-test-5511999999999"
}
```

## BlackPearl Integration

### Contact Creation Flow

1. **User sends first message** → STAN checks BlackPearl for existing contact
2. **If no contact exists** → Creates new contact with WhatsApp info
3. **Contact created** → Status set to `NOT_REGISTERED`
4. **User provides registration info** → STAN collects all required data
5. **User confirms info** → Backoffice agent creates client in BlackPearl
6. **Client created** → Contact status updated to `PENDING_REVIEW`
7. **Lead email sent** → Solid team notified of new registration

### Contact Lookup Process

```python
# STAN performs these checks on every message:
1. Get WhatsApp number from payload
2. Search BlackPearl contacts by phone
3. If found: Load appropriate prompt based on status
4. If not found: Create new contact as NOT_REGISTERED
5. Store contact_id in user context for session
```

## Registration Workflow

### Required Information
- **Company Details**: CNPJ, Razão Social, Nome Fantasia
- **Contact Info**: Email, Phone
- **Address**: Full address with CEP
- **Business Info**: Number of employees, operation type
- **State Registration**: Inscrição Estadual (or "Isento")

### CNPJ Verification
STAN automatically verifies CNPJs and retrieves company information from government APIs, reducing manual data entry.

### Lead Email Generation
Upon successful registration, STAN automatically sends a formatted email to the Solid team with all collected information.

## Configuration

### Environment Variables
```bash
# BlackPearl API
BLACKPEARL_BASE_URL=https://blackpearl.talbitz.com
BLACKPEARL_API_TOKEN=your-token

# Evolution API
EVOLUTION_API_URL=https://evolution-api.com
EVOLUTION_API_TOKEN=your-token

# Gmail (for lead emails)
GMAIL_SENDER_EMAIL=sender@solidbr.com
GMAIL_APP_PASSWORD=your-app-password
```

### Memory Variables
STAN uses persistent memory for:
- `user_information`: Stores user name and phone
- `recent_approval_email_message`: Tracks approval communications

## Debugging

### Log Markers
- `🔍` - Debug/trace information
- `📝` - Standard operations
- `✅` - Success operations
- `❌` - Errors
- `⚠️` - Warnings

### Common Issues

1. **"Technical difficulties" message**
   - Usually indicates BlackPearl API error
   - Check logs for 500 errors
   - Verify API connectivity

2. **Status not updating**
   - Ensure contact exists in BlackPearl
   - Check contact approval_status field
   - Verify prompt files exist for status

3. **Registration not completing**
   - Check all required fields are collected
   - Verify CNPJ is valid
   - Ensure BlackPearl API is accessible

## Prompt Management

### Adding New Status
1. Create new prompt file: `prompts/NEW_STATUS.md`
2. Add status to `StatusAprovacaoEnum` in BlackPearl schema
3. Update prompt loading logic if needed

### Template Variables
Prompts support dynamic variables:
- `{{user_information}}` - User's name and phone
- `{{recent_approval_email_message}}` - Last approval email

## API Endpoints

### Main Endpoint
```
POST /api/v1/agents/{agent_id}/pydanticai/run
```

### Health Check
```
GET /health
```

## Development Tips

1. **Test locally** with Evolution API sandbox
2. **Use debug mode** to see detailed BlackPearl responses
3. **Monitor logs** for conversation flow
4. **Test each status** separately
5. **Verify email delivery** for leads

## Error Handling

STAN gracefully handles:
- BlackPearl API timeouts
- Invalid CNPJ formats
- Missing required fields
- Network failures
- Invalid WhatsApp payloads

Errors are logged but users receive friendly messages to maintain conversation flow.