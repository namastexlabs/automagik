# Airtable Agent Tests

This directory contains tests for the Airtable agent functionality, specifically focused on testing task filtering and querying capabilities.

## Files

- `test_filters_airtable_agent.py` - Main test script for Airtable agent functionality

## Test Overview

The test script validates the Airtable agent's ability to:

1. **Query specific records** based on user names (e.g., "Cezar Vasconcelos")
2. **Filter tasks by assignee** and other criteria
3. **Present results** in a user-friendly format
4. **Handle various query patterns** and edge cases

## Setup Requirements

Before running the tests, ensure you have the following configuration in your `.env` file:

```bash
# Required for Airtable integration
AIRTABLE_TOKEN=your_airtable_api_token
AIRTABLE_DEFAULT_BASE_ID=your_base_id

# Required for LLM functionality
OPENAI_API_KEY=your_openai_api_key
```

### Getting Airtable Credentials

1. **AIRTABLE_TOKEN**: 
   - Go to [Airtable Developer Hub](https://airtable.com/developers/web/api/introduction)
   - Create a personal access token
   - Ensure it has read access to your base

2. **AIRTABLE_DEFAULT_BASE_ID**:
   - Open your Airtable base in the browser
   - The base ID is in the URL: `https://airtable.com/[BASE_ID]/...`
   - Or use the Airtable API documentation for your base

## Running the Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the test script
python tests/agents/airtable/test_filters_airtable_agent.py
```

## Test Behavior

### With Full Configuration
When all required environment variables are set, the test will:
- Initialize the Airtable agent with fresh schema
- Run basic capability tests
- Test Cezar Vasconcelos task queries
- Test improved query patterns
- Analyze agent capabilities

### With Missing Configuration
When configuration is missing, the test will:
- Show configuration status
- Run basic tests only (if possible)
- Skip advanced tests that require API access
- Provide guidance on what needs to be configured

## Expected Output

The test provides detailed output including:
- ✅ Success indicators for working functionality
- ❌ Error indicators with specific error messages
- 🔧 Configuration status and setup guidance
- 📊 Test results and improvement suggestions

## Troubleshooting

### Common Issues

1. **"Connection error"**: Usually indicates missing or invalid OPENAI_API_KEY
2. **"AIRTABLE_TOKEN not configured"**: Missing Airtable API credentials
3. **"maximum recursion depth exceeded"**: Fixed in current version, but indicates agent initialization issues

### Debug Steps

1. Check `.env` file has all required variables
2. Verify Airtable token has correct permissions
3. Test OpenAI API key with a simple request
4. Check network connectivity and firewall settings

## Test Improvements

Based on test results, consider these improvements:
1. 🔍 Better field name recognition for assignee/responsible person
2. 🎯 More intelligent filtering based on partial name matches
3. 📋 Enhanced presentation of task lists with status, priority, dates
4. 🔗 Better handling of linked record fields (Team Members table)
5. 💬 More conversational and user-friendly response formatting
6. 🚀 Caching of common queries for better performance 