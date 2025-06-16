# Automagik UI Dashboard

A Next.js dashboard for managing Automagik workflows and monitoring system health.

## Features

- **Quick Actions**: Start workflows with an intuitive interface
- **System Health**: Real-time monitoring of API, database, MCP, and memory services
- **Workflow Management**: View and track running workflows with real-time updates
- **Responsive Design**: Built with Tailwind CSS for all screen sizes

## Getting Started

### Prerequisites

- Node.js 18+ 
- Automagik API running on localhost:28881

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The dashboard will be available at [http://localhost:3000](http://localhost:3000).

### Production Build

```bash
# Build for production
npm run build

# Start production server
npm start
```

## API Integration

The dashboard connects to the Automagik API at `http://localhost:28881` and uses the following endpoints:

- `/health` - System health monitoring
- `/automagik-workflows/list-workflows` - Available workflows
- `/automagik-workflows/run-workflow` - Start new workflows
- `/automagik-workflows/get-workflow-status/{id}` - Workflow status
- `/automagik-workflows/list-recent-runs` - Recent workflow runs

## Components

### QuickActions
Interactive workflow launcher with form validation and real-time feedback.

### SystemHealth
Real-time system monitoring with service status indicators and health metrics.

### WorkflowCard
Displays workflow status with progress tracking, timing information, and real-time updates.

## Architecture

- **Framework**: Next.js 14 with App Router
- **Styling**: Tailwind CSS with custom Automagik theme
- **API Client**: Axios with TypeScript interfaces
- **State Management**: React hooks for local state
- **Real-time Updates**: Polling for workflow status updates

## Development

The project uses TypeScript for type safety and includes:

- ESLint for code quality
- Tailwind CSS for styling
- Responsive design patterns
- Error handling and loading states
- Real-time polling for dynamic updates

## Deployment

Build the project and serve the static files:

```bash
npm run build
npm start
```

Or deploy to platforms like Vercel, Netlify, or any Node.js hosting service.