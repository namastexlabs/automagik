# Workflow Management UI Integration Guide

## 🚨 IMPORTANT: What Changed from the Original Plan

### The API Endpoint Structure
The workflow management API uses a **single endpoint** for all CRUD operations:
- Base URL: `/api/v1/workflows/claude-code/manage`
- **NOT** separate endpoints like `/workflows/definitions` or `/workflows/tools`
- **NOT** complex nested resources

### Simple CRUD Operations

#### 1. GET - List All Workflows
```http
GET /api/v1/workflows/claude-code/manage
Authorization: Bearer your-api-key
```

**Response:**
```json
[
  {
    "name": "genie",
    "description": "Self-improving architect and orchestrator consciousness",
    "valid": true,
    "category": "improvement"
  },
  {
    "name": "my-custom-workflow",
    "description": "A custom workflow",
    "valid": true,
    "category": "custom"
  }
]
```

#### 2. POST - Create New Workflow
```http
POST /api/v1/workflows/claude-code/manage
Authorization: Bearer your-api-key
Content-Type: application/json

{
  "name": "my-new-workflow",
  "display_name": "My New Workflow",
  "description": "Description of the workflow",
  "category": "anything-you-want",  // ✅ ANY string is valid now!
  "prompt_template": "You are a specialized agent that...",
  "allowed_tools": ["git", "sqlite", "linear"],
  "mcp_config": {},
  "active": true,
  "config": {}
}
```

**Response:**
```json
{
  "success": true,
  "message": "Workflow 'my-new-workflow' created successfully",
  "workflow": {
    "id": 8,
    "name": "my-new-workflow",
    "display_name": "My New Workflow",
    "description": "Description of the workflow",
    "category": "anything-you-want",
    "active": true,
    "is_system_workflow": false,
    "created_at": "2025-06-27T12:34:56"
  }
}
```

#### 3. PUT - Update Existing Workflow
```http
PUT /api/v1/workflows/claude-code/manage
Authorization: Bearer your-api-key
Content-Type: application/json

{
  "name": "my-new-workflow",  // ⚠️ REQUIRED to identify which workflow
  "display_name": "Updated Workflow Name",
  "description": "Updated description",
  "category": "my-special-category",  // ✅ Custom categories allowed!
  "prompt_template": "Updated prompt...",
  "allowed_tools": ["git", "sqlite", "linear", "agent-memory"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Workflow 'my-new-workflow' updated successfully",
  "workflow": {
    "id": 8,
    "name": "my-new-workflow",
    "display_name": "Updated Workflow Name",
    "description": "Updated description",
    "category": "my-special-category",
    "active": true,
    "is_system_workflow": false,
    "updated_at": "2025-06-27T12:35:56"
  }
}
```

#### 4. DELETE - Delete Workflow
```http
DELETE /api/v1/workflows/claude-code/manage?name=my-new-workflow
Authorization: Bearer your-api-key
```

**Response:**
```json
{
  "success": true,
  "message": "Workflow 'my-new-workflow' deleted successfully"
}
```

## ⚠️ Critical Implementation Notes

### 1. Workflow Name is the Primary Identifier
- The `name` field is **UNIQUE** and used as the identifier
- Always include `name` in PUT requests to identify the workflow
- The `name` field **CANNOT** be changed after creation
- Use `display_name` for the human-readable name that can be changed

### 2. System Workflow Protection
```javascript
// Check this flag to disable edit/delete buttons
if (workflow.is_system_workflow) {
  // Disable update and delete actions
  // Show "System Workflow" badge
  // These are: genie, builder, guardian, surgeon, shipper, brain, lina
}
```

### 3. Category Field is Now Flexible
- **NO VALIDATION** on category values
- Users can enter **ANY STRING** as a category
- Suggested categories for UI dropdown:
  - `custom` (default)
  - `system`
  - `security`
  - `maintenance`
  - `analysis`
  - `creation`
  - `improvement`
  - But allow free text input!

**IMPORTANT TypeScript Fix Required:**
```typescript
// ❌ OLD - REMOVE THIS
interface WorkflowRequest {
  category?: 'analysis' | 'improvement' | 'security' | 'system' | 'creation' | 'maintenance' | 'custom';
}

// ✅ NEW - USE THIS
interface WorkflowRequest {
  category?: string;  // ANY string is valid now!
}

### 4. Required vs Optional Fields

**Required for POST (create):**
- `name` - Unique identifier (alphanumeric, hyphens, underscores)
- `prompt_template` - The main prompt content

**Required for PUT (update):**
- `name` - To identify which workflow to update

**All other fields are optional with defaults:**
- `display_name` - Defaults to null
- `description` - Defaults to null
- `category` - Defaults to "custom"
- `allowed_tools` - Defaults to []
- `mcp_config` - Defaults to {}
- `active` - Defaults to true
- `config` - Defaults to {}

## 🐛 Common Integration Issues and Solutions

### Issue 1: "Invalid category" Error
**Old behavior**: Category was restricted to a specific list
**New behavior**: ANY category string is accepted
**Solution**: Remove any client-side validation for category

### Issue 2: Trying to Update Workflow Name
**Problem**: The `name` field is immutable
**Solution**: Only allow editing `display_name`, not `name`
```javascript
// ❌ WRONG
updateWorkflow({ 
  name: "new-name",  // This will create a new workflow!
  ...otherFields 
})

// ✅ CORRECT
updateWorkflow({ 
  name: "existing-name",  // Original name to identify
  display_name: "New Display Name",  // What user sees
  ...otherFields 
})
```

### Issue 3: Missing Workflow in GET Response
**Problem**: GET endpoint returns minimal data
**Solution**: The GET response includes these fields:
- `name` - Unique identifier
- `description` - Description text
- `valid` - Boolean validation status
- `category` - Category string

For full workflow details, you'll need to:
1. Store additional data from POST/PUT responses
2. Or enhance the backend GET endpoint (let me know if needed)

### Issue 4: 404 on Update/Delete
**Problem**: Workflow not found
**Common causes**:
1. Wrong workflow name (it's case-sensitive)
2. Trying to update a workflow that doesn't exist
3. URL encoding issues with special characters

**Solution**: Always use exact workflow name from GET response

## 📝 Recommended UI Implementation

### 1. Workflow List Table
```javascript
const columns = [
  { field: 'display_name', header: 'Name', sortable: true },
  { field: 'name', header: 'ID', sortable: true },
  { field: 'category', header: 'Category', sortable: true },
  { field: 'description', header: 'Description' },
  { 
    field: 'is_system_workflow', 
    header: 'Type',
    render: (value) => value ? 
      <Badge color="blue">System</Badge> : 
      <Badge color="green">Custom</Badge>
  },
  {
    field: 'actions',
    header: 'Actions',
    render: (row) => (
      <>
        <EditButton disabled={row.is_system_workflow} />
        <DeleteButton disabled={row.is_system_workflow} />
      </>
    )
  }
];
```

### 2. Create/Edit Form
```javascript
const WorkflowForm = ({ workflow, onSubmit }) => {
  const isEdit = !!workflow;
  const isSystem = workflow?.is_system_workflow;
  
  return (
    <Form onSubmit={onSubmit}>
      {/* Name field - disabled on edit */}
      <TextField
        name="name"
        label="Workflow ID"
        required
        disabled={isEdit}
        pattern="[a-z0-9-_]+"
        helperText="Lowercase letters, numbers, hyphens, underscores only"
      />
      
      {/* Display name - always editable */}
      <TextField
        name="display_name"
        label="Display Name"
        disabled={isSystem}
      />
      
      {/* Category - free text input with suggestions */}
      <Autocomplete
        name="category"
        label="Category"
        freeSolo  // Allow custom values!
        options={['custom', 'security', 'maintenance', 'analysis', 'creation', 'improvement']}
        disabled={isSystem}
      />
      
      {/* Prompt template - large text area */}
      <TextArea
        name="prompt_template"
        label="Prompt Template"
        required
        rows={10}
        disabled={isSystem}
        helperText="The main prompt that defines this workflow's behavior"
      />
      
      {/* Allowed tools - multi-select */}
      <MultiSelect
        name="allowed_tools"
        label="Allowed Tools"
        options={availableTools}  // Get from tools API
        disabled={isSystem}
      />
      
      {/* MCP Config - JSON editor */}
      <JsonEditor
        name="mcp_config"
        label="MCP Configuration (Advanced)"
        disabled={isSystem}
      />
      
      {/* Active toggle */}
      <Switch
        name="active"
        label="Active"
        disabled={isSystem}
      />
    </Form>
  );
};
```

### 3. Error Handling
```javascript
const handleApiError = (error) => {
  switch (error.status) {
    case 400:
      if (error.detail.includes('Cannot update system workflows')) {
        showError('System workflows cannot be modified');
      } else if (error.detail.includes('already exists')) {
        showError('A workflow with this name already exists');
      } else {
        showError(error.detail);
      }
      break;
    case 404:
      showError('Workflow not found. It may have been deleted.');
      break;
    case 401:
      showError('Invalid API key. Please check your authentication.');
      break;
    default:
      showError('An unexpected error occurred. Please try again.');
  }
};
```

## 🎯 Complete Working Example

```javascript
// IMPORTANT: Update your TypeScript interfaces!
interface WorkflowManageRequest {
  name: string;
  display_name?: string;
  description?: string;
  category?: string;  // ✅ NOT a union type - ANY string is valid!
  prompt_template: string;
  allowed_tools?: string[];
  mcp_config?: Record<string, any>;
  active?: boolean;
  config?: Record<string, any>;
}

// Workflow Management Service
class WorkflowService {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.baseUrl = '/api/v1/workflows/claude-code/manage';
  }

  async listWorkflows() {
    const response = await fetch(this.baseUrl, {
      headers: {
        'Authorization': `Bearer ${this.apiKey}`
      }
    });
    
    if (!response.ok) throw new Error(`Failed to list workflows: ${response.statusText}`);
    return response.json();
  }

  async createWorkflow(workflowData) {
    const response = await fetch(this.baseUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(workflowData)
    });
    
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Failed to create workflow');
    return data;
  }

  async updateWorkflow(workflowData) {
    // Note: workflowData MUST include the original 'name' field
    const response = await fetch(this.baseUrl, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(workflowData)
    });
    
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Failed to update workflow');
    return data;
  }

  async deleteWorkflow(workflowName) {
    const response = await fetch(`${this.baseUrl}?name=${encodeURIComponent(workflowName)}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`
      }
    });
    
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Failed to delete workflow');
    return data;
  }
}

// Usage
const workflowService = new WorkflowService('your-api-key');

// Create a new workflow
const newWorkflow = await workflowService.createWorkflow({
  name: 'data-analyzer',
  display_name: 'Data Analysis Workflow',
  description: 'Analyzes data and provides insights',
  category: 'data-science',  // Custom category!
  prompt_template: 'You are a data analysis expert...',
  allowed_tools: ['sqlite', 'agent-memory'],
  active: true
});

// Update the workflow
const updated = await workflowService.updateWorkflow({
  name: 'data-analyzer',  // MUST include original name
  display_name: 'Advanced Data Analyzer',
  allowed_tools: ['sqlite', 'agent-memory', 'linear']
});

// Delete the workflow
await workflowService.deleteWorkflow('data-analyzer');
```

## 💡 Additional Tips

1. **Workflow Naming Convention**: Suggest using kebab-case for workflow names (e.g., `my-custom-workflow`)

2. **Tool Suggestions**: Get available tools from `/api/v1/tools` endpoint to populate the allowed_tools selector

3. **Prompt Template Help**: Consider adding a markdown preview for the prompt template field

4. **Validation Feedback**: Show real-time validation for the workflow name field (alphanumeric + hyphens + underscores only)

5. **Bulk Operations**: The API doesn't support bulk operations, so implement client-side queuing for multiple updates

6. **Caching**: Cache the workflow list and update optimistically for better UX

## 🆘 Need Help?

If you encounter any issues or need additional functionality:

1. The GET endpoint can be enhanced to return full workflow details if needed
2. Bulk operations can be added if required
3. Additional filtering/searching capabilities can be implemented
4. Export/Import functionality can be added

Just let me know what specific features the UI needs, and I can implement them in the backend!