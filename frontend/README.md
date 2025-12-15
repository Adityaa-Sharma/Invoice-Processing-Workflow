# Invoice Processing Workflow - Frontend

Minimal React frontend for demonstrating the LangGraph Invoice Processing Workflow.

## Setup

```bash
cd frontend
npm install
npm run dev
```

## Features

- **Pipeline Visualization**: Shows all 12 workflow stages with real-time progress
- **Invoice Form**: Submit invoices with demo data option
- **HITL Panel**: Human-in-the-loop review interface for discrepancy handling
- **Log Panel**: Real-time processing logs
- **Server Health**: Visual status of API, COMMON MCP, and ATLAS MCP servers

## Architecture

```
src/
├── App.tsx              # Main application
├── components/
│   ├── ui.tsx           # Reusable primitives (Badge, Button, Card, Input)
│   ├── Pipeline.tsx     # Workflow stage visualization
│   ├── InvoiceForm.tsx  # Invoice submission form
│   ├── HITLPanel.tsx    # Human review interface
│   ├── LogPanel.tsx     # Processing log display
│   └── ServerHealth.tsx # Server status indicators
├── hooks/
│   └── useWorkflow.ts   # Workflow state management & API calls
└── config/
    └── stages.ts        # Stage definitions
```

## Running the Demo

1. Start backend servers: `cd backend && python run_servers.py`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:3000
4. Click "Demo Data" and submit to see the workflow in action
