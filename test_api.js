// Test API calls directly
const axios = require('axios');

const api = axios.create({
  baseURL: 'http://localhost:28881',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    'x-api-key': 'namastex888',
  },
});

async function testAPI() {
  try {
    console.log('Testing workflows endpoint...');
    const workflows = await api.get('/api/v1/workflows/claude-code/workflows');
    console.log('✅ Workflows:', workflows.data.length, 'workflows found');
    
    console.log('Testing recent runs endpoint...');
    const runs = await api.get('/api/v1/workflows/claude-code/runs', { 
      params: { page_size: 3 } 
    });
    console.log('✅ Recent runs:', runs.data.runs.length, 'runs found');
    
    console.log('✅ API test successful!');
  } catch (error) {
    console.error('❌ API test failed:', error.message);
    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', error.response.data);
    }
  }
}

testAPI();